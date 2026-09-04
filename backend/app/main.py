import asyncio
import getpass
import json
import os
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import gettempdir

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator

from app.artifacts import try_create_requested_artifact
from app.config import Settings, get_settings
from app.files import UnsupportedFileTypeError, extract_text, is_supported
from app.providers import ChatMessage, OpenAICompatibleProvider, ProviderError, ProviderFailover, ProviderHealth, SystemHealth, check_system_health
from app.speech_recognition import LocalWhisperService
from app.monitoring import (
    MonitoringActionRequest,
    MonitoringActionResult,
    MonitoringCollector,
    MonitoringDashboard,
    MonitoringStore,
)
from app.operations_monitoring import MonitorDescriptor, OperationsMonitoringSnapshot, OperationsSummary, collect_operations_snapshot
from app.storage import ApprovalState, FileEntry, JarvisStore, NotificationOutboxItem, SessionState, Workflow, WorkflowImportResult, WorkflowRun, WorkflowRunEvent, WorkflowTransferPackage, WorkflowTransition
from app.supervisor import TopologyReconciliation, WorkflowCapacity, WorkflowWindowPlacement, get_workflow_capacity
from app.workflow_execution import WorkflowExecutionError, WorkflowExecutionManager
from app.workflow_runner import WorkflowTestEvidence, WorkflowTestRunner
from app.workflow_scheduler import ScheduleError, is_due, prerequisites_met
from app.workflow_notifications import WorkflowNotificationWorker


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    attachment_ids: list[int] = Field(default_factory=list)


class ChatResponse(BaseModel):
    model: str
    content: str
    provider: str = ""
    location: str = ""
    failover: ProviderFailover = Field(default_factory=ProviderFailover)


class ApprovalRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")


class WorkflowRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=20_000)
    attachment_ids: list[int] = Field(default_factory=list)
    language: str = Field(default="powershell", pattern="^(powershell|csharp)$")


class WorkflowReviewRequest(BaseModel):
    decision: str = Field(pattern="^(approve_plan|submit_for_test|user_accept|request_supervisor|supervisor_approve|reject)$")


class WorkflowTestRequest(BaseModel):
    profile: str = Field(default="static", pattern="^(static|restricted)$")


class WorkflowTestResult(BaseModel):
    workflow: Workflow
    evidence: WorkflowTestEvidence


class WorkflowScheduleRequest(BaseModel):
    trigger: str = Field(default="recurring", pattern="^(once|recurring|daily|weekly|interval|manual)$")
    expression: str = Field(default="", max_length=200)
    timezone: str = Field(default="America/New_York", max_length=100)
    reason: str = Field(default="", max_length=500)
    start_conditions: str = Field(default="", max_length=2000)
    stop_conditions: str = Field(default="", max_length=2000)
    start_date: str = Field(default="", max_length=10)
    end_date: str = Field(default="", max_length=10)
    start_time: str = Field(default="00:00", max_length=5)
    end_time: str = Field(default="23:59", max_length=5)
    interval_value: int = Field(default=1, ge=1, le=100000)
    interval_unit: str = Field(default="days", pattern="^(minutes|hours|days|weeks|months)$")

    @model_validator(mode="after")
    def validate_calendar_window(self) -> "WorkflowScheduleRequest":
        from datetime import date, time
        if self.trigger == "manual":
            return self
        if not self.start_date:
            raise ValueError("Start date is required.")
        try:
            start = date.fromisoformat(self.start_date)
            end = date.fromisoformat(self.end_date) if self.end_date else None
            time.fromisoformat(self.start_time)
            time.fromisoformat(self.end_time)
        except ValueError as error:
            raise ValueError("Dates must use YYYY-MM-DD and times must use 24-hour HH:mm format.") from error
        if end and end < start:
            raise ValueError("End date cannot be earlier than start date.")
        return self


class WorkflowClarificationAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)


def parse_workflow_plan_response(content: str) -> tuple[str, list[dict]]:
    candidate = content.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL | re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1)
    elif "{" in candidate and "}" in candidate:
        candidate = candidate[candidate.find("{"):candidate.rfind("}") + 1]
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        malformed_plan = re.search(r'"plan"\s*:\s*"(.*)"\s*,\s*"questions"\s*:', candidate, re.DOTALL | re.IGNORECASE)
        if malformed_plan:
            recovered = malformed_plan.group(1).replace(r'\n', '\n').replace(r'\"', '"').strip()
            if recovered:
                return recovered, infer_unresolved_plan_questions(recovered)
        questions = infer_unresolved_plan_questions(content)
        return content.strip(), questions
    if not isinstance(payload, dict):
        return content.strip(), []
    plan = str(payload.get("plan") or "").strip()
    questions: list[dict] = []
    for index, raw in enumerate(payload.get("questions") or []):
        if not isinstance(raw, dict) or not str(raw.get("prompt") or "").strip():
            continue
        options = [str(option).strip() for option in raw.get("options") or [] if str(option).strip()]
        questions.append({
            "id": str(raw.get("id") or f"question_{index + 1}"),
            "prompt": str(raw["prompt"]).strip(),
            "required": bool(raw.get("required", True)),
            "options": options,
        })
    if not plan:
        return "", []
    resolved_plan = plan
    return resolved_plan, questions or infer_unresolved_plan_questions(resolved_plan)


def parse_markdown_clarification_questions(content: str) -> list[dict]:
    section = re.search(
        r"(?ims)^#{1,6}\s*(?:clarification|required|unanswered)\s+questions?\s*:?\s*$\s*(.*?)(?=^#{1,6}\s|\Z)",
        content,
    )
    if not section:
        return []
    questions: list[dict] = []
    for index, match in enumerate(re.finditer(r"(?m)^\s*(?:\d+[.)]|[-*])\s+(.+?\?)\s*$", section.group(1))):
        prompt = match.group(1).strip()
        questions.append({"id": f"question_{index + 1}", "prompt": prompt, "required": True, "options": []})
    return questions


def infer_unresolved_plan_questions(content: str) -> list[dict]:
    questions = parse_markdown_clarification_questions(content)
    if questions:
        return questions
    normalized = content.replace("\\n", "\n")
    unresolved: list[str] = []
    for line in normalized.splitlines():
        cleaned = re.sub(r"^[\s>*#\-\d.)]+", "", line).strip()
        lowered = cleaned.lower()
        if not cleaned or not any(marker in lowered for marker in ("requires clarification", "needs clarification", "not specified", "to be confirmed", "must be confirmed")):
            continue
        unresolved.append(f"Please confirm or correct this requirement: {cleaned}")
    return [{"id": f"question_{index + 1}", "prompt": prompt, "required": True, "options": []} for index, prompt in enumerate(dict.fromkeys(unresolved))]


class WorkflowActionRequest(BaseModel):
    action: str = Field(pattern="^(pause|resume|stop)$")


class WorkflowExecuteRequest(BaseModel):
    trigger: str = Field(default="manual", pattern="^(manual|scheduled|retry)$")


class SpeechTranscriptionResponse(BaseModel):
    text: str
    language: str
    confidence: float
    detail: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.store = JarvisStore(settings.database_path)
    app.state.store.initialize()
    app.state.store.recover_interrupted_workflow_tests()
    app.state.store.recover_interrupted_workflow_runs()
    app.state.store.recover_processing_notifications()
    app.state.workflow_notifications = WorkflowNotificationWorker(app.state.store, settings)
    app.state.workflow_execution = WorkflowExecutionManager(
        app.state.store, settings.workflow_artifact_root, settings.workflow_action_catalog_path,
        settings.workflow_execution_timeout_seconds, settings.workflow_test_output_limit,
    )
    for workflow in app.state.store.get_workflows():
        parsed_plan, _ = parse_workflow_plan_response(workflow.plan_text) if workflow.plan_text else ("", [])
        if workflow.state in {"design_review", "needs_clarification", "plan_review"} and not parsed_plan:
            app.state.store.reset_invalid_workflow_plan(workflow.id)
            continue
        if parsed_plan and parsed_plan != workflow.plan_text:
            app.state.store.normalize_workflow_plan_text(workflow.id, parsed_plan)
            workflow = app.state.store.get_workflow(workflow.id) or workflow
        if workflow.state != "plan_review" or not workflow.plan_text:
            continue
        inferred = infer_unresolved_plan_questions(workflow.plan_text)
        malformed_json = False
        if workflow.plan_text.lstrip().startswith("{"):
            try:
                json.loads(workflow.plan_text)
            except json.JSONDecodeError:
                malformed_json = True
        if inferred or malformed_json:
            app.state.store.save_workflow_plan(
                workflow.id,
                workflow.plan_text,
                workflow.plan_provider,
                workflow.plan_model,
                inferred or [{"id": "question_1", "prompt": "The tentative plan was incomplete. What additional requirements or corrections should A.E.G.I.S.-9 include before finalizing it?", "required": True, "options": []}],
                finalizing=False,
            )
    app.state.speech_recognition = LocalWhisperService(settings)
    app.state.monitoring = MonitoringCollector(
        MonitoringStore(app.state.store._connect),
        settings.upload_dir,
        settings,
    )
    collect_operations_snapshot(app.state.monitoring)

    async def monitoring_loop() -> None:
        while True:
            await asyncio.sleep(settings.moveit_task_poll_seconds)
            collect_operations_snapshot(app.state.monitoring)

    async def workflow_scheduler_loop() -> None:
        while True:
            await asyncio.sleep(15)
            for workflow in app.state.store.get_workflows():
                try:
                    if not is_due(workflow):
                        if workflow.state == "scheduled":
                            app.state.store.update_workflow_scheduler_status(workflow.id, "waiting")
                        continue
                    allowed, detail = await asyncio.to_thread(prerequisites_met, workflow.schedule)
                    if not allowed:
                        app.state.store.update_workflow_scheduler_status(workflow.id, "deferred", detail)
                        app.state.store.record_workflow_scheduler_event(workflow.id, f"scheduled run deferred: {detail}", "warning")
                        continue
                    await app.state.workflow_execution.start(workflow, "scheduled", "A.E.G.I.S.-9 scheduler")
                    app.state.store.update_workflow_scheduler_status(workflow.id, "queued")
                    app.state.store.record_workflow_scheduler_event(workflow.id, "scheduled run queued after approval and prerequisite revalidation.", "success")
                except (OSError, ScheduleError, WorkflowExecutionError, ValueError) as error:
                    app.state.store.update_workflow_scheduler_status(workflow.id, "blocked", str(error))
                    app.state.store.record_workflow_scheduler_event(workflow.id, f"schedule blocked: {error}", "warning")

    async def workflow_notification_loop() -> None:
        while True:
            await asyncio.sleep(15)
            await asyncio.to_thread(app.state.workflow_notifications.deliver_one)

    monitoring_task = asyncio.create_task(monitoring_loop())
    workflow_scheduler_task = asyncio.create_task(workflow_scheduler_loop())
    workflow_notification_task = asyncio.create_task(workflow_notification_loop())
    app.state.monitoring_task = monitoring_task
    app.state.workflow_scheduler_task = workflow_scheduler_task
    app.state.workflow_notification_task = workflow_notification_task
    yield
    monitoring_task.cancel()
    workflow_scheduler_task.cancel()
    workflow_notification_task.cancel()
    await asyncio.gather(monitoring_task, workflow_scheduler_task, workflow_notification_task, return_exceptions=True)


app = FastAPI(title="A.E.G.I.S.-9 API", version="0.1.0", lifespan=lifespan)


def get_provider(settings: Settings = Depends(get_settings)) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(settings)


def get_store() -> JarvisStore:
    return app.state.store


def get_workflow_execution() -> WorkflowExecutionManager:
    return app.state.workflow_execution


def get_monitoring() -> MonitoringCollector:
    return app.state.monitoring


def get_speech_recognition() -> LocalWhisperService:
    return app.state.speech_recognition


def get_workflow_capacity_from_settings(
    settings: Settings = Depends(get_settings),
) -> WorkflowCapacity:
    return get_workflow_capacity(settings.workflow_window_limit)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "jarvis-api"}


@app.get("/api/provider/health", response_model=ProviderHealth)
async def provider_health(
    provider: OpenAICompatibleProvider = Depends(get_provider),
) -> ProviderHealth:
    return await provider.health()


@app.get("/api/system/health", response_model=SystemHealth)
async def system_health(
    settings: Settings = Depends(get_settings),
) -> SystemHealth:
    return await check_system_health(settings)


@app.get("/api/session", response_model=SessionState)
async def session(store: JarvisStore = Depends(get_store)) -> SessionState:
    return store.get_session()


@app.post("/api/speech/transcribe", response_model=SpeechTranscriptionResponse)
async def transcribe_speech(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    speech_recognition: LocalWhisperService = Depends(get_speech_recognition),
) -> SpeechTranscriptionResponse:
    filename = file.filename or ""
    if Path(filename).suffix.lower() != ".wav":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Local speech transcription accepts WAV audio only.",
        )

    contents = await file.read(settings.max_upload_bytes + 1)
    if not contents:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The audio recording is empty.")
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The audio recording exceeds the configured upload size limit.",
        )

    temporary_directory = Path(gettempdir()) / "Aegis9" / "VoiceInput"
    temporary_directory.mkdir(parents=True, exist_ok=True)
    temporary_path = temporary_directory / f"speech-{uuid.uuid4().hex}.wav"
    try:
        temporary_path.write_bytes(contents)
        transcription = await asyncio.to_thread(speech_recognition.transcribe, temporary_path)
    except (OSError, RuntimeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Local Whisper transcription is unavailable: {error}",
        ) from error
    finally:
        temporary_path.unlink(missing_ok=True)

    return SpeechTranscriptionResponse(
        text=transcription.text,
        language=transcription.language,
        confidence=transcription.confidence,
        detail=f"Transcribed locally with Whisper on {transcription.runtime}.",
    )


@app.get("/api/monitoring", response_model=MonitoringDashboard)
async def monitoring_dashboard(
    monitoring: MonitoringCollector = Depends(get_monitoring),
) -> MonitoringDashboard:
    return monitoring.collect()


@app.get("/api/operations/monitoring", response_model=OperationsMonitoringSnapshot)
async def operations_monitoring_snapshot(
    monitoring: MonitoringCollector = Depends(get_monitoring),
) -> OperationsMonitoringSnapshot:
    return collect_operations_snapshot(monitoring)


@app.get("/api/operations/summary", response_model=OperationsSummary)
async def operations_monitoring_summary(
    monitoring: MonitoringCollector = Depends(get_monitoring),
) -> OperationsSummary:
    return collect_operations_snapshot(monitoring).summary


@app.get("/api/operations/collectors", response_model=list[MonitorDescriptor])
async def operations_monitoring_collectors(
    monitoring: MonitoringCollector = Depends(get_monitoring),
) -> list[MonitorDescriptor]:
    return collect_operations_snapshot(monitoring).monitors


@app.post("/api/monitoring/actions", response_model=MonitoringActionResult, status_code=status.HTTP_202_ACCEPTED)
async def monitoring_action(request: MonitoringActionRequest) -> MonitoringActionResult:
    return MonitoringActionResult(
        status="not_configured",
        source=request.source,
        issue=request.issue,
        detail="Action catalog and external integration are not configured. Nothing was executed.",
    )


@app.post("/api/monitoring/alerts/{alert_id}/resolve", response_model=MonitoringDashboard)
async def resolve_monitoring_alert(
    alert_id: int,
    monitoring: MonitoringCollector = Depends(get_monitoring),
) -> MonitoringDashboard:
    if monitoring.store.resolve_alert(alert_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitoring alert was not found.")
    return monitoring.collect()


@app.post("/api/files/upload", response_model=FileEntry, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    store: JarvisStore = Depends(get_store),
) -> FileEntry:
    if not file.filename or not is_supported(file.filename):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type for intake.",
        )

    contents = await file.read()
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the configured upload size limit.",
        )

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{file.filename}"
    stored_path = settings.upload_dir / stored_name
    stored_path.write_bytes(contents)

    try:
        extracted_text = extract_text(stored_path, file.filename)
    except UnsupportedFileTypeError as error:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(error)) from error

    return store.save_uploaded_file(
        name=file.filename,
        size=len(contents),
        content_type=file.content_type,
        stored_name=stored_name,
        extracted_text=extracted_text,
    )


@app.get("/api/files/{file_id}/content")
async def file_content(
    file_id: int,
    store: JarvisStore = Depends(get_store),
) -> dict[str, str | None]:
    content = store.get_file_content(file_id)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No extracted text is available for this file.")
    return {"content": content}


@app.delete("/api/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: int,
    settings: Settings = Depends(get_settings),
    store: JarvisStore = Depends(get_store),
) -> None:
    stored_name = store.delete_file(file_id)
    if stored_name is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File was not found.")
    stored_path = settings.upload_dir / stored_name
    try:
        stored_path.unlink(missing_ok=True)
    except OSError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="File metadata was removed but stored content could not be deleted.") from error


@app.post("/api/approvals", response_model=ApprovalState)
async def update_approval(
    request: ApprovalRequest,
    store: JarvisStore = Depends(get_store),
) -> ApprovalState:
    return store.set_approval(request.decision)


@app.get("/api/workflows/capacity", response_model=WorkflowCapacity)
async def workflow_capacity(
    capacity: WorkflowCapacity = Depends(get_workflow_capacity_from_settings),
) -> WorkflowCapacity:
    return capacity


@app.get("/api/workflows", response_model=list[Workflow])
async def workflows(store: JarvisStore = Depends(get_store)) -> list[Workflow]:
    return store.get_workflows()


@app.get("/api/workflows/{workflow_id}", response_model=Workflow)
async def workflow(workflow_id: int, store: JarvisStore = Depends(get_store)) -> Workflow:
    result = store.get_workflow(workflow_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow was not found.")
    return result


@app.get("/api/workflows/{workflow_id}/export")
async def export_workflow(workflow_id: int, store: JarvisStore = Depends(get_store)) -> Response:
    package = store.export_workflow(workflow_id)
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow was not found.")
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", package.workflow["title"]).strip("-") or "workflow"
    return Response(
        content=package.model_dump_json(indent=2),
        media_type="application/vnd.aegis9.workflow+json",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.aegisworkflow"'},
    )


@app.post("/api/workflows/import", response_model=WorkflowImportResult)
async def import_workflow(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    store: JarvisStore = Depends(get_store),
) -> WorkflowImportResult:
    if not file.filename or Path(file.filename).suffix.lower() != ".aegisworkflow":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Select an .aegisworkflow file.")
    contents = await file.read(settings.max_upload_bytes + 1)
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Workflow package exceeds the configured upload limit.")
    try:
        package = WorkflowTransferPackage.model_validate_json(contents)
        return store.import_workflow(package)
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid workflow package: {error}") from error


@app.get("/api/workflows/placements", response_model=list[WorkflowWindowPlacement])
async def workflow_placements(
    store: JarvisStore = Depends(get_store),
    capacity: WorkflowCapacity = Depends(get_workflow_capacity_from_settings),
) -> list[WorkflowWindowPlacement]:
    monitors_by_slot = {monitor.slot: monitor for monitor in capacity.monitors}
    return [
        WorkflowWindowPlacement(
            workflow_id=workflow.id,
            title=workflow.title,
            state=workflow.state,
            monitor=monitors_by_slot[workflow.monitor_slot],
        )
        for workflow in store.get_workflows()
        if workflow.state in {"running", "paused"} and workflow.monitor_slot in monitors_by_slot
    ]


@app.post("/api/workflows/reconcile-topology", response_model=TopologyReconciliation)
async def reconcile_workflow_topology(
    store: JarvisStore = Depends(get_store),
    capacity: WorkflowCapacity = Depends(get_workflow_capacity_from_settings),
) -> TopologyReconciliation:
    changed, requeued_workflow_ids = store.reconcile_workflow_topology(
        capacity.topology_fingerprint,
        {monitor.slot for monitor in capacity.monitors},
    )
    return TopologyReconciliation(
        changed=changed,
        topology_fingerprint=capacity.topology_fingerprint,
        requeued_workflow_ids=requeued_workflow_ids,
    )


@app.post("/api/workflows", response_model=Workflow, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowRequest,
    store: JarvisStore = Depends(get_store),
) -> Workflow:
    return store.create_workflow(request.title, request.description, request.attachment_ids, request.language)


@app.put("/api/workflows/{workflow_id}", response_model=Workflow)
async def update_workflow(workflow_id: int, request: WorkflowRequest, store: JarvisStore = Depends(get_store)) -> Workflow:
    result = store.update_workflow(workflow_id, request.title, request.description, request.attachment_ids, request.language)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow cannot be edited while active or was not found.")
    return result


@app.post("/api/workflows/{workflow_id}/review", response_model=Workflow)
async def review_workflow(
    workflow_id: int,
    request: WorkflowReviewRequest,
    settings: Settings = Depends(get_settings),
    store: JarvisStore = Depends(get_store),
) -> Workflow:
    if request.decision == "submit_for_test":
        workflow = store.get_workflow(workflow_id)
        if workflow is None or workflow.state != "implementation_review":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only an implementation under review can be submitted for testing.")
        runner = WorkflowTestRunner(settings.workflow_artifact_root, settings.workflow_test_timeout_seconds, settings.workflow_test_output_limit)
        try:
            artifact = runner.prepare(workflow.transfer_id, workflow.revision, workflow.language, workflow.implementation_text)
        except (OSError, RuntimeError, ValueError) as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Implementation artifact could not be prepared: {error}") from error
        if store.save_prepared_artifact(workflow_id, artifact.sha256, artifact.manifest.model_dump()) is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow changed before its test artifact could be stored.")
    if request.decision == "supervisor_approve":
        identity = getpass.getuser()
        allowed = {item.strip().casefold() for item in settings.workflow_supervisor_identities.split(",") if item.strip()}
        candidates = {identity.casefold(), f"{os.environ.get('USERDOMAIN', '')}\\{identity}".casefold()}
        if not allowed or allowed.isdisjoint(candidates):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Windows identity '{identity}' is not configured as an A.E.G.I.S.-9 workflow supervisor.")
        result = store.approve_workflow_for_production(workflow_id, identity)
    else:
        result = store.review_workflow(workflow_id, request.decision)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Decision is not valid for the workflow's current gate.")
    return result


@app.post("/api/workflows/{workflow_id}/run-test", response_model=WorkflowTestResult)
async def run_workflow_test(
    workflow_id: int,
    request: WorkflowTestRequest,
    settings: Settings = Depends(get_settings),
    store: JarvisStore = Depends(get_store),
) -> WorkflowTestResult:
    workflow = store.get_workflow(workflow_id)
    if workflow is None or workflow.state not in {"test_ready", "test_failed"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow is not ready for isolated validation.")
    runner = WorkflowTestRunner(settings.workflow_artifact_root, settings.workflow_test_timeout_seconds, settings.workflow_test_output_limit)
    try:
        artifact = runner.prepare(workflow.transfer_id, workflow.revision, workflow.language, workflow.implementation_text)
    except (OSError, RuntimeError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Implementation artifact is invalid: {error}") from error
    if artifact.sha256 != workflow.artifact_sha256:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Generated implementation changed after test submission; return it to implementation review.")
    if store.begin_workflow_test(workflow_id) is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow could not enter the testing state.")
    evidence = await asyncio.to_thread(runner.run, artifact, workflow.language, request.profile)
    updated = store.complete_workflow_test(workflow_id, evidence.model_dump())
    if updated is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Test evidence could not be attached to the workflow.")
    return WorkflowTestResult(workflow=updated, evidence=evidence)


@app.post("/api/workflows/{workflow_id}/design-plan", response_model=Workflow)
async def design_workflow_plan(
    workflow_id: int,
    provider: OpenAICompatibleProvider = Depends(get_provider),
    store: JarvisStore = Depends(get_store),
) -> Workflow:
    return await _generate_workflow_plan(workflow_id, provider, store, finalizing=False)


async def _generate_workflow_plan(
    workflow_id: int,
    provider: OpenAICompatibleProvider,
    store: JarvisStore,
    finalizing: bool,
) -> Workflow:
    workflow = store.get_workflow(workflow_id)
    if workflow is None or workflow.archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow was not found.")
    if workflow.state not in {"draft", "rejected", "plan_review", "design_review"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The workflow is not available for plan design.")
    attachments = [store.get_file_content(file_id) for file_id in workflow.attachment_ids]
    context = "\n\n".join(content for content in attachments if content)
    messages = [
        ChatMessage(role="system", content="You are the A.E.G.I.S.-9 workflow architect. Design a safe, testable operational workflow plan only; do not generate executable code. Return strict JSON with this shape: {\"plan\": \"complete markdown plan\", \"questions\": [{\"id\": \"stable_key\", \"prompt\": \"question\", \"required\": true, \"options\": [\"optional choice\"]}]}. The plan must cover goal, inputs, assumptions, ordered steps, permissions, risks, test strategy, success criteria, schedule considerations, and stop conditions. Ask only material unresolved questions. Return an empty questions array when the plan is ready for approval."),
        ChatMessage(role="user", content=f"Workflow: {workflow.title}\nRequest: {workflow.description}\nPreferred implementation: {workflow.language}\nAttached material:\n{context or '[none]'}\nPreviously submitted clarification answers:\n{json.dumps(workflow.clarification_answers, indent=2) if workflow.clarification_answers else '[none]'}"),
    ]
    routed = None
    plan = ""
    questions: list[dict] = []
    for attempt in range(2):
        try:
            routed = await provider.chat_for_task("reasoning", messages)
        except ProviderError as error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
        plan, questions = parse_workflow_plan_response(routed.content)
        if plan:
            break
        messages.extend([
            ChatMessage(role="assistant", content=routed.content),
            ChatMessage(role="user", content="Your response contained an empty plan. Return the requested strict JSON again with a substantive, complete markdown plan. Do not leave the plan field empty."),
        ])
    if not plan or routed is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The selected planning model returned an empty workflow plan twice. The draft remains unchanged; retry planning or select another reasoning model.",
        )
    result = store.save_workflow_plan(workflow_id, plan, routed.route.provider, routed.route.model, questions, finalizing=finalizing)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow changed before the plan could be saved.")
    return result


@app.put("/api/workflows/{workflow_id}/clarifications/{question_id}", response_model=Workflow)
async def answer_one_workflow_clarification(
    workflow_id: int,
    question_id: str,
    request: WorkflowClarificationAnswerRequest,
    store: JarvisStore = Depends(get_store),
) -> Workflow:
    result = store.save_clarification_answer(workflow_id, question_id, request.answer)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The question is unavailable or the workflow is not in design review.")
    return result


@app.post("/api/workflows/{workflow_id}/complete-design-review", response_model=Workflow)
async def complete_workflow_design_review(
    workflow_id: int,
    provider: OpenAICompatibleProvider = Depends(get_provider),
    store: JarvisStore = Depends(get_store),
) -> Workflow:
    if store.begin_workflow_reevaluation(workflow_id) is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Every required question must be submitted before updating the draft.")
    return await _generate_workflow_plan(workflow_id, provider, store, finalizing=True)


@app.post("/api/workflows/{workflow_id}/generate-implementation", response_model=Workflow)
async def generate_workflow_implementation(
    workflow_id: int,
    provider: OpenAICompatibleProvider = Depends(get_provider),
    store: JarvisStore = Depends(get_store),
) -> Workflow:
    workflow = store.get_workflow(workflow_id)
    if workflow is None or workflow.archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow was not found.")
    if workflow.state != "plan_approved" or not workflow.plan_text:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The workflow plan must be approved before implementation generation.")
    language = "PowerShell" if workflow.language == "powershell" else "C#"
    messages = [
        ChatMessage(role="system", content=f"You are the A.E.G.I.S.-9 implementation engineer. Implement the approved workflow plan in {language}. Produce reviewable code with strict input validation, structured logging, dry-run support, cancellation/timeouts, no embedded credentials, and clear configuration placeholders. After the implementation, provide at least two distinct non-production test plans with setup, inputs, expected results, cleanup, and pass/fail criteria. Do not claim that the implementation or tests were executed."),
        ChatMessage(role="user", content=f"Approved plan, revision {workflow.revision}:\n{workflow.plan_text}"),
    ]
    try:
        routed = await provider.chat_for_task("code", messages)
    except ProviderError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    result = store.save_workflow_implementation(workflow_id, routed.content, routed.route.provider, routed.route.model)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow approval changed before the implementation could be saved.")
    return result


@app.put("/api/workflows/{workflow_id}/schedule", response_model=Workflow)
async def schedule_workflow(workflow_id: int, request: WorkflowScheduleRequest, store: JarvisStore = Depends(get_store)) -> Workflow:
    result = store.set_workflow_schedule(workflow_id, request.model_dump())
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A workflow must be awaiting supervisor review before its approval-bound schedule can be recorded.")
    return result


@app.post("/api/workflows/{workflow_id}/execute", response_model=WorkflowRun, status_code=status.HTTP_202_ACCEPTED)
async def execute_workflow(
    workflow_id: int,
    request: WorkflowExecuteRequest,
    store: JarvisStore = Depends(get_store),
    manager: WorkflowExecutionManager = Depends(get_workflow_execution),
) -> WorkflowRun:
    workflow = store.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow was not found.")
    try:
        return await manager.start(workflow, request.trigger, getpass.getuser())
    except (OSError, ValueError, WorkflowExecutionError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@app.get("/api/workflows/{workflow_id}/runs", response_model=list[WorkflowRun])
async def list_workflow_runs(workflow_id: int, store: JarvisStore = Depends(get_store)) -> list[WorkflowRun]:
    if store.get_workflow(workflow_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow was not found.")
    return store.get_workflow_runs(workflow_id)


@app.get("/api/workflow-runs/{run_id}", response_model=WorkflowRun)
async def get_workflow_run(run_id: int, store: JarvisStore = Depends(get_store)) -> WorkflowRun:
    run = store.get_workflow_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow run was not found.")
    return run


@app.get("/api/workflow-runs/{run_id}/events", response_model=list[WorkflowRunEvent])
async def list_workflow_run_events(run_id: int, after_sequence: int = 0, store: JarvisStore = Depends(get_store)) -> list[WorkflowRunEvent]:
    if store.get_workflow_run(run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow run was not found.")
    return store.get_workflow_run_events(run_id, after_sequence)


@app.get("/api/notifications", response_model=list[NotificationOutboxItem])
async def notification_history(
    category: str | None = None,
    limit: int = 100,
    store: JarvisStore = Depends(get_store),
) -> list[NotificationOutboxItem]:
    return store.get_notification_outbox_items(category, limit)


@app.post("/api/notifications/{item_id}/retry", response_model=NotificationOutboxItem)
async def retry_notification(item_id: int, store: JarvisStore = Depends(get_store)) -> NotificationOutboxItem:
    item = store.retry_notification_outbox_item(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a failed notification can be retried.",
        )
    return item


@app.post("/api/workflow-runs/{run_id}/cancel", response_model=WorkflowRun)
async def cancel_workflow_run(run_id: int, manager: WorkflowExecutionManager = Depends(get_workflow_execution)) -> WorkflowRun:
    run = manager.cancel(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow run is not active or cannot be cancelled.")
    return run


@app.post("/api/workflow-runs/{run_id}/retry", response_model=WorkflowRun, status_code=status.HTTP_202_ACCEPTED)
async def retry_workflow_run(
    run_id: int,
    store: JarvisStore = Depends(get_store),
    manager: WorkflowExecutionManager = Depends(get_workflow_execution),
) -> WorkflowRun:
    prior = store.get_workflow_run(run_id)
    if prior is None or prior.status not in {"failed", "cancelled", "timed_out", "interrupted"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a terminal unsuccessful run can be retried.")
    workflow = store.get_workflow(prior.workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow was not found.")
    try:
        return await manager.start(workflow, "retry", getpass.getuser(), prior.attempt + 1)
    except (OSError, ValueError, WorkflowExecutionError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@app.delete("/api/workflows/{workflow_id}", response_model=Workflow)
async def archive_workflow(workflow_id: int, store: JarvisStore = Depends(get_store)) -> Workflow:
    result = store.archive_workflow(workflow_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active workflows must be stopped before archival.")
    return result


@app.post("/api/workflows/{workflow_id}/approve", response_model=Workflow)
async def approve_workflow(
    workflow_id: int,
    store: JarvisStore = Depends(get_store),
    capacity: WorkflowCapacity = Depends(get_workflow_capacity_from_settings),
) -> Workflow:
    workflow = store.approve_workflow(workflow_id, capacity.effective_capacity)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workflow must be awaiting approval before it can be scheduled.",
        )
    return workflow


@app.post("/api/workflows/{workflow_id}/actions", response_model=WorkflowTransition)
async def transition_workflow(
    workflow_id: int,
    request: WorkflowActionRequest,
    store: JarvisStore = Depends(get_store),
    capacity: WorkflowCapacity = Depends(get_workflow_capacity_from_settings),
) -> WorkflowTransition:
    transition = store.transition_workflow(
        workflow_id,
        request.action,
        capacity.effective_capacity,
    )
    if transition is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested workflow action is not valid for its current state.",
        )
    return transition


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
    provider: OpenAICompatibleProvider = Depends(get_provider),
    store: JarvisStore = Depends(get_store),
) -> ChatResponse:
    latest_user_message = request.messages[-1]
    artifact = try_create_requested_artifact(latest_user_message.content, Path(__file__).resolve().parents[2])
    if artifact is not None:
        content = (
            f"Created {artifact.description}\n\n"
            f"Path: {artifact.relative_path}\n\n"
            "Run it with:\n"
            f"powershell -ExecutionPolicy Bypass -File {artifact.relative_path}"
        )
        assistant_message = ChatMessage(role="assistant", content=content)
        store.record_chat(latest_user_message, assistant_message)
        return ChatResponse(
            model="local-artifact-generator",
            content=content,
            provider="aegis9",
            location="local",
        )

    outgoing_messages = list(request.messages)
    if request.attachment_ids:
        attachment_sections = []
        for file_id in request.attachment_ids:
            content = store.get_file_content(file_id)
            if content:
                attachment_sections.append(f"[Attached file {file_id}]\n{content}")
        if attachment_sections:
            outgoing_messages = [
                ChatMessage(role="system", content="The operator attached the following file context:\n\n" + "\n\n".join(attachment_sections)),
                *outgoing_messages,
            ]

    try:
        routed_result = await provider.chat(outgoing_messages)
    except ProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    assistant_message = ChatMessage(role="assistant", content=routed_result.content)
    store.record_chat(request.messages[-1], assistant_message)
    return ChatResponse(
        model=routed_result.route.model,
        content=routed_result.content,
        provider=routed_result.route.provider,
        location=routed_result.route.location,
        failover=routed_result.failover,
    )
