"""Provider-neutral governed MCP bridge for approved workflow implementation."""

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.local_audit import LocalAuditStore
from app.mcp_lifecycle import McpLifecycleError, create_session
from app.mcp_registry import load_registry
from app.network_destination_policy import NetworkDestinationPolicy
from app.security_control import SecurityControlError, SecurityControlPolicy
from app.workflow_agent_tools import WorkflowAgentTool, WorkflowAgentToolError
from app.resource_governance import ResourceBudgetError, ResourceGovernor


MCP_WORKFLOW_TOOLS = (
    WorkflowAgentTool("callMcpTool", "Call one enabled read-only tool from the approved local MCP registry. Role, target, DLP, destination, audit, and approval policy remain authoritative.", {"type": "object", "additionalProperties": False, "properties": {"serverId": {"type": "string", "maxLength": 128}, "toolName": {"type": "string", "maxLength": 128}, "arguments": {"type": "object"}}, "required": ["serverId", "toolName", "arguments"]}),
)


class WorkflowMcpToolContext:
    def __init__(self, security: SecurityControlPolicy, registry_path: Path, audit_path: Path, governor: ResourceGovernor | None = None) -> None:
        self._security = security
        self._registry_path = registry_path
        self._audit = LocalAuditStore(audit_path)
        self._governor = governor or ResourceGovernor(max_memory_mb=4096, max_cpu_percent=95, max_children=12)

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [tool.as_openai_tool() for tool in MCP_WORKFLOW_TOOLS]

    async def invoke(self, name: str, arguments: dict[str, Any]) -> str:
        if name != "callMcpTool":
            raise WorkflowAgentToolError(f"Unknown MCP workflow tool '{name}'.")
        try: self._governor.check()
        except ResourceBudgetError as error: raise WorkflowAgentToolError(str(error)) from error
        try:
            self._security.require("workflow-mcp-tools", name, mutating=False)
        except SecurityControlError as error:
            raise WorkflowAgentToolError(str(error)) from error
        catalog = load_registry(self._registry_path)
        server_id, tool_name = arguments.get("serverId"), arguments.get("toolName")
        payload = arguments.get("arguments")
        if not isinstance(server_id, str) or not isinstance(tool_name, str) or not isinstance(payload, dict):
            raise WorkflowAgentToolError("MCP serverId, toolName, and object arguments are required.")
        server = next((item for item in catalog["servers"] if item["id"] == server_id and item["enabled"]), None)
        if server is None:
            raise WorkflowAgentToolError("The MCP server is unavailable.")
        tool = next((item for item in server["tools"] if item["name"] == tool_name and item["enabled"]), None)
        if tool is None or tool["approvalRequired"] or tool["risk"] not in {"R0", "R1"}:
            raise WorkflowAgentToolError("Only enabled read-only MCP tools without an outstanding per-call approval may run in workflow creation.")
        allowed_hosts: dict[str, set[int]] = {}
        if server.get("endpoint"):
            endpoint = urlparse(server["endpoint"])
            allowed_hosts[endpoint.hostname or ""] = {endpoint.port or (443 if endpoint.scheme == "https" else 80)}
        policy = NetworkDestinationPolicy(profile=catalog["connectivityProfile"], allowed_hosts=allowed_hosts)
        session = create_session(catalog, server_id, policy, self._audit, "workflow-implementation", "aegis-9")
        try:
            session.start()
            return json.dumps(session.call_tool(tool_name, payload), separators=(",", ":"))[:50_000]
        except McpLifecycleError as error:
            raise WorkflowAgentToolError(str(error)) from error
        finally:
            session.stop()
