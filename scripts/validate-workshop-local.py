"""Probe Workshop with synthetic messages only; never start Aegis monitoring.

Run from the repository root with .venv/Scripts/python.exe. No .env is loaded.
Default: discovery only. --generate also checks chat and qualified tool use.
Qualification evidence uses a temporary directory, removed on exit.
"""
import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import Settings
from app.providers import ChatMessage, ProviderError, WorkshopLocalProvider


async def validate(args):
    with tempfile.TemporaryDirectory(prefix="aegis-workshop-acceptance-") as directory:
        settings = Settings(
            _env_file=None, JARVIS_ENVIRONMENT="home", JARVIS_WORKSHOP_ENABLED=True,
            JARVIS_WORKSHOP_LOCAL_PORT=args.port, JARVIS_WORKSHOP_MODEL=args.model,
            JARVIS_TOOL_QUALIFICATION_STORE_PATH=Path(directory) / "qualification.json",
            JARVIS_REQUEST_TIMEOUT_SECONDS=60,
        )
        provider = WorkshopLocalProvider(settings)
        report = {"health": (await provider.discover()).model_dump(), "synthetic_only": True}
        if not report["health"]["available"]:
            print(json.dumps(report, indent=2))
            return 1
        if args.generate:
            calls = []

            async def execute(name, arguments):
                if name != "read_synthetic_request" or arguments != {}:
                    raise ValueError("Only the synthetic read tool with empty arguments is allowed")
                calls.append(name)
                return json.dumps({"request": "Describe a PowerShell function adding two supplied integers. Do not execute anything."})

            try:
                result = await provider.chat([ChatMessage(role="user", content="Reply with AEGIS_WORKSHOP_LOCAL_OK.")])
                report["chat"] = {"provider": result.route.provider, "model": result.route.model, "content": result.content[:2000]}
                tools = [{"type": "function", "function": {"name": "read_synthetic_request", "description": "Read a harmless synthetic workflow request.",
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}}]
                result = await provider.chat_for_task_with_tools("reasoning", [
                    ChatMessage(role="system", content="Call read_synthetic_request once, then describe a short plan based on its result. Do not execute anything."),
                    ChatMessage(role="user", content="Plan the synthetic workflow.")], tools, execute, max_turns=3)
                report["tools"] = {"provider": result.route.provider, "model": result.route.model, "executed": calls, "content": result.content[:4000]}
                if calls != ["read_synthetic_request"]:
                    raise ProviderError("Expected one synthetic read-tool call before completion")
            except ProviderError as error:
                report["error"] = str(error)
                qualification = Path(directory) / "qualification.json"
                if qualification.exists():
                    report["qualification"] = json.loads(qualification.read_text())
                print(json.dumps(report, indent=2))
                return 1
        print(json.dumps(report, indent=2))
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--port", type=int)
    parser.add_argument("--model")
    raise SystemExit(asyncio.run(validate(parser.parse_args())))
