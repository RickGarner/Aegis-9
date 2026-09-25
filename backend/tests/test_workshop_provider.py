"""Workshop routing contract; no live models, production state, or network."""
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from pydantic import ValidationError

from app.config import Settings
from app.main import app, get_workshop_provider
from app.providers import ChatMessage, OpenAICompatibleProvider, ProviderError, ProviderHealth, WorkshopLocalProvider


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def workshop(tmp_path, monkeypatch):
    monkeypatch.setattr(OpenAICompatibleProvider, "_detect_gpu", staticmethod(lambda: ("", 0)))
    settings = Settings(
        _env_file=None, JARVIS_ENVIRONMENT="home", JARVIS_WORKSHOP_ENABLED=True,
        JARVIS_WORKSHOP_LOCAL_PORT=44245, JARVIS_WORKSHOP_MODEL="local-test-model",
        JARVIS_TOOL_QUALIFICATION_STORE_PATH=tmp_path / "qualification.json",
        JARVIS_PROVIDER_RETRY_COUNT=0,
    )
    return WorkshopLocalProvider(settings)


def mock_http(monkeypatch, handler):
    client_class = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr("app.providers.httpx.AsyncClient", lambda **kwargs: client_class(transport=transport, **kwargs))


def answer(content=None, calls=None):
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": content, "tool_calls": calls or []}}]})


def call(name, arguments, identifier="call-1"):
    return {"id": identifier, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}


@pytest.mark.anyio
async def test_configured_endpoint_health_and_plain_chat(workshop, monkeypatch):
    requests = []

    def handler(request):
        requests.append(str(request.url))
        assert request.url.host == "127.0.0.1" and request.url.port == 44245
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "local-test-model"}]})
        assert json.loads(request.content)["model"] == "local-test-model"
        return answer("Generated test plans")

    mock_http(monkeypatch, handler)
    health = await workshop.discover()
    assert isinstance(health, ProviderHealth) and health.available
    result = await workshop.chat_for_task("reasoning", [ChatMessage(role="user", content="Test plan")])
    assert result.route.provider == "workshop"
    assert result.content == "Generated test plans"
    assert len(requests) == 2


@pytest.mark.anyio
@pytest.mark.parametrize("task", ["reasoning", "code"])
async def test_native_tool_qualification_and_workflow_continuation(workshop, monkeypatch, task):
    executions = []
    requests = []

    def handler(request):
        assert request.url.host == "127.0.0.1" and request.url.port == 44245
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "local-test-model"}]})
        payload = json.loads(request.content)
        requests.append(payload)
        results = [message for message in payload["messages"] if message["role"] == "tool"]
        name = payload["tools"][0]["function"]["name"]
        if name == "aegis_tool_capability_probe":
            if len(results) < 2:
                return answer(calls=[call(name, {"step": len(results) + 1}, f"probe-{len(results)}")])
            return answer("AEGIS_TOOL_PROBE_COMPLETE")
        if not results:
            return answer(calls=[call("get_workflow_request", {})])
        assert json.loads(results[-1]["content"])["description"] == "Synthetic workflow"
        return answer("Generated workflow content")

    mock_http(monkeypatch, handler)

    async def execute(name, arguments):
        executions.append((name, arguments))
        return json.dumps({"description": "Synthetic workflow"})

    tools = [{"type": "function", "function": {"name": "get_workflow_request", "parameters": {"type": "object"}}}]
    result = await workshop.chat_for_task_with_tools(task, [ChatMessage(role="user", content="Create workflow")], tools, execute)
    assert result.route.provider == "workshop"
    assert result.content == "Generated workflow content"
    assert executions == [("get_workflow_request", {})]
    assert len(requests) == 5  # Two probe calls, probe completion, workflow call, completion.


@pytest.mark.anyio
async def test_unqualified_model_never_receives_workflow_tools(workshop, monkeypatch):
    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "local-test-model"}]})
        payload = json.loads(request.content)
        assert payload["tools"][0]["function"]["name"] == "aegis_tool_capability_probe"
        return answer("I cannot call tools")

    mock_http(monkeypatch, handler)

    async def execute(*args):
        pytest.fail("An unqualified model must not execute workflow tools")

    with pytest.raises(ProviderError, match="native tool call"):
        await workshop.chat_for_task_with_tools("code", [ChatMessage(role="user", content="Implement")],
            [{"type": "function", "function": {"name": "writeFile"}}], execute)


@pytest.mark.anyio
@pytest.mark.parametrize("failure", ["http", "empty", "malformed"])
async def test_chat_failure_never_falls_back_to_other_providers(workshop, monkeypatch, failure):
    def handler(request):
        assert request.url.port == 44245
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "local-test-model"}]})
        if failure == "http":
            return httpx.Response(503)
        return answer("") if failure == "empty" else httpx.Response(200, json={"unexpected": True})

    mock_http(monkeypatch, handler)
    with pytest.raises(ProviderError):
        await workshop.chat([ChatMessage(role="user", content="Hello")])


@pytest.mark.anyio
async def test_ambiguous_models_require_selection(workshop, monkeypatch):
    workshop._settings.workshop_model = None
    mock_http(monkeypatch, lambda _: httpx.Response(200, json={"data": [{"id": "a"}, {"id": "b"}]}))
    health = await workshop.discover()
    assert not health.available and "Multiple" in health.detail
    assert workshop._candidates == []


@pytest.mark.anyio
@pytest.mark.parametrize("payload", [{"data": []}, {"data": [{"id": "wrong-model"}]}, {"data": "invalid"}, []])
async def test_missing_or_invalid_model_catalog(workshop, monkeypatch, payload):
    mock_http(monkeypatch, lambda _: httpx.Response(200, json=payload))
    assert not (await workshop.discover()).available


@pytest.mark.anyio
async def test_missing_workshop_tool_route_reports_discovery_failure(workshop, monkeypatch):
    mock_http(monkeypatch, lambda _: httpx.Response(503))
    with pytest.raises(ProviderError, match="No usable Workshop model"):
        await workshop.chat_for_task_with_tools("reasoning", [ChatMessage(role="user", content="Plan")],
            [{"type": "function", "function": {"name": "read"}}], None)


def test_discovery_ignores_unrelated_llama_servers(monkeypatch):
    def process(pid, parent):
        return SimpleNamespace(pid=pid, info={"name": "llama-server.exe"},
                               parents=lambda: [SimpleNamespace(name=lambda: parent)])
    monkeypatch.setattr("app.providers.psutil.process_iter", lambda _: [process(1, "other.exe"), process(2, "workshop-desktop.exe")])
    def connection(pid, port, status="LISTEN"):
        return SimpleNamespace(pid=pid, status=status, laddr=SimpleNamespace(ip="127.0.0.1", port=port))
    monkeypatch.setattr("app.providers.psutil.net_connections", lambda **_: [connection(1, 1111), connection(2, 2222), connection(2, 3333, "ESTABLISHED")])
    assert WorkshopLocalProvider._workshop_ports() == [2222]


def test_workshop_jobs_cannot_use_generic_provider_when_disabled():
    with pytest.raises(HTTPException) as error:
        get_workshop_provider(Settings(_env_file=None, JARVIS_ENVIRONMENT="home", JARVIS_WORKSHOP_ENABLED=False))
    assert error.value.status_code == 503
    for path in ("/api/workflows/{workflow_id}/workshop-jobs", "/api/workshop-jobs/{job_id}/retry"):
        route = next(route for route in app.routes if isinstance(route, APIRoute) and route.path == path and "POST" in route.methods)
        assert get_workshop_provider in {dependency.call for dependency in route.dependant.dependencies}


@pytest.mark.parametrize("field,value", [("JARVIS_WORKSHOP_LOCAL_HOST", "example.com"), ("JARVIS_WORKSHOP_LOCAL_PORT", 0), ("JARVIS_WORKSHOP_LOCAL_PORT", 65536)])
def test_endpoint_configuration_is_loopback_and_valid(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, JARVIS_ENVIRONMENT="home", **{field: value})
