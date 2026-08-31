import json
import tempfile
import unittest
from pathlib import Path

from app.config import Settings
from app.monitoring import FreeFlowAdapter, QualysAdapter


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


if __name__ == "__main__":
    unittest.main()
