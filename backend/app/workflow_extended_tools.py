"""Final portable workflow tools with sandbox, registry, and approval boundaries."""

import json
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.security_control import SecurityControlError, SecurityControlPolicy
from app.workflow_agent_tools import WorkflowAgentTool, WorkflowAgentToolError
from app.mcp_registry import McpRegistryError, discover_tools, load_registry


EXTENDED_TOOLS = (
    WorkflowAgentTool("applyUnifiedPatch", "Apply a validated unified patch only inside the workflow sandbox.", {"type": "object", "additionalProperties": False, "properties": {"patch": {"type": "string", "maxLength": 200000}}, "required": ["patch"]}),
    WorkflowAgentTool("compareDiagnostics", "Compare caller-supplied bounded before and after diagnostic snapshots.", {"type": "object", "additionalProperties": False, "properties": {"before": {"type": "array", "maxItems": 500, "items": {"type": "object"}}, "after": {"type": "array", "maxItems": 500, "items": {"type": "object"}}}, "required": ["before", "after"]}),
    WorkflowAgentTool("deletePath", "Move one sandbox file or empty directory into protected recovery storage.", {"type": "object", "additionalProperties": False, "properties": {"path": {"type": "string"}}, "required": ["path"]}),
    WorkflowAgentTool("getMcpTools", "List only enabled and healthy tools from the approved local MCP registry; discovery grants no authority.", {"type": "object", "additionalProperties": False, "properties": {"query": {"type": "string", "maxLength": 200}}}),
    WorkflowAgentTool("getWorkspaceSymbols", "Return bounded lexical symbols from sandbox source files.", {"type": "object", "additionalProperties": False, "properties": {"query": {"type": "string", "maxLength": 200}, "maxResults": {"type": "integer", "minimum": 1, "maximum": 500}}}),
    WorkflowAgentTool("movePath", "Move one sandbox path without overwrite or cross-sandbox access.", {"type": "object", "additionalProperties": False, "properties": {"sourcePath": {"type": "string"}, "targetPath": {"type": "string"}}, "required": ["sourcePath", "targetPath"]}),
    WorkflowAgentTool("renamePath", "Rename one sandbox path without overwrite or cross-sandbox access.", {"type": "object", "additionalProperties": False, "properties": {"sourcePath": {"type": "string"}, "targetPath": {"type": "string"}}, "required": ["sourcePath", "targetPath"]}),
    WorkflowAgentTool("runWorkspaceCommand", "Run one typed validation operation; arbitrary command text is not accepted.", {"type": "object", "additionalProperties": False, "properties": {"operation": {"type": "string", "enum": ["powershellSyntax", "dotnetBuild", "dotnetTest"]}, "path": {"type": "string"}, "timeoutSeconds": {"type": "integer", "minimum": 5, "maximum": 300}}, "required": ["operation", "path"]}),
    WorkflowAgentTool("scaffoldWorkspaceProject", "Scaffold a constrained PowerShell or .NET project into a new sandbox directory.", {"type": "object", "additionalProperties": False, "properties": {"template": {"type": "string", "enum": ["powershell-console", "dotnet-console-csharp", "dotnet-wpf-csharp", "dotnet-winforms-csharp"]}, "projectName": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,63}$"}, "targetDirectory": {"type": "string"}}, "required": ["template", "projectName", "targetDirectory"]}),
    WorkflowAgentTool("searchAvailableTools", "Search the locally registered Aegis workflow tool catalog by literal text.", {"type": "object", "additionalProperties": False, "properties": {"query": {"type": "string", "maxLength": 200}, "maxResults": {"type": "integer", "minimum": 1, "maximum": 100}}}),
    WorkflowAgentTool("delegateToAgentHostSession", "Delegate a bounded subtask to an approved Aegis local-model role without granting tools.", {"type": "object", "additionalProperties": False, "properties": {"role": {"type": "string", "enum": ["planning", "implementation", "testing", "review"]}, "prompt": {"type": "string", "maxLength": 4000}}, "required": ["role", "prompt"]}),
)


class WorkflowExtendedToolContext:
    def __init__(self, root: Path, security_policy: SecurityControlPolicy, all_definitions: Any = None, registry_path: Path | None = None, delegate: Callable[[str, str], Awaitable[dict[str, Any]]] | None = None) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._security = security_policy
        self._all_definitions = all_definitions
        self._registry = registry_path or Path(__file__).resolve().parents[2] / "config" / "mcp" / "catalog.json"
        self._recovery = self._root / ".aegis" / "recovery"
        self._delegate_callback = delegate

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [tool.as_openai_tool() for tool in EXTENDED_TOOLS]

    async def invoke(self, name: str, arguments: dict[str, Any]) -> str:
        mutating = name in {"applyUnifiedPatch", "deletePath", "movePath", "renamePath", "runWorkspaceCommand", "scaffoldWorkspaceProject"}
        try:
            self._security.require("workflow-extended-tools", name, mutating=mutating)
        except SecurityControlError as error:
            raise WorkflowAgentToolError(str(error)) from error
        handlers = {"applyUnifiedPatch": self._patch, "compareDiagnostics": self._diagnostics, "deletePath": self._delete, "getMcpTools": self._mcp, "getWorkspaceSymbols": self._symbols, "movePath": self._relocate, "renamePath": self._relocate, "runWorkspaceCommand": self._command, "scaffoldWorkspaceProject": self._scaffold, "searchAvailableTools": self._search_tools}
        if name == "delegateToAgentHostSession":
            return json.dumps(await self._delegate(arguments), indent=2)
        handler = handlers.get(name)
        if handler is None:
            raise WorkflowAgentToolError(f"Unknown extended tool '{name}'; default-deny policy blocked it.")
        return json.dumps(handler(arguments), indent=2)

    async def _delegate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        role, prompt = arguments.get("role"), arguments.get("prompt")
        if role not in {"planning", "implementation", "testing", "review"} or not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4000:
            raise WorkflowAgentToolError("A supported role and bounded non-empty prompt are required.")
        if self._delegate_callback is None:
            raise WorkflowAgentToolError("No independent local agent host is configured for this request.")
        result = await self._delegate_callback(role, prompt.strip())
        return {"role": role, "result": result, "toolsGranted": False, "productionAuthority": False}

    def _resolve(self, value: Any, *, missing: bool = False) -> Path:
        if not isinstance(value, str) or not value.strip() or Path(value).is_absolute():
            raise WorkflowAgentToolError("A non-empty sandbox-relative path is required.")
        path = (self._root / value).resolve()
        if path == self._root or self._root not in path.parents or ".aegis" in path.parts:
            raise WorkflowAgentToolError("The path is outside the sandbox or protected.")
        if not missing and not path.exists():
            raise WorkflowAgentToolError("The source path does not exist.")
        return path

    @staticmethod
    def _integer(value: Any, default: int, low: int, high: int) -> int:
        value = default if value is None else value
        if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
            raise WorkflowAgentToolError(f"Value must be between {low} and {high}.")
        return value

    def _patch(self, arguments: dict[str, Any]) -> dict[str, Any]:
        patch = arguments.get("patch")
        if not isinstance(patch, str) or not patch.strip() or len(patch) > 200000:
            raise WorkflowAgentToolError("A bounded unified patch is required.")
        targets = re.findall(r"^\+\+\+\s+b/(.+)$", patch, re.MULTILINE)
        if not targets or len(targets) > 50:
            raise WorkflowAgentToolError("The patch must contain between 1 and 50 workspace file targets.")
        for target in targets:
            self._resolve(target, missing=True)
        check = subprocess.run(["git", "apply", "--check", "--whitespace=error-all", "-"], cwd=self._root, input=patch, text=True, capture_output=True, timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if check.returncode:
            raise WorkflowAgentToolError((check.stderr or "Patch validation failed.")[:3000])
        result = subprocess.run(["git", "apply", "--whitespace=error-all", "-"], cwd=self._root, input=patch, text=True, capture_output=True, timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode:
            raise WorkflowAgentToolError((result.stderr or "Patch application failed.")[:3000])
        return {"applied": targets, "sandboxOnly": True}

    def _diagnostics(self, arguments: dict[str, Any]) -> dict[str, Any]:
        before, after = arguments.get("before"), arguments.get("after")
        if not isinstance(before, list) or not isinstance(after, list) or len(before) > 500 or len(after) > 500:
            raise WorkflowAgentToolError("Bounded before and after arrays are required.")
        encode = lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"))
        old, new = {encode(item) for item in before}, {encode(item) for item in after}
        return {"added": [json.loads(item) for item in sorted(new - old)], "resolved": [json.loads(item) for item in sorted(old - new)], "unchangedCount": len(old & new)}

    def _delete(self, arguments: dict[str, Any]) -> dict[str, Any]:
        source = self._resolve(arguments.get("path"))
        if source.is_dir() and any(source.iterdir()):
            raise WorkflowAgentToolError("Only empty directories can be deleted by this tool.")
        self._recovery.mkdir(parents=True, exist_ok=True)
        destination = self._recovery / f"{uuid.uuid4()}-{source.name}"
        shutil.move(str(source), str(destination))
        return {"deleted": source.relative_to(self._root).as_posix(), "recoverable": True, "recoveryId": destination.name}

    def _relocate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        source = self._resolve(arguments.get("sourcePath"))
        target = self._resolve(arguments.get("targetPath"), missing=True)
        if target.exists() or not target.parent.is_dir() or source in target.parents:
            raise WorkflowAgentToolError("The target must be a new path with an existing parent and cannot be inside the source.")
        source.rename(target)
        return {"source": source.relative_to(self._root).as_posix(), "target": target.relative_to(self._root).as_posix()}

    def _load_registry(self) -> dict[str, Any]:
        try:
            return load_registry(self._registry)
        except McpRegistryError as error:
            raise WorkflowAgentToolError(str(error)) from error

    def _mcp(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query", "")
        if not isinstance(query, str) or len(query) > 200:
            raise WorkflowAgentToolError("The MCP query is invalid.")
        registry = self._load_registry()
        return {"connectivityProfile": registry["connectivityProfile"], "tools": discover_tools(registry, query), "grantsAuthority": False}

    def _symbols(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query", "")
        maximum = self._integer(arguments.get("maxResults"), 100, 1, 500)
        if not isinstance(query, str) or len(query) > 200:
            raise WorkflowAgentToolError("The symbol query is invalid.")
        pattern = re.compile(r"(?im)^\s*(?:(?:public|private|protected|internal|static|sealed|abstract|partial|export)\s+)*(?:class|interface|record|struct|enum|function|def)\s+([A-Za-z_][A-Za-z0-9_-]*)")
        found = []
        for path in sorted(self._root.rglob("*")):
            if not path.is_file() or path.is_symlink() or {".aegis", ".git", "bin", "obj", "node_modules"}.intersection(path.parts) or path.stat().st_size > 400000:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for match in pattern.finditer(text):
                if not query or query.casefold() in match.group(1).casefold():
                    found.append({"name": match.group(1), "path": path.relative_to(self._root).as_posix(), "line": text.count("\n", 0, match.start()) + 1})
                    if len(found) >= maximum:
                        return {"symbols": found, "truncated": True, "languageService": False}
        return {"symbols": found, "truncated": False, "languageService": False}

    def _command(self, arguments: dict[str, Any]) -> dict[str, Any]:
        operation = arguments.get("operation")
        target = self._resolve(arguments.get("path"))
        timeout = self._integer(arguments.get("timeoutSeconds"), 120, 5, 300)
        if operation == "powershellSyntax" and target.is_file() and target.suffix.casefold() == ".ps1":
            escaped = str(target).replace("'", "''")
            command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", f"$e=$null;$t=$null;[System.Management.Automation.Language.Parser]::ParseFile('{escaped}',[ref]$t,[ref]$e)|Out-Null;if($e.Count){{$e|% Message;exit 1}}"]
        elif operation in {"dotnetBuild", "dotnetTest"} and target.suffix.casefold() in {".csproj", ".sln", ".slnx"}:
            command = ["dotnet", "build" if operation == "dotnetBuild" else "test", str(target), "--nologo", "--verbosity", "minimal", "-p:RestoreIgnoreFailedSources=true"]
        else:
            raise WorkflowAgentToolError("That typed operation is not valid for the selected artifact.")
        result = subprocess.run(command, cwd=target.parent, capture_output=True, text=True, timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        output = (result.stdout + result.stderr)[:100000]
        return {"operation": operation, "path": target.relative_to(self._root).as_posix(), "exitCode": result.returncode, "output": output, "truncated": len(result.stdout + result.stderr) > 100000}

    def _scaffold(self, arguments: dict[str, Any]) -> dict[str, Any]:
        template, name = arguments.get("template"), arguments.get("projectName")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", name):
            raise WorkflowAgentToolError("projectName is invalid.")
        target = self._resolve(arguments.get("targetDirectory"), missing=True)
        if target.exists() or not target.parent.is_dir():
            raise WorkflowAgentToolError("Scaffolding requires a new directory with an existing parent.")
        if template == "powershell-console":
            target.mkdir()
            (target / f"{name}.ps1").write_text("Set-StrictMode -Version Latest\n\nWrite-Output 'TODO'\n", encoding="utf-8", newline="\n")
        else:
            mappings = {"dotnet-console-csharp": "console", "dotnet-wpf-csharp": "wpf", "dotnet-winforms-csharp": "winforms"}
            if template not in mappings:
                raise WorkflowAgentToolError("The scaffold template is not allowed.")
            result = subprocess.run(["dotnet", "new", mappings[template], "--name", name, "--output", str(target), "--no-restore"], cwd=self._root, capture_output=True, text=True, timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode:
                if target.exists():
                    shutil.rmtree(target)
                raise WorkflowAgentToolError((result.stderr or result.stdout)[:3000])
        return {"projectName": name, "template": template, "targetDirectory": target.relative_to(self._root).as_posix(), "production": False}

    def _search_tools(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query", "")
        maximum = self._integer(arguments.get("maxResults"), 20, 1, 100)
        if not isinstance(query, str) or len(query) > 200:
            raise WorkflowAgentToolError("The tool query is invalid.")
        definitions = self._all_definitions() if callable(self._all_definitions) else self.definitions
        results = []
        for tool in definitions:
            function = tool.get("function", {})
            if not query or query.casefold() in f"{function.get('name','')} {function.get('description','')}".casefold():
                results.append({"name": function.get("name"), "description": function.get("description", "")})
        return {"tools": results[:maximum], "truncated": len(results) > maximum, "grantsAuthority": False}
