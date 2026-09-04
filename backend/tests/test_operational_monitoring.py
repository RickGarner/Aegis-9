import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import Mock, patch

from app.config import Settings
from app.monitoring import (
    FreeFlowAdapter, FreeFlowMonitor, LocalServerAdapter, MonitoringAlert,
    MonitoringDashboard, MonitoringStore, MoveItAdapter, MoveItMonitor,
    MoveItTask, QualysAdapter, QualysMonitor, ServerMonitor,
)
from app.operations_monitoring import OperationsMonitoringSnapshot, build_operations_snapshot
from app.storage import JarvisStore


class OperationalMonitoringTests(unittest.TestCase):
    def test_operations_snapshot_separates_target_and_collector_state(self):
        captured_at = "2026-09-03T12:00:00+00:00"
        dashboard = MonitoringDashboard(
            generated_at=captured_at,
            moveit=MoveItMonitor(status="unavailable", adapter="moveit-rest", last_checked_at=captured_at, detail="MoveIT credentials are not configured."),
            server=ServerMonitor(status="warning", last_checked_at=captured_at, detail="One automatic service requires attention."),
            freeflow=FreeFlowMonitor(status="healthy", last_checked_at=captured_at, detail="Both portals responded."),
            qualys=QualysMonitor(status="error", last_checked_at=captured_at, detail="Urgent findings detected."),
            alerts=[MonitoringAlert(id=7, source="qualys", severity="error", title="Urgent finding", detail="Review required", status="active", created_at=captured_at)],
        )

        snapshot = build_operations_snapshot(dashboard)
        moveit = next(item for item in snapshot.monitors if item.monitor_id == "moveit")
        moveit_observation = next(item for item in snapshot.observations if item.monitor_id == "moveit")

        self.assertEqual("1.0", snapshot.contract_version)
        self.assertEqual("critical", snapshot.summary.overall_state)
        self.assertEqual(1, snapshot.summary.counts.healthy)
        self.assertEqual(1, snapshot.summary.counts.degraded)
        self.assertEqual(1, snapshot.summary.counts.critical)
        self.assertEqual(1, snapshot.summary.counts.unknown)
        self.assertEqual("unconfigured", moveit.configuration_state)
        self.assertEqual("misconfigured", moveit.collector_state)
        self.assertEqual("unknown", moveit_observation.state)
        self.assertEqual("collector.misconfigured", moveit_observation.diagnostic_code)
        self.assertEqual("critical", snapshot.alerts[0].severity)

    def test_operations_snapshot_uses_platform_contract_aliases(self):
        captured_at = "2026-09-03T12:00:00Z"
        dashboard = MonitoringDashboard(
            generated_at=captured_at,
            moveit=MoveItMonitor(status="healthy", adapter="moveit-rest", last_checked_at=captured_at, detail="Ready"),
            server=ServerMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
            freeflow=FreeFlowMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
            qualys=QualysMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
        )

        payload = build_operations_snapshot(dashboard).model_dump(by_alias=True)

        self.assertEqual({"contractVersion", "generatedAtUtc", "summary", "monitors", "observations", "alerts", "workflows"}, set(payload))
        self.assertIn("overallState", payload["summary"])
        self.assertIn("collectorState", payload["monitors"][0])
        self.assertIn("validUntilUtc", payload["observations"][0])

    def test_operations_snapshot_includes_actionable_workflow_scheduler_status(self):
        captured_at = "2026-09-03T12:00:00Z"
        dashboard = MonitoringDashboard(
            generated_at=captured_at,
            moveit=MoveItMonitor(status="healthy", adapter="moveit-rest", last_checked_at=captured_at, detail="Ready"),
            server=ServerMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
            freeflow=FreeFlowMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
            qualys=QualysMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
        )
        with tempfile.TemporaryDirectory() as directory:
            store = JarvisStore(Path(directory) / "aegis.db")
            store.initialize()
            workflow = store.create_workflow("Awaiting approval", "", [], "powershell")
            with store._connect() as connection:
                connection.execute(
                    "UPDATE workflows SET state='supervisor_pending', approval_stage='supervisor_pending', "
                    "scheduler_status='deferred', scheduler_last_deferred_reason='Required host is unavailable' WHERE id=?",
                    (workflow.id,),
                )
            workflow = store.get_workflow(workflow.id)

            snapshot = build_operations_snapshot(dashboard, workflows=[workflow])

        self.assertEqual(1, len(snapshot.workflows))
        status = snapshot.workflows[0]
        self.assertEqual("supervisor_pending", status.lifecycle_state)
        self.assertEqual("deferred", status.scheduler_status)
        self.assertEqual("Required host is unavailable", status.deferred_reason)
        self.assertTrue(status.requires_action)
        self.assertEqual(f"aegis://workflows/{workflow.id}", status.navigation_target)

    def test_operations_snapshot_includes_latest_run_and_notification_delivery(self):
        captured_at = "2026-09-03T12:00:00Z"
        dashboard = MonitoringDashboard(
            generated_at=captured_at,
            moveit=MoveItMonitor(status="healthy", adapter="moveit-rest", last_checked_at=captured_at, detail="Ready"),
            server=ServerMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
            freeflow=FreeFlowMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
            qualys=QualysMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
        )
        with tempfile.TemporaryDirectory() as directory:
            store = JarvisStore(Path(directory) / "aegis.db")
            store.initialize()
            workflow = store.create_workflow("Run visibility", "", [], "powershell")
            with store._connect() as connection:
                cursor = connection.execute(
                    """INSERT INTO workflow_runs(workflow_id,revision,artifact_sha256,trigger,status,attempt,requested_by,
                    completed_at,error) VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP,?)""",
                    (workflow.id, 1, "abc", "scheduled", "failed", 2, "scheduler", "Test failure"),
                )
                run_id = int(cursor.lastrowid)
                connection.execute(
                    """INSERT INTO notification_outbox(category,subject,payload_json,status,attempts,last_error)
                    VALUES('workflow-run','failed',?,'pending',1,'SMTP unavailable')""",
                    (json.dumps({"workflow_id": workflow.id, "run_id": run_id}),),
                )
            latest_runs = store.get_latest_workflow_runs()
            notifications = store.get_latest_workflow_notification_states()

            snapshot = build_operations_snapshot(
                dashboard,
                workflows=[store.get_workflow(workflow.id)],
                latest_runs=latest_runs,
                notification_states=notifications,
            )

        status = snapshot.workflows[0]
        self.assertEqual(run_id, status.latest_run_id)
        self.assertEqual("failed", status.latest_run_status)
        self.assertEqual(2, status.latest_run_attempt)
        self.assertEqual("Test failure", status.latest_run_error)
        self.assertEqual("pending", status.notification_status)
        self.assertEqual(1, status.notification_attempts)
        self.assertEqual("SMTP unavailable", status.notification_error)

    def test_operations_snapshot_retains_last_good_target_but_marks_collector_failure(self):
        captured_at = "2026-09-03T12:00:00Z"
        healthy = MonitoringDashboard(
            generated_at=captured_at,
            moveit=MoveItMonitor(status="healthy", adapter="moveit-rest", last_checked_at=captured_at, detail="Last run succeeded"),
            server=ServerMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
            freeflow=FreeFlowMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
            qualys=QualysMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
        )
        previous = build_operations_snapshot(healthy, now=datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc))
        failed_at = "2026-09-03T12:01:00Z"
        failed = healthy.model_copy(deep=True)
        failed.generated_at = failed_at
        failed.moveit = MoveItMonitor(status="unavailable", adapter="moveit-rest", last_checked_at=failed_at, detail="MoveIT credentials are not configured.")

        snapshot = build_operations_snapshot(failed, previous=previous, now=datetime(2026, 9, 3, 12, 1, tzinfo=timezone.utc))
        observation = next(item for item in snapshot.observations if item.monitor_id == "moveit")

        self.assertEqual("healthy", observation.state)
        self.assertEqual("misconfigured", observation.collector_state)
        self.assertEqual(captured_at, observation.collected_at_utc)
        self.assertIn("Last known target evidence", observation.summary)
        self.assertEqual("misconfigured", snapshot.summary.overall_state)

    def test_expired_evidence_is_marked_stale(self):
        captured_at = "2026-09-03T12:00:00Z"
        dashboard = MonitoringDashboard(
            generated_at=captured_at,
            moveit=MoveItMonitor(status="healthy", adapter="moveit-rest", last_checked_at=captured_at, detail="Ready"),
            server=ServerMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
            freeflow=FreeFlowMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
            qualys=QualysMonitor(status="healthy", last_checked_at=captured_at, detail="Ready"),
        )

        snapshot = build_operations_snapshot(dashboard, now=datetime(2026, 9, 3, 12, 20, tzinfo=timezone.utc))

        self.assertTrue(all(item.collector_state == "stale" for item in snapshot.observations))
        self.assertTrue(all(item.collector_state == "stale" for item in snapshot.monitors))
        self.assertEqual("unknown", snapshot.summary.overall_state)

    def test_normalized_snapshot_persists_across_store_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            store = JarvisStore(Path(directory) / "aegis.db")
            store.initialize()
            monitoring_store = MonitoringStore(store._connect)
            payload = OperationsMonitoringSnapshot(
                generated_at_utc="2026-09-03T12:00:00Z",
                summary={"overall_state": "unknown", "counts": {}},
                monitors=[], observations=[], alerts=[],
            ).model_dump_json(by_alias=True)

            monitoring_store.save_operations_snapshot(payload, "2026-09-03T12:00:00Z")
            reloaded = MonitoringStore(store._connect).get_latest_operations_snapshot()

            self.assertEqual("1.0", OperationsMonitoringSnapshot.model_validate_json(reloaded).contract_version)

    def test_freeflow_hosts_are_visible_before_urls_are_configured(self):
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "freeflow.json"
            inventory.write_text(json.dumps([
                {"name": "BSOXERALB001", "role": "Primary", "webUrl": "", "enabled": True},
                {"name": "BSOXERALB002", "role": "Secondary", "webUrl": "", "enabled": True},
            ]), encoding="utf-8")
            monitor = FreeFlowAdapter(Settings(JARVIS_FREEFLOW_INVENTORY_PATH=str(inventory))).collect("2026-08-30T00:00:00+00:00")
            self.assertEqual("unavailable", monitor.status)
            self.assertEqual(["BSOXERALB001", "BSOXERALB002"], [server.name for server in monitor.servers])
            self.assertTrue(all("awaiting configuration" in server.detail for server in monitor.servers))

    def test_qualys_remains_configuration_required_without_credentials(self):
        monitor = QualysAdapter(Settings()).collect("2026-08-30T00:00:00+00:00")
        self.assertEqual("unavailable", monitor.status)
        self.assertEqual([], monitor.findings)
        self.assertIn("awaiting configuration", monitor.detail)

    @patch("app.monitoring.httpx.get")
    def test_freeflow_windows_auth_challenge_confirms_portal_availability(self, get: Mock):
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "freeflow.json"
            inventory.write_text(json.dumps([
                {"name": "BSOXERALB001", "role": "Primary", "webUrl": "http://BSOXERALB001/FreeFlowCore", "expectedText": "", "enabled": True},
            ]), encoding="utf-8")
            get.return_value = Mock(status_code=401, text="Unauthorized")

            monitor = FreeFlowAdapter(Settings(JARVIS_FREEFLOW_INVENTORY_PATH=str(inventory))).collect("2026-09-01T00:00:00+00:00")

            self.assertEqual("healthy", monitor.status)
            self.assertEqual(401, monitor.servers[0].http_status)

    @patch("app.monitoring.subprocess.run")
    def test_remote_cim_inventory_is_normalized(self, run: Mock):
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "servers.json"
            inventory.write_text(json.dumps([
                {"name": "SERVER01", "address": "SERVER01", "role": "Application"},
            ]), encoding="utf-8")
            run.return_value = CompletedProcess([], 0, json.dumps([{
                "Name": "SERVER01", "Address": "SERVER01", "Role": "Application", "Total": 107374182400,
                "Free": 53687091200, "DiskAvailable": 50, "Cpu": 12, "MemoryAvailable": 60, "ServiceIssues": 0, "Error": None,
            }]), "")
            settings = Settings(
                JARVIS_SERVER_INVENTORY_PATH=str(inventory), JARVIS_SERVER_REMOTE_CIM_ENABLED=True,
            )

            rows = LocalServerAdapter(settings).collect_remote_inventory()

            self.assertEqual("Good", rows[0].status)
            self.assertEqual("50.0 GB", rows[0].free_disk)
            self.assertEqual("Good", rows[0].automatic_services)

    def test_moveit_task_run_history_sets_latest_confirmed_result(self):
        tasks = [MoveItTask(name="Daily export", task_id="42", status="Scheduled", detail="Configured task")]
        records = [
            {"TaskID": 42, "RunID": 100, "EndTime": "2026-09-01T08:00:00", "Status": "Failure", "StatusCode": 6, "StatusMsg": "Connection failed"},
            {"TaskID": 42, "RunID": 101, "EndTime": "2026-09-01T09:00:00", "Status": "Success", "StatusCode": 0, "StatusMsg": ""},
        ]

        entries = MoveItAdapter._apply_task_run_history(tasks, records)

        self.assertEqual("Success", tasks[0].last_run_status)
        self.assertEqual("2026-09-01T09:00:00", tasks[0].last_run_at)
        self.assertEqual("Scheduled", tasks[0].status)
        self.assertEqual(1, len(entries))

    def test_moveit_latest_failure_marks_task_for_alerting(self):
        tasks = [MoveItTask(name="Daily export", task_id="42", status="Scheduled", detail="Configured task")]

        MoveItAdapter._apply_task_run_history(tasks, [
            {"TaskID": 42, "RunID": 102, "EndTime": "2026-09-01T10:00:00", "Status": "Failure", "StatusCode": 6, "StatusMsg": "Authentication failed"},
        ])

        self.assertEqual("Failed", tasks[0].status)
        self.assertIn("Authentication failed", tasks[0].detail)

    def test_moveit_success_resolution_retains_failure_history(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("""CREATE TABLE monitoring_alerts (
                id INTEGER PRIMARY KEY, source TEXT, severity TEXT, title TEXT, detail TEXT,
                status TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, resolved_at TEXT)""")
            monitoring = MonitoringStore(lambda: connection)
            title = "MoveIT task issue: Daily export"
            monitoring.ensure_alert("moveit", "error", title, "Original transfer failure", active=True)

            monitoring.ensure_alert("moveit", "error", title, "Automatically resolved after confirmed Success.", active=False)

            row = connection.execute("SELECT status,resolved_at,detail FROM monitoring_alerts WHERE title=?", (title,)).fetchone()
            self.assertEqual("resolved", row["status"])
            self.assertIsNotNone(row["resolved_at"])
            self.assertIn("Original transfer failure", row["detail"])
            self.assertIn("confirmed Success", row["detail"])
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
