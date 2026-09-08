"""Transactional file, search, project, and todo tools for a workflow sandbox."""

import difflib
import fnmatch
import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.security_control import SecurityControlError, SecurityControlPolicy
from app.workflow_agent_tools import WorkflowAgentTool, WorkflowAgentToolError


SANDBOX_FILE_TOOLS = (
    WorkflowAgentTool("manageTodos", "Persist evidence-backed todos for this workflow revision.", {"type": "object", "additionalProperties": False, "properties": {"action": {"type": "string", "enum": ["create", "add", "list", "set"]}, "itemId": {"type": "string"}, "title": {"type": "string", "maxLength": 500}, "status": {"type": "string", "enum": ["pending", "in-progress", "completed", "blocked"]}, "evidence": {"type": "string", "maxLength": 2000}}, "required": ["action"]}),
    WorkflowAgentTool("readWorkspaceFile", "Read a bounded UTF-8 file inside the workflow sandbox.", {"type": "object", "additionalProperties": False, "properties": {"path": {"type": "string"}, "offset": {"type": "integer", "minimum": 0}, "maxChars": {"type": "integer", "minimum": 500, "maximum": 50000}}, "required": ["path"]}),
    WorkflowAgentTool("createFile", "Stage creation of one new sandbox file in an existing change set.", {"type": "object", "additionalProperties": False, "properties": {"changeSetId": {"type": "string"}, "path": {"type": "string"}, "content": {"type": "string", "maxLength": 200000}}, "required": ["changeSetId", "path", "content"]}),
    WorkflowAgentTool("applyEdit", "Stage whole-file replacement with an expected SHA-256 guard.", {"type": "object", "additionalProperties": False, "properties": {"changeSetId": {"type": "string"}, "path": {"type": "string"}, "expectedSha256": {"type": "string"}, "content": {"type": "string", "maxLength": 200000}}, "required": ["changeSetId", "path", "expectedSha256", "content"]}),
    WorkflowAgentTool("previewChangeSet", "Preview a bounded unified diff for a sandbox change set.", {"type": "object", "additionalProperties": False, "properties": {"changeSetId": {"type": "string"}} , "required": ["changeSetId"]}),
    WorkflowAgentTool("beginChangeSet", "Begin a named, request-local sandbox transaction.", {"type": "object", "additionalProperties": False, "properties": {"description": {"type": "string", "maxLength": 1000}}, "required": ["description"]}),
    WorkflowAgentTool("validateChangeSet", "Validate staged paths, sizes, stale guards, and protected-path policy.", {"type": "object", "additionalProperties": False, "properties": {"changeSetId": {"type": "string"}}, "required": ["changeSetId"]}),
    WorkflowAgentTool("commitChangeSet", "Commit a previewed and validated change set inside the non-production sandbox.", {"type": "object", "additionalProperties": False, "properties": {"changeSetId": {"type": "string"}}, "required": ["changeSetId"]}),
    WorkflowAgentTool("rollbackChangeSet", "Restore files committed by one sandbox change set.", {"type": "object", "additionalProperties": False, "properties": {"changeSetId": {"type": "string"}}, "required": ["changeSetId"]}),
    WorkflowAgentTool("searchFiles", "Find bounded sandbox-relative file paths by glob.", {"type": "object", "additionalProperties": False, "properties": {"pattern": {"type": "string"}, "maxResults": {"type": "integer", "minimum": 1, "maximum": 500}}, "required": ["pattern"]}),
    WorkflowAgentTool("searchWorkspaceText", "Search bounded UTF-8 sandbox files for literal text.", {"type": "object", "additionalProperties": False, "properties": {"query": {"type": "string", "maxLength": 500}, "glob": {"type": "string"}, "maxResults": {"type": "integer", "minimum": 1, "maximum": 200}}, "required": ["query"]}),
    WorkflowAgentTool("getRepositoryInstructions", "Read bounded repository instruction files found inside the sandbox.", {"type": "object", "additionalProperties": False, "properties": {"maxChars": {"type": "integer", "minimum": 500, "maximum": 30000}}}),
    WorkflowAgentTool("getValidationRecipe", "Discover typed PowerShell and .NET validation recipes from sandbox artifacts.", {"type": "object", "additionalProperties": False, "properties": {}}),
    WorkflowAgentTool("getProjectStructure", "Inspect bounded solution and project structure inside the sandbox.", {"type": "object", "additionalProperties": False, "properties": {"maxFiles": {"type": "integer", "minimum": 1, "maximum": 500}}}),
    WorkflowAgentTool("getChangedFiles", "List staged or committed files for sandbox change sets.", {"type": "object", "additionalProperties": False, "properties": {"changeSetId": {"type": "string"}}}),
    WorkflowAgentTool("readWorkspaceFiles", "Read bounded sections from up to 20 UTF-8 sandbox files.", {"type": "object", "additionalProperties": False, "properties": {"paths": {"type": "array", "minItems": 1, "maxItems": 20, "items": {"type": "string"}}, "maxCharsPerFile": {"type": "integer", "minimum": 500, "maximum": 50000}}, "required": ["paths"]}),
    WorkflowAgentTool("createDirectory", "Stage creation of one sandbox directory in an existing change set.", {"type": "object", "additionalProperties": False, "properties": {"changeSetId": {"type": "string"}, "path": {"type": "string"}}, "required": ["changeSetId", "path"]}),
    WorkflowAgentTool("replaceFileContent", "Stage guarded whole-file replacement in an existing change set.", {"type": "object", "additionalProperties": False, "properties": {"changeSetId": {"type": "string"}, "path": {"type": "string"}, "expectedSha256": {"type": "string"}, "content": {"type": "string", "maxLength": 200000}}, "required": ["changeSetId", "path", "expectedSha256", "content"]}),
    WorkflowAgentTool("applyWorkspaceEdits", "Atomically stage guarded replacements for up to 20 existing sandbox files.", {"type": "object", "additionalProperties": False, "properties": {"changeSetId": {"type": "string"}, "edits": {"type": "array", "minItems": 1, "maxItems": 20, "items": {"type": "object", "additionalProperties": False, "properties": {"path": {"type": "string"}, "expectedSha256": {"type": "string"}, "content": {"type": "string", "maxLength": 200000}}, "required": ["path", "expectedSha256", "content"]}}}, "required": ["changeSetId", "edits"]}),
)


@dataclass
class FileSnapshot:
    path: Path
    existed: bool
    content: str
    sha256: str


@dataclass
class SandboxChangeSet:
    change_set_id: str
    description: str
    originals: dict[str, FileSnapshot] = field(default_factory=dict)
    staged: dict[str, str] = field(default_factory=dict)
    staged_directories: set[str] = field(default_factory=set)
    phase: str = "draft"


class WorkflowSandboxFileToolContext:
    def __init__(self, root: Path, security_policy: SecurityControlPolicy) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._security = security_policy
        self._change_sets: dict[str, SandboxChangeSet] = {}
        self._metadata = self._root / ".aegis"
        self._metadata.mkdir(exist_ok=True)
        self._todo_path = self._metadata / "todos.json"

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [tool.as_openai_tool() for tool in SANDBOX_FILE_TOOLS]

    async def invoke(self, name: str, arguments: dict[str, Any]) -> str:
        mutating = name in {"manageTodos", "createFile", "applyEdit", "beginChangeSet", "commitChangeSet", "rollbackChangeSet", "createDirectory", "replaceFileContent", "applyWorkspaceEdits"}
        try:
            self._security.require("workflow-sandbox-files", name, mutating=mutating)
        except SecurityControlError as error:
            raise WorkflowAgentToolError(str(error)) from error
        handlers = {
            "manageTodos": self._manage_todos,
            "readWorkspaceFile": self._read_file,
            "createFile": self._create_file,
            "applyEdit": self._apply_edit,
            "previewChangeSet": self._preview,
            "beginChangeSet": self._begin,
            "validateChangeSet": self._validate,
            "commitChangeSet": self._commit,
            "rollbackChangeSet": self._rollback,
            "searchFiles": self._search_files,
            "searchWorkspaceText": self._search_text,
            "getRepositoryInstructions": self._instructions,
            "getValidationRecipe": self._recipes,
            "getProjectStructure": self._project_structure,
            "getChangedFiles": self._changed_files,
            "readWorkspaceFiles": self._read_files,
            "createDirectory": self._create_directory,
            "replaceFileContent": self._apply_edit,
            "applyWorkspaceEdits": self._apply_workspace_edits,
        }
        handler = handlers.get(name)
        if handler is None:
            raise WorkflowAgentToolError(f"Unknown sandbox tool '{name}'; default-deny policy blocked it.")
        return json.dumps(handler(arguments), indent=2)

    def _resolve(self, raw_path: Any, *, allow_missing: bool = False) -> Path:
        if not isinstance(raw_path, str) or not raw_path.strip() or Path(raw_path).is_absolute():
            raise WorkflowAgentToolError("A non-empty sandbox-relative path is required.")
        candidate = (self._root / raw_path).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise WorkflowAgentToolError("The requested path is outside the workflow sandbox.")
        if candidate == self._metadata or self._metadata in candidate.parents:
            raise WorkflowAgentToolError("Aegis sandbox metadata is protected.")
        if not allow_missing and not candidate.exists():
            raise WorkflowAgentToolError("The requested sandbox path does not exist.")
        return candidate

    @staticmethod
    def _sha(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _integer(value: Any, default: int, minimum: int, maximum: int, name: str) -> int:
        value = default if value is None else value
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            raise WorkflowAgentToolError(f"{name} must be between {minimum} and {maximum}.")
        return value

    def _todos(self) -> list[dict[str, str]]:
        if not self._todo_path.exists():
            return []
        try:
            value = json.loads(self._todo_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise WorkflowAgentToolError(f"Workflow todo state is invalid: {error}") from error
        if not isinstance(value, list):
            raise WorkflowAgentToolError("Workflow todo state is invalid.")
        return value

    def _manage_todos(self, arguments: dict[str, Any]) -> dict[str, Any]:
        action = arguments.get("action")
        items = self._todos()
        if action == "create":
            if items:
                raise WorkflowAgentToolError("The workflow revision already has a todo list.")
            items = [self._new_todo("item-1", arguments.get("title"))]
        elif action == "add":
            if len(items) >= 50:
                raise WorkflowAgentToolError("Workflow todo lists are limited to 50 items.")
            items.append(self._new_todo(f"item-{len(items) + 1}", arguments.get("title")))
        elif action == "set":
            item = next((candidate for candidate in items if candidate["id"] == arguments.get("itemId")), None)
            status = arguments.get("status")
            evidence = arguments.get("evidence", "")
            if item is None or status not in {"pending", "in-progress", "completed", "blocked"}:
                raise WorkflowAgentToolError("A known itemId and valid status are required.")
            if status == "completed" and (not isinstance(evidence, str) or not evidence.strip()):
                raise WorkflowAgentToolError("Completing a workflow todo requires evidence.")
            item["status"] = status
            item["evidence"] = evidence.strip()[:2000] if isinstance(evidence, str) else ""
        elif action != "list":
            raise WorkflowAgentToolError("Unsupported todo action.")
        if action != "list":
            temporary = self._todo_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(items, indent=2), encoding="utf-8")
            os.replace(temporary, self._todo_path)
        return {"items": items, "revisionScoped": True}

    @staticmethod
    def _new_todo(item_id: str, title: Any) -> dict[str, str]:
        if not isinstance(title, str) or not title.strip():
            raise WorkflowAgentToolError("A todo title is required.")
        return {"id": item_id, "title": title.strip()[:500], "status": "pending", "evidence": ""}

    def _read_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve(arguments.get("path"))
        if not path.is_file() or path.stat().st_size > 2_000_000:
            raise WorkflowAgentToolError("The requested file is not a bounded regular file.")
        content = path.read_text(encoding="utf-8")
        offset = self._integer(arguments.get("offset"), 0, 0, len(content), "offset")
        maximum = self._integer(arguments.get("maxChars"), 20000, 500, 50000, "maxChars")
        section = content[offset:offset + maximum]
        return {"path": path.relative_to(self._root).as_posix(), "sha256": self._sha(content), "offset": offset, "nextOffset": offset + len(section), "hasMore": offset + len(section) < len(content), "content": section}

    def _read_files(self, arguments: dict[str, Any]) -> dict[str, Any]:
        paths = arguments.get("paths")
        if not isinstance(paths, list) or not 1 <= len(paths) <= 20 or any(not isinstance(item, str) for item in paths):
            raise WorkflowAgentToolError("readWorkspaceFiles requires between 1 and 20 paths.")
        maximum = self._integer(arguments.get("maxCharsPerFile"), 20000, 500, 50000, "maxCharsPerFile")
        return {"files": [self._read_file({"path": item, "offset": 0, "maxChars": maximum}) for item in paths]}

    def _begin(self, arguments: dict[str, Any]) -> dict[str, Any]:
        description = arguments.get("description")
        if not isinstance(description, str) or not description.strip():
            raise WorkflowAgentToolError("A change-set description is required.")
        if len(self._change_sets) >= 20:
            raise WorkflowAgentToolError("The implementation request is limited to 20 change sets.")
        change_set_id = f"workflow-change-{uuid.uuid4()}"
        self._change_sets[change_set_id] = SandboxChangeSet(change_set_id, description.strip()[:1000])
        return {"changeSetId": change_set_id, "phase": "draft"}

    def _change_set(self, arguments: dict[str, Any]) -> SandboxChangeSet:
        change_set_id = arguments.get("changeSetId")
        if not isinstance(change_set_id, str) or change_set_id not in self._change_sets:
            raise WorkflowAgentToolError("A known changeSetId is required.")
        return self._change_sets[change_set_id]

    def _capture(self, change_set: SandboxChangeSet, path: Path) -> None:
        key = path.relative_to(self._root).as_posix()
        if key not in change_set.originals:
            existed = path.exists()
            content = path.read_text(encoding="utf-8") if existed and path.is_file() else ""
            change_set.originals[key] = FileSnapshot(path, existed, content, self._sha(content))

    def _create_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        change_set = self._change_set(arguments)
        self._require_draft(change_set)
        path = self._resolve(arguments.get("path"), allow_missing=True)
        if path.exists() or path.relative_to(self._root).as_posix() in change_set.staged:
            raise WorkflowAgentToolError("createFile requires a new path.")
        self._require_parent_available(change_set, path)
        content = self._content(arguments)
        self._require_change_capacity(change_set, path, content)
        self._capture(change_set, path)
        change_set.staged[path.relative_to(self._root).as_posix()] = content
        return {"changeSetId": change_set.change_set_id, "staged": path.relative_to(self._root).as_posix(), "sha256": self._sha(content)}

    def _create_directory(self, arguments: dict[str, Any]) -> dict[str, Any]:
        change_set = self._change_set(arguments)
        self._require_draft(change_set)
        path = self._resolve(arguments.get("path"), allow_missing=True)
        key = path.relative_to(self._root).as_posix()
        if path.exists() or key in change_set.staged_directories:
            raise WorkflowAgentToolError("createDirectory requires a new path.")
        self._require_parent_available(change_set, path)
        if len(change_set.staged_directories) >= 50:
            raise WorkflowAgentToolError("A change set is limited to 50 staged directories.")
        change_set.staged_directories.add(key)
        return {"changeSetId": change_set.change_set_id, "stagedDirectory": key}

    def _require_parent_available(self, change_set: SandboxChangeSet, path: Path) -> None:
        if path.parent.exists():
            return
        parent_key = path.parent.relative_to(self._root).as_posix()
        if parent_key not in change_set.staged_directories:
            raise WorkflowAgentToolError("The parent directory must exist or be staged first.")

    def _apply_edit(self, arguments: dict[str, Any]) -> dict[str, Any]:
        change_set = self._change_set(arguments)
        self._require_draft(change_set)
        path = self._resolve(arguments.get("path"))
        if not path.is_file():
            raise WorkflowAgentToolError("applyEdit requires an existing file.")
        current = path.read_text(encoding="utf-8")
        expected = arguments.get("expectedSha256")
        if not isinstance(expected, str) or expected != self._sha(current):
            raise WorkflowAgentToolError("The expected SHA-256 is stale or invalid; read the file again.")
        content = self._content(arguments)
        self._require_change_capacity(change_set, path, content)
        self._capture(change_set, path)
        change_set.staged[path.relative_to(self._root).as_posix()] = content
        return {"changeSetId": change_set.change_set_id, "staged": path.relative_to(self._root).as_posix(), "sha256": self._sha(content)}

    def _apply_workspace_edits(self, arguments: dict[str, Any]) -> dict[str, Any]:
        change_set = self._change_set(arguments)
        self._require_draft(change_set)
        edits = arguments.get("edits")
        if not isinstance(edits, list) or not 1 <= len(edits) <= 20 or any(not isinstance(item, dict) for item in edits):
            raise WorkflowAgentToolError("applyWorkspaceEdits requires between 1 and 20 edits.")
        prepared: list[tuple[Path, str]] = []
        seen: set[str] = set()
        for edit in edits:
            path = self._resolve(edit.get("path"))
            key = path.relative_to(self._root).as_posix()
            if key in seen or not path.is_file():
                raise WorkflowAgentToolError("Workspace edit paths must be unique existing files.")
            current = path.read_text(encoding="utf-8")
            if edit.get("expectedSha256") != self._sha(current):
                raise WorkflowAgentToolError(f"The expected SHA-256 for {key} is stale or invalid.")
            content = self._content(edit)
            prepared.append((path, content))
            seen.add(key)
        projected = dict(change_set.staged)
        projected.update({path.relative_to(self._root).as_posix(): content for path, content in prepared})
        if len(projected) > 50 or sum(len(content) for content in projected.values()) > 2_000_000:
            raise WorkflowAgentToolError("The combined workspace edit exceeds change-set limits.")
        for path, content in prepared:
            self._capture(change_set, path)
            change_set.staged[path.relative_to(self._root).as_posix()] = content
        return {"changeSetId": change_set.change_set_id, "staged": sorted(seen)}

    @staticmethod
    def _content(arguments: dict[str, Any]) -> str:
        content = arguments.get("content")
        if not isinstance(content, str) or len(content) > 200000:
            raise WorkflowAgentToolError("File content must be text no larger than 200000 characters.")
        return content

    def _require_change_capacity(self, change_set: SandboxChangeSet, path: Path, content: str) -> None:
        key = path.relative_to(self._root).as_posix()
        if key not in change_set.staged and len(change_set.staged) >= 50:
            raise WorkflowAgentToolError("A change set is limited to 50 files.")
        total = sum(len(value) for staged_key, value in change_set.staged.items() if staged_key != key) + len(content)
        if total > 2_000_000:
            raise WorkflowAgentToolError("A change set is limited to 2000000 staged characters.")

    @staticmethod
    def _require_draft(change_set: SandboxChangeSet) -> None:
        if change_set.phase != "draft":
            raise WorkflowAgentToolError(f"The change set is already {change_set.phase}.")

    def _preview(self, arguments: dict[str, Any]) -> dict[str, Any]:
        change_set = self._change_set(arguments)
        self._require_draft(change_set)
        if not change_set.staged and not change_set.staged_directories:
            raise WorkflowAgentToolError("The change set has no staged files.")
        chunks = []
        for key, after in change_set.staged.items():
            before = change_set.originals[key].content
            chunks.extend(difflib.unified_diff(before.splitlines(), after.splitlines(), fromfile=f"a/{key}", tofile=f"b/{key}", lineterm=""))
        chunks.extend(f"create directory {key}" for key in sorted(change_set.staged_directories))
        preview = "\n".join(chunks)
        change_set.phase = "previewed"
        return {"changeSetId": change_set.change_set_id, "phase": change_set.phase, "preview": preview[:50000], "truncated": len(preview) > 50000}

    def _validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        change_set = self._change_set(arguments)
        if change_set.phase != "previewed":
            raise WorkflowAgentToolError("Preview the change set before validation.")
        stale = [
            key for key, snapshot in change_set.originals.items()
            if (snapshot.existed and (not snapshot.path.exists() or self._sha(snapshot.path.read_text(encoding="utf-8")) != snapshot.sha256))
            or (not snapshot.existed and snapshot.path.exists())
        ]
        stale.extend(key for key in change_set.staged_directories if (self._root / key).exists())
        if stale:
            raise WorkflowAgentToolError("Change-set validation found stale files: " + ", ".join(stale))
        change_set.phase = "validated"
        return {"changeSetId": change_set.change_set_id, "phase": change_set.phase, "files": len(change_set.staged), "directories": len(change_set.staged_directories)}

    def _commit(self, arguments: dict[str, Any]) -> dict[str, Any]:
        change_set = self._change_set(arguments)
        if change_set.phase != "validated":
            raise WorkflowAgentToolError("A change set must be previewed and validated before commit.")
        temporary_files: list[tuple[Path, Path]] = []
        try:
            for key in sorted(change_set.staged_directories, key=lambda value: (value.count("/"), value)):
                (self._root / key).mkdir(parents=True, exist_ok=False)
            for key, content in change_set.staged.items():
                path = self._root / key
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_name(path.name + ".aegis-tmp")
                temporary.write_text(content, encoding="utf-8", newline="\n")
                temporary_files.append((temporary, path))
            for temporary, path in temporary_files:
                os.replace(temporary, path)
        except OSError as error:
            for temporary, _ in temporary_files:
                temporary.unlink(missing_ok=True)
            for snapshot in change_set.originals.values():
                if snapshot.existed:
                    snapshot.path.write_text(snapshot.content, encoding="utf-8", newline="\n")
                else:
                    snapshot.path.unlink(missing_ok=True)
            for key in sorted(change_set.staged_directories, key=lambda value: value.count("/"), reverse=True):
                try:
                    (self._root / key).rmdir()
                except OSError:
                    pass
            raise WorkflowAgentToolError(f"Change-set commit failed and was restored: {error}") from error
        change_set.phase = "committed"
        return {"changeSetId": change_set.change_set_id, "phase": change_set.phase, "files": list(change_set.staged)}

    def _rollback(self, arguments: dict[str, Any]) -> dict[str, Any]:
        change_set = self._change_set(arguments)
        if change_set.phase != "committed":
            raise WorkflowAgentToolError("Only a committed change set can be rolled back.")
        for snapshot in change_set.originals.values():
            if snapshot.existed:
                snapshot.path.parent.mkdir(parents=True, exist_ok=True)
                snapshot.path.write_text(snapshot.content, encoding="utf-8", newline="\n")
            elif snapshot.path.exists():
                snapshot.path.unlink()
        for key in sorted(change_set.staged_directories, key=lambda value: value.count("/"), reverse=True):
            try:
                (self._root / key).rmdir()
            except OSError:
                pass
        change_set.phase = "rolled-back"
        return {"changeSetId": change_set.change_set_id, "phase": change_set.phase}

    def _iter_files(self):
        visited = 0
        for path in sorted(self._root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            visited += 1
            if visited > 5000:
                break
            if path.is_file() and not path.is_symlink() and self._metadata not in path.parents:
                yield path

    def _search_files(self, arguments: dict[str, Any]) -> dict[str, Any]:
        pattern = arguments.get("pattern")
        if not isinstance(pattern, str) or not pattern.strip():
            raise WorkflowAgentToolError("A file glob is required.")
        maximum = self._integer(arguments.get("maxResults"), 100, 1, 500, "maxResults")
        matches = []
        for path in self._iter_files():
            relative = path.relative_to(self._root).as_posix()
            if fnmatch.fnmatch(relative, pattern):
                matches.append(relative)
                if len(matches) > maximum:
                    break
        return {"matches": matches[:maximum], "truncated": len(matches) > maximum}

    def _search_text(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query")
        glob = arguments.get("glob", "*")
        if not isinstance(query, str) or not query or len(query) > 500 or not isinstance(glob, str):
            raise WorkflowAgentToolError("A bounded literal query and valid glob are required.")
        maximum = self._integer(arguments.get("maxResults"), 50, 1, 200, "maxResults")
        results = []
        for path in self._iter_files():
            relative = path.relative_to(self._root).as_posix()
            if not fnmatch.fnmatch(relative, glob) or path.stat().st_size > 2_000_000:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for number, line in enumerate(lines, 1):
                if query.casefold() in line.casefold():
                    results.append({"path": relative, "line": number, "preview": line[:500]})
                    if len(results) >= maximum:
                        return {"results": results, "truncated": True}
        return {"results": results, "truncated": False}

    def _instructions(self, arguments: dict[str, Any]) -> dict[str, Any]:
        maximum = self._integer(arguments.get("maxChars"), 12000, 500, 30000, "maxChars")
        names = {"AGENTS.md", "CLAUDE.md", "copilot-instructions.md"}
        sections = []
        used = 0
        for path in self._iter_files():
            if path.name not in names:
                continue
            content = path.read_text(encoding="utf-8")[:maximum - used]
            sections.append({"path": path.relative_to(self._root).as_posix(), "content": content})
            used += len(content)
            if used >= maximum:
                break
        return {"instructions": sections, "truncated": used >= maximum}

    def _recipes(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if arguments:
            raise WorkflowAgentToolError("getValidationRecipe does not accept arguments.")
        recipes = []
        for path in self._iter_files():
            relative = path.relative_to(self._root).as_posix()
            suffix = path.suffix.casefold()
            if suffix == ".ps1":
                recipes.append({"operation": "powershellSyntax", "path": relative})
            elif suffix in {".csproj", ".sln", ".slnx"}:
                recipes.extend([{"operation": "dotnetBuild", "path": relative}, {"operation": "dotnetTest", "path": relative}])
            if len(recipes) >= 100:
                break
        return {"recipes": recipes, "count": len(recipes)}

    def _project_structure(self, arguments: dict[str, Any]) -> dict[str, Any]:
        maximum = self._integer(arguments.get("maxFiles"), 200, 1, 500, "maxFiles")
        files = []
        for path in self._iter_files():
            relative = path.relative_to(self._root).as_posix()
            if path.suffix.casefold() in {".sln", ".slnx", ".csproj", ".props", ".targets", ".ps1", ".cs", ".xaml"}:
                files.append({"path": relative, "type": path.suffix.casefold().lstrip("."), "bytes": path.stat().st_size})
            if len(files) >= maximum:
                break
        return {"files": files, "count": len(files)}

    def _changed_files(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if arguments.get("changeSetId"):
            change_sets = [self._change_set(arguments)]
        else:
            change_sets = list(self._change_sets.values())
        return {"changeSets": [{"changeSetId": item.change_set_id, "description": item.description, "phase": item.phase, "directories": sorted(item.staged_directories), "files": [{"path": key, "sha256": self._sha(value)} for key, value in item.staged.items()]} for item in change_sets]}
