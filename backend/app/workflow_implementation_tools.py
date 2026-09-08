"""Bounded, non-production tools for an approved workflow implementation revision."""

import hashlib
import json
import re
import subprocess
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.security_control import SecurityControlError, SecurityControlPolicy
from app.storage import JarvisStore, Workflow
from app.workflow_agent_tools import WorkflowAgentTool, WorkflowAgentToolContext, WorkflowAgentToolError
from app.workflow_sandbox_files import SANDBOX_FILE_TOOLS, WorkflowSandboxFileToolContext
from app.workflow_repository_tools import REPOSITORY_TOOLS, WorkflowRepositoryToolContext
from app.workflow_intelligence_tools import INTELLIGENCE_TOOLS, WorkflowIntelligenceToolContext
from app.workflow_extended_tools import EXTENDED_TOOLS, WorkflowExtendedToolContext
from app.workflow_mcp_tools import MCP_WORKFLOW_TOOLS, WorkflowMcpToolContext
from app.resource_governance import ResourceBudgetError, ResourceGovernor


IMPLEMENTATION_TOOLS = (
    WorkflowAgentTool("listDirectory", "List a bounded directory inside this workflow revision's non-production sandbox.", {"type": "object", "additionalProperties": False, "properties": {"path": {"type": "string"}, "maxDepth": {"type": "integer", "minimum": 1, "maximum": 3}, "maxEntries": {"type": "integer", "minimum": 1, "maximum": 500}}, "required": ["path"]}),
    WorkflowAgentTool("startTerminalSession", "Start one typed validation operation in the workflow sandbox. Arbitrary shell commands are not accepted.", {"type": "object", "additionalProperties": False, "properties": {"operation": {"type": "string", "enum": ["powershellSyntax", "dotnetBuild", "dotnetTest"]}, "path": {"type": "string"}, "timeoutSeconds": {"type": "integer", "minimum": 5, "maximum": 300}}, "required": ["operation", "path"]}),
    WorkflowAgentTool("getTerminalOutput", "Read bounded retained output from a workflow-sandbox validation session without rerunning it.", {"type": "object", "additionalProperties": False, "properties": {"sessionId": {"type": "string"}, "offset": {"type": "integer", "minimum": 0}, "maxChars": {"type": "integer", "minimum": 500, "maximum": 50000}}, "required": ["sessionId"]}),
    WorkflowAgentTool("cancelTerminalSession", "Cancel one running workflow-sandbox validation session by exact ID.", {"type": "object", "additionalProperties": False, "properties": {"sessionId": {"type": "string"}}, "required": ["sessionId"]}),
    WorkflowAgentTool("getStructuredFailures", "Extract bounded compiler and test failures from retained workflow-sandbox output.", {"type": "object", "additionalProperties": False, "properties": {"sessionId": {"type": "string"}, "maxResults": {"type": "integer", "minimum": 1, "maximum": 200}}, "required": ["sessionId"]}),
    WorkflowAgentTool("discoverTests", "Discover bounded PowerShell and .NET test artifacts in the workflow sandbox.", {"type": "object", "additionalProperties": False, "properties": {"maxResults": {"type": "integer", "minimum": 1, "maximum": 200}}}),
    WorkflowAgentTool("buildProjects", "Start a typed .NET build session for a sandbox project or solution.", {"type": "object", "additionalProperties": False, "properties": {"path": {"type": "string"}, "timeoutSeconds": {"type": "integer", "minimum": 5, "maximum": 300}}, "required": ["path"]}),
    WorkflowAgentTool("runTargetedTests", "Start a typed .NET test session for a sandbox project or solution.", {"type": "object", "additionalProperties": False, "properties": {"path": {"type": "string"}, "timeoutSeconds": {"type": "integer", "minimum": 5, "maximum": 300}}, "required": ["path"]}),
    WorkflowAgentTool("runFormatter", "Check .NET formatting without changing sandbox files.", {"type": "object", "additionalProperties": False, "properties": {"path": {"type": "string"}, "timeoutSeconds": {"type": "integer", "minimum": 5, "maximum": 300}}, "required": ["path"]}),
    WorkflowAgentTool("runLinter", "Run a typed PowerShell or .NET analyzer against a sandbox artifact.", {"type": "object", "additionalProperties": False, "properties": {"path": {"type": "string"}, "timeoutSeconds": {"type": "integer", "minimum": 5, "maximum": 300}}, "required": ["path"]}),
    WorkflowAgentTool("runStaticAnalysis", "Start the applicable typed static validation for a sandbox artifact.", {"type": "object", "additionalProperties": False, "properties": {"path": {"type": "string"}, "timeoutSeconds": {"type": "integer", "minimum": 5, "maximum": 300}}, "required": ["path"]}),
)


@dataclass
class SandboxSession:
    session_id: str
    operation: str
    relative_path: str
    process: subprocess.Popen[str]
    output: str = ""
    status: str = "running"
    exit_code: int | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


class WorkflowImplementationToolContext:
    """Owns revision-scoped tools and process state for one model request."""

    def __init__(self, root: Path, security_policy: SecurityControlPolicy, output_limit: int = 100_000, governor: ResourceGovernor | None = None) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._security = security_policy
        self._output_limit = min(max(output_limit, 4096), 1_000_000)
        self._sessions: dict[str, SandboxSession] = {}
        self._governor = governor or ResourceGovernor(max_memory_mb=4096, max_cpu_percent=95, max_children=12)

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [tool.as_openai_tool() for tool in IMPLEMENTATION_TOOLS]

    async def invoke(self, name: str, arguments: dict[str, Any]) -> str:
        mutating = name in {"startTerminalSession", "cancelTerminalSession", "buildProjects", "runTargetedTests", "runFormatter", "runLinter", "runStaticAnalysis"}
        try:
            self._security.require("workflow-implementation-tools", name, mutating=mutating)
        except SecurityControlError as error:
            raise WorkflowAgentToolError(str(error)) from error
        if name == "listDirectory":
            return self._list_directory(arguments)
        if name == "startTerminalSession":
            return self._start(arguments)
        if name == "getTerminalOutput":
            return self._output(arguments)
        if name == "cancelTerminalSession":
            return self._cancel(arguments)
        if name == "getStructuredFailures":
            return self._failures(arguments)
        if name == "discoverTests":
            return self._discover_tests(arguments)
        if name == "buildProjects":
            return self._start_typed("dotnetBuild", arguments)
        if name == "runTargetedTests":
            return self._start_typed("dotnetTest", arguments)
        if name == "runFormatter":
            return self._start_typed("dotnetFormatCheck", arguments)
        if name == "runLinter":
            target = self._resolve(arguments.get("path"))
            return self._start_typed("powershellAnalyze" if target.suffix.casefold() == ".ps1" else "dotnetAnalyze", arguments)
        if name == "runStaticAnalysis":
            target = self._resolve(arguments.get("path"))
            return self._start_typed("powershellSyntax" if target.suffix.casefold() == ".ps1" else "dotnetBuild", arguments)
        raise WorkflowAgentToolError(f"Unknown workflow implementation tool '{name}'; default-deny policy blocked it.")

    def close(self) -> None:
        for session in self._sessions.values():
            if session.process.poll() is None:
                session.process.kill()

    def _resolve(self, raw_path: Any, *, must_exist: bool = True) -> Path:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise WorkflowAgentToolError("A non-empty sandbox-relative path is required.")
        candidate = (self._root / raw_path).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise WorkflowAgentToolError("The requested path is outside the workflow sandbox.")
        if must_exist and not candidate.exists():
            raise WorkflowAgentToolError("The requested sandbox path does not exist.")
        return candidate

    def _list_directory(self, arguments: dict[str, Any]) -> str:
        target = self._resolve(arguments.get("path"))
        if not target.is_dir():
            raise WorkflowAgentToolError("listDirectory requires a directory path.")
        max_depth = self._bounded_int(arguments.get("maxDepth", 1), 1, 3, "maxDepth")
        max_entries = self._bounded_int(arguments.get("maxEntries", 100), 1, 500, "maxEntries")
        pending = [(target, 0)]
        entries: list[dict[str, str]] = []
        while pending and len(entries) < max_entries:
            current, depth = pending.pop(0)
            for child in sorted(current.iterdir(), key=lambda item: item.name.casefold()):
                if len(entries) >= max_entries:
                    break
                if child.is_symlink():
                    kind = "symbolic-link"
                else:
                    kind = "directory" if child.is_dir() else "file"
                entries.append({"path": child.relative_to(self._root).as_posix(), "type": kind})
                if kind == "directory" and depth + 1 < max_depth and child.name not in {".git", ".vs", "bin", "obj", "node_modules"}:
                    pending.append((child, depth + 1))
        return json.dumps({"path": target.relative_to(self._root).as_posix() or ".", "entries": entries, "truncated": bool(pending) or len(entries) >= max_entries})

    def _start(self, arguments: dict[str, Any]) -> str:
        try:
            self._governor.check()
        except ResourceBudgetError as error:
            raise WorkflowAgentToolError(str(error)) from error
        if len(self._sessions) >= 20:
            raise WorkflowAgentToolError("The workflow request is limited to 20 terminal sessions.")
        operation = arguments.get("operation")
        target = self._resolve(arguments.get("path"))
        timeout = self._bounded_int(arguments.get("timeoutSeconds", 120), 5, 300, "timeoutSeconds")
        command = self._command(operation, target)
        process = subprocess.Popen(command, cwd=target.parent if target.is_file() else target, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        session_id = f"workflow-terminal-{uuid.uuid4()}"
        session = SandboxSession(session_id, operation, target.relative_to(self._root).as_posix(), process)
        self._sessions[session_id] = session
        threading.Thread(target=self._capture, args=(session, timeout), daemon=True).start()
        return json.dumps({"sessionId": session_id, "status": "running", "operation": operation, "path": session.relative_path})

    def _start_typed(self, operation: str, arguments: dict[str, Any]) -> str:
        return self._start({"operation": operation, "path": arguments.get("path"), "timeoutSeconds": arguments.get("timeoutSeconds", 120)})

    def _command(self, operation: Any, target: Path) -> list[str]:
        if operation == "powershellSyntax" and target.is_file() and target.suffix.casefold() == ".ps1":
            escaped = str(target).replace("'", "''")
            script = f"$e=$null;$t=$null;[System.Management.Automation.Language.Parser]::ParseFile('{escaped}',[ref]$t,[ref]$e)|Out-Null;if($e.Count){{$e|ForEach-Object{{$_.Message}}|Write-Error;exit 1}}"
            return ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script]
        if operation in {"dotnetBuild", "dotnetTest"} and target.is_file() and target.suffix.casefold() in {".csproj", ".sln", ".slnx"}:
            verb = "build" if operation == "dotnetBuild" else "test"
            return ["dotnet", verb, str(target), "--nologo", "--verbosity", "minimal", "-p:RestoreIgnoreFailedSources=true"]
        if operation in {"dotnetFormatCheck", "dotnetAnalyze"} and target.is_file() and target.suffix.casefold() in {".csproj", ".sln", ".slnx"}:
            return ["dotnet", "format", str(target), "--verify-no-changes", "--no-restore", "--verbosity", "minimal"]
        if operation == "powershellAnalyze" and target.is_file() and target.suffix.casefold() == ".ps1":
            escaped = str(target).replace("'", "''")
            script = f"if(-not(Get-Command Invoke-ScriptAnalyzer -ErrorAction SilentlyContinue)){{Write-Error 'PSScriptAnalyzer is not installed.';exit 2}};$r=Invoke-ScriptAnalyzer -Path '{escaped}';$r|Format-Table -AutoSize;if($r){{exit 1}}"
            return ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script]
        raise WorkflowAgentToolError("The selected validation operation is not allowed for that file type.")

    def _discover_tests(self, arguments: dict[str, Any]) -> str:
        maximum = self._bounded_int(arguments.get("maxResults", 100), 1, 200, "maxResults")
        tests = []
        visited = 0
        for path in sorted(self._root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            visited += 1
            if visited > 5000:
                break
            if not path.is_file() or path.is_symlink() or ".aegis" in path.parts:
                continue
            name = path.name.casefold()
            if name.endswith(".tests.ps1") or name.endswith(".test.ps1") or (path.suffix.casefold() == ".csproj" and ("test" in name or "test" in path.parent.name.casefold())):
                tests.append({"path": path.relative_to(self._root).as_posix(), "type": "pester" if path.suffix.casefold() == ".ps1" else "dotnet"})
                if len(tests) >= maximum:
                    break
        return json.dumps({"tests": tests, "count": len(tests), "scanCapped": visited > 5000})

    def _capture(self, session: SandboxSession, timeout: int) -> None:
        try:
            output, _ = session.process.communicate(timeout=timeout)
            with session.lock:
                session.output = (output or "")[-self._output_limit:]
                session.exit_code = session.process.returncode
                if session.status == "running":
                    session.status = "completed" if session.exit_code == 0 else "failed"
        except subprocess.TimeoutExpired:
            session.process.kill()
            output, _ = session.process.communicate()
            with session.lock:
                session.output = (output or "")[-self._output_limit:]
                session.exit_code = session.process.returncode
                session.status = "timed-out"

    def _session(self, arguments: dict[str, Any]) -> SandboxSession:
        session_id = arguments.get("sessionId")
        if not isinstance(session_id, str) or session_id not in self._sessions:
            raise WorkflowAgentToolError("A known workflow terminal sessionId is required.")
        return self._sessions[session_id]

    def _output(self, arguments: dict[str, Any]) -> str:
        session = self._session(arguments)
        offset = self._bounded_int(arguments.get("offset", 0), 0, self._output_limit, "offset")
        maximum = self._bounded_int(arguments.get("maxChars", 20_000), 500, 50_000, "maxChars")
        with session.lock:
            content = session.output[offset:offset + maximum]
            return json.dumps({"sessionId": session.session_id, "status": session.status, "exitCode": session.exit_code, "offset": offset, "nextOffset": offset + len(content), "outputLength": len(session.output), "truncated": offset + len(content) < len(session.output), "output": content})

    def _cancel(self, arguments: dict[str, Any]) -> str:
        session = self._session(arguments)
        with session.lock:
            if session.status != "running":
                raise WorkflowAgentToolError(f"Terminal session is already {session.status}.")
            session.status = "cancelled"
            session.process.kill()
        return json.dumps({"sessionId": session.session_id, "status": "cancelled"})

    def _failures(self, arguments: dict[str, Any]) -> str:
        session = self._session(arguments)
        maximum = self._bounded_int(arguments.get("maxResults", 50), 1, 200, "maxResults")
        pattern = re.compile(r"^(?P<file>.+?\.[A-Za-z0-9]+)\((?P<line>\d+)(?:,(?P<column>\d+))?\):\s*(?P<severity>error|warning)\s+(?P<code>[A-Za-z]+\d+):\s*(?P<message>.+)$", re.IGNORECASE)
        failures = []
        with session.lock:
            for line in session.output.splitlines():
                match = pattern.match(line.strip())
                if match:
                    record = match.groupdict(default="")
                    record["line"] = int(record["line"])
                    record["column"] = int(record["column"] or 0)
                    failures.append(record)
                elif re.match(r"^(?:FAIL|FAILED|error|failure)\b", line.strip(), re.IGNORECASE):
                    failures.append({"file": "", "line": 0, "column": 0, "severity": "error", "code": "", "message": line.strip()[:1000]})
                if len(failures) >= maximum:
                    break
            digest = hashlib.sha256(session.output.encode("utf-8")).hexdigest()
        return json.dumps({"sessionId": session.session_id, "status": session.status, "exitCode": session.exit_code, "outputSha256": digest, "failures": failures, "count": len(failures)})

    @staticmethod
    def _bounded_int(value: Any, minimum: int, maximum: int, name: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            raise WorkflowAgentToolError(f"{name} must be an integer between {minimum} and {maximum}.")
        return value


class ApprovedWorkflowImplementationToolContext:
    """Combines workflow context and sandbox tools after plan/test-plan approval."""

    def __init__(self, store: JarvisStore, workflow: Workflow, security_policy: SecurityControlPolicy, artifact_root: Path, output_limit: int, delegate=None, max_memory_mb: int = 4096, max_cpu_percent: float = 95, max_child_processes: int = 12) -> None:
        self._workflow = WorkflowAgentToolContext(store, workflow, security_policy)
        sandbox_root = artifact_root / workflow.transfer_id / f"revision-{workflow.revision}" / "agent-workspace"
        governor = ResourceGovernor(max_memory_mb=max_memory_mb, max_cpu_percent=max_cpu_percent, max_children=max_child_processes)
        self._sandbox = WorkflowImplementationToolContext(sandbox_root, security_policy, output_limit, governor)
        self._files = WorkflowSandboxFileToolContext(sandbox_root, security_policy)
        self._repository = WorkflowRepositoryToolContext(sandbox_root, security_policy)
        self._intelligence = WorkflowIntelligenceToolContext(sandbox_root, security_policy)
        self._extended = WorkflowExtendedToolContext(sandbox_root, security_policy, lambda: self.definitions, delegate=delegate)
        repository_root = Path(__file__).resolve().parents[2]
        self._mcp = WorkflowMcpToolContext(security_policy, repository_root / "config" / "mcp" / "catalog.json", artifact_root / "Logs" / "mcp-audit.jsonl", governor)
        self._sandbox_names = {tool.name for tool in IMPLEMENTATION_TOOLS}
        self._file_names = {tool.name for tool in SANDBOX_FILE_TOOLS}
        self._repository_names = {tool.name for tool in REPOSITORY_TOOLS}
        self._intelligence_names = {tool.name for tool in INTELLIGENCE_TOOLS}
        self._extended_names = {tool.name for tool in EXTENDED_TOOLS}
        self._mcp_names = {tool.name for tool in MCP_WORKFLOW_TOOLS}

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [*self._workflow.definitions, *self._sandbox.definitions, *self._files.definitions, *self._repository.definitions, *self._intelligence.definitions, *self._extended.definitions, *self._mcp.definitions]

    async def invoke(self, name: str, arguments: dict[str, Any]) -> str:
        if name in self._sandbox_names:
            return await self._sandbox.invoke(name, arguments)
        if name in self._file_names:
            return await self._files.invoke(name, arguments)
        if name in self._repository_names:
            return await self._repository.invoke(name, arguments)
        if name in self._intelligence_names:
            return await self._intelligence.invoke(name, arguments)
        if name in self._extended_names:
            return await self._extended.invoke(name, arguments)
        if name in self._mcp_names:
            return await self._mcp.invoke(name, arguments)
        return await self._workflow.invoke(name, arguments)

    def close(self) -> None:
        self._sandbox.close()
