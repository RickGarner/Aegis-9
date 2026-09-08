import hashlib
import json
import sys
from pathlib import Path

import pytest

from app.mcp_lifecycle import McpLifecycleError, create_session
from app.network_destination_policy import NetworkDestinationPolicy


def catalog(script: Path) -> dict:
    executable = Path(sys.executable)
    tool = {"name": "echo.run", "description": "echo", "enabled": True, "risk": "R0", "allowedRoles": ["test"], "allowedTargets": ["local"], "outboundFields": ["value"], "approvalRequired": False}
    server = {"id": "local.echo", "displayName": "Echo", "enabled": True, "transport": "stdio", "connectivity": "local", "version": "1", "health": "healthy", "credentialRef": None, "timeoutSeconds": 3, "concurrencyLimit": 1, "audit": True, "command": str(executable), "args": ["-u", str(script)], "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(), "tools": [tool]}
    return {"schemaVersion": 1, "connectivityProfile": "airgapped", "servers": [server]}


def test_stdio_initializes_lists_calls_and_stops(tmp_path: Path) -> None:
    script = tmp_path / "fake.py"
    script.write_text("import json,sys\nfor line in sys.stdin:\n r=json.loads(line); m=r['method']; result={'protocolVersion':'2025-06-18'} if m=='initialize' else ({'tools':[{'name':'echo.run'}]} if m=='tools/list' else {'content':[{'type':'text','text':'ok'}]}); print(json.dumps({'jsonrpc':'2.0','id':r['id'],'result':result}),flush=True) if 'id' in r else None\n", encoding="utf-8")
    session = create_session(catalog(script), "local.echo", role="test", target="local")
    started = session.start()
    assert started["state"] == "healthy"
    assert session.call_tool("echo.run", {"value": "safe"})["content"][0]["text"] == "ok"
    with pytest.raises(McpLifecycleError):
        session.call_tool("unapproved", {})
    session.stop()


def test_rejects_unpinned_executable(tmp_path: Path) -> None:
    script = tmp_path / "fake.py"
    script.write_text("", encoding="utf-8")
    value = catalog(script)
    value["servers"][0]["sha256"] = "0" * 64
    session = create_session(value, "local.echo", role="test", target="local")
    with pytest.raises(McpLifecycleError, match="hash"):
        session.start()


def test_private_lan_requires_profile_policy_role_target_and_dlp(monkeypatch) -> None:
    tool = {"name": "status.get", "description": "status", "enabled": True, "risk": "R1", "allowedRoles": ["operator"], "allowedTargets": ["service-a"], "outboundFields": ["query"], "approvalRequired": False}
    server = {"id": "internal.status", "displayName": "Internal", "enabled": True, "transport": "private-http", "connectivity": "organization-controlled", "version": "1", "health": "healthy", "credentialRef": "internal.read", "timeoutSeconds": 3, "concurrencyLimit": 1, "audit": True, "endpoint": "https://internal.test:8443/mcp", "tools": [tool]}
    value = {"schemaVersion": 1, "connectivityProfile": "local-network", "servers": [server]}
    policy = NetworkDestinationPolicy(profile="local-network", allowed_hosts={"internal.test": {8443}}, resolver=lambda _: ["10.1.2.3"], allow_proxy=True)
    session = create_session(value, "internal.status", policy, role="operator", target="service-a")
    monkeypatch.setattr(session, "request", lambda method, params: params)
    assert session.call_tool("status.get", {"query": "health"})["arguments"] == {"query": "health"}
    with pytest.raises(McpLifecycleError, match="absent"):
        session.call_tool("status.get", {"extra": "blocked"})
