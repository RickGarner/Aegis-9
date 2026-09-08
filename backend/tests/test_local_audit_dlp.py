from pathlib import Path

import pytest

from app.local_audit import LocalAuditStore, redact
from app.outbound_dlp import DlpDenied, enforce_outbound


def test_local_audit_redacts_and_retains_bounded_events(tmp_path: Path) -> None:
    store = LocalAuditStore(tmp_path / "audit.jsonl", max_events=100, max_bytes=100000)
    store.append("mcp.tool.completed", {"token": "secret-value", "message": "Bearer abc.def"})
    event = store.query(limit=1)[0]
    assert event["data"]["token"] == "[REDACTED]"
    assert "abc.def" not in str(event)


def test_dlp_rejects_unknown_secret_and_external_protected_fields() -> None:
    assert enforce_outbound({"query": "status"}, ["query"], "organization-controlled") == {"query": "status"}
    with pytest.raises(DlpDenied, match="absent"):
        enforce_outbound({"extra": "x"}, ["query"], "local")
    with pytest.raises(DlpDenied, match="secret"):
        enforce_outbound({"query": "token=abcd"}, ["query"], "local")
    with pytest.raises(DlpDenied, match="Protected"):
        enforce_outbound({"sourceCode": "class A {}"}, ["sourceCode"], "external-zero-protected-data")
