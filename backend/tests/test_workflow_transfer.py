import tempfile
import unittest
from pathlib import Path

from app.storage import JarvisStore


class WorkflowTransferTests(unittest.TestCase):
    def make_store(self, name: str) -> JarvisStore:
        root = Path(tempfile.mkdtemp(prefix=f"aegis-transfer-{name}-"))
        store = JarvisStore(root / "jarvis.db")
        store.initialize()
        return store

    def test_round_trip_preserves_design_state_answers_and_attachments(self) -> None:
        source = self.make_store("source")
        attachment = source.save_uploaded_file(
            "requirements.txt", 18, "text/plain", "source-file.txt", "Create the daily report.",
        )
        workflow = source.create_workflow("Daily report", "Automate reporting", [attachment.id], "powershell")
        workflow = source.save_workflow_plan(
            workflow.id,
            "Tentative plan",
            "lmstudio",
            "reasoning-model",
            [{"id": "schedule", "prompt": "When?", "required": True, "options": []}],
        )
        workflow = source.save_clarification_answer(workflow.id, "schedule", "Weekdays at 7 AM")

        package = source.export_workflow(workflow.id)
        self.assertIsNotNone(package)
        destination = self.make_store("destination")
        result = destination.import_workflow(package)

        self.assertEqual("imported", result.action)
        self.assertEqual(workflow.transfer_id, result.workflow.transfer_id)
        self.assertEqual("needs_clarification", result.workflow.state)
        self.assertEqual("Weekdays at 7 AM", result.workflow.clarification_answers["schedule"])
        self.assertEqual("Tentative plan", result.workflow.plan_text)
        self.assertEqual("Create the daily report.", destination.get_file_content(result.workflow.attachment_ids[0]))

    def test_reimport_does_not_overwrite_same_or_newer_local_workflow(self) -> None:
        source = self.make_store("source")
        workflow = source.create_workflow("Transfer conflict", "Initial", [], "powershell")
        package = source.export_workflow(workflow.id)
        destination = self.make_store("destination")
        first = destination.import_workflow(package)
        second = destination.import_workflow(package)

        self.assertEqual("imported", first.action)
        self.assertEqual("unchanged", second.action)
        self.assertEqual(first.workflow.id, second.workflow.id)

    def test_active_workflow_is_paused_and_detached_from_monitor_on_import(self) -> None:
        source = self.make_store("source")
        workflow = source.create_workflow("Active transfer", "Running elsewhere", [], "powershell")
        with source._connect() as connection:
            connection.execute("UPDATE workflows SET state='running', monitor_slot=2 WHERE id=?", (workflow.id,))
        package = source.export_workflow(workflow.id)
        destination = self.make_store("destination")
        result = destination.import_workflow(package)

        self.assertEqual("paused", result.workflow.state)
        self.assertIsNone(result.workflow.monitor_slot)
        self.assertIn("for safety", result.detail)


if __name__ == "__main__":
    unittest.main()
