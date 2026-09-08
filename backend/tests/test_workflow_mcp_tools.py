import json
import asyncio

import pytest

from app.security_control import SecurityControlPolicy
from app.workflow_agent_tools import WorkflowAgentToolError
from app.workflow_mcp_tools import WorkflowMcpToolContext


def test_workflow_mcp_bridge_is_registered_and_empty_registry_fails_closed(tmp_path) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"schema_version": 1, "global_kill_switch": False, "adapters": {"workflow-mcp-tools": {"enabled": True, "mode": "read-only", "capabilities": ["callMcpTool"]}}}), encoding="utf-8")
    registry = tmp_path / "catalog.json"
    registry.write_text(json.dumps({"schemaVersion": 1, "connectivityProfile": "airgapped", "servers": []}), encoding="utf-8")
    context = WorkflowMcpToolContext(SecurityControlPolicy(policy), registry, tmp_path / "audit.jsonl")
    assert context.definitions[0]["function"]["name"] == "callMcpTool"
    with pytest.raises(WorkflowAgentToolError, match="unavailable"):
        asyncio.run(context.invoke("callMcpTool", {"serverId": "local.none", "toolName": "none", "arguments": {}}))
