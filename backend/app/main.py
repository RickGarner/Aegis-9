import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import gettempdir

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

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
from app.storage import ApprovalState, FileEntry, JarvisStore, SessionState, Workflow, WorkflowTransition
from app.supervisor import TopologyReconciliation, WorkflowCapacity, WorkflowWindowPlacement, get_workflow_capacity


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
    description: str = Field(default="", max_length=500)
    attachment_ids: list[int] = Field(default_factory=list)


class WorkflowActionRequest(BaseModel):
    action: str = Field(pattern="^(pause|resume|stop)$")


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
    app.state.speech_recognition = LocalWhisperService(settings)
    app.state.monitoring = MonitoringCollector(
        MonitoringStore(app.state.store._connect),
        settings.upload_dir,
        settings,
    )
    app.state.monitoring.collect()

    async def monitoring_loop() -> None:
        while True:
            await asyncio.sleep(settings.moveit_task_poll_seconds)
            app.state.monitoring.collect()

    monitoring_task = asyncio.create_task(monitoring_loop())
    app.state.monitoring_task = monitoring_task
    yield
    monitoring_task.cancel()
    await asyncio.gather(monitoring_task, return_exceptions=True)


app = FastAPI(title="A.E.G.I.S.-9 API", version="0.1.0", lifespan=lifespan)


def get_provider(settings: Settings = Depends(get_settings)) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(settings)


def get_store() -> JarvisStore:
    return app.state.store


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
    return store.create_workflow(request.title, request.description, request.attachment_ids)


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
