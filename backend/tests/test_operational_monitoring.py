import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import Mock, patch

from app.config import Settings
from app.monitoring import FreeFlowAdapter, LocalServerAdapter, QualysAdapter


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


if __name__ == "__main__":
    unittest.main()
