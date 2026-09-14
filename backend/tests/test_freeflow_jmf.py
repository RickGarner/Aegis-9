import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx

from app.config import Settings
from app.freeflow_jmf import FreeFlowJmfDevice, FreeFlowJmfError, FreeFlowJmfServerResult, FreeFlowJmfService, build_known_devices_request, build_queue_status_request, compare_server_devices, parse_known_devices, parse_queue_status

FIXTURES = Path(__file__).parent / "fixtures" / "freeflow"


class FreeFlowJmfTests(unittest.TestCase):
    def test_parses_sanitized_freeflow_8x_contract_fixtures(self):
        devices = parse_known_devices((FIXTURES / "known_devices_sanitized.xml").read_bytes())
        jobs = parse_queue_status((FIXTURES / "queue_status_sanitized.xml").read_bytes())
        self.assertEqual(
            (["workflow", "queue", "printer"], "SYNTHETIC-JOB-001"),
            ([device.kind for device in devices], jobs[0].job_id),
        )

    def test_compares_primary_and_backup_without_exposing_identifiers(self):
        servers = [
            FreeFlowJmfServerResult(name="FFC1", role="Primary", state="healthy", detail="ok", devices=[FreeFlowJmfDevice(device_id="sensitive-a"), FreeFlowJmfDevice(device_id="sensitive-b"), FreeFlowJmfDevice(device_id="sensitive-b"), FreeFlowJmfDevice(device_id="")]),
            FreeFlowJmfServerResult(name="FFC2", role="Backup", state="healthy", detail="ok", devices=[FreeFlowJmfDevice(device_id="sensitive-a"), FreeFlowJmfDevice(device_id="sensitive-c")]),
        ]
        result = compare_server_devices(servers)
        self.assertTrue(result.comparable)
        self.assertEqual("drift", result.state)
        self.assertEqual(1, result.shared_device_count)
        self.assertEqual(1, result.primary_only_count)
        self.assertEqual(1, result.backup_only_count)
        self.assertEqual(1, result.primary_blank_id_count)
        self.assertEqual(1, result.primary_duplicate_id_count)
        self.assertNotIn("sensitive-a", result.detail)

    def test_comparison_fails_closed_on_partial_server_failure(self):
        servers = [
            FreeFlowJmfServerResult(name="FFC1", role="Primary", state="healthy", detail="ok"),
            FreeFlowJmfServerResult(name="FFC2", role="Backup", state="error", detail="timeout"),
        ]
        result = compare_server_devices(servers)
        self.assertFalse(result.comparable)
        self.assertEqual("partial", result.state)

    def test_builds_read_only_known_devices_query(self):
        request = build_known_devices_request().decode("utf-8")
        self.assertIn('Type="KnownDevices"', request)
        self.assertIn('SenderID="AEGIS9"', request)
        self.assertIn('xsi:type="QueryKnownDevices"', request)
        self.assertIn('DeviceDetails="Brief"', request)

    def test_builds_read_only_queue_status_query(self):
        request = build_queue_status_request().decode("utf-8")
        self.assertIn('Type="QueueStatus"', request)
        self.assertIn('xsi:type="QueryQueueStatus"', request)

    def test_parses_and_bounds_newest_queue_entries(self):
        jobs = parse_queue_status(b'''<JMF xmlns="http://www.CIP4.org/JDFSchema_1_1"><Response Type="QueueStatus" ReturnCode="0"><Queue><QueueEntry QueueEntryID="1" Status="Completed" SubmissionTime="2026-09-01T00:00:00Z"/><QueueEntry QueueEntryID="2" Status="Waiting" StatusDetails="Queued" SubmissionTime="2026-09-02T00:00:00Z"/></Queue></Response></JMF>''', limit=1)
        self.assertEqual("2", jobs[0].queue_entry_id)
        self.assertEqual("Waiting", jobs[0].status)

    def test_parses_namespaced_device_info_and_preserves_attributes(self):
        devices = parse_known_devices(b'''<JMF xmlns="http://www.CIP4.org/JDFSchema_1_1"><Response Type="KnownDevices"><DeviceInfo DeviceID="WF1" DescriptiveName="Production Workflow" DeviceStatus="Running" VendorField="retained" /></Response></JMF>''')
        self.assertEqual("WF1", devices[0].device_id)
        self.assertEqual("retained", devices[0].attributes["VendorField"])

    def test_classifies_child_device_contract(self):
        devices = parse_known_devices(b'''<JMF xmlns="http://www.CIP4.org/JDFSchema_1_1"><Response Type="KnownDevices"><DeviceList><DeviceInfo DeviceID="WF1" DeviceStatus="Idle"><Device DeviceID="WF1" DeviceClass="Preset" DescriptiveName="Workflow One" ModelDescription="FreeFlow Core Workflow" /></DeviceInfo><DeviceInfo DeviceID="Q1" DeviceStatus="Running"><Device DeviceID="Q1" DeviceClass="PrinterDestination" /></DeviceInfo></DeviceList></Response></JMF>''')
        self.assertEqual("workflow", devices[0].kind)
        self.assertEqual("Workflow One", devices[0].descriptive_name)
        self.assertEqual("FreeFlow Core Workflow", devices[0].model_description)
        self.assertEqual("queue", devices[1].kind)

    def test_rejects_malformed_xml_without_returning_raw_response(self):
        with self.assertRaisesRegex(FreeFlowJmfError, "malformed XML"):
            parse_known_devices(b"<JMF><broken>")

    @patch("app.freeflow_jmf.httpx.post")
    def test_discovers_each_configured_server(self, post: Mock):
        post.return_value = Mock(status_code=200, content=b'''<JMF xmlns="http://www.CIP4.org/JDFSchema_1_1"><Response Type="KnownDevices"><DeviceInfo DeviceID="Q1" /></Response></JMF>''')
        post.return_value.raise_for_status.return_value = None
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "freeflow.json"
            inventory.write_text(json.dumps([{"name": "FFC1", "role": "Primary", "version": "8.0.0", "build": "33969", "jmfUrl": "http://ffc1:7751/FreeFlowCore", "enabled": True}]), encoding="utf-8")
            result = FreeFlowJmfService(Settings(JARVIS_FREEFLOW_INVENTORY_PATH=str(inventory))).discover()
        self.assertEqual("healthy", result.servers[0].state)
        self.assertEqual("Q1", result.servers[0].devices[0].device_id)
        self.assertEqual("8.0.0", result.servers[0].version)
        self.assertEqual("33969", result.servers[0].build)
        self.assertEqual("application/vnd.cip4-jmf+xml", post.call_args.kwargs["headers"]["Content-Type"])

    def test_missing_jmf_url_is_explicitly_unconfigured(self):
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "freeflow.json"
            inventory.write_text(json.dumps([{"name": "FFC1", "enabled": True}]), encoding="utf-8")
            result = FreeFlowJmfService(Settings(JARVIS_FREEFLOW_INVENTORY_PATH=str(inventory))).discover()
        self.assertEqual("unconfigured", result.servers[0].state)

    @patch("app.freeflow_jmf.httpx.post")
    def test_forced_refresh_recovers_after_a_partial_outage(self, post: Mock):
        healthy = Mock(status_code=200, content=(FIXTURES / "known_devices_sanitized.xml").read_bytes())
        healthy.raise_for_status.return_value = None
        post.side_effect = [healthy, httpx.ReadTimeout("synthetic outage"), healthy, healthy]
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "freeflow.json"
            inventory.write_text(json.dumps([
                {"name": "FFC1", "role": "Primary", "jmfUrl": "http://ffc1:7751/FreeFlowCore"},
                {"name": "FFC2", "role": "Backup", "jmfUrl": "http://ffc2:7751/FreeFlowCore"},
            ]), encoding="utf-8")
            service = FreeFlowJmfService(Settings(JARVIS_FREEFLOW_INVENTORY_PATH=str(inventory)))
            degraded = service.discover(force=True)
            recovered = service.discover(force=True)
            cached = service.discover()
        self.assertEqual(
            ("partial", "matched", 4, recovered.model_dump()),
            (degraded.comparison.state, recovered.comparison.state, post.call_count, cached.model_dump()),
        )

    @patch("app.freeflow_jmf.httpx.post")
    def test_repeated_forced_refresh_remains_bounded_and_isolated(self, post: Mock):
        response = Mock(status_code=200, content=(FIXTURES / "known_devices_sanitized.xml").read_bytes())
        response.raise_for_status.return_value = None
        post.return_value = response
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "freeflow.json"
            inventory.write_text(json.dumps([
                {"name": "FFC1", "role": "Primary", "jmfUrl": "http://ffc1:7751/FreeFlowCore"},
                {"name": "FFC2", "role": "Backup", "jmfUrl": "http://ffc2:7751/FreeFlowCore"},
            ]), encoding="utf-8")
            service = FreeFlowJmfService(Settings(JARVIS_FREEFLOW_INVENTORY_PATH=str(inventory)))
            results = [service.discover(force=True) for _ in range(100)]
        self.assertEqual((100, 200, {"healthy"}, {"matched"}), (
            len(results), post.call_count,
            {server.state for result in results for server in result.servers},
            {result.comparison.state for result in results},
        ))

    @patch("app.freeflow_jmf.httpx.post")
    def test_filtered_results_reuse_discovery_and_status_reports_roles(self, post: Mock):
        post.return_value = Mock(status_code=200, content=b'''<JMF xmlns="http://www.CIP4.org/JDFSchema_1_1"><Response Type="KnownDevices"><DeviceList><DeviceInfo DeviceID="WF1"><Device DeviceID="WF1" DeviceClass="Preset" /></DeviceInfo><DeviceInfo DeviceID="Q1"><Device DeviceID="Q1" DeviceClass="PrinterDestination" /></DeviceInfo></DeviceList></Response></JMF>''')
        post.return_value.raise_for_status.return_value = None
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "freeflow.json"
            inventory.write_text(json.dumps([{"name": "FFC1", "role": "Primary", "jmfUrl": "http://ffc1:7751/FreeFlowCore"}, {"name": "FFC2", "role": "Backup", "jmfUrl": "http://ffc2:7751/FreeFlowCore"}]), encoding="utf-8")
            service = FreeFlowJmfService(Settings(JARVIS_FREEFLOW_INVENTORY_PATH=str(inventory)))
            workflows = service.filtered("workflow")
            status = service.status()
        self.assertEqual(["WF1"], [device.device_id for device in workflows.servers[0].devices])
        self.assertTrue(status.primary_available)
        self.assertTrue(status.backup_available)
        self.assertEqual(2, post.call_count)


if __name__ == "__main__":
    unittest.main()
