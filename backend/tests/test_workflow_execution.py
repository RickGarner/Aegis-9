import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.storage import JarvisStore
from app.workflow_execution import WorkflowExecutionError, WorkflowExecutionManager
from app.workflow_runner import WorkflowTestRunner
from app.workflow_scheduler import is_due, prerequisites_met


class WorkflowExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_approved_artifact_runs_and_retains_events(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="aegis-execution-"))
        store = JarvisStore(root / "jarvis.db")
        store.initialize()
        workflow = store.create_workflow("Safe execution", "Emit structured output", [], "powershell")
        with store._connect() as connection:
            connection.execute("UPDATE workflows SET state='test_plan_approved',approval_stage='test_plan_approved',test_plan_text='Approved tests' WHERE id=?", (workflow.id,))
        workflow = store.save_workflow_implementation(
            workflow.id, "```powershell\n$workflowType = 'safe-test'\nWrite-Output '{\"ok\":true}'\n```", "test", "model",
        )
        runner = WorkflowTestRunner(root / "artifacts")
        artifact = runner.prepare(workflow.transfer_id, workflow.revision, workflow.language, workflow.implementation_text)
        store.save_prepared_artifact(workflow.id, artifact.sha256, artifact.manifest.model_dump())
        with store._connect() as connection:
            connection.execute("UPDATE workflows SET state='supervisor_pending',approval_stage='supervisor_pending',latest_test_status='passed' WHERE id=?", (workflow.id,))
        store.set_workflow_schedule(workflow.id, {"trigger": "manual", "expression": "", "timezone": "UTC"})
        workflow = store.approve_workflow_for_production(workflow.id, "test-supervisor")
        catalog = root / "catalog.json"
        catalog.write_text(json.dumps({"profiles": {"safe-test": {"enabled": True, "language": "powershell", "allowed_capabilities": ["unsupported_syntax"], "allowed_commands": ["Write-Output"], "maximum_runtime_seconds": 20}}}), encoding="utf-8")
        manager = WorkflowExecutionManager(store, root / "artifacts", catalog, 20, 10_000)

        run = await manager.start(workflow, "manual", "test-operator")
        for _ in range(100):
            await asyncio.sleep(0.05)
            completed = store.get_workflow_run(run.id)
            if completed.status == "succeeded":
                break
        self.assertEqual("succeeded", completed.status)
        self.assertIn('"ok":true', completed.stdout)
        self.assertTrue(completed.output_sha256)
        self.assertTrue(any(item.event_type == "stdout" for item in store.get_workflow_run_events(run.id)))

    def test_schedule_and_prerequisite_contract(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="aegis-schedule-"))
        store = JarvisStore(root / "jarvis.db")
        store.initialize()
        workflow = store.create_workflow("Daily", "", [], "powershell")
        with store._connect() as connection:
            connection.execute("UPDATE workflows SET state='scheduled',schedule_json=? WHERE id=?", (json.dumps({"trigger": "daily", "expression": "07:00", "timezone": "UTC"}), workflow.id))
        workflow = store.get_workflow(workflow.id)
        self.assertTrue(is_due(workflow, datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)))
        self.assertEqual((True, "Every declarative prerequisite passed."), prerequisites_met({"start_conditions": f"file_exists={__file__}"}))
        self.assertFalse(prerequisites_met({"start_conditions": "run arbitrary code"})[0])

    def test_recurring_calendar_window_and_interval(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="aegis-calendar-schedule-"))
        store = JarvisStore(root / "jarvis.db")
        store.initialize()
        workflow = store.create_workflow("Recurring", "", [], "powershell")
        schedule = {"trigger": "recurring", "start_date": "2026-09-01", "end_date": "2026-09-30", "start_time": "08:00", "end_time": "17:00", "interval_value": 30, "interval_unit": "minutes", "timezone": "UTC"}
        with store._connect() as connection:
            connection.execute("UPDATE workflows SET state='scheduled',schedule_json=?,last_run_at='2026-09-01 08:00:00' WHERE id=?", (json.dumps(schedule), workflow.id))
        workflow = store.get_workflow(workflow.id)
        self.assertFalse(is_due(workflow, datetime(2026, 9, 1, 8, 29, tzinfo=timezone.utc)))
        self.assertTrue(is_due(workflow, datetime(2026, 9, 1, 8, 30, tzinfo=timezone.utc)))
        self.assertFalse(is_due(workflow, datetime(2026, 10, 1, 8, 30, tzinfo=timezone.utc)))

    def test_csharp_production_execution_fails_closed(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="aegis-csharp-execution-"))
        store = JarvisStore(root / "jarvis.db")
        store.initialize()
        workflow = store.create_workflow("C# execution", "", [], "csharp")
        with store._connect() as connection:
            connection.execute("UPDATE workflows SET state='test_plan_approved',approval_stage='test_plan_approved',test_plan_text='Approved tests' WHERE id=?", (workflow.id,))
        workflow = store.save_workflow_implementation(
            workflow.id,
            "```csharp\n// workflowType = 'safe-csharp'\nConsole.WriteLine(\"test\");\n```",
            "test",
            "model",
        )
        runner = WorkflowTestRunner(root / "artifacts")
        artifact = runner.prepare(workflow.transfer_id, workflow.revision, workflow.language, workflow.implementation_text)
        store.save_prepared_artifact(workflow.id, artifact.sha256, artifact.manifest.model_dump())
        with store._connect() as connection:
            connection.execute("UPDATE workflows SET state='supervisor_pending',approval_stage='supervisor_pending',latest_test_status='passed' WHERE id=?", (workflow.id,))
        store.set_workflow_schedule(workflow.id, {"trigger": "manual", "expression": "", "timezone": "UTC"})
        workflow = store.approve_workflow_for_production(workflow.id, "test-supervisor")
        catalog = root / "catalog.json"
        catalog.write_text(json.dumps({"profiles": {}}), encoding="utf-8")
        manager = WorkflowExecutionManager(store, root / "artifacts", catalog, 20, 10_000)

        with self.assertRaisesRegex(WorkflowExecutionError, "isolated executor"):
            manager.validate(workflow)

    def test_scheduler_events_are_deduplicated(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="aegis-scheduler-events-"))
        store = JarvisStore(root / "jarvis.db")
        store.initialize()
        workflow = store.create_workflow("Deferred workflow", "", [], "powershell")

        self.assertTrue(store.record_workflow_scheduler_event(workflow.id, "scheduled run deferred: prerequisite unavailable"))
        self.assertFalse(store.record_workflow_scheduler_event(workflow.id, "scheduled run deferred: prerequisite unavailable"))
        self.assertTrue(store.record_workflow_scheduler_event(workflow.id, "schedule blocked: invalid timezone"))
        with store._connect() as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS value FROM activity_logs WHERE event_type='workflow-scheduler'"
            ).fetchone()["value"]
        self.assertEqual(2, count)

    def test_scheduler_status_is_durable_and_validated(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="aegis-scheduler-status-"))
        store = JarvisStore(root / "jarvis.db")
        store.initialize()
        workflow = store.create_workflow("Scheduled status", "", [], "powershell")

        updated = store.update_workflow_scheduler_status(workflow.id, "deferred", "Required host is unavailable")
        self.assertEqual("deferred", updated.scheduler_status)
        self.assertEqual("Required host is unavailable", updated.scheduler_last_deferred_reason)
        self.assertTrue(updated.scheduler_last_evaluated_at)
        self.assertEqual("deferred", store.get_workflow(workflow.id).scheduler_status)
        with self.assertRaisesRegex(ValueError, "Unsupported scheduler status"):
            store.update_workflow_scheduler_status(workflow.id, "made-up")


if __name__ == "__main__":
    unittest.main()
