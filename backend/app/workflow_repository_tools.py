"""Bounded repository-intelligence tools for an A.E.G.I.S.-9 workflow sandbox."""

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from app.security_control import SecurityControlError, SecurityControlPolicy
from app.workflow_agent_tools import WorkflowAgentTool, WorkflowAgentToolError


REPOSITORY_TOOLS = (
    WorkflowAgentTool("getWorkspaceDiagnostics", "Read bounded compiler-style diagnostics retained in sandbox text logs.", {"type": "object", "additionalProperties": False, "properties": {"maxResults": {"type": "integer", "minimum": 1, "maximum": 200}}}),
    WorkflowAgentTool("getFileOutline", "Extract a bounded PowerShell, C#, or XAML symbol outline from one sandbox file.", {"type": "object", "additionalProperties": False, "properties": {"path": {"type": "string"}, "maxSymbols": {"type": "integer", "minimum": 1, "maximum": 500}}, "required": ["path"]}),
    WorkflowAgentTool("getDependencyGraph", "Build a bounded project/file dependency graph from sandbox artifacts.", {"type": "object", "additionalProperties": False, "properties": {"maxEdges": {"type": "integer", "minimum": 1, "maximum": 1000}}}),
    WorkflowAgentTool("getRepositoryMap", "Return a bounded map of source and project files in the workflow sandbox.", {"type": "object", "additionalProperties": False, "properties": {"maxFiles": {"type": "integer", "minimum": 1, "maximum": 1000}}}),
    WorkflowAgentTool("getRankedWorkspaceContext", "Rank bounded sandbox text excerpts against a literal query.", {"type": "object", "additionalProperties": False, "properties": {"query": {"type": "string", "maxLength": 500}, "maxResults": {"type": "integer", "minimum": 1, "maximum": 50}}, "required": ["query"]}),
    WorkflowAgentTool("summarizeRepositoryContext", "Summarize bounded sandbox languages, projects, files, and sizes without sending data externally.", {"type": "object", "additionalProperties": False, "properties": {"maxFiles": {"type": "integer", "minimum": 1, "maximum": 1000}}}),
    WorkflowAgentTool("getGitContext", "Read bounded branch and working-tree context from a sandbox Git repository.", {"type": "object", "additionalProperties": False, "properties": {}}),
    WorkflowAgentTool("getGitHistory", "Read bounded Git history using fixed arguments and an optional sandbox file path.", {"type": "object", "additionalProperties": False, "properties": {"path": {"type": "string"}, "maxEntries": {"type": "integer", "minimum": 1, "maximum": 100}}}),
    WorkflowAgentTool("getGitBlame", "Read bounded Git blame for a sandbox file and optional line range.", {"type": "object", "additionalProperties": False, "properties": {"path": {"type": "string"}, "startLine": {"type": "integer", "minimum": 1}, "endLine": {"type": "integer", "minimum": 1}}, "required": ["path"]}),
    WorkflowAgentTool("getBranchComparison", "Compare validated Git revisions in a sandbox repository with fixed read-only arguments.", {"type": "object", "additionalProperties": False, "properties": {"base": {"type": "string"}, "target": {"type": "string"}, "maxFiles": {"type": "integer", "minimum": 1, "maximum": 500}}, "required": ["base"]}),
)


class WorkflowRepositoryToolContext:
    def __init__(self, root: Path, security_policy: SecurityControlPolicy) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._security = security_policy
        self._metadata = self._root / ".aegis"

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [tool.as_openai_tool() for tool in REPOSITORY_TOOLS]

    async def invoke(self, name: str, arguments: dict[str, Any]) -> str:
        try:
            self._security.require("workflow-repository-tools", name, mutating=False)
        except SecurityControlError as error:
            raise WorkflowAgentToolError(str(error)) from error
        handlers = {
            "getWorkspaceDiagnostics": self._diagnostics,
            "getFileOutline": self._outline,
            "getDependencyGraph": self._dependencies,
            "getRepositoryMap": self._repository_map,
            "getRankedWorkspaceContext": self._ranked_context,
            "summarizeRepositoryContext": self._summary,
            "getGitContext": self._git_context,
            "getGitHistory": self._git_history,
            "getGitBlame": self._git_blame,
            "getBranchComparison": self._branch_comparison,
        }
        handler = handlers.get(name)
        if handler is None:
            raise WorkflowAgentToolError(f"Unknown repository tool '{name}'; default-deny policy blocked it.")
        return json.dumps(handler(arguments), indent=2)

    def _resolve(self, raw_path: Any) -> Path:
        if not isinstance(raw_path, str) or not raw_path.strip() or Path(raw_path).is_absolute():
            raise WorkflowAgentToolError("A non-empty sandbox-relative path is required.")
        candidate = (self._root / raw_path).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise WorkflowAgentToolError("The requested path is outside the workflow sandbox.")
        if candidate == self._metadata or self._metadata in candidate.parents or not candidate.is_file():
            raise WorkflowAgentToolError("The requested sandbox file is unavailable or protected.")
        return candidate

    @staticmethod
    def _integer(value: Any, default: int, minimum: int, maximum: int, name: str) -> int:
        value = default if value is None else value
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            raise WorkflowAgentToolError(f"{name} must be between {minimum} and {maximum}.")
        return value

    def _files(self, maximum: int = 5000):
        visited = 0
        for path in sorted(self._root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            visited += 1
            if visited > maximum:
                break
            if path.is_file() and not path.is_symlink() and self._metadata not in path.parents and ".git" not in path.parts:
                yield path

    def _text(self, path: Path, maximum: int = 200000) -> str:
        if path.stat().st_size > maximum * 4:
            raise WorkflowAgentToolError("The requested source file exceeds the read limit.")
        try:
            return path.read_text(encoding="utf-8")[:maximum]
        except UnicodeDecodeError as error:
            raise WorkflowAgentToolError("The requested source file is not UTF-8 text.") from error

    def _diagnostics(self, arguments: dict[str, Any]) -> dict[str, Any]:
        maximum = self._integer(arguments.get("maxResults"), 50, 1, 200, "maxResults")
        pattern = re.compile(r"^(?P<file>.+?\.[A-Za-z0-9]+)\((?P<line>\d+)(?:,(?P<column>\d+))?\):\s*(?P<severity>error|warning)\s+(?P<code>[A-Za-z]+\d+):\s*(?P<message>.+)$", re.IGNORECASE)
        results = []
        for path in self._files():
            if path.suffix.casefold() not in {".log", ".txt"}:
                continue
            for line in self._text(path, 100000).splitlines():
                match = pattern.match(line.strip())
                if match:
                    item = match.groupdict(default="")
                    item.update({"line": int(item["line"]), "column": int(item["column"] or 0), "source": path.relative_to(self._root).as_posix()})
                    results.append(item)
                    if len(results) >= maximum:
                        return {"diagnostics": results, "truncated": True}
        return {"diagnostics": results, "truncated": False}

    def _outline(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve(arguments.get("path"))
        maximum = self._integer(arguments.get("maxSymbols"), 100, 1, 500, "maxSymbols")
        content = self._text(path)
        patterns = {
            ".ps1": re.compile(r"(?im)^\s*(?:function|class|enum|filter)\s+([A-Za-z_][\w-]*)"),
            ".cs": re.compile(r"(?m)^\s*(?:public|private|protected|internal|static|sealed|abstract|partial|async|\s)+\s*(?:class|interface|enum|record|struct|void|[A-Za-z_][\w<>?,\[\]]*)\s+([A-Za-z_]\w*)\s*(?:[({:]|$)"),
            ".xaml": re.compile(r"x:(?:Name|Key)=['\"]([^'\"]+)['\"]"),
        }
        pattern = patterns.get(path.suffix.casefold())
        symbols = []
        if pattern:
            for match in pattern.finditer(content):
                symbols.append({"name": match.group(1), "line": content.count("\n", 0, match.start()) + 1})
                if len(symbols) >= maximum:
                    break
        return {"path": path.relative_to(self._root).as_posix(), "symbols": symbols, "count": len(symbols)}

    def _dependencies(self, arguments: dict[str, Any]) -> dict[str, Any]:
        maximum = self._integer(arguments.get("maxEdges"), 500, 1, 1000, "maxEdges")
        edges = []
        for path in self._files():
            relative = path.relative_to(self._root).as_posix()
            if path.suffix.casefold() in {".csproj", ".props", ".targets"}:
                try:
                    root = ET.fromstring(self._text(path))
                except ET.ParseError:
                    continue
                for node in root.iter():
                    tag = node.tag.rsplit("}", 1)[-1]
                    if tag in {"ProjectReference", "PackageReference", "Reference"} and node.get("Include"):
                        edges.append({"from": relative, "to": node.get("Include"), "type": tag})
            elif path.suffix.casefold() == ".ps1":
                for module in re.findall(r"(?im)^\s*Import-Module\s+['\"]?([^'\"\s]+)", self._text(path)):
                    edges.append({"from": relative, "to": module, "type": "PowerShellModule"})
            if len(edges) >= maximum:
                break
        return {"edges": edges[:maximum], "truncated": len(edges) >= maximum}

    def _repository_map(self, arguments: dict[str, Any]) -> dict[str, Any]:
        maximum = self._integer(arguments.get("maxFiles"), 500, 1, 1000, "maxFiles")
        files = [{"path": path.relative_to(self._root).as_posix(), "extension": path.suffix.casefold(), "bytes": path.stat().st_size} for path in self._files(maximum + 1)]
        return {"files": files[:maximum], "truncated": len(files) > maximum}

    def _ranked_context(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip() or len(query) > 500:
            raise WorkflowAgentToolError("A bounded non-empty context query is required.")
        maximum = self._integer(arguments.get("maxResults"), 10, 1, 50, "maxResults")
        terms = {term.casefold() for term in re.findall(r"[A-Za-z0-9_.-]+", query) if len(term) > 1}
        ranked = []
        for path in self._files():
            try:
                content = self._text(path, 50000)
            except WorkflowAgentToolError:
                continue
            lowered = content.casefold()
            score = sum(lowered.count(term) for term in terms)
            if score:
                first = min((lowered.find(term) for term in terms if term in lowered), default=0)
                ranked.append({"path": path.relative_to(self._root).as_posix(), "score": score, "excerpt": content[max(0, first - 200):first + 800]})
        ranked.sort(key=lambda item: (-item["score"], item["path"].casefold()))
        return {"results": ranked[:maximum], "truncated": len(ranked) > maximum}

    def _summary(self, arguments: dict[str, Any]) -> dict[str, Any]:
        maximum = self._integer(arguments.get("maxFiles"), 500, 1, 1000, "maxFiles")
        extensions: dict[str, int] = {}
        total_bytes = 0
        projects = []
        count = 0
        for path in self._files(maximum + 1):
            count += 1
            total_bytes += path.stat().st_size
            extension = path.suffix.casefold() or "[none]"
            extensions[extension] = extensions.get(extension, 0) + 1
            if extension in {".sln", ".slnx", ".csproj"}:
                projects.append(path.relative_to(self._root).as_posix())
        return {"fileCount": min(count, maximum), "totalBytes": total_bytes, "extensions": extensions, "projects": projects, "truncated": count > maximum}

    def _git(self, arguments: list[str], maximum: int = 100000) -> str:
        try:
            result = subprocess.run(["git", "-C", str(self._root), *arguments], capture_output=True, text=True, timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.TimeoutExpired) as error:
            raise WorkflowAgentToolError(f"Git inspection failed: {error}") from error
        if result.returncode != 0:
            raise WorkflowAgentToolError((result.stderr or "The sandbox is not a Git repository.")[:2000])
        return result.stdout[:maximum]

    def _git_context(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if arguments:
            raise WorkflowAgentToolError("getGitContext does not accept arguments.")
        return {"branch": self._git(["branch", "--show-current"], 500).strip(), "status": self._git(["status", "--short"], 50000)}

    def _git_history(self, arguments: dict[str, Any]) -> dict[str, Any]:
        maximum = self._integer(arguments.get("maxEntries"), 20, 1, 100, "maxEntries")
        command = ["log", f"-{maximum}", "--date=iso-strict", "--pretty=format:%H%x09%ad%x09%an%x09%s"]
        if arguments.get("path") is not None:
            path = self._resolve(arguments.get("path"))
            command.extend(["--", path.relative_to(self._root).as_posix()])
        return {"history": self._git(command)}

    def _git_blame(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve(arguments.get("path"))
        start = self._integer(arguments.get("startLine"), 1, 1, 1_000_000, "startLine")
        end = self._integer(arguments.get("endLine"), min(start + 199, 1_000_000), start, min(start + 499, 1_000_000), "endLine")
        relative = path.relative_to(self._root).as_posix()
        return {"path": relative, "startLine": start, "endLine": end, "blame": self._git(["blame", "--line-porcelain", f"-L{start},{end}", "--", relative])}

    @staticmethod
    def _revision(value: Any, name: str) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,199}", value) or value.startswith("-") or ".." in value or "@{" in value:
            raise WorkflowAgentToolError(f"{name} is not a permitted Git revision name.")
        return value

    def _branch_comparison(self, arguments: dict[str, Any]) -> dict[str, Any]:
        base = self._revision(arguments.get("base"), "base")
        target = self._revision(arguments.get("target", "HEAD"), "target")
        maximum = self._integer(arguments.get("maxFiles"), 200, 1, 500, "maxFiles")
        output = self._git(["diff", "--name-status", f"{base}...{target}"])
        lines = output.splitlines()
        return {"base": base, "target": target, "files": lines[:maximum], "truncated": len(lines) > maximum}
