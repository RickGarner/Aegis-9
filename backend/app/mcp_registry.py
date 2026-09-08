"""Fail-closed local MCP registry validation and discovery (no transport I/O)."""

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from app.policy_integrity import PolicyIntegrityError, require_policy


class McpRegistryError(ValueError):
    pass


PROFILES = {
    "airgapped": {"connectivity": {"local"}, "transports": {"stdio", "loopback-http"}},
    "local-network": {"connectivity": {"local", "organization-controlled"}, "transports": {"stdio", "loopback-http", "private-http"}},
    "online": {"connectivity": {"local", "organization-controlled", "external-zero-protected-data"}, "transports": {"stdio", "loopback-http", "private-http", "https"}},
}
RISKS = {"R0", "R1", "W1", "W2", "D"}
HEALTH = {"healthy", "degraded", "unavailable", "disabled", "quarantined", "version-mismatch", "authentication-failure"}
ID = re.compile(r"^[a-z][a-z0-9.-]{0,127}$")
SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")


def load_registry(path: Path) -> dict[str, Any]:
    try:
        require_policy(path, required=os.environ.get("JARVIS_REQUIRE_SIGNED_POLICIES", "").casefold() in {"1", "true", "yes"}, public_key_path=Path(os.environ.get("JARVIS_POLICY_PUBLIC_KEY_PATH", "config/policy-signing-public.pem")))
    except PolicyIntegrityError as error:
        raise McpRegistryError(str(error)) from error
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise McpRegistryError(f"The local MCP registry is unavailable: {error}") from error
    validate_registry(value)
    return value


def validate_registry(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != {"schemaVersion", "connectivityProfile", "servers"}:
        raise McpRegistryError("The MCP registry must contain only schemaVersion, connectivityProfile, and servers.")
    profile = value.get("connectivityProfile")
    servers = value.get("servers")
    if value.get("schemaVersion") != 1 or profile not in PROFILES or not isinstance(servers, list) or len(servers) > 100:
        raise McpRegistryError("The local MCP registry does not match schema version 1.")
    seen: set[str] = set()
    for server in servers:
        _validate_server(server, profile)
        if server["id"] in seen:
            raise McpRegistryError(f"Duplicate MCP server id: {server['id']}")
        seen.add(server["id"])


def _validate_server(server: Any, profile: str) -> None:
    required = {"id", "displayName", "enabled", "transport", "connectivity", "version", "health", "credentialRef", "timeoutSeconds", "concurrencyLimit", "audit", "tools"}
    optional = {"command", "args", "endpoint", "sha256", "allowedRoles", "allowedTargets", "owner", "retentionPolicy"}
    if not isinstance(server, dict) or not required <= set(server) or not set(server) <= required | optional:
        raise McpRegistryError("An MCP server entry has missing or unknown fields.")
    if not isinstance(server["id"], str) or not ID.fullmatch(server["id"]):
        raise McpRegistryError("MCP server id is invalid.")
    if not isinstance(server["displayName"], str) or not 1 <= len(server["displayName"]) <= 200 or not isinstance(server["enabled"], bool):
        raise McpRegistryError("MCP displayName/enabled is invalid.")
    if server["transport"] not in PROFILES[profile]["transports"] or server["connectivity"] not in PROFILES[profile]["connectivity"]:
        raise McpRegistryError("MCP transport or connectivity is not allowed by the active profile.")
    if server["health"] not in HEALTH or not isinstance(server["version"], str) or not server["version"]:
        raise McpRegistryError("MCP version or health is invalid.")
    if server["credentialRef"] is not None and (not isinstance(server["credentialRef"], str) or not ID.fullmatch(server["credentialRef"])):
        raise McpRegistryError("credentialRef must be null or a non-secret identifier.")
    if not isinstance(server["timeoutSeconds"], int) or not 1 <= server["timeoutSeconds"] <= 300 or not isinstance(server["concurrencyLimit"], int) or not 1 <= server["concurrencyLimit"] <= 32 or not isinstance(server["audit"], bool):
        raise McpRegistryError("MCP timeout, concurrency, or audit setting is invalid.")
    if server["transport"] == "stdio":
        if not isinstance(server.get("command"), str) or not Path(server["command"]).is_absolute() or not SHA256.fullmatch(str(server.get("sha256", ""))):
            raise McpRegistryError("stdio servers require an absolute command and pinned SHA-256.")
        if not isinstance(server.get("args", []), list) or any(not isinstance(item, str) for item in server.get("args", [])):
            raise McpRegistryError("stdio args must be a string array.")
    else:
        endpoint = urlparse(str(server.get("endpoint", "")))
        if endpoint.scheme not in {"http", "https"} or not endpoint.hostname or endpoint.username or endpoint.password:
            raise McpRegistryError("HTTP MCP servers require a credential-free endpoint URL.")
        if server["transport"] == "https" and endpoint.scheme != "https":
            raise McpRegistryError("External MCP endpoints require HTTPS.")
        if server["transport"] == "loopback-http" and endpoint.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise McpRegistryError("Loopback MCP endpoints must use an exact loopback host.")
    tools = server["tools"]
    if not isinstance(tools, list) or len(tools) > 500:
        raise McpRegistryError("MCP tools must be a bounded array.")
    tool_names: set[str] = set()
    for tool in tools:
        _validate_tool(tool)
        if tool["name"] in tool_names:
            raise McpRegistryError(f"Duplicate MCP tool name in {server['id']}: {tool['name']}")
        tool_names.add(tool["name"])


def _validate_tool(tool: Any) -> None:
    required = {"name", "description", "enabled", "risk", "allowedRoles", "allowedTargets", "outboundFields", "approvalRequired"}
    if not isinstance(tool, dict) or set(tool) != required or not isinstance(tool["name"], str) or not ID.fullmatch(tool["name"]):
        raise McpRegistryError("An MCP tool entry is invalid or has unknown fields.")
    if not isinstance(tool["description"], str) or len(tool["description"]) > 1000 or not isinstance(tool["enabled"], bool) or tool["risk"] not in RISKS:
        raise McpRegistryError("MCP tool description, enabled, or risk is invalid.")
    for field in ("allowedRoles", "allowedTargets", "outboundFields"):
        if not isinstance(tool[field], list) or len(tool[field]) > 100 or any(not isinstance(item, str) or len(item) > 200 for item in tool[field]):
            raise McpRegistryError(f"MCP tool {field} must be a bounded string array.")
    if not isinstance(tool["approvalRequired"], bool) or (tool["risk"] in {"W1", "W2", "D"} and not tool["approvalRequired"]):
        raise McpRegistryError("Write/destructive MCP tools must require approval.")


def discover_tools(value: dict[str, Any], query: str = "") -> list[dict[str, Any]]:
    validate_registry(value)
    found = []
    for server in value["servers"]:
        if not server["enabled"] or server["health"] != "healthy":
            continue
        for tool in server["tools"]:
            if tool["enabled"] and (not query or query.casefold() in f"{tool['name']} {tool['description']}".casefold()):
                found.append({"serverId": server["id"], "name": tool["name"], "description": tool["description"], "risk": tool["risk"], "approvalRequired": tool["approvalRequired"], "connectivity": server["connectivity"], "discoveryOnly": True})
    return found[:200]
