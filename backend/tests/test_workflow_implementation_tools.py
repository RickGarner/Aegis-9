import asyncio
import json
from pathlib import Path

import pytest

from app.security_control import SecurityControlPolicy
from app.workflow_agent_tools import WorkflowAgentToolError
from app.workflow_implementation_tools import SandboxSession, WorkflowImplementationToolContext


class FakeProcess:
    def __init__(self, running: bool = True) -> None:
        self.running = running
        self.returncode = None if running else 0
        self.killed = False

    def poll(self):
        return None if self.running else self.returncode

    def kill(self) -> None:
        self.killed = True
        self.running = False
        self.returncode = -9


def write_policy(path: Path, capabilities: list[str]) -> None:
    path.write_text(json.dumps({"schema_version": 1, "global_kill_switch": False, "adapters": {"workflow-implementation-tools": {"enabled": True, "mode": "read-write", "capabilities": capabilities}}}), encoding="utf-8")


def make_context(tmp_path: Path) -> WorkflowImplementationToolContext:
    policy = tmp_path / "security.json"
    write_policy(policy, ["listDirectory", "startTerminalSession", "getTerminalOutput", "cancelTerminalSession", "getStructuredFailures", "discoverTests", "buildProjects", "runTargetedTests", "runFormatter", "runLinter", "runStaticAnalysis"])
    return WorkflowImplementationToolContext(tmp_path / "sandbox", SecurityControlPolicy(policy))


def test_lists_only_the_revision_sandbox_and_rejects_traversal(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    (tmp_path / "sandbox" / "src").mkdir()
    (tmp_path / "sandbox" / "src" / "workflow.ps1").write_text("Write-Output 'ok'", encoding="utf-8")

    result = json.loads(asyncio.run(context.invoke("listDirectory", {"path": ".", "maxDepth": 2})))
    assert [entry["path"] for entry in result["entries"]] == ["src", "src/workflow.ps1"]
    with pytest.raises(WorkflowAgentToolError, match="outside"):
        asyncio.run(context.invoke("listDirectory", {"path": ".."}))


def test_terminal_results_are_retained_parsed_and_cancelled_by_exact_id(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    process = FakeProcess()
    session = SandboxSession("workflow-terminal-test", "dotnetBuild", "test.csproj", process)  # type: ignore[arg-type]
    session.output = r"D:\Test\File.cs(4,9): error CS1002: ; expected"
    context._sessions[session.session_id] = session

    output = json.loads(asyncio.run(context.invoke("getTerminalOutput", {"sessionId": session.session_id, "maxChars": 500})))
    failures = json.loads(asyncio.run(context.invoke("getStructuredFailures", {"sessionId": session.session_id})))
    cancelled = json.loads(asyncio.run(context.invoke("cancelTerminalSession", {"sessionId": session.session_id})))

    assert output["outputLength"] > 0
    assert failures["failures"][0]["code"] == "CS1002"
    assert cancelled["status"] == "cancelled"
    assert process.killed is True


def test_terminal_start_accepts_only_typed_file_appropriate_operations(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    script = tmp_path / "sandbox" / "workflow.ps1"
    script.write_text("Write-Output 'ok'", encoding="utf-8")
    command = context._command("powershellSyntax", script)
    assert command[0] == "powershell.exe"
    with pytest.raises(WorkflowAgentToolError, match="not allowed"):
        context._command("dotnetBuild", script)


def test_discovers_tests_and_builds_only_typed_validation_commands(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    test_script = tmp_path / "sandbox" / "workflow.Tests.ps1"
    test_script.write_text("Describe 'workflow' {}", encoding="utf-8")
    discovered = json.loads(asyncio.run(context.invoke("discoverTests", {})))
    assert discovered["tests"] == [{"path": "workflow.Tests.ps1", "type": "pester"}]
    project = tmp_path / "sandbox" / "Workflow.csproj"
    project.write_text("<Project />", encoding="utf-8")
    assert context._command("dotnetFormatCheck", project)[:2] == ["dotnet", "format"]
    assert context._command("dotnetAnalyze", project)[:2] == ["dotnet", "format"]
