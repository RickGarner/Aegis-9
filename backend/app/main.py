import asyncio
import json
import re
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
    language: str = Field(default="powershell", pattern="^(powershell|csharp)$")


class WorkflowReviewRequest(BaseModel):
    decision: str = Field(pattern="^(approve_plan|submit_for_test|test_pass|test_fail|user_accept|request_supervisor|supervisor_approve|reject)$")


class WorkflowScheduleRequest(BaseModel):
    trigger: str = Field(default="daily", pattern="^(once|daily|weekly|interval|manual)$")
    expression: str = Field(default="", max_length=200)
    timezone: str = Field(default="America/New_York", max_length=100)
    reason: str = Field(default="", max_length=500)
    start_conditions: str = Field(default="", max_length=2000)
    stop_conditions: str = Field(default="", max_length=2000)


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
    resolved_plan = plan or content.strip()
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
    for workflow in app.state.store.get_workflows():
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


@app.get("/api/workflows/{workflow_id}", response_model=Workflow)
async def workflow(workflow_id: int, store: JarvisStore = Depends(get_store)) -> Workflow:
    result = store.get_workflow(workflow_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow was not found.")
    return result


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
async def review_workflow(workflow_id: int, request: WorkflowReviewRequest, store: JarvisStore = Depends(get_store)) -> Workflow:
    result = store.review_workflow(workflow_id, request.decision)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Decision is not valid for the workflow's current gate.")
    return result


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
    try:
        routed = await provider.chat_for_task("reasoning", messages)
    except ProviderError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    plan, questions = parse_workflow_plan_response(routed.content)
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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Supervisor approval is required before scheduling.")
    return result


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
