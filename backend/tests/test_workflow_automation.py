from pathlib import Path

from app.storage import JarvisStore
from app.main import parse_workflow_plan_response
from app.main import WorkflowRequest


def make_store(tmp_path: Path) -> JarvisStore:
    store = JarvisStore(tmp_path / "jarvis.db")
    store.initialize()
    return store


def test_workflow_request_accepts_detailed_operating_instructions() -> None:
    request = WorkflowRequest(title="Detailed workflow", description="x" * 10_000)
    assert len(request.description) == 10_000


def test_empty_json_plan_is_rejected_instead_of_becoming_reviewable() -> None:
    plan, questions = parse_workflow_plan_response('```json\n{"plan":"","questions":[]}\n```')
    assert plan == ""
    assert questions == []


def test_malformed_multiline_json_plan_recovers_clean_markdown() -> None:
    response = '''{
      "plan": "# Account Lockout Plan

## Goal
Monitor locked accounts safely.",
      "questions": []
    }
    Additional model commentary.'''
    plan, questions = parse_workflow_plan_response(response)
    assert plan.startswith("# Account Lockout Plan")
    assert "Additional model commentary" not in plan
    assert questions == []


def test_invalid_saved_plan_can_be_returned_to_draft(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow("Invalid plan", "Create a real plan", [], "powershell")
    workflow = store.save_workflow_plan(workflow.id, 'Plan:\n```json\n{"plan":"","questions":[]}\n```', "lmstudio", "model")
    assert workflow.state == "design_review"
    repaired = store.reset_invalid_workflow_plan(workflow.id)
    assert repaired is not None
    assert repaired.state == "draft"
    assert repaired.plan_text == ""


def test_workflow_requires_test_user_and_supervisor_gates(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow("Daily report", "Build the report", [], "powershell")
    assert workflow.state == "draft"
    assert store.set_workflow_schedule(workflow.id, {"trigger": "daily"}) is None

    workflow = store.save_workflow_plan(workflow.id, "Approved design", "ollama", "reasoning-model")
    assert workflow is not None
    assert workflow.state == "design_review"
    assert store.review_workflow(workflow.id, "approve_plan") is None
    assert store.begin_workflow_reevaluation(workflow.id) is not None
    workflow = store.save_workflow_plan(workflow.id, "Final approved design", "ollama", "reasoning-model", finalizing=True)
    assert workflow is not None
    assert workflow.state == "plan_review"
    workflow = store.review_workflow(workflow.id, "approve_plan")
    assert workflow is not None
    assert workflow.state == "plan_approved"
    workflow = store.save_workflow_implementation(workflow.id, "Write-Output 'ready'", "ollama", "coder-model")
    assert workflow is not None
    assert workflow.state == "implementation_review"

    workflow = store.save_prepared_artifact(workflow.id, "a" * 64, {"restricted_execution_allowed": False})
    assert workflow is not None
    workflow = store.review_workflow(workflow.id, "submit_for_test")
    assert workflow is not None and workflow.state == "test_ready"
    assert store.review_workflow(workflow.id, "test_pass") is None
    assert store.begin_workflow_test(workflow.id) is not None
    workflow = store.complete_workflow_test(workflow.id, {
        "artifact_sha256": "a" * 64,
        "profile": "static",
        "status": "passed",
        "permission_manifest": {"restricted_execution_allowed": False},
        "exit_code": 0,
        "stdout": "syntax valid",
        "stderr": "",
        "duration_ms": 10,
        "evidence_sha256": "b" * 64,
        "summary": "Static validation passed.",
    })
    assert workflow is not None and workflow.state == "test_passed"

    for decision, expected in (
        ("user_accept", "user_accepted"),
        ("request_supervisor", "supervisor_pending"),
        ("supervisor_approve", "approved"),
    ):
        workflow = store.review_workflow(workflow.id, decision)
        assert workflow is not None
        assert workflow.state == expected

    scheduled = store.set_workflow_schedule(workflow.id, {"trigger": "daily", "expression": "07:00"})
    assert scheduled is not None
    assert scheduled.state == "scheduled"


def test_implementation_cannot_be_generated_before_plan_approval(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow("Protected task")
    assert store.save_workflow_implementation(workflow.id, "unsafe", "provider", "coder") is None


def test_questions_block_plan_approval_until_answers_are_submitted(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow("Daily export")
    workflow = store.save_workflow_plan(workflow.id, "Draft plan", "ollama", "reasoner", [{"id": "format", "prompt": "Which format?", "required": True, "options": ["CSV", "JSON"]}])
    assert workflow is not None
    assert workflow.state == "needs_clarification"
    assert store.review_workflow(workflow.id, "approve_plan") is None
    answered = store.save_clarification_answer(workflow.id, "format", "CSV")
    assert answered is not None
    assert answered.state == "needs_clarification"
    assert answered.clarification_answers == {"format": "CSV"}


def test_each_answer_is_saved_individually_before_update_draft(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow("Daily export")
    workflow = store.save_workflow_plan(workflow.id, "Draft", "ollama", "reasoner", [
        {"id": "format", "prompt": "Which format?", "required": True, "options": ["CSV", "JSON"]},
        {"id": "recipient", "prompt": "Who receives it?", "required": True, "options": []},
    ])
    assert workflow is not None
    first = store.save_clarification_answer(workflow.id, "format", "CSV")
    assert first is not None
    assert first.state == "needs_clarification"
    assert first.clarification_answers == {"format": "CSV"}
    assert store.begin_workflow_reevaluation(workflow.id) is None
    second = store.save_clarification_answer(workflow.id, "recipient", "operations@example.test")
    assert second is not None
    ready = store.begin_workflow_reevaluation(workflow.id)
    assert ready is not None
    assert ready.state == "draft"


def test_structured_plan_response_exposes_text_and_selectable_questions() -> None:
    plan, questions = parse_workflow_plan_response('{"plan":"Use a safe export.","questions":[{"id":"format","prompt":"Which format?","required":true,"options":["CSV","JSON"]}]}')
    assert plan == "Use a safe export."
    assert questions[0]["id"] == "format"
    assert questions[0]["options"] == ["CSV", "JSON"]


def test_markdown_plan_questions_are_converted_to_renderable_inputs() -> None:
    plan, questions = parse_workflow_plan_response("""### Goal
Monitor accounts.

#### Clarification Questions:
1. Which notification endpoint should be used?
2. How should earlier accounts be handled?

#### Ordered Steps
1. Query accounts.
""")
    assert plan.startswith("### Goal")
    assert [question["prompt"] for question in questions] == [
        "Which notification endpoint should be used?",
        "How should earlier accounts be handled?",
    ]


def test_malformed_model_json_with_unresolved_requirements_cannot_bypass_review() -> None:
    plan, questions = parse_workflow_plan_response('{"plan":"Domain: bsoc.local (to be confirmed).\\nNotification method: not specified and requires clarification.')
    assert plan.startswith('{"plan"')
    assert len(questions) == 2
    assert all(question["required"] for question in questions)


def test_edit_increments_revision_and_invalidates_approval(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow("Daily report", "First version")
    revised = store.update_workflow(workflow.id, "Daily report", "Second version", [], "csharp")
    assert revised is not None
    assert revised.revision == 2
    assert revised.state == "draft"
    assert revised.approval_stage == "draft"
    assert revised.language == "csharp"


def test_archive_is_recoverable_and_hidden_from_active_list(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow("Retired task")
    archived = store.archive_workflow(workflow.id)
    assert archived is not None
    assert archived.archived is True
    assert archived.state == "archived"
    assert store.get_workflows() == []
    assert store.get_workflow(workflow.id) is not None
