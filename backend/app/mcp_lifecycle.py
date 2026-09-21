"""Supervised MCP lifecycle for pinned stdio and exact-loopback HTTP servers."""

import hashlib
import base64
import json
import subprocess
import threading
import urllib.request
import uuid
from pathlib import Path
from queue import Empty, Queue
from typing import Any

from app.mcp_registry import McpRegistryError, validate_registry
from app.network_destination_policy import NetworkDestinationPolicy, NetworkPolicyError
from app.local_audit import LocalAuditStore
from app.outbound_dlp import DlpDenied, enforce_outbound
from app.credential_broker import ProtectedCredential, resolve_credential


class McpLifecycleError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise McpLifecycleError("MCP redirects require explicit destination revalidation.")


class McpSession:
    def __init__(self, server: dict[str, Any], network_policy: NetworkDestinationPolicy | None = None, audit: LocalAuditStore | None = None, role: str = "", target: str = "") -> None:
        self.server = server
        self.network_policy = network_policy
        self.process: subprocess.Popen[str] | None = None
        self.failures = 0
        self.quarantined = False
        self._responses: Queue[str] = Queue()
        self.audit = audit
        self.role = role
        self.target = target
        self.credential: ProtectedCredential | None = None
        if server.get("credentialRef"):
            self.credential = resolve_credential(f"Aegis-9/MCP/{server['credentialRef']}")
            if self.credential is None:
                raise McpLifecycleError("The approved MCP credential reference is not configured.")

    def _http_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if not self.credential:
            return headers
        if self.server.get("credentialAuth") == "bearer":
            headers["Authorization"] = f"Bearer {self.credential.password}"
        else:
            value = base64.b64encode(f"{self.credential.username}:{self.credential.password}".encode()).decode()
            headers["Authorization"] = f"Basic {value}"
        return headers

    def start(self) -> dict[str, Any]:
        if self.quarantined:
            raise McpLifecycleError("The MCP server is quarantined.")
        try:
            if self.server["transport"] == "stdio":
                executable = Path(self.server["command"])
                digest = hashlib.sha256(executable.read_bytes()).hexdigest()
                if digest.casefold() != self.server["sha256"].casefold():
                    raise McpLifecycleError("Pinned MCP executable hash does not match.")
                self.process = subprocess.Popen([str(executable), *self.server.get("args", [])], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                threading.Thread(target=self._read_lines, daemon=True).start()
            else:
                if self.server["transport"] not in {"loopback-http", "private-http"} or self.network_policy is None:
                    raise McpLifecycleError("Only stdio and policy-approved loopback/private HTTP lifecycle are enabled.")
                self.network_policy.approve(self.server["endpoint"])
            initialized = self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "aegis", "version": "1"}})
            self._notify("notifications/initialized", {})
            tools = self.request("tools/list", {})
            self.failures = 0
            self._audit("mcp.lifecycle.started", {"serverId": self.server["id"], "transport": self.server["transport"]})
            return {"state": "healthy", "initialize": initialized, "tools": tools}
        except Exception as error:
            self._audit("mcp.lifecycle.failed", {"serverId": self.server["id"], "error": str(error)})
            self._failure()
            self.stop()
            if isinstance(error, McpLifecycleError):
                raise
            raise McpLifecycleError(str(error)) from error

    def _read_lines(self) -> None:
        assert self.process and self.process.stdout
        for line in self.process.stdout:
            self._responses.put(line)

    def request(self, method: str, params: dict[str, Any]) -> Any:
        if self.quarantined or method not in {"initialize", "tools/list", "tools/call", "ping"}:
            raise McpLifecycleError("MCP method is unavailable or not allowed.")
        request_id = str(uuid.uuid4())
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        timeout = self.server["timeoutSeconds"]
        try:
            if self.server["transport"] == "stdio":
                if not self.process or self.process.poll() is not None or not self.process.stdin:
                    raise McpLifecycleError("MCP stdio process is not running.")
                self.process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
                self.process.stdin.flush()
                while True:
                    response = json.loads(self._responses.get(timeout=timeout))
                    if response.get("id") == request_id:
                        break
            else:
                assert self.network_policy
                self.network_policy.approve(self.server["endpoint"])
                request = urllib.request.Request(self.server["endpoint"], data=json.dumps(payload).encode(), headers=self._http_headers(), method="POST")
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
                with opener.open(request, timeout=timeout) as result:
                    response = json.loads(result.read(1_000_001))
            if response.get("error"):
                raise McpLifecycleError(f"MCP error: {response['error']}")
            return response.get("result")
        except (Empty, OSError, ValueError, NetworkPolicyError) as error:
            self._failure()
            raise McpLifecycleError(f"MCP request failed: {error}") from error

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params}, separators=(",", ":"))
        if self.server["transport"] == "stdio":
            if not self.process or self.process.poll() is not None or not self.process.stdin:
                raise McpLifecycleError("MCP stdio process is not running.")
            self.process.stdin.write(payload + "\n")
            self.process.stdin.flush()
            return
        assert self.network_policy
        self.network_policy.approve(self.server["endpoint"])
        request = urllib.request.Request(self.server["endpoint"], data=payload.encode(), headers=self._http_headers(), method="POST")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        with opener.open(request, timeout=self.server["timeoutSeconds"]):
            pass

    def call_tool(self, name: str, arguments: dict[str, Any], *, approved: bool = False) -> Any:
        tool = next((tool for tool in self.server["tools"] if tool["enabled"] and tool["name"] == name), None)
        if tool is None:
            raise McpLifecycleError("MCP tool is not enabled in the approved registry.")
        if self.role not in tool["allowedRoles"] or self.target not in tool["allowedTargets"]:
            self._audit("mcp.tool.denied", {"serverId": self.server["id"], "tool": name, "reason": "role-or-target"})
            raise McpLifecycleError("MCP role or target is not approved.")
        if tool["approvalRequired"] and not approved:
            raise McpLifecycleError("MCP tool requires explicit approval.")
        try:
            safe = enforce_outbound(arguments, tool["outboundFields"], self.server["connectivity"])
        except DlpDenied as error:
            self._audit("mcp.tool.denied", {"serverId": self.server["id"], "tool": name, "reason": str(error)})
            raise McpLifecycleError(str(error)) from error
        self._audit("mcp.tool.started", {"serverId": self.server["id"], "tool": name, "target": self.target})
        result = self.request("tools/call", {"name": name, "arguments": safe})
        self._audit("mcp.tool.completed", {"serverId": self.server["id"], "tool": name, "target": self.target})
        return result

    def _audit(self, event_type: str, fields: dict[str, Any]) -> None:
        if self.audit:
            self.audit.append(event_type, fields)

    def _failure(self) -> None:
        self.failures += 1
        if self.failures >= 3:
            self.quarantined = True

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        self._audit("mcp.lifecycle.stopped", {"serverId": self.server["id"]})


def create_session(catalog: dict[str, Any], server_id: str, network_policy: NetworkDestinationPolicy | None = None, audit: LocalAuditStore | None = None, role: str = "", target: str = "") -> McpSession:
    validate_registry(catalog)
    server = next((item for item in catalog["servers"] if item["id"] == server_id and item["enabled"]), None)
    if server is None:
        raise McpRegistryError("The requested MCP server is not enabled in the approved registry.")
    if server["transport"] not in {"stdio", "loopback-http", "private-http"}:
        raise McpLifecycleError("External MCP lifecycle is not enabled in this phase.")
    if server["transport"] == "private-http" and (catalog["connectivityProfile"] != "local-network" or server["connectivity"] != "organization-controlled"):
        raise McpLifecycleError("Private-LAN MCP requires the local-network profile and organization-controlled classification.")
    return McpSession(server, network_policy, audit, role, target)
