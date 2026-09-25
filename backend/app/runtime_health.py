from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path
from typing import Literal

import httpx
import psutil
from pydantic import BaseModel, Field

from app.config import Settings
from app.providers import OpenAICompatibleProvider


RuntimeStatus = Literal["healthy", "warning", "error", "unavailable"]


class RuntimeHealthComponent(BaseModel):
    monitor_id: str
    display_name: str
    status: RuntimeStatus
    detail: str
    adapter_id: str
    resource_type: str
    metrics: dict[str, str | int | float | bool] = Field(default_factory=dict)


async def collect_runtime_health(settings: Settings) -> list[RuntimeHealthComponent]:
    return [
        _backend_health(settings),
        await _provider_health(settings),
        await _voice_health(settings),
        _dependency_health(settings),
    ]


def _backend_health(settings: Settings) -> RuntimeHealthComponent:
    process = psutil.Process(os.getpid())
    database_ready = settings.database_path.is_file() and os.access(settings.database_path, os.R_OK | os.W_OK)
    status: RuntimeStatus = "healthy" if database_ready else "error"
    detail = "Backend process and writable application database are available." if database_ready else "Backend is running, but the application database is missing or not writable."
    return RuntimeHealthComponent(
        monitor_id="aegis-backend",
        display_name="A.E.G.I.S. Backend",
        status=status,
        detail=detail,
        adapter_id="in-process-runtime",
        resource_type="application-runtime",
        metrics={
            "processId": process.pid,
            "memoryMb": round(process.memory_info().rss / (1024 * 1024), 1),
            "python": sys.version.split()[0],
            "databaseReady": database_ready,
        },
    )


async def _provider_health(settings: Settings) -> RuntimeHealthComponent:
    health = await OpenAICompatibleProvider(settings).health()
    status: RuntimeStatus = "healthy" if health.available and health.status == "ready" else "unavailable"
    detail = health.detail or (f"Active route: {health.location} {health.provider} · {health.model}." if health.available else "No approved AI provider route is available.")
    return RuntimeHealthComponent(
        monitor_id="aegis-provider",
        display_name="AI Provider Route",
        status=status,
        detail=detail,
        adapter_id="adaptive-provider-router",
        resource_type="ai-provider",
        metrics={"provider": health.provider, "model": health.model, "location": health.location, "routeStatus": health.status},
    )


async def _voice_health(settings: Settings) -> RuntimeHealthComponent:
    whisper_available = importlib.util.find_spec("faster_whisper") is not None
    kokoro_available = False
    kokoro_detail = "Kokoro did not return a trusted health response."
    try:
        async with httpx.AsyncClient(timeout=settings.runtime_health_timeout_seconds) as client:
            response = await client.get(f"{settings.voice_runtime_url.rstrip('/')}/health")
            response.raise_for_status()
            payload = response.json()
            kokoro_available = payload.get("available") is True
            kokoro_detail = "Kokoro model and voice assets are available." if kokoro_available else "Kokoro responded, but its model or voice assets are unavailable."
    except (httpx.HTTPError, ValueError, TypeError):
        pass
    status: RuntimeStatus = "healthy" if whisper_available and kokoro_available else "warning" if whisper_available or kokoro_available else "unavailable"
    return RuntimeHealthComponent(
        monitor_id="aegis-voice",
        display_name="Voice Runtime",
        status=status,
        detail=f"Faster-Whisper {'available' if whisper_available else 'unavailable'}; {kokoro_detail}",
        adapter_id="local-voice-runtime",
        resource_type="voice-runtime",
        metrics={"whisperAvailable": whisper_available, "kokoroAvailable": kokoro_available},
    )


def _dependency_health(settings: Settings) -> RuntimeHealthComponent:
    root = Path(__file__).resolve().parents[2]
    required_files = [settings.security_control_policy_path, root / "config" / "mcp" / "catalog.json"]
    missing = [path.name for path in required_files if not path.is_file()]
    dotnet_available = shutil.which("dotnet") is not None
    healthy = not missing and dotnet_available
    status: RuntimeStatus = "healthy" if healthy else "warning"
    parts = ["Required policy/catalog files are present." if not missing else f"Missing required files: {', '.join(missing)}."]
    parts.append(".NET runtime is available." if dotnet_available else ".NET runtime was not found on PATH.")
    return RuntimeHealthComponent(
        monitor_id="aegis-dependencies",
        display_name="Runtime Dependencies",
        status=status,
        detail=" ".join(parts),
        adapter_id="local-dependency-check",
        resource_type="runtime-dependency",
        metrics={"dotnetAvailable": dotnet_available, "requiredFilesPresent": not missing},
    )
