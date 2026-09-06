import asyncio
import json

from app.config import Settings
from app.providers import OpenAICompatibleProvider, ProviderRoute


async def main() -> int:
    settings = Settings()
    provider = OpenAICompatibleProvider(settings)
    routes = [
        ProviderRoute("local", "dmr", "docker.io/ai/qwen3:8b-q4_K_M", "http://127.0.0.1:12434/engines/v1/chat/completions"),
        ProviderRoute("local", "ollama", "llama3.1:8b", "http://127.0.0.1:11434/v1/chat/completions"),
    ]
    passed = True
    for route in routes:
        report = await provider._probe_tool_route(route)
        print(json.dumps({
            "provider": report.provider,
            "model": report.model,
            "qualified": report.qualified,
            "nativeStructuredCalls": report.native_structured_calls,
            "validArguments": report.valid_arguments,
            "sequentialCalls": report.sequential_calls,
            "toolResultContinuation": report.tool_result_continuation,
            "validUntil": report.valid_until.isoformat(),
            "failureReason": report.failure_reason,
        }))
        passed = passed and report.qualified
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
