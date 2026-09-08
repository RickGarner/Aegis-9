"""Offline repository-reasoning tools for an A.E.G.I.S.-9 workflow sandbox."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.security_control import SecurityControlError, SecurityControlPolicy
from app.workflow_agent_tools import WorkflowAgentTool, WorkflowAgentToolError


INTELLIGENCE_TOOLS = (
    WorkflowAgentTool("activateToolGroup", "Describe the bounded local tools in one approved workflow tool group.", {"type": "object", "additionalProperties": False, "properties": {"group": {"type": "string", "enum": ["inspect", "edit", "filesystem", "validate", "git", "project"]}}, "required": ["group"]}),
    WorkflowAgentTool("analyzeChangeImpact", "Find bounded repository files and tests that may be affected by a symbol or file change.", {"type": "object", "additionalProperties": False, "properties": {"query": {"type": "string", "maxLength": 300}, "path": {"type": "string"}, "maxResults": {"type": "integer", "minimum": 1, "maximum": 100}}, "required": ["query"]}),
    WorkflowAgentTool("estimateContextBudget", "Estimate local prompt, schema, input, and output token budget without transmitting content.", {"type": "object", "additionalProperties": False, "properties": {"prompt": {"type": "string", "maxLength": 20000}, "toolGroup": {"type": "string", "enum": ["inspect", "edit", "filesystem", "validate", "git", "project"]}, "contextLength": {"type": "integer", "minimum": 4096, "maximum": 1048576}, "reservedOutputTokens": {"type": "integer", "minimum": 256, "maximum": 65536}}, "required": ["contextLength"]}),
    WorkflowAgentTool("findSymbolUsages", "Find bounded lexical usages of an exact symbol in sandbox source files.", {"type": "object", "additionalProperties": False, "properties": {"symbol": {"type": "string", "maxLength": 200}, "maxResults": {"type": "integer", "minimum": 1, "maximum": 200}}, "required": ["symbol"]}),
    WorkflowAgentTool("getBuildTestOwnership", "Identify projects and test artifacts that own or cover a sandbox file.", {"type": "object", "additionalProperties": False, "properties": {"filePath": {"type": "string"}}, "required": ["filePath"]}),
    WorkflowAgentTool("getDefinitionsAndReferences", "Find bounded lexical definitions and references for a symbol.", {"type": "object", "additionalProperties": False, "properties": {"symbol": {"type": "string", "maxLength": 200}, "maxResults": {"type": "integer", "minimum": 1, "maximum": 200}}, "required": ["symbol"]}),
    WorkflowAgentTool("getProjectExecutionPlan", "Create a deterministic repository-aware implementation and validation plan.", {"type": "object", "additionalProperties": False, "properties": {"requestSummary": {"type": "string", "maxLength": 2000}, "maxProjects": {"type": "integer", "minimum": 1, "maximum": 100}}, "required": ["requestSummary"]}),
    WorkflowAgentTool("getProjectImprovementSuggestions", "Return bounded evidence-backed improvement suggestions for sandbox projects.", {"type": "object", "additionalProperties": False, "properties": {"focus": {"type": "string", "enum": ["all", "testing", "security", "maintainability"]}, "maxSuggestions": {"type": "integer", "minimum": 1, "maximum": 50}}}),
    WorkflowAgentTool("getRepositoryMemory", "Return a deterministic local repository snapshot for reuse during this workflow revision.", {"type": "object", "additionalProperties": False, "properties": {"maxFiles": {"type": "integer", "minimum": 1, "maximum": 1000}}}),
    WorkflowAgentTool("getSymbolGraph", "Build a bounded lexical symbol-to-symbol relationship graph from sandbox source.", {"type": "object", "additionalProperties": False, "properties": {"symbol": {"type": "string", "maxLength": 200}, "maxEdges": {"type": "integer", "minimum": 1, "maximum": 500}}, "required": ["symbol"]}),
)


class WorkflowIntelligenceToolContext:
    def __init__(self, root: Path, security_policy: SecurityControlPolicy) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._security = security_policy

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [tool.as_openai_tool() for tool in INTELLIGENCE_TOOLS]

    async def invoke(self, name: str, arguments: dict[str, Any]) -> str:
        try:
            self._security.require("workflow-intelligence-tools", name, mutating=False)
        except SecurityControlError as error:
            raise WorkflowAgentToolError(str(error)) from error
        handlers = {
            "activateToolGroup": self._activate,
            "analyzeChangeImpact": self._impact,
            "estimateContextBudget": self._budget,
            "findSymbolUsages": self._usages,
            "getBuildTestOwnership": self._ownership,
            "getDefinitionsAndReferences": self._definitions,
            "getProjectExecutionPlan": self._plan,
            "getProjectImprovementSuggestions": self._suggestions,
            "getRepositoryMemory": self._memory,
            "getSymbolGraph": self._graph,
        }
        handler = handlers.get(name)
        if handler is None:
            raise WorkflowAgentToolError(f"Unknown intelligence tool '{name}'; default-deny policy blocked it.")
        return json.dumps(handler(arguments), indent=2)

    @staticmethod
    def _integer(value: Any, default: int, low: int, high: int, name: str) -> int:
        value = default if value is None else value
        if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
            raise WorkflowAgentToolError(f"{name} must be between {low} and {high}.")
        return value

    def _resolve(self, value: Any) -> Path:
        if not isinstance(value, str) or not value.strip() or Path(value).is_absolute():
            raise WorkflowAgentToolError("A non-empty sandbox-relative file path is required.")
        path = (self._root / value).resolve()
        if self._root not in path.parents or not path.is_file() or ".aegis" in path.parts:
            raise WorkflowAgentToolError("The requested file is unavailable or outside the sandbox.")
        return path

    def _files(self, maximum: int = 5000) -> list[Path]:
        result = []
        for path in sorted(self._root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            if len(result) >= maximum:
                break
            if path.is_file() and not path.is_symlink() and not {".git", ".aegis", "bin", "obj", "node_modules"}.intersection(path.parts):
                result.append(path)
        return result

    @staticmethod
    def _is_source(path: Path) -> bool:
        return path.suffix.casefold() in {".cs", ".ps1", ".psm1", ".xaml", ".js", ".ts", ".tsx", ".py"}

    def _read(self, path: Path, maximum: int = 100000) -> str:
        if path.stat().st_size > maximum * 4:
            return ""
        try:
            return path.read_text(encoding="utf-8")[:maximum]
        except UnicodeDecodeError:
            return ""

    def _matches(self, symbol: Any, maximum: int) -> list[dict[str, Any]]:
        if not isinstance(symbol, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,199}", symbol):
            raise WorkflowAgentToolError("symbol must be a bounded identifier.")
        pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(symbol)}(?![A-Za-z0-9_])", re.IGNORECASE)
        matches = []
        for path in self._files():
            if not self._is_source(path):
                continue
            for number, line in enumerate(self._read(path).splitlines(), 1):
                if pattern.search(line):
                    matches.append({"path": path.relative_to(self._root).as_posix(), "line": number, "text": line.strip()[:500]})
                    if len(matches) >= maximum:
                        return matches
        return matches

    def _activate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        groups = {
            "inspect": ["getFileOutline", "getDependencyGraph", "findSymbolUsages", "getDefinitionsAndReferences", "getSymbolGraph", "analyzeChangeImpact"],
            "edit": ["beginChangeSet", "previewChangeSet", "validateChangeSet", "commitChangeSet", "rollbackChangeSet"],
            "filesystem": ["createFile", "createDirectory", "applyEdit", "applyWorkspaceEdits", "replaceFileContent"],
            "validate": ["discoverTests", "buildProjects", "runTargetedTests", "runFormatter", "runLinter", "runStaticAnalysis"],
            "git": ["getGitContext", "getGitHistory", "getGitBlame", "getBranchComparison", "getChangedFiles"],
            "project": ["getRepositoryMap", "getProjectExecutionPlan", "getProjectImprovementSuggestions", "getBuildTestOwnership", "getRepositoryMemory"],
        }
        group = arguments.get("group")
        if group not in groups:
            raise WorkflowAgentToolError("An approved local tool group is required.")
        return {"group": group, "tools": groups[group], "note": "The server already enforces approval-stage exposure; this call grants no additional authority."}

    def _budget(self, arguments: dict[str, Any]) -> dict[str, Any]:
        context = self._integer(arguments.get("contextLength"), 16384, 4096, 1048576, "contextLength")
        reserve = self._integer(arguments.get("reservedOutputTokens"), 4096, 256, min(65536, context - 1), "reservedOutputTokens")
        prompt = arguments.get("prompt", "")
        if not isinstance(prompt, str) or len(prompt) > 20000:
            raise WorkflowAgentToolError("prompt exceeds the local estimate limit.")
        group = arguments.get("toolGroup", "inspect")
        schema_chars = sum(len(json.dumps(tool.as_openai_tool())) for tool in INTELLIGENCE_TOOLS if group in tool.description.casefold() or tool.name in {"activateToolGroup", "estimateContextBudget"})
        prompt_tokens = (len(prompt) + 3) // 4
        schema_tokens = (schema_chars + 3) // 4
        remaining = context - reserve - prompt_tokens - schema_tokens
        return {"contextLength": context, "promptTokensEstimate": prompt_tokens, "schemaTokensEstimate": schema_tokens, "reservedOutputTokens": reserve, "remainingInputTokens": remaining, "fits": remaining >= 0}

    def _usages(self, arguments: dict[str, Any]) -> dict[str, Any]:
        maximum = self._integer(arguments.get("maxResults"), 50, 1, 200, "maxResults")
        matches = self._matches(arguments.get("symbol"), maximum)
        return {"symbol": arguments.get("symbol"), "usages": matches, "count": len(matches)}

    def _definitions(self, arguments: dict[str, Any]) -> dict[str, Any]:
        maximum = self._integer(arguments.get("maxResults"), 100, 1, 200, "maxResults")
        matches = self._matches(arguments.get("symbol"), maximum)
        marker = re.compile(rf"\b(?:class|interface|record|struct|enum|function|def|const|let|var)\s+{re.escape(str(arguments.get('symbol')))}\b", re.IGNORECASE)
        definitions = [item for item in matches if marker.search(item["text"])]
        references = [item for item in matches if item not in definitions]
        return {"symbol": arguments.get("symbol"), "definitions": definitions, "references": references, "languageService": False}

    def _impact(self, arguments: dict[str, Any]) -> dict[str, Any]:
        maximum = self._integer(arguments.get("maxResults"), 50, 1, 100, "maxResults")
        matches = self._matches(arguments.get("query"), maximum)
        source = None
        if arguments.get("path") is not None:
            source = self._resolve(arguments.get("path")).relative_to(self._root).as_posix()
        tests = [item for item in matches if "test" in item["path"].casefold()]
        return {"query": arguments.get("query"), "source": source, "affectedFiles": sorted({item["path"] for item in matches}), "relatedTests": sorted({item["path"] for item in tests}), "basis": "bounded lexical references"}

    def _projects(self) -> list[str]:
        return [path.relative_to(self._root).as_posix() for path in self._files() if path.suffix.casefold() in {".sln", ".slnx", ".csproj"}]

    def _ownership(self, arguments: dict[str, Any]) -> dict[str, Any]:
        target = self._resolve(arguments.get("filePath"))
        projects = self._projects()
        owners = sorted(projects, key=lambda item: len(Path(item).parts), reverse=True)
        owners = [item for item in owners if (self._root / item).parent == target.parent or (self._root / item).parent in target.parents]
        tests = [path.relative_to(self._root).as_posix() for path in self._files() if "test" in path.name.casefold() or "test" in path.parent.name.casefold()]
        return {"filePath": target.relative_to(self._root).as_posix(), "owningProjects": owners, "candidateTests": tests[:100]}

    def _plan(self, arguments: dict[str, Any]) -> dict[str, Any]:
        summary = arguments.get("requestSummary")
        if not isinstance(summary, str) or not summary.strip() or len(summary) > 2000:
            raise WorkflowAgentToolError("A bounded requestSummary is required.")
        maximum = self._integer(arguments.get("maxProjects"), 20, 1, 100, "maxProjects")
        projects = self._projects()[:maximum]
        return {"requestSummary": summary, "projects": projects, "steps": ["Inspect repository instructions and relevant symbols.", "Confirm API, credential, and environment requirements without storing secrets.", "Stage changes in one guarded change set.", "Preview and validate the change set.", "Run the narrowest discovered build and tests.", "Record evidence for user approval."], "requiresUserApprovalBeforeImplementation": True}

    def _suggestions(self, arguments: dict[str, Any]) -> dict[str, Any]:
        maximum = self._integer(arguments.get("maxSuggestions"), 10, 1, 50, "maxSuggestions")
        focus = arguments.get("focus", "all")
        files = self._files()
        suggestions = []
        if not any("test" in path.name.casefold() or "test" in path.parent.name.casefold() for path in files):
            suggestions.append({"category": "testing", "evidence": "No test-named artifact was found in the bounded scan.", "suggestion": "Add focused automated tests before production approval."})
        if any(path.name.casefold() in {".env", "appsettings.json"} for path in files):
            suggestions.append({"category": "security", "evidence": "A potentially sensitive configuration file exists.", "suggestion": "Verify secret values are excluded and injected locally."})
        if not any(path.name.casefold() in {"readme.md", "readme.txt"} for path in files):
            suggestions.append({"category": "maintainability", "evidence": "No README was found.", "suggestion": "Document build, test, and workflow usage."})
        if focus != "all":
            suggestions = [item for item in suggestions if item["category"] == focus]
        return {"focus": focus, "suggestions": suggestions[:maximum]}

    def _memory(self, arguments: dict[str, Any]) -> dict[str, Any]:
        maximum = self._integer(arguments.get("maxFiles"), 500, 1, 1000, "maxFiles")
        files = self._files(maximum + 1)
        records = [{"path": path.relative_to(self._root).as_posix(), "bytes": path.stat().st_size, "modifiedNs": path.stat().st_mtime_ns} for path in files[:maximum]]
        digest = hashlib.sha256(json.dumps(records, sort_keys=True).encode("utf-8")).hexdigest()
        return {"snapshotId": digest, "files": records, "projects": self._projects()[:100], "truncated": len(files) > maximum, "scope": "workflow-revision-sandbox"}

    def _graph(self, arguments: dict[str, Any]) -> dict[str, Any]:
        maximum = self._integer(arguments.get("maxEdges"), 100, 1, 500, "maxEdges")
        matches = self._matches(arguments.get("symbol"), maximum)
        identifiers = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")
        ignored = {"class", "public", "private", "return", "function", "static", "async", "await", "string", "void"}
        edges = []
        for item in matches:
            for target in identifiers.findall(item["text"]):
                if target.casefold() != str(arguments.get("symbol")).casefold() and target.casefold() not in ignored:
                    edges.append({"from": arguments.get("symbol"), "to": target, "path": item["path"], "line": item["line"], "basis": "same-line lexical occurrence"})
                    if len(edges) >= maximum:
                        return {"edges": edges, "truncated": True, "languageService": False}
        return {"edges": edges, "truncated": False, "languageService": False}
