import asyncio
import json
from pathlib import Path

import pytest

from app.security_control import SecurityControlPolicy
from app.workflow_agent_tools import WorkflowAgentToolError
from app.workflow_extended_tools import EXTENDED_TOOLS, WorkflowExtendedToolContext


def make_context(tmp_path: Path, delegate=None) -> WorkflowExtendedToolContext:
    policy = tmp_path / "security.json"
    policy.write_text(json.dumps({"schema_version": 1, "global_kill_switch": False, "adapters": {"workflow-extended-tools": {"enabled": True, "mode": "read-write", "capabilities": [tool.name for tool in EXTENDED_TOOLS]}}}), encoding="utf-8")
    registry = tmp_path / "catalog.json"
    server = {"id": "local", "displayName": "Local test", "enabled": True, "transport": "loopback-http", "connectivity": "local", "version": "1.0.0", "health": "healthy", "credentialRef": None, "timeoutSeconds": 10, "concurrencyLimit": 1, "audit": True, "endpoint": "http://127.0.0.1:9999/mcp", "tools": [{"name": "docs.search", "description": "local docs", "enabled": True, "risk": "R0", "allowedRoles": ["workflow-implementation"], "allowedTargets": ["localhost"], "outboundFields": ["query"], "approvalRequired": False}]}
    blocked = {**server, "id": "blocked", "displayName": "Blocked", "health": "quarantined", "tools": [{**server["tools"][0], "name": "shell.run", "risk": "D", "approvalRequired": True}]}
    registry.write_text(json.dumps({"schemaVersion": 1, "connectivityProfile": "airgapped", "servers": [server, blocked]}), encoding="utf-8")
    return WorkflowExtendedToolContext(tmp_path / "sandbox", SecurityControlPolicy(policy), registry_path=registry, delegate=delegate)


def invoke(context: WorkflowExtendedToolContext, name: str, arguments: dict) -> dict:
    return json.loads(asyncio.run(context.invoke(name, arguments)))


def test_catalog_has_eleven_closed_schemas() -> None:
    assert len(EXTENDED_TOOLS) == 11
    assert len({tool.name for tool in EXTENDED_TOOLS}) == 11
    assert all(tool.parameters["type"] == "object" and tool.parameters["additionalProperties"] is False for tool in EXTENDED_TOOLS)


def test_registry_discovery_is_approved_healthy_and_non_authorizing(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    result = invoke(context, "getMcpTools", {"query": "docs"})
    assert result["grantsAuthority"] is False
    assert [tool["name"] for tool in result["tools"]] == ["docs.search"]


def test_symbols_diagnostics_and_tool_search_are_bounded(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    (context._root / "Monitor.cs").write_text("public class Monitor {}\n", encoding="utf-8")
    assert invoke(context, "getWorkspaceSymbols", {"query": "Mon"})["symbols"][0]["name"] == "Monitor"
    comparison = invoke(context, "compareDiagnostics", {"before": [{"code": "A"}], "after": [{"code": "B"}]})
    assert comparison["resolved"] == [{"code": "A"}]
    assert invoke(context, "searchAvailableTools", {"query": "MCP"})["grantsAuthority"] is False


def test_patch_relocation_and_recoverable_delete_stay_in_sandbox(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    source = context._root / "one.txt"
    source.write_text("old\n", encoding="utf-8")
    patch = "--- a/one.txt\n+++ b/one.txt\n@@ -1 +1 @@\n-old\n+new\n"
    assert invoke(context, "applyUnifiedPatch", {"patch": patch})["applied"] == ["one.txt"]
    assert source.read_text(encoding="utf-8") == "new\n"
    invoke(context, "renamePath", {"sourcePath": "one.txt", "targetPath": "two.txt"})
    deleted = invoke(context, "deletePath", {"path": "two.txt"})
    assert deleted["recoverable"] is True
    with pytest.raises(WorkflowAgentToolError):
        invoke(context, "movePath", {"sourcePath": "../outside", "targetPath": "x"})


def test_powershell_scaffold_and_typed_command(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    result = invoke(context, "scaffoldWorkspaceProject", {"template": "powershell-console", "projectName": "Health", "targetDirectory": "Health"})
    assert result["production"] is False
    command = invoke(context, "runWorkspaceCommand", {"operation": "powershellSyntax", "path": "Health/Health.ps1"})
    assert command["exitCode"] == 0


def test_delegation_uses_bounded_callback_without_tools_or_authority(tmp_path: Path) -> None:
    async def delegate(role: str, prompt: str) -> dict:
        return {"content": f"{role}:{prompt}", "provider": "dmr", "model": "local"}

    context = make_context(tmp_path, delegate)
    result = invoke(context, "delegateToAgentHostSession", {"role": "review", "prompt": "Check the plan"})
    assert result["result"]["content"] == "review:Check the plan"
    assert result["toolsGranted"] is False
    assert result["productionAuthority"] is False
