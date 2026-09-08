import json
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.security_control import SecurityControlPolicy
from app.workflow_agent_tools import WorkflowAgentToolContext, WorkflowAgentToolError


class FakeStore:
    def get_file_content(self, file_id: int) -> str | None:
        return "workflow attachment content" if file_id == 7 else None


def write_policy(path: Path, capabilities: list[str]) -> None:
    path.write_text(json.dumps({"schema_version": 1, "global_kill_switch": False, "adapters": {"workflow-design-tools": {"enabled": True, "mode": "read-only", "capabilities": capabilities}}}), encoding="utf-8")


def test_workflow_tools_are_bounded_to_the_current_workflow(tmp_path: Path) -> None:
    policy_path = tmp_path / "security.json"
    write_policy(policy_path, ["get_workflow_request", "list_workflow_attachments", "read_workflow_attachment"])
    workflow = SimpleNamespace(title="Health check", description="Inspect servers", language="powershell", revision=3, clarification_answers={"scope": "test"}, attachment_ids=[7])
    tools = WorkflowAgentToolContext(FakeStore(), workflow, SecurityControlPolicy(policy_path))

    request = json.loads(asyncio.run(tools.invoke("get_workflow_request", {})))
    attachment = json.loads(asyncio.run(tools.invoke("read_workflow_attachment", {"fileId": 7, "maxChars": 500})))

    assert request == {"title": "Health check", "request": "Inspect servers", "language": "powershell", "revision": 3, "clarificationAnswers": {"scope": "test"}}
    assert attachment["content"] == "workflow attachment content"
    with pytest.raises(WorkflowAgentToolError, match="not attached"):
        asyncio.run(tools.invoke("read_workflow_attachment", {"fileId": 8}))


def test_workflow_tools_fail_closed_when_capability_is_absent(tmp_path: Path) -> None:
    policy_path = tmp_path / "security.json"
    write_policy(policy_path, ["get_workflow_request"])
    workflow = SimpleNamespace(title="x", description="x", language="powershell", revision=1, clarification_answers={}, attachment_ids=[])
    tools = WorkflowAgentToolContext(FakeStore(), workflow, SecurityControlPolicy(policy_path))

    with pytest.raises(WorkflowAgentToolError, match="not authorized"):
        asyncio.run(tools.invoke("list_workflow_attachments", {}))


def test_workflow_coordination_tools_are_read_only_and_evidence_backed(tmp_path: Path) -> None:
    capabilities = ["askQuestions", "getRequestExecutionState", "getCompletionCriteria", "getValidationEvidence", "getArtifactManifest"]
    policy_path = tmp_path / "security.json"
    write_policy(policy_path, capabilities)
    workflow = SimpleNamespace(
        id=9, revision=4, state="test_ready", approval_stage="testing", scheduler_status="not_scheduled",
        latest_test_status="passed", latest_test_summary="isolated tests passed", latest_test_evidence_sha256="evidence-hash",
        artifact_sha256="artifact-hash", language="powershell", implementation_provider="dockerModelRunner",
        implementation_model="qwen", permission_manifest={"network": False}, clarification_questions=[{"id": "scope", "required": True}],
        clarification_answers={"scope": "test only"}, plan_text="approved plan", test_plan_text="approved tests",
        supervisor_approved_by="", supervisor_approved_at=None,
    )
    tools = WorkflowAgentToolContext(FakeStore(), workflow, SecurityControlPolicy(policy_path))

    questions = json.loads(asyncio.run(tools.invoke("askQuestions", {"questions": [{"id": "scope", "prompt": "Which scope?", "options": ["test", "production"]}]})))
    state = json.loads(asyncio.run(tools.invoke("getRequestExecutionState", {})))
    completion = json.loads(asyncio.run(tools.invoke("getCompletionCriteria", {})))
    evidence = json.loads(asyncio.run(tools.invoke("getValidationEvidence", {})))
    manifest = json.loads(asyncio.run(tools.invoke("getArtifactManifest", {})))

    assert questions["requiresUserReview"] is True
    assert questions["submittedAnswers"] == {"scope": "test only"}
    assert state["state"] == "test_ready"
    assert completion["criteria"]["nonProductionTestsPassed"] is True
    assert completion["productionActionAvailable"] is False
    assert evidence["evidenceSha256"] == "evidence-hash"
    assert manifest["artifactSha256"] == "artifact-hash"
    assert manifest["executableContentIncluded"] is False
