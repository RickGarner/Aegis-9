import asyncio
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

import httpx
import psutil
from pydantic import BaseModel, Field

from app.config import Settings


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1)


class ProviderFailover(BaseModel):
    occurred: bool = False
    requires_acknowledgement: bool = False
    previous_location: str = ""
    previous_provider: str = ""
    previous_model: str = ""
    active_location: str = ""
    active_provider: str = ""
    active_model: str = ""
    reason: str = ""


class ProviderHealth(BaseModel):
    available: bool
    provider: str = ""
    model: str = ""
    location: str = ""
    status: str = "initializing"
    detail: str | None = None
    recommendation: str | None = None


class ComponentHealth(BaseModel):
    name: str
    available: bool
    configured: bool = False
    detail: str
    models: list[str] = []


class SystemHealth(BaseModel):
    components: list[ComponentHealth]


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderEndpoint:
    location: str
    provider: str
    catalog_url: str
    chat_url: str
    api_key: str | None = None


@dataclass(frozen=True)
class ProviderRoute:
    location: str
    provider: str
    model: str
    chat_url: str
    api_key: str | None = None
    size_bytes: int = 0


@dataclass(frozen=True)
class RoutedChatResult:
    content: str
    route: ProviderRoute
    failover: ProviderFailover


class OpenAICompatibleProvider:
    """Remote-first provider discovery and task-aware runtime routing."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = asyncio.Lock()
        self._candidates: list[ProviderRoute] = []
        self._active: ProviderRoute | None = None
        self._status = "initializing"
        self._detail = "Preparing AI provider discovery."
        self._recommendation: str | None = None
        self._location = ""
        self._ram_bytes = psutil.virtual_memory().total
        self._gpu_name, self._gpu_vram_mb = self._detect_gpu()

    async def discover(self, force: bool = False) -> ProviderHealth:
        async with self._lock:
            if self._candidates and not force:
                return self._health()

            self._candidates = []
            self._active = None
            if not self._settings.provider_discovery_enabled:
                self._status = "scanning_configured"
                self._detail = "Checking the explicitly configured provider."
                self._candidates = await self._scan_configured_provider()
            else:
                self._status = "scanning_remote"
                self._detail = f"Scanning remote AI services on {self._settings.remote_provider_host}."
                self._candidates = await self._scan_location("remote")
                if not self._candidates:
                    self._status = "scanning_local"
                    self._detail = "Remote AI services are unavailable. Scanning providers on this computer."
                    self._candidates = await self._scan_location("local")

            if not self._candidates:
                self._status = "unavailable"
                self._detail = "No usable remote or local chat model was discovered."
                self._recommendation = self._build_recommendation([])
                return self._health()

            self._candidates.sort(key=lambda route: self._score(route, "general"), reverse=True)
            self._active = self._candidates[0]
            self._location = self._active.location
            self._status = "ready"
            self._detail = (
                f"Selected {self._active.location} {self._active.provider} model "
                f"'{self._active.model}' from {len(self._candidates)} compatible route(s)."
            )
            self._recommendation = self._build_recommendation(self._candidates)
            return self._health()

    async def health(self) -> ProviderHealth:
        if self._status == "initializing":
            await self.discover()
        return self._health()

    async def chat(self, messages: Sequence[ChatMessage]) -> RoutedChatResult:
        if not self._candidates:
            await self.discover()
        if not self._candidates:
            raise ProviderError(self._detail)

        task = self._classify_task(messages)
        initial = self._active
        errors: list[str] = []
        result = await self._try_routes(self._ranked_candidates(task), messages, errors)

        if result is None and self._location == "remote":
            self._status = "scanning_local"
            self._detail = "The remote provider stopped responding. Scanning local fallback providers."
            local_candidates = await self._scan_location("local")
            if local_candidates:
                self._candidates = local_candidates
                self._location = "local"
                result = await self._try_routes(self._ranked_candidates(task), messages, errors)

        if result is None and self._location == "local":
            self._status = "scanning_local"
            self._detail = "Refreshing the local provider inventory after a failed request."
            refreshed_candidates = await self._scan_location("local")
            if refreshed_candidates:
                self._candidates = refreshed_candidates
                result = await self._try_routes(self._ranked_candidates(task), messages, errors)

        if result is None:
            self._status = "unavailable"
            self._detail = "All discovered provider routes failed. " + " | ".join(errors)
            raise ProviderError(self._detail)

        content, route = result
        self._active = route
        self._status = "ready"
        self._detail = f"Active route: {route.location} {route.provider} · {route.model}."
        location_changed = initial is not None and initial.location == "remote" and route.location == "local"
        route_changed = initial is not None and initial != route
        failover = ProviderFailover(
            occurred=route_changed,
            requires_acknowledgement=location_changed,
            previous_location=initial.location if initial else "",
            previous_provider=initial.provider if initial else "",
            previous_model=initial.model if initial else "",
            active_location=route.location,
            active_provider=route.provider,
            active_model=route.model,
            reason="The remote route did not complete the request. " + " | ".join(errors) if location_changed else "",
        )
        return RoutedChatResult(content=content, route=route, failover=failover)

    def _health(self) -> ProviderHealth:
        return ProviderHealth(
            available=self._active is not None and self._status == "ready",
            provider=self._active.provider if self._active else "",
            model=self._active.model if self._active else "",
            location=self._active.location if self._active else self._location,
            status=self._status,
            detail=self._detail,
            recommendation=self._recommendation,
        )

    def _endpoints(self, location: str) -> list[ProviderEndpoint]:
        host = self._settings.remote_provider_host if location == "remote" else self._settings.local_provider_host
        return [
            ProviderEndpoint(location, "lmstudio", f"http://{host}:1234/v1/models", f"http://{host}:1234/v1/chat/completions"),
            ProviderEndpoint(location, "ollama", f"http://{host}:11434/api/tags", f"http://{host}:11434/v1/chat/completions"),
            ProviderEndpoint(location, "litellm", f"http://{host}:4000/v1/models", f"http://{host}:4000/v1/chat/completions", self._settings.litellm_api_key),
        ]

    async def _scan_location(self, location: str) -> list[ProviderRoute]:
        results = await asyncio.gather(*(self._probe(endpoint) for endpoint in self._endpoints(location)))
        return [route for routes in results for route in routes if not self._is_embedding(route.model)]

    async def _scan_configured_provider(self) -> list[ProviderRoute]:
        base = str(self._settings.provider_base_url).rstrip("/")
        if not base:
            return []
        endpoint = ProviderEndpoint("configured", self._settings.provider, f"{base}/models", f"{base}/chat/completions", self._settings.litellm_api_key if self._settings.provider == "litellm" else None)
        return await self._probe(endpoint)

    async def _probe(self, endpoint: ProviderEndpoint) -> list[ProviderRoute]:
        try:
            async with httpx.AsyncClient(timeout=self._settings.provider_discovery_timeout_seconds) as client:
                response = await client.get(endpoint.catalog_url, headers=self._headers(endpoint.api_key))
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            return []

        raw_models = payload.get("models", []) if endpoint.provider == "ollama" else payload.get("data", [])
        routes: list[ProviderRoute] = []
        for item in raw_models:
            if not isinstance(item, dict):
                continue
            model = item.get("name") if endpoint.provider == "ollama" else item.get("id")
            if not isinstance(model, str) or not model.strip():
                continue
            routes.append(ProviderRoute(endpoint.location, endpoint.provider, model.strip(), endpoint.chat_url, endpoint.api_key, int(item.get("size") or 0)))
        return routes

    async def _try_routes(self, routes: list[ProviderRoute], messages: Sequence[ChatMessage], errors: list[str]) -> tuple[str, ProviderRoute] | None:
        for route in routes:
            payload = {"model": route.model, "messages": [message.model_dump() for message in messages], "stream": False, "max_tokens": self._settings.max_response_tokens}
            for attempt in range(self._settings.provider_retry_count + 1):
                try:
                    async with httpx.AsyncClient(timeout=self._settings.request_timeout_seconds) as client:
                        response = await client.post(route.chat_url, json=payload, headers=self._headers(route.api_key))
                        response.raise_for_status()
                        content = response.json()["choices"][0]["message"]["content"]
                    if isinstance(content, str) and content.strip():
                        return content.strip(), route
                    raise ValueError("empty response")
                except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
                    if attempt == self._settings.provider_retry_count:
                        errors.append(f"{route.location}/{route.provider}/{route.model}: {str(error) or error.__class__.__name__}")
        return None

    def _ranked_candidates(self, task: str) -> list[ProviderRoute]:
        ranked = sorted(self._candidates, key=lambda route: self._score(route, task), reverse=True)
        best_per_provider: list[ProviderRoute] = []
        selected_providers: set[str] = set()
        for route in ranked:
            if route.provider in selected_providers:
                continue
            best_per_provider.append(route)
            selected_providers.add(route.provider)
        return best_per_provider

    def _score(self, route: ProviderRoute, task: str) -> float:
        name = route.model.lower()
        preference = [item.strip().lower() for item in self._settings.provider_preference.split(",") if item.strip()]
        provider_score = max(0, 8 - (preference.index(route.provider) * 2)) if route.provider in preference else 0
        match = re.search(r"(?<![\d.])(\d+(?:\.\d+)?)b(?![a-z])", name)
        parameter_score = min(float(match.group(1)), 40) if match else 4
        role_score = 0
        role_tokens = {
            "code": (("coder", "code", "devstral"), 60),
            "vision": (("vl", "vision"), 70),
            "reasoning": (("reason", "deepseek-r1", "gpt-oss"), 55),
            "fast": (("fast", "0.8b", "1b", "3b", "4b"), 45),
            "general": (("general", "instruct", "gemma", "llama", "gpt-oss"), 35),
        }
        tokens, bonus = role_tokens[task]
        if any(token in name for token in tokens):
            role_score += bonus
        if task != "vision" and any(token in name for token in ("vl", "vision")):
            role_score -= 15
        if route.model == self._settings.model:
            role_score += 25
        hardware_score = 0
        if route.location == "local" and route.size_bytes > 0:
            if self._gpu_vram_mb > 0 and route.size_bytes <= self._gpu_vram_mb * 1024 * 1024 * 0.90:
                hardware_score += 12
            elif self._gpu_vram_mb > 0 and route.size_bytes <= self._gpu_vram_mb * 1024 * 1024 * 1.75:
                hardware_score += 5
            elif route.size_bytes <= self._ram_bytes * 0.35:
                hardware_score -= 15
            else:
                hardware_score -= 30
        return role_score + parameter_score + provider_score + hardware_score

    @staticmethod
    def _classify_task(messages: Sequence[ChatMessage]) -> str:
        text = messages[-1].content.lower()
        if any(token in text for token in ("image", "screenshot", "picture", "diagram", "what do you see")):
            return "vision"
        if any(token in text for token in ("code", "compile", "debug", "refactor", "function", "class ", ".cs", ".py", "powershell", "repository")):
            return "code"
        if any(token in text for token in ("reason step", "analyze", "root cause", "compare", "investigate", "why does")):
            return "reasoning"
        if len(text) < 80 and any(token in text for token in ("status", "ping", "hello", "good morning", "time", "date")):
            return "fast"
        return "general"

    @staticmethod
    def _headers(api_key: str | None) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}"} if api_key else {}

    @staticmethod
    def _is_embedding(model: str) -> bool:
        lowered = model.lower()
        return "embed" in lowered or "rerank" in lowered

    def _build_recommendation(self, routes: list[ProviderRoute]) -> str:
        names = [route.model.lower() for route in routes]
        missing: list[str] = []
        if not any(any(token in name for token in ("instruct", "general", "gemma", "llama", "gpt-oss")) for name in names):
            missing.append("a general instruction model")
        if not any(any(token in name for token in ("coder", "code", "devstral")) for name in names):
            missing.append("a coding model")
        if not any(any(token in name for token in ("vl", "vision")) for name in names):
            missing.append("a vision-language model")
        if missing:
            return "Recommended download: " + ", ".join(missing) + "."

        ram_gb = round(self._ram_bytes / (1024**3))
        gpu = f"{self._gpu_name}, {self._gpu_vram_mb} MiB" if self._gpu_vram_mb else "GPU unavailable"
        return f"Model coverage is complete for this system ({ram_gb} GB RAM; {gpu})."

    @staticmethod
    def _detect_gpu() -> tuple[str, int]:
        try:
            result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=2, check=False)
            if result.returncode == 0 and result.stdout.strip():
                line = result.stdout.strip().splitlines()[0]
                name, memory = [value.strip() for value in line.rsplit(",", 1)]
                match = re.search(r"(\d+)", memory)
                return name, int(match.group(1)) if match else 0
        except (OSError, subprocess.SubprocessError):
            pass
        return "", 0


async def check_system_health(settings: Settings) -> SystemHealth:
    provider = OpenAICompatibleProvider(settings)

    async def probe(endpoint: ProviderEndpoint) -> ComponentHealth:
        routes = await provider._probe(endpoint)
        models = [route.model for route in routes]
        return ComponentHealth(
            name=f"{endpoint.location.title()} {endpoint.provider.title()}",
            available=bool(models),
            configured=False,
            detail=f"{len(models)} model(s) reported" if models else "Unavailable or no accessible models",
            models=models,
        )

    endpoints = [*provider._endpoints("remote"), *provider._endpoints("local")]
    return SystemHealth(components=list(await asyncio.gather(*(probe(endpoint) for endpoint in endpoints))))
