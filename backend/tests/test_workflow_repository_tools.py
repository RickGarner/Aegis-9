import asyncio
import json
import subprocess
from pathlib import Path

import pytest

from app.security_control import SecurityControlPolicy
from app.workflow_agent_tools import WorkflowAgentToolError
from app.workflow_repository_tools import REPOSITORY_TOOLS, WorkflowRepositoryToolContext


def make_context(tmp_path: Path) -> WorkflowRepositoryToolContext:
    policy = tmp_path / "security.json"
    policy.write_text(json.dumps({"schema_version": 1, "global_kill_switch": False, "adapters": {"workflow-repository-tools": {"enabled": True, "mode": "read-only", "capabilities": [tool.name for tool in REPOSITORY_TOOLS]}}}), encoding="utf-8")
    return WorkflowRepositoryToolContext(tmp_path / "sandbox", SecurityControlPolicy(policy))


def invoke(context: WorkflowRepositoryToolContext, name: str, arguments: dict) -> dict:
    return json.loads(asyncio.run(context.invoke(name, arguments)))


def test_repository_catalog_has_ten_closed_read_only_schemas() -> None:
    assert len(REPOSITORY_TOOLS) == 10
    assert len({tool.name for tool in REPOSITORY_TOOLS}) == 10
    assert all(tool.parameters["type"] == "object" and tool.parameters["additionalProperties"] is False for tool in REPOSITORY_TOOLS)


def test_outlines_dependencies_maps_ranked_context_and_summary(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    project = context._root / "App.csproj"
    project.write_text('<Project><ItemGroup><PackageReference Include="Example" /></ItemGroup></Project>', encoding="utf-8")
    source = context._root / "Monitor.cs"
    source.write_text("public class Monitor {\n public void Refresh() {}\n}\n", encoding="utf-8")
    script = context._root / "Health.ps1"
    script.write_text("Import-Module Pester\nfunction Get-Health { 'healthy' }", encoding="utf-8")

    assert invoke(context, "getFileOutline", {"path": "Health.ps1"})["symbols"][0]["name"] == "Get-Health"
    dependencies = invoke(context, "getDependencyGraph", {})["edges"]
    assert {edge["to"] for edge in dependencies} == {"Example", "Pester"}
    assert invoke(context, "getRepositoryMap", {})["files"]
    assert invoke(context, "getRankedWorkspaceContext", {"query": "healthy"})["results"][0]["path"] == "Health.ps1"
    summary = invoke(context, "summarizeRepositoryContext", {})
    assert summary["fileCount"] == 3
    assert summary["projects"] == ["App.csproj"]


def test_reads_compiler_diagnostics_from_bounded_sandbox_logs(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    (context._root / "build.log").write_text(r"D:\Work\Monitor.cs(8,4): error CS1002: ; expected", encoding="utf-8")
    result = invoke(context, "getWorkspaceDiagnostics", {})
    assert result["diagnostics"][0]["code"] == "CS1002"
    assert result["diagnostics"][0]["line"] == 8


def test_git_tools_use_sandbox_paths_and_validated_revisions(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    subprocess.run(["git", "init", "-q", "-b", "main", str(context._root)], check=True)
    subprocess.run(["git", "-C", str(context._root), "config", "user.email", "test@local"], check=True)
    subprocess.run(["git", "-C", str(context._root), "config", "user.name", "Local Test"], check=True)
    source = context._root / "workflow.ps1"
    source.write_text("Write-Output 'ok'\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(context._root), "add", "workflow.ps1"], check=True)
    subprocess.run(["git", "-C", str(context._root), "commit", "-q", "-m", "initial"], check=True)

    assert invoke(context, "getGitContext", {})["branch"] == "main"
    assert "initial" in invoke(context, "getGitHistory", {"maxEntries": 1})["history"]
    assert invoke(context, "getGitBlame", {"path": "workflow.ps1", "startLine": 1, "endLine": 1})["blame"]
    assert invoke(context, "getBranchComparison", {"base": "HEAD", "target": "HEAD"})["files"] == []
    with pytest.raises(WorkflowAgentToolError, match="not a permitted"):
        invoke(context, "getBranchComparison", {"base": "--output=bad"})
