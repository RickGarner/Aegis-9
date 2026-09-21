import json
from pathlib import Path

import pytest

from app.authorization import AuthorizationError, RoleAuthorizer, WindowsPrincipal


def policy(tmp_path: Path, assignments: list[dict]) -> Path:
    path = tmp_path / "roles.json"
    path.write_text(json.dumps({"schemaVersion": 1, "assignments": assignments}), encoding="utf-8")
    return path


def test_user_and_group_roles_are_combined(tmp_path: Path) -> None:
    authorizer = RoleAuthorizer(policy(tmp_path, [
        {"type": "user", "subject": "BSOC\\alice", "roles": ["Operator"]},
        {"type": "group", "subject": "BSOC\\Monitoring Admins", "roles": ["MonitoringAdministrator"]},
    ]))
    principal = WindowsPrincipal("bsoc\\ALICE", frozenset({"bsoc\\monitoring admins"}))
    assert authorizer.roles_for(principal) == {"Operator", "MonitoringAdministrator"}
    authorizer.require("monitoring.configure", principal)


def test_direct_call_is_denied_without_required_role(tmp_path: Path) -> None:
    authorizer = RoleAuthorizer(policy(tmp_path, [{"type": "user", "subject": "BSOC\\reader", "roles": ["Operator"]}]))
    with pytest.raises(AuthorizationError, match="not authorized"):
        authorizer.require("credentials.manage", WindowsPrincipal("BSOC\\reader"))


def test_unknown_capability_and_invalid_role_fail_closed(tmp_path: Path) -> None:
    authorizer = RoleAuthorizer(policy(tmp_path, []))
    with pytest.raises(AuthorizationError, match="Unknown capability"):
        authorizer.require("unregistered.action", WindowsPrincipal("BSOC\\user"))
    invalid = policy(tmp_path, [{"type": "user", "subject": "BSOC\\user", "roles": ["Administrator"]}])
    with pytest.raises(AuthorizationError, match="invalid"):
        RoleAuthorizer(invalid).roles_for(WindowsPrincipal("BSOC\\user"))


@pytest.mark.parametrize("roles", [[], ["Operator", "Operator"]])
def test_empty_or_duplicate_role_assignments_fail_closed(tmp_path: Path, roles: list[str]) -> None:
    invalid = policy(tmp_path, [{"type": "user", "subject": "BSOC\\user", "roles": roles}])
    with pytest.raises(AuthorizationError, match="invalid"):
        RoleAuthorizer(invalid).roles_for(WindowsPrincipal("BSOC\\user"))


def test_assignment_subject_whitespace_is_normalized(tmp_path: Path) -> None:
    authorizer = RoleAuthorizer(policy(tmp_path, [
        {"type": "group", "subject": "  BSOC\\Aegis Operators  ", "roles": ["Operator"]},
    ]))
    assert authorizer.roles_for(WindowsPrincipal("BSOC\\user", frozenset({"BSOC\\Aegis Operators"}))) == {"Operator"}
