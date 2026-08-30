import types
import unittest

from app.config import Settings
from app.main import ChatResponse
from app.providers import ChatMessage, OpenAICompatibleProvider, ProviderFailover, ProviderRoute


def settings() -> Settings:
    return Settings(
        JARVIS_PROVIDER_BASE_URL="http://127.0.0.1:1234/v1",
        JARVIS_PROVIDER_DISCOVERY_ENABLED=True,
        JARVIS_LITELLM_API_KEY="sk-test",
    )


class ProviderDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_response_exposes_route_and_failover_contract(self) -> None:
        response = ChatResponse(
            model="local-model",
            content="ready",
            provider="ollama",
            location="local",
            failover=ProviderFailover(occurred=True, active_location="local"),
        )

        payload = response.model_dump()

        self.assertEqual("ollama", payload["provider"])
        self.assertEqual("local", payload["location"])
        self.assertTrue(payload["failover"]["occurred"])

    async def test_code_routing_prefers_model_that_better_fits_local_gpu(self) -> None:
        router = OpenAICompatibleProvider(settings())
        router._gpu_vram_mb = 8151
        router._ram_bytes = 64 * 1024**3
        router._candidates = [
            ProviderRoute("local", "ollama", "qwen3-coder:30b", "http://chat", size_bytes=18_556_700_000),
            ProviderRoute("local", "ollama", "qwen2.5-coder:14b", "http://chat", size_bytes=8_988_000_000),
        ]

        ranked = router._ranked_candidates("code")

        self.assertEqual("qwen2.5-coder:14b", ranked[0].model)

    async def test_remote_routes_are_preferred_without_scanning_local(self) -> None:
        router = OpenAICompatibleProvider(settings())
        locations: list[str] = []

        async def scan(_self, location: str):
            locations.append(location)
            return [ProviderRoute(location, "ollama", "gpt-oss:20b", "http://chat")]

        router._scan_location = types.MethodType(scan, router)
        health = await router.discover()

        self.assertTrue(health.available)
        self.assertEqual("remote", health.location)
        self.assertEqual(["remote"], locations)

    async def test_local_routes_are_scanned_when_remote_is_unavailable(self) -> None:
        router = OpenAICompatibleProvider(settings())

        async def scan(_self, location: str):
            if location == "remote":
                return []
            return [ProviderRoute("local", "lmstudio", "gemma-4-e4b-it-qat", "http://chat")]

        router._scan_location = types.MethodType(scan, router)
        health = await router.discover()

        self.assertTrue(health.available)
        self.assertEqual("local", health.location)

    async def test_remote_request_failure_recovers_locally_and_requires_acknowledgement(self) -> None:
        router = OpenAICompatibleProvider(settings())
        remote = ProviderRoute("remote", "lmstudio", "remote-model", "http://remote/chat")
        local = ProviderRoute("local", "ollama", "local-model", "http://local/chat")
        router._candidates = [remote]
        router._active = remote
        router._location = "remote"
        router._status = "ready"

        async def scan(_self, location: str):
            return [local] if location == "local" else [remote]

        async def try_routes(_self, routes, _messages, errors):
            if routes[0].location == "remote":
                errors.append("remote unavailable")
                return None
            return "recovered", routes[0]

        router._scan_location = types.MethodType(scan, router)
        router._try_routes = types.MethodType(try_routes, router)
        result = await router.chat([ChatMessage(role="user", content="hello")])

        self.assertEqual("recovered", result.content)
        self.assertEqual("local", result.route.location)
        self.assertTrue(result.failover.requires_acknowledgement)


if __name__ == "__main__":
    unittest.main()
