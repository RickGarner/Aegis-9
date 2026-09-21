import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from app.authorization import RoleAuthorizer, WindowsPrincipal
from app.config import Settings
from app.main import WorkflowReviewRequest, app, require_capability, require_workflow_review_capability


def role_policy(tmp_path: Path) -> Path:
    path = tmp_path / "roles.json"
    path.write_text(json.dumps({
        "schemaVersion": 1,
        "assignments": [
            {"type": "user", "subject": "BSOC\\reader", "roles": ["Operator"]},
            {"type": "user", "subject": "BSOC\\designer", "roles": ["WorkflowDesigner"]},
            {"type": "user", "subject": "BSOC\\approver", "roles": ["WorkflowApprover"]},
            {"type": "user", "subject": "BSOC\\supervisor", "roles": ["Supervisor"]},
        ],
    }), encoding="utf-8")
    return path


def test_capability_dependency_allows_and_denies_exact_roles(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(JARVIS_ROLE_MAPPING_PATH=role_policy(tmp_path))
    dependency = require_capability("monitoring.read")
    monkeypatch.setattr(RoleAuthorizer, "current_principal", lambda _: WindowsPrincipal("BSOC\\reader"))
    assert dependency(settings) == {"Operator"}

    configure = require_capability("monitoring.configure")
    with pytest.raises(HTTPException) as denied:
        configure(settings)
    assert denied.value.status_code == 403


@pytest.mark.parametrize(
    ("identity", "decision", "allowed"),
    [
        ("BSOC\\designer", "submit_for_test", True),
        ("BSOC\\designer", "approve_plan", False),
        ("BSOC\\approver", "approve_plan", True),
        ("BSOC\\approver", "submit_for_test", False),
        ("BSOC\\supervisor", "supervisor_approve", True),
        ("BSOC\\approver", "supervisor_approve", False),
    ],
)
def test_workflow_review_dependency_uses_decision_specific_capability(
    tmp_path: Path,
    monkeypatch,
    identity: str,
    decision: str,
    allowed: bool,
) -> None:
    settings = Settings(JARVIS_ROLE_MAPPING_PATH=role_policy(tmp_path))
    monkeypatch.setattr(RoleAuthorizer, "current_principal", lambda _: WindowsPrincipal(identity))
    request = WorkflowReviewRequest(decision=decision)
    if allowed:
        assert require_workflow_review_capability(request, settings)
    else:
        with pytest.raises(HTTPException) as denied:
            require_workflow_review_capability(request, settings)
        assert denied.value.status_code == 403


def test_sensitive_routes_declare_backend_authorization_dependencies() -> None:
    expected = {
        ("GET", "/api/monitoring"): "monitoring.read",
        ("POST", "/api/monitoring/actions"): "monitoring.configure",
        ("POST", "/api/monitoring/alerts/{alert_id}/resolve"): "monitoring.acknowledge",
        ("POST", "/api/workflows"): "workflow.design",
        ("GET", "/api/workflows"): "workflow.read",
        ("POST", "/api/workflows/{workflow_id}/execute"): "workflow.execute",
        ("PUT", "/api/workflows/{workflow_id}/schedule"): "workflow.approve",
        ("POST", "/api/notifications/{item_id}/retry"): "monitoring.configure",
    }
    routes = {
        (method, route.path): route
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }
    for key, capability in expected.items():
        dependencies = routes[key].dependant.dependencies
        assert capability in {getattr(item.call, "required_capability", None) for item in dependencies}

    review = routes[("POST", "/api/workflows/{workflow_id}/review")]
    assert require_workflow_review_capability in {item.call for item in review.dependant.dependencies}
