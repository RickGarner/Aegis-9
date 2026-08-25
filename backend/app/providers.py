import asyncio
from collections.abc import Sequence

import httpx
from pydantic import BaseModel, Field

from app.config import Settings


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1)


class ProviderHealth(BaseModel):
    available: bool
    provider: str
    model: str
    detail: str | None = None


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


class OpenAICompatibleProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = str(settings.provider_base_url).rstrip("/")

    async def health(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=self._settings.request_timeout_seconds) as client:
                response = await client.get(f"{self._base_url}/models")
                response.raise_for_status()
                models = response.json().get("data", [])
        except (httpx.HTTPError, ValueError) as error:
            return ProviderHealth(
                available=False,
                provider=self._settings.provider,
                model=self._settings.model,
                detail=str(error),
            )

        available_models = {item.get("id") for item in models if isinstance(item, dict)}
        if self._settings.model not in available_models:
            return ProviderHealth(
                available=False,
                provider=self._settings.provider,
                model=self._settings.model,
                detail="Configured model was not returned by the provider.",
            )

        return ProviderHealth(
            available=True,
            provider=self._settings.provider,
            model=self._settings.model,
        )

    async def chat(self, messages: Sequence[ChatMessage]) -> str:
        models = [self._settings.model]
        if self._settings.fallback_model and self._settings.fallback_model != self._settings.model:
            models.append(self._settings.fallback_model)
        errors: list[str] = []
        for model in models:
            payload = {
                "model": model,
                "messages": [message.model_dump() for message in messages],
                "stream": False,
                "max_tokens": self._settings.max_response_tokens,
            }
            try:
                timeout = self._settings.primary_model_timeout_seconds if model == self._settings.model and len(models) > 1 else self._settings.request_timeout_seconds
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{self._base_url}/chat/completions",
                        json=payload,
                    )
                    response.raise_for_status()
                    content = response.json()["choices"][0]["message"]["content"]
                    break
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
                errors.append(f"{model}: {str(error) or error.__class__.__name__}")
        else:
            raise ProviderError("The configured model provider did not return a chat response. " + " | ".join(errors))

        if not isinstance(content, str) or not content.strip():
            raise ProviderError("The configured model provider returned an empty chat response.")
        return content


async def check_system_health(settings: Settings) -> SystemHealth:
    lmstudio_url = settings.provider_base_url if settings.provider == "lmstudio" else settings.lmstudio_base_url
    ollama_url = settings.provider_base_url if settings.provider == "ollama" else settings.ollama_base_url
    litellm_url = settings.provider_base_url if settings.provider == "litellm" else settings.litellm_base_url
    endpoints = [
        ("LM Studio", str(lmstudio_url).rstrip("/"), "/models", settings.provider == "lmstudio"),
        ("Ollama", str(ollama_url).rstrip("/"), "/api/tags", settings.provider == "ollama"),
        ("LiteLLM", str(litellm_url).rstrip("/"), "/models", settings.provider == "litellm"),
    ]

    async def probe(name: str, base_url: str, path: str, configured: bool) -> ComponentHealth:
        try:
            async with httpx.AsyncClient(timeout=min(settings.request_timeout_seconds, 3)) as client:
                response = await client.get(f"{base_url}{path}")
                if name == "LiteLLM" and response.status_code >= 500:
                    liveliness = await client.get(f"{base_url.rsplit('/v1', 1)[0]}/health/liveliness")
                    liveliness.raise_for_status()
                    return ComponentHealth(name=name, available=True, configured=configured, detail=f"Service is alive; model catalog returned HTTP {response.status_code}")
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            detail = str(error) or error.__class__.__name__.replace("ConnectTimeout", "connection timeout").replace("ConnectError", "connection failed")
            return ComponentHealth(name=name, available=False, configured=configured, detail=detail)

        if path == "/api/tags":
            models = [item.get("name", "") for item in payload.get("models", []) if isinstance(item, dict) and item.get("name")]
        else:
            models = [item.get("id", "") for item in payload.get("data", []) if isinstance(item, dict) and item.get("id")]
        model_detail = f"{len(models)} model(s) reported"
        if configured and settings.model not in models:
            model_detail += f"; configured model '{settings.model}' not found"
        return ComponentHealth(name=name, available=True, configured=configured, detail=model_detail, models=models)

    return SystemHealth(components=list(await asyncio.gather(*(probe(*endpoint) for endpoint in endpoints))))
