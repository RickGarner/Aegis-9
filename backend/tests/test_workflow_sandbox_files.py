import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from app.security_control import SecurityControlPolicy
from app.workflow_agent_tools import WorkflowAgentToolError
from app.workflow_sandbox_files import SANDBOX_FILE_TOOLS, WorkflowSandboxFileToolContext


CAPABILITIES = [tool.name for tool in SANDBOX_FILE_TOOLS]


def context(tmp_path: Path) -> WorkflowSandboxFileToolContext:
    policy = tmp_path / "security.json"
    policy.write_text(json.dumps({"schema_version": 1, "global_kill_switch": False, "adapters": {"workflow-sandbox-files": {"enabled": True, "mode": "read-write", "capabilities": CAPABILITIES}}}), encoding="utf-8")
    return WorkflowSandboxFileToolContext(tmp_path / "sandbox", SecurityControlPolicy(policy))


def invoke(tools: WorkflowSandboxFileToolContext, name: str, arguments: dict) -> dict:
    return json.loads(asyncio.run(tools.invoke(name, arguments)))


def test_catalog_contains_the_nineteen_closed_schema_tools() -> None:
    assert len(SANDBOX_FILE_TOOLS) == 19
    assert len(set(CAPABILITIES)) == 19
    assert all(tool.parameters.get("type") == "object" and tool.parameters.get("additionalProperties") is False for tool in SANDBOX_FILE_TOOLS)


def test_todos_persist_by_revision_and_require_completion_evidence(tmp_path: Path) -> None:
    tools = context(tmp_path)
    invoke(tools, "manageTodos", {"action": "create", "title": "Create workflow"})
    invoke(tools, "manageTodos", {"action": "add", "title": "Validate workflow"})
    with pytest.raises(WorkflowAgentToolError, match="requires evidence"):
        invoke(tools, "manageTodos", {"action": "set", "itemId": "item-1", "status": "completed"})
    invoke(tools, "manageTodos", {"action": "set", "itemId": "item-1", "status": "completed", "evidence": "change set committed"})

    reloaded = WorkflowSandboxFileToolContext(tools._root, tools._security)
    assert invoke(reloaded, "manageTodos", {"action": "list"})["items"][0]["evidence"] == "change set committed"


def test_change_set_requires_preview_and_validation_before_commit_and_can_rollback(tmp_path: Path) -> None:
    tools = context(tmp_path)
    existing = tools._root / "workflow.ps1"
    existing.write_text("Write-Output 'before'\n", encoding="utf-8")
    digest = hashlib.sha256(existing.read_text(encoding="utf-8").encode()).hexdigest()
    change_set_id = invoke(tools, "beginChangeSet", {"description": "Update workflow"})["changeSetId"]
    invoke(tools, "applyEdit", {"changeSetId": change_set_id, "path": "workflow.ps1", "expectedSha256": digest, "content": "Write-Output 'after'\n"})
    invoke(tools, "createDirectory", {"changeSetId": change_set_id, "path": "tests"})
    invoke(tools, "createFile", {"changeSetId": change_set_id, "path": "tests/workflow.Tests.ps1", "content": "Describe 'workflow' {}\n"})
    with pytest.raises(WorkflowAgentToolError, match="previewed and validated"):
        invoke(tools, "commitChangeSet", {"changeSetId": change_set_id})
    assert "workflow.ps1" in invoke(tools, "previewChangeSet", {"changeSetId": change_set_id})["preview"]
    invoke(tools, "validateChangeSet", {"changeSetId": change_set_id})
    invoke(tools, "commitChangeSet", {"changeSetId": change_set_id})
    assert "after" in existing.read_text(encoding="utf-8")
    assert (tools._root / "tests" / "workflow.Tests.ps1").exists()
    invoke(tools, "rollbackChangeSet", {"changeSetId": change_set_id})
    assert "before" in existing.read_text(encoding="utf-8")
    assert not (tools._root / "tests" / "workflow.Tests.ps1").exists()


def test_stale_and_out_of_sandbox_changes_fail_closed(tmp_path: Path) -> None:
    tools = context(tmp_path)
    existing = tools._root / "workflow.cs"
    existing.write_text("class A {}", encoding="utf-8")
    change_set_id = invoke(tools, "beginChangeSet", {"description": "stale test"})["changeSetId"]
    with pytest.raises(WorkflowAgentToolError, match="stale"):
        invoke(tools, "applyEdit", {"changeSetId": change_set_id, "path": "workflow.cs", "expectedSha256": "bad", "content": "class B {}"})
    with pytest.raises(WorkflowAgentToolError, match="outside"):
        invoke(tools, "readWorkspaceFile", {"path": "../security.json"})
    with pytest.raises(WorkflowAgentToolError, match="protected"):
        invoke(tools, "readWorkspaceFile", {"path": ".aegis/todos.json"})


def test_search_instructions_recipes_structure_and_changed_files_are_bounded(tmp_path: Path) -> None:
    tools = context(tmp_path)
    (tools._root / "src").mkdir()
    (tools._root / "src" / "workflow.ps1").write_text("Write-Output 'health'", encoding="utf-8")
    (tools._root / "AGENTS.md").write_text("Keep tests local.", encoding="utf-8")
    assert invoke(tools, "searchFiles", {"pattern": "**/*.ps1"})["matches"] == ["src/workflow.ps1"]
    assert invoke(tools, "searchWorkspaceText", {"query": "health"})["results"][0]["line"] == 1
    assert invoke(tools, "getRepositoryInstructions", {})["instructions"][0]["path"] == "AGENTS.md"
    assert invoke(tools, "getValidationRecipe", {})["recipes"][0]["operation"] == "powershellSyntax"
    assert invoke(tools, "getProjectStructure", {})["files"][0]["path"] == "src/workflow.ps1"
    change_set_id = invoke(tools, "beginChangeSet", {"description": "new file"})["changeSetId"]
    invoke(tools, "createFile", {"changeSetId": change_set_id, "path": "README.md", "content": "workflow"})
    assert invoke(tools, "getChangedFiles", {})["changeSets"][0]["files"][0]["path"] == "README.md"


def test_multi_file_reads_and_edits_are_guarded_as_one_transaction(tmp_path: Path) -> None:
    tools = context(tmp_path)
    first = tools._root / "first.txt"
    second = tools._root / "second.txt"
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")
    read = invoke(tools, "readWorkspaceFiles", {"paths": ["first.txt", "second.txt"], "maxCharsPerFile": 500})
    change_set_id = invoke(tools, "beginChangeSet", {"description": "both files"})["changeSetId"]
    edits = [{"path": item["path"], "expectedSha256": item["sha256"], "content": item["content"].upper()} for item in read["files"]]
    assert invoke(tools, "applyWorkspaceEdits", {"changeSetId": change_set_id, "edits": edits})["staged"] == ["first.txt", "second.txt"]
    invoke(tools, "previewChangeSet", {"changeSetId": change_set_id})
    invoke(tools, "validateChangeSet", {"changeSetId": change_set_id})
    invoke(tools, "commitChangeSet", {"changeSetId": change_set_id})
    assert first.read_text(encoding="utf-8") == "ONE"
    assert second.read_text(encoding="utf-8") == "TWO"
