from pathlib import Path

from app.storage import JarvisStore
from app.workflow_documentation import WorkflowDocumentationManager, safe_workflow_name


def test_workflow_documentation_creates_versioned_manual_and_daily_log(tmp_path: Path) -> None:
    store = JarvisStore(tmp_path / "aegis.db")
    store.initialize()
    workflow = store.create_workflow("MOVEit HA / Failback", "Observe and safely restore the preferred topology.")
    manager = WorkflowDocumentationManager(tmp_path / "Workflows")

    manual = manager.record(workflow, "workflow-created", "password=do-not-log")

    assert manual == tmp_path / "Workflows" / "MOVEit_HA_Failback_v001" / "USER-MANUAL.md"
    assert "How to use it" in manual.read_text(encoding="utf-8")
    logs = list((tmp_path / "Workflows" / "Logs").glob("MOVEit_HA_Failback_*.log"))
    assert len(logs) == 1
    log = logs[0].read_text(encoding="utf-8")
    assert "workflow-created" in log
    assert "do-not-log" not in log
    assert "[REDACTED]" in log


def test_safe_workflow_name_is_portable_and_bounded() -> None:
    assert safe_workflow_name('  Daily: Report / Export?  ') == "Daily_Report_Export"
    assert len(safe_workflow_name("x" * 200)) == 80


def test_ensure_does_not_duplicate_existing_workflow_log(tmp_path: Path) -> None:
    store = JarvisStore(tmp_path / "aegis.db")
    store.initialize()
    workflow = store.create_workflow("Daily Health")
    manager = WorkflowDocumentationManager(tmp_path / "Workflows")
    manager.ensure(workflow)
    log = next((tmp_path / "Workflows" / "Logs").glob("*.log"))
    initial = log.read_text(encoding="utf-8")
    manager.ensure(workflow)
    assert log.read_text(encoding="utf-8") == initial


def test_test_results_are_recorded_and_secrets_redacted(tmp_path: Path) -> None:
    store = JarvisStore(tmp_path / "aegis.db")
    store.initialize()
    workflow = store.create_workflow("Daily Health")
    manager = WorkflowDocumentationManager(tmp_path / "Workflows")
    result = manager.record_test_result(workflow, {
        "profile": "static", "status": "passed", "artifact_sha256": "a" * 64,
        "evidence_sha256": "b" * 64, "exit_code": 0, "duration_ms": 12,
        "summary": "Validation passed", "stdout": "token=private-value", "stderr": "",
    })
    text = result.read_text(encoding="utf-8")
    assert "Validation passed" in text
    assert "private-value" not in text
    assert "[REDACTED]" in text
