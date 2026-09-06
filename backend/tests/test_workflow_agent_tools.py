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
