import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import Mock, patch

from app.config import Settings
from app.monitoring import FreeFlowAdapter, LocalServerAdapter, MoveItAdapter, MoveItTask, QualysAdapter


class OperationalMonitoringTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
