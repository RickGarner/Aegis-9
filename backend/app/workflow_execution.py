import asyncio
import json
import os
import queue
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from app.storage import JarvisStore, Workflow, WorkflowRun
from app.workflow_runner import PreparedArtifact, WorkflowTestRunner


class WorkflowExecutionError(RuntimeError):
    pass


class WorkflowExecutionManager:
    def __init__(self, store: JarvisStore, artifact_root: Path, catalog_path: Path, timeout_seconds: int, output_limit: int) -> None:
        self._store = store
        self._runner = WorkflowTestRunner(artifact_root, timeout_seconds, output_limit)
        self._catalog_path = catalog_path
        self._timeout_seconds = timeout_seconds
        self._output_limit = output_limit
        self._tasks: dict[int, asyncio.Task] = {}
        self._cancel: dict[int, threading.Event] = {}

    def validate(self, workflow: Workflow) -> tuple[PreparedArtifact, dict]:
        if not self._store.workflow_approval_is_current(workflow):
            raise WorkflowExecutionError("Supervisor approval no longer matches the workflow revision, artifact, manifest, and schedule.")
        artifact = self._runner.prepare(workflow.transfer_id, workflow.revision, workflow.language, workflow.implementation_text)
        if artifact.sha256 != workflow.artifact_sha256:
            raise WorkflowExecutionError("Prepared artifact hash does not match the supervisor-approved artifact.")
        catalog = json.loads(self._catalog_path.read_text(encoding="utf-8"))
        match = re.search(r"workflowType\s*=\s*['\"]([^'\"]+)", artifact.source_text, re.IGNORECASE)
        profile_name = match.group(1) if match else ""
        profile = catalog.get("profiles", {}).get(profile_name)
        if not profile or not profile.get("enabled"):
            raise WorkflowExecutionError(f"No enabled production action profile matches workflow type '{profile_name or '[missing]'}'.")
        if profile.get("language") != workflow.language:
            raise WorkflowExecutionError("Action profile language does not match the approved artifact.")
        denied_capabilities = set(artifact.manifest.capabilities) - set(profile.get("allowed_capabilities", []))
        denied_commands = {item.casefold() for item in artifact.manifest.commands} - {item.casefold() for item in profile.get("allowed_commands", [])}
        if denied_capabilities or denied_commands:
            raise WorkflowExecutionError("Action catalog denied capabilities or commands: " + ", ".join(sorted(denied_capabilities | denied_commands)))
        return artifact, profile

    async def start(self, workflow: Workflow, trigger: str, requested_by: str, attempt: int = 1) -> WorkflowRun:
        artifact, profile = self.validate(workflow)
        run = self._store.begin_workflow_run(workflow.id, trigger, requested_by, attempt)
        if run is None:
            raise WorkflowExecutionError("Workflow is not eligible to run or already has an active run.")
        cancel = threading.Event()
        self._cancel[run.id] = cancel
        task = asyncio.create_task(self._execute(run, artifact, profile, cancel))
        self._tasks[run.id] = task
        task.add_done_callback(lambda _task, run_id=run.id: self._forget(run_id))
        return run

    def cancel(self, run_id: int) -> WorkflowRun | None:
        run = self._store.request_workflow_run_cancel(run_id)
        if run is not None:
            event = self._cancel.get(run_id)
            if event:
                event.set()
        return run

    def _forget(self, run_id: int) -> None:
        self._tasks.pop(run_id, None)
        self._cancel.pop(run_id, None)

    async def _execute(self, run: WorkflowRun, artifact: PreparedArtifact, profile: dict, cancel: threading.Event) -> None:
        if self._store.mark_workflow_run_running(run.id) is None:
            return
        timeout = min(self._timeout_seconds, int(profile.get("maximum_runtime_seconds", self._timeout_seconds)))
        try:
            result = await asyncio.to_thread(self._run_powershell, run.id, artifact.source_path, timeout, cancel)
            self._store.complete_workflow_run(run.id, *result)
        except Exception as error:
            self._store.complete_workflow_run(run.id, "failed", None, "", "", f"Execution manager failure: {error}")

    def _run_powershell(self, run_id: int, source_path: Path, timeout: int, cancel: threading.Event) -> tuple[str, int | None, str, str, str]:
        environment = {
            "PATH": os.environ.get("PATH", ""), "SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
            "TEMP": tempfile.gettempdir(), "TMP": tempfile.gettempdir(), "USERPROFILE": os.environ.get("USERPROFILE", ""),
            "APPDATA": os.environ.get("APPDATA", ""), "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
            "PSModulePath": os.environ.get("PSModulePath", ""),
        }
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "RemoteSigned", "-File", str(source_path)],
            cwd=source_path.parent, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        messages: queue.Queue[tuple[str, str | None]] = queue.Queue()
        def read_stream(name: str, stream) -> None:
            try:
                for line in iter(stream.readline, ""):
                    messages.put((name, line.rstrip()))
            finally:
                messages.put((name, None))
        threading.Thread(target=read_stream, args=("stdout", process.stdout), daemon=True).start()
        threading.Thread(target=read_stream, args=("stderr", process.stderr), daemon=True).start()
        stdout: list[str] = []
        stderr: list[str] = []
        closed = set()
        started = time.monotonic()
        terminal = "failed"
        error = ""
        while len(closed) < 2 or process.poll() is None:
            if cancel.is_set():
                process.kill(); terminal = "cancelled"; error = "Operator cancellation terminated the workflow process."
            elif time.monotonic() - started > timeout:
                process.kill(); terminal = "timed_out"; error = f"Workflow exceeded its {timeout}-second approved runtime limit."
            try:
                name, line = messages.get(timeout=0.1)
                if line is None:
                    closed.add(name); continue
                target = stdout if name == "stdout" else stderr
                target.append(line)
                self._store.append_workflow_run_event(run_id, name, line)
            except queue.Empty:
                pass
            if terminal in {"cancelled", "timed_out"} and process.poll() is not None and len(closed) >= 2:
                break
        exit_code = process.wait()
        if process.stdout: process.stdout.close()
        if process.stderr: process.stderr.close()
        out = "\n".join(stdout)[-self._output_limit:]
        err = "\n".join(stderr)[-self._output_limit:]
        if terminal not in {"cancelled", "timed_out"}:
            terminal = "succeeded" if exit_code == 0 else "failed"
            if terminal == "failed": error = f"PowerShell exited with code {exit_code}."
        return terminal, exit_code, out, err, error
