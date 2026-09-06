import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.tool_qualification import ToolQualificationStore


def test_persists_and_reloads_qualified_route_without_endpoint_secrets(tmp_path: Path) -> None:
    path = tmp_path / "reports.json"
    store = ToolQualificationStore(path)
    report = store.save("dmr", "qwen", "local", "http://127.0.0.1/chat", native=True, arguments=True, sequential=True, continuation=True)

    loaded = ToolQualificationStore(path).get("dmr", "qwen", "local", "http://127.0.0.1/chat")
    raw = path.read_text(encoding="utf-8")

    assert report.qualified is True
    assert loaded is not None and loaded.qualified is True
    assert "http://127.0.0.1/chat" not in raw


def test_stale_malformed_or_different_endpoint_report_does_not_authorize(tmp_path: Path) -> None:
    path = tmp_path / "reports.json"
    store = ToolQualificationStore(path)
    store.save("ollama", "llama", "local", "http://127.0.0.1/chat", native=True, arguments=True, sequential=True, continuation=True)
    payload = json.loads(path.read_text(encoding="utf-8"))
    record = next(iter(payload["reports"].values()))
    record["valid_until"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert store.get("ollama", "llama", "local", "http://127.0.0.1/chat") is None
    assert store.get("ollama", "llama", "local", "http://127.0.0.1/other") is None


def test_failed_probe_is_retained_but_never_qualified(tmp_path: Path) -> None:
    store = ToolQualificationStore(tmp_path / "reports.json")
    report = store.save("ollama", "bad", "local", "http://localhost/chat", native=True, arguments=False, sequential=False, continuation=False, failure_reason="invalid arguments")

    assert report.qualified is False
    assert store.get("ollama", "bad", "local", "http://localhost/chat").qualified is False
