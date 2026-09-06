import json
from pathlib import Path

import pytest

from app.security_control import SecurityControlError, SecurityControlPolicy


def write_policy(path: Path, *, kill: bool = False, adapters: dict | None = None) -> None:
    path.write_text(json.dumps({"schema_version": 1, "global_kill_switch": kill, "adapters": adapters or {}}), encoding="utf-8")


def test_registered_adapter_capability_is_allowed(tmp_path: Path) -> None:
    path = tmp_path / "security.json"
    write_policy(path, adapters={"workflow-execution": {"enabled": True, "mode": "read-write", "capabilities": ["execute-approved-workflow"]}})

    policy = SecurityControlPolicy(path).require("workflow-execution", "execute-approved-workflow", mutating=True)

    assert policy.adapter_id == "workflow-execution"


def test_unknown_adapter_is_denied_by_default(tmp_path: Path) -> None:
    path = tmp_path / "security.json"
    write_policy(path)

    with pytest.raises(SecurityControlError, match="not registered; default-deny"):
        SecurityControlPolicy(path).require("unknown", "execute", mutating=True)


def test_global_kill_switch_blocks_mutation_but_not_registered_read_only_status(tmp_path: Path) -> None:
    path = tmp_path / "security.json"
    write_policy(path, kill=True, adapters={"status": {"enabled": True, "mode": "read-only", "capabilities": ["read-status"]}})
    policy = SecurityControlPolicy(path)

    with pytest.raises(SecurityControlError, match="global kill switch"):
        policy.require("status", "read-status", mutating=True)
    assert policy.require("status", "read-status", mutating=False).mode == "read-only"


def test_invalid_or_missing_policy_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(SecurityControlError, match="unavailable or invalid"):
        SecurityControlPolicy(tmp_path / "missing.json").require("workflow-execution", "execute-approved-workflow", mutating=True)


def test_malformed_adapter_policy_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "security.json"
    write_policy(path, adapters={"workflow-execution": {"enabled": True, "mode": "read-write", "capabilities": None}})

    with pytest.raises(SecurityControlError, match="invalid security policy"):
        SecurityControlPolicy(path).require("workflow-execution", "execute-approved-workflow", mutating=True)
