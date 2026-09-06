import tempfile
import unittest
from pathlib import Path

from app.config import Settings
from app.main import WorkflowReviewRequest, WorkflowTestRequest, review_workflow, run_workflow_test
from app.storage import JarvisStore
from app.workflow_runner import WorkflowTestRunner


class WorkflowRunnerTests(unittest.TestCase):
    def make_runner(self, timeout: int = 20) -> WorkflowTestRunner:
        return WorkflowTestRunner(Path(tempfile.mkdtemp(prefix="aegis-runner-")), timeout_seconds=timeout)

    def test_powershell_artifact_is_hashed_and_static_validation_passes(self) -> None:
        runner = self.make_runner()
        artifact = runner.prepare("workflow-one", 1, "powershell", "```powershell\nparam([int]$Value)\nWrite-Output ($Value + 1)\n```")
        evidence = runner.run(artifact, "powershell", "static")

        self.assertEqual(64, len(artifact.sha256))
        self.assertTrue(artifact.source_path.exists())
        self.assertEqual("passed", evidence.status)
        self.assertEqual(64, len(evidence.evidence_sha256))

    def test_external_capabilities_block_restricted_execution(self) -> None:
        runner = self.make_runner()
        implementation = "```powershell\nSearch-ADAccount -LockedOut | Add-Content -Path 'C:\\logs\\locked.txt'\nwhile ($true) { Start-Sleep 30 }\n```"
        artifact = runner.prepare("workflow-ad", 1, "powershell", implementation)
        evidence = runner.run(artifact, "powershell", "restricted")

        self.assertFalse(artifact.manifest.restricted_execution_allowed)
        self.assertIn("directory_service", artifact.manifest.capabilities)
        self.assertIn("filesystem_write", artifact.manifest.capabilities)
        self.assertIn("long_running", artifact.manifest.capabilities)
        self.assertEqual("blocked", evidence.status)

    def test_low_risk_powershell_can_run_in_restricted_profile(self) -> None:
        runner = self.make_runner()
        artifact = runner.prepare("workflow-safe", 1, "powershell", "```powershell\nWrite-Output 'validation-ok'\n```")
        evidence = runner.run(artifact, "powershell", "restricted")

        self.assertTrue(artifact.manifest.restricted_execution_allowed)
        self.assertEqual("passed", evidence.status)
        self.assertIn("validation-ok", evidence.stdout)

    def test_lowercase_destructive_cmdlet_cannot_bypass_manifest(self) -> None:
        runner = self.make_runner()
        artifact = runner.prepare("workflow-lowercase", 1, "powershell", "```powershell\nremove-item '.\\evidence.txt'\n```")

        self.assertFalse(artifact.manifest.restricted_execution_allowed)
        self.assertIn("filesystem_write", artifact.manifest.capabilities)
        self.assertIn("remove-item", [command.lower() for command in artifact.manifest.commands])

    def test_destructive_alias_cannot_bypass_manifest(self) -> None:
        runner = self.make_runner()
        artifact = runner.prepare("workflow-alias", 1, "powershell", "```powershell\nrm '.\\evidence.txt'\n```")

        self.assertFalse(artifact.manifest.restricted_execution_allowed)
        self.assertIn("alias_or_native", artifact.manifest.capabilities)

    def test_unknown_native_command_cannot_bypass_manifest(self) -> None:
        runner = self.make_runner()
        artifact = runner.prepare("workflow-native", 1, "powershell", "```powershell\nwhoami\n```")

        self.assertFalse(artifact.manifest.restricted_execution_allowed)
        self.assertIn("unsupported_syntax", artifact.manifest.capabilities)

    def test_csharp_artifact_builds_in_static_profile(self) -> None:
        runner = self.make_runner(timeout=60)
        artifact = runner.prepare("workflow-csharp", 1, "csharp", "```csharp\nConsole.WriteLine(2 + 2);\n```")
        evidence = runner.run(artifact, "csharp", "static")

        self.assertEqual("passed", evidence.status, evidence.stderr)
        self.assertIn("Build succeeded", evidence.stdout)

    def test_missing_fenced_source_is_rejected(self) -> None:
        runner = self.make_runner()
        with self.assertRaises(ValueError):
            runner.prepare("workflow-invalid", 1, "powershell", "Run Search-ADAccount.")


class WorkflowRunnerLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_submit_and_static_test_require_and_retain_real_evidence(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="aegis-runner-lifecycle-"))
        store = JarvisStore(root / "jarvis.db")
        store.initialize()
        workflow = store.create_workflow("Evidence gate", "Validate safely", [], "powershell")
        with store._connect() as connection:
            connection.execute("UPDATE workflows SET state='test_plan_approved', approval_stage='test_plan_approved',test_plan_text='Approved tests' WHERE id=?", (workflow.id,))
        workflow = store.save_workflow_implementation(
            workflow.id, "```powershell\nWrite-Output 'safe validation'\n```", "test", "coding-model",
        )
        settings = Settings(
            JARVIS_WORKFLOW_ARTIFACT_ROOT=root / "artifacts",
            JARVIS_WORKFLOW_TEST_TIMEOUT_SECONDS=20,
        )

        submitted = await review_workflow(workflow.id, WorkflowReviewRequest(decision="submit_for_test"), settings, store)
        self.assertEqual("test_ready", submitted.state)
        self.assertEqual(64, len(submitted.artifact_sha256))
        result = await run_workflow_test(workflow.id, WorkflowTestRequest(profile="static"), settings, store)

        self.assertEqual("test_passed", result.workflow.state)
        self.assertEqual("passed", result.workflow.latest_test_status)
        self.assertEqual(64, len(result.workflow.latest_test_evidence_sha256))
        with store._connect() as connection:
            retained = connection.execute("SELECT status,evidence_sha256 FROM workflow_test_runs WHERE workflow_id=?", (workflow.id,)).fetchone()
        self.assertEqual("passed", retained["status"])
        self.assertEqual(result.evidence.evidence_sha256, retained["evidence_sha256"])

    async def test_interrupted_test_is_recoverable(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="aegis-runner-recovery-"))
        store = JarvisStore(root / "jarvis.db")
        store.initialize()
        workflow = store.create_workflow("Interrupted gate", "Recover safely", [], "powershell")
        with store._connect() as connection:
            connection.execute(
                "UPDATE workflows SET state='testing', approval_stage='testing', latest_test_status='running' WHERE id=?",
                (workflow.id,),
            )

        self.assertEqual(1, store.recover_interrupted_workflow_tests())
        recovered = store.get_workflow(workflow.id)
        self.assertEqual("test_failed", recovered.state)
        self.assertEqual("interrupted", recovered.latest_test_status)


if __name__ == "__main__":
    unittest.main()
