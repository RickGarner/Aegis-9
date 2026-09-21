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
from app.security_control import SecurityControlPolicy
from app.workflow_agent_tools import WorkflowAgentToolContext
from app.policy_integrity import policy_status
from app.post_acceptance import EncryptedSemanticStore, ReviewHistoryStore, create_cyclonedx, export_migration, import_migration, local_embedding, match_offline_vulnerabilities, scan_dependencies, semantic_similarity
from app.test_lab import create_test_package, create_test_plan
from app.workflow_implementation_tools import ApprovedWorkflowImplementationToolContext
from app.workflow_governance import WORKFLOW_ARCHITECT_INSTRUCTIONS, workflow_implementer_instructions
from app.workflow_documentation import WorkflowDocumentationManager
from app.moveit_ha import MoveItHaService
from app.moveit_ha.models import HaStatus
from app.freeflow_jmf import FreeFlowJmfCapabilities, FreeFlowJmfDiscovery, FreeFlowJmfJobs, FreeFlowJmfService, FreeFlowJmfStatus
from app.authorization import AuthorizationError, RoleAuthorizer


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


class SemanticIndexRequest(BaseModel):
    records: list[dict] = Field(max_length=50_000)


class SemanticQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    limit: int = Field(default=20, ge=1, le=100)


class ReviewHistoryRequest(BaseModel):
    summary: str = Field(min_length=1, max_length=2000)
    findings: int = Field(default=0, ge=0, le=100_000)
    validation: str = Field(default="", max_length=2000)
    approved: bool = False


class DependencyScanRequest(BaseModel):
    files: dict[str, str] = Field(max_length=1000)
    vulnerability_database: list[dict[str, str]] = Field(default_factory=list, max_length=1_000_000)


class MigrationRequest(BaseModel):
    files: dict[str, str] = Field(max_length=1000)


class TestLabPlanRequest(BaseModel):
    files: dict[str, str] = Field(min_length=1, max_length=100)
    use_ai: bool = True


class TestLabPackageRequest(BaseModel):
    files: dict[str, str] = Field(min_length=1, max_length=100)
    plan: dict
    approved: bool = False


class WorkflowRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=20_000)
    attachment_ids: list[int] = Field(default_factory=list)
    language: str = Field(default="powershell", pattern="^(powershell|csharp)$")


class WorkflowReviewRequest(BaseModel):
    decision: str = Field(pattern="^(approve_plan|approve_test_plan|submit_for_test|user_accept|request_supervisor|supervisor_approve|reject)$")


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
        settings.security_control_policy_path,
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
        workflow_store=app.state.store,
    )
    app.state.workflow_documentation = WorkflowDocumentationManager(settings.workflow_documentation_root)
    for workflow in app.state.store.get_workflows():
        app.state.workflow_documentation.ensure(workflow)
    app.state.moveit_ha = MoveItHaService(settings.moveit_ha_config_path, settings.moveit_ha_state_path)
    app.state.freeflow_jmf = FreeFlowJmfService(settings)
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


def require_capability(capability: str):
    def dependency(settings: Settings = Depends(get_settings)) -> frozenset[str]:
        try:
            return RoleAuthorizer(settings.role_mapping_path).require(capability)
        except AuthorizationError as error:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error

    dependency.__name__ = f"require_{capability.replace('.', '_').replace('-', '_')}"
    dependency.required_capability = capability
    return dependency


def require_workflow_review_capability(
    request: WorkflowReviewRequest,
    settings: Settings = Depends(get_settings),
) -> frozenset[str]:
    capability = (
        "workflow.supervisor-approve"
        if request.decision == "supervisor_approve"
        else "workflow.design"
        if request.decision == "submit_for_test"
        else "workflow.approve"
    )
    try:
        return RoleAuthorizer(settings.role_mapping_path).require(capability)
    except AuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


def get_provider(settings: Settings = Depends(get_settings)) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(settings)


def get_store() -> JarvisStore:
    return app.state.store


def get_workflow_execution() -> WorkflowExecutionManager:
    return app.state.workflow_execution


def get_monitoring() -> MonitoringCollector:
    return app.state.monitoring


def get_freeflow_jmf() -> FreeFlowJmfService:
    return app.state.freeflow_jmf


def document_workflow(workflow: Workflow, event: str, detail: str = "") -> Workflow:
    manager = getattr(app.state, "workflow_documentation", None)
    if manager is not None:
        manager.record(workflow, event, detail)
    return workflow


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

@app.get("/api/security/policy-status")
async def security_policy_status(settings: Settings = Depends(get_settings)) -> dict:
    root = Path(__file__).resolve().parents[2]
    return policy_status([settings.security_control_policy_path, root / "config" / "mcp" / "catalog.json", root / "docs" / "SHARED-TOOL-PARITY-CONTRACT.json"], required=settings.require_signed_policies, public_key_path=settings.policy_public_key_path)


def _semantic_store(settings: Settings) -> EncryptedSemanticStore:
    key_path = settings.post_acceptance_storage_root / "semantic.key"
    if not key_path.exists():
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(os.urandom(32))
        try:
            key_path.chmod(0o600)
        except OSError:
            pass
    return EncryptedSemanticStore(settings.post_acceptance_storage_root / "semantic-index.bin", key_path.read_bytes())


@app.post("/api/local-intelligence/semantic-index")
async def refresh_semantic_index(request: SemanticIndexRequest, settings: Settings = Depends(get_settings)) -> dict:
    records = []
    for item in request.records:
        identifier, text, metadata = str(item.get("id", ""))[:500], str(item.get("text", ""))[:200_000], item.get("metadata", {})
        if not identifier or not isinstance(metadata, dict):
            raise HTTPException(status_code=400, detail="Each semantic record requires id, text, and object metadata.")
        records.append({"id": identifier, "vector": local_embedding(text), "metadata": {str(key)[:200]: str(value)[:2000] for key, value in list(metadata.items())[:50]}})
    _semantic_store(settings).save(records)
    return {"status": "ready", "records": len(records), "offline": True, "encrypted": True}


@app.post("/api/local-intelligence/semantic-query")
async def query_semantic_index(request: SemanticQueryRequest, settings: Settings = Depends(get_settings)) -> dict:
    query = local_embedding(request.query)
    matches = sorted(({"id": item["id"], "score": semantic_similarity(query, item["vector"]), "metadata": item.get("metadata", {})} for item in _semantic_store(settings).load()), key=lambda item: item["score"], reverse=True)[:request.limit]
    return {"matches": matches, "offline": True}


@app.delete("/api/local-intelligence/semantic-index", status_code=status.HTTP_204_NO_CONTENT)
async def clear_semantic_index(settings: Settings = Depends(get_settings)) -> Response:
    _semantic_store(settings).clear()
    (settings.post_acceptance_storage_root / "semantic.key").unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/review-history")
async def get_review_history(limit: int = 100, settings: Settings = Depends(get_settings)) -> list[dict]:
    return ReviewHistoryStore(settings.post_acceptance_storage_root / "review-history.jsonl").list(limit)


@app.post("/api/review-history", status_code=status.HTTP_201_CREATED)
async def add_review_history(request: ReviewHistoryRequest, settings: Settings = Depends(get_settings)) -> dict:
    return ReviewHistoryStore(settings.post_acceptance_storage_root / "review-history.jsonl").append(request.summary, request.findings, request.validation, request.approved)


@app.post("/api/dependencies/offline-scan")
async def offline_dependency_scan(request: DependencyScanRequest) -> dict:
    dependencies = scan_dependencies(request.files)
    return {"sbom": create_cyclonedx(dependencies), "vulnerabilities": match_offline_vulnerabilities(dependencies, request.vulnerability_database), "offline": True}


@app.post("/api/migration/export")
async def export_local_migration(request: MigrationRequest, settings: Settings = Depends(get_settings)) -> Response:
    destination = settings.post_acceptance_storage_root / f"aegis-export-{uuid.uuid4()}.aegis-export"
    export_migration(destination, request.files)
    value = destination.read_bytes()
    destination.unlink(missing_ok=True)
    return Response(content=value, media_type="application/vnd.aegis.export", headers={"Content-Disposition": "attachment; filename=aegis-9.aegis-export"})


@app.post("/api/migration/inspect")
async def inspect_local_migration(file: UploadFile = File(...), settings: Settings = Depends(get_settings)) -> dict:
    destination = settings.post_acceptance_storage_root / f"inspect-{uuid.uuid4()}.aegis-export"
    try:
        content = await file.read(25_000_001)
        if len(content) > 25_000_000:
            raise HTTPException(status_code=413, detail="Migration bundle exceeds 25 MB.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        payload = import_migration(destination)
        return {"schemaVersion": payload["schemaVersion"], "createdAt": payload["createdAt"], "files": list(payload["files"]), "validated": True, "applied": False}
    finally:
        destination.unlink(missing_ok=True)


def _bounded_test_lab_files(files: dict[str, str]) -> dict[str, str]:
    if sum(len(value) for value in files.values()) > 2_000_000 or any(not name.strip() or len(name) > 500 or len(content) > 500_000 for name, content in files.items()):
        raise HTTPException(status_code=413, detail="Test Lab source exceeds bounded file or request limits.")
    return files


@app.post("/api/test-lab/plan", dependencies=[Depends(require_capability("workflow.design"))])
async def create_test_lab_plan(request: TestLabPlanRequest, provider: OpenAICompatibleProvider = Depends(get_provider)) -> dict:
    files = _bounded_test_lab_files(request.files)
    ai_cases: list[dict] = []
    ai_status = "disabled"
    if request.use_ai:
        source = "\n\n".join(f"FILE {name}\n{content[:20_000]}" for name, content in list(files.items())[:10])[:80_000]
        messages = [
            ChatMessage(role="system", content="You are the A.E.G.I.S. Test Lab test architect. Analyze without executing. Return only a JSON array of at most 10 objects with string name, string purpose, object syntheticInput, and string expected. Use synthetic values only. Never request production credentials, external network access, host writes, or weaker sandbox controls."),
            ChatMessage(role="user", content=source),
        ]
        try:
            routed = await provider.chat_for_task("reasoning", messages)
            match = re.search(r"\[[\s\S]*\]", routed.content)
            candidate = json.loads(match.group(0)) if match else []
            if isinstance(candidate, list):
                ai_cases = candidate
                ai_status = f"generated locally by {routed.route.provider}/{routed.route.model}"
            else:
                ai_status = "local model returned an invalid test-case shape; deterministic cases retained"
        except (ProviderError, json.JSONDecodeError, ValueError) as error:
            ai_status = f"local AI unavailable; deterministic cases retained: {str(error)[:300]}"
    plan = create_test_plan(files, ai_cases)
    plan["aiStatus"] = ai_status
    return plan


@app.post("/api/test-lab/package", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_capability("workflow.design"))])
async def create_approved_test_lab_package(request: TestLabPackageRequest, settings: Settings = Depends(get_settings)) -> dict:
    if not request.approved:
        raise HTTPException(status_code=409, detail="Explicit user approval of the displayed Test Lab plan is required.")
    files = _bounded_test_lab_files(request.files)
    expected = create_test_plan(files)
    if request.plan.get("schemaVersion") != 1 or request.plan.get("risk") != expected["risk"] or request.plan.get("capabilities") != expected["capabilities"]:
        raise HTTPException(status_code=409, detail="The approved plan is stale or attempts to weaken enforced Test Lab controls.")
    try:
        package = create_test_package(settings.test_lab_root, files, request.plan)
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"planId": request.plan["id"], "packagePath": str(package), "configurationPath": str(package / "AegisTestLab.wsb"), "status": "ready-for-explicit-launch", "executed": False, "capabilities": request.plan["capabilities"]}


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


@app.get("/api/monitoring", response_model=MonitoringDashboard, dependencies=[Depends(require_capability("monitoring.read"))])
async def monitoring_dashboard(
    monitoring: MonitoringCollector = Depends(get_monitoring),
) -> MonitoringDashboard:
    return monitoring.collect()


@app.get("/api/monitoring/moveit-ha", response_model=HaStatus, dependencies=[Depends(require_capability("monitoring.read"))])
async def moveit_ha_status() -> HaStatus:
    """Return fail-closed HA readiness until the live, version-specific adapter is bound."""
    return app.state.moveit_ha.status()


@app.get("/api/integrations/freeflow/devices", response_model=FreeFlowJmfDiscovery, dependencies=[Depends(require_capability("monitoring.read"))])
async def freeflow_known_devices(service: FreeFlowJmfService = Depends(get_freeflow_jmf)) -> FreeFlowJmfDiscovery:
    """Run the vendor-documented, read-only JMF KnownDevices discovery query."""
    return await asyncio.to_thread(service.discover)


@app.get("/api/integrations/freeflow/status", response_model=FreeFlowJmfStatus, dependencies=[Depends(require_capability("monitoring.read"))])
async def freeflow_status(service: FreeFlowJmfService = Depends(get_freeflow_jmf)) -> FreeFlowJmfStatus:
    return await asyncio.to_thread(service.status)


@app.get("/api/integrations/freeflow/workflows", response_model=FreeFlowJmfDiscovery, dependencies=[Depends(require_capability("monitoring.read"))])
async def freeflow_workflows(service: FreeFlowJmfService = Depends(get_freeflow_jmf)) -> FreeFlowJmfDiscovery:
    return await asyncio.to_thread(service.filtered, "workflow")


@app.get("/api/integrations/freeflow/queues", response_model=FreeFlowJmfDiscovery, dependencies=[Depends(require_capability("monitoring.read"))])
async def freeflow_queues(service: FreeFlowJmfService = Depends(get_freeflow_jmf)) -> FreeFlowJmfDiscovery:
    return await asyncio.to_thread(service.filtered, "queue")


@app.get("/api/integrations/freeflow/capabilities", response_model=FreeFlowJmfCapabilities, dependencies=[Depends(require_capability("monitoring.read"))])
async def freeflow_capabilities() -> FreeFlowJmfCapabilities:
    return FreeFlowJmfCapabilities()


@app.get("/api/integrations/freeflow/jobs", response_model=FreeFlowJmfJobs, dependencies=[Depends(require_capability("monitoring.read"))])
async def freeflow_jobs(service: FreeFlowJmfService = Depends(get_freeflow_jmf)) -> FreeFlowJmfJobs:
    return await asyncio.to_thread(service.jobs)


@app.get("/api/operations/monitoring", response_model=OperationsMonitoringSnapshot, dependencies=[Depends(require_capability("monitoring.read"))])
async def operations_monitoring_snapshot(
    monitoring: MonitoringCollector = Depends(get_monitoring),
) -> OperationsMonitoringSnapshot:
    return collect_operations_snapshot(monitoring)


@app.get("/api/operations/summary", response_model=OperationsSummary, dependencies=[Depends(require_capability("monitoring.read"))])
async def operations_monitoring_summary(
    monitoring: MonitoringCollector = Depends(get_monitoring),
) -> OperationsSummary:
    return collect_operations_snapshot(monitoring).summary


@app.get("/api/operations/collectors", response_model=list[MonitorDescriptor], dependencies=[Depends(require_capability("monitoring.read"))])
async def operations_monitoring_collectors(
    monitoring: MonitoringCollector = Depends(get_monitoring),
) -> list[MonitorDescriptor]:
    return collect_operations_snapshot(monitoring).monitors


@app.post("/api/monitoring/actions", response_model=MonitoringActionResult, status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_capability("monitoring.configure"))])
async def monitoring_action(request: MonitoringActionRequest) -> MonitoringActionResult:
    return MonitoringActionResult(
        status="not_configured",
        source=request.source,
        issue=request.issue,
        detail="Action catalog and external integration are not configured. Nothing was executed.",
    )


@app.post("/api/monitoring/alerts/{alert_id}/resolve", response_model=MonitoringDashboard, dependencies=[Depends(require_capability("monitoring.acknowledge"))])
async def resolve_monitoring_alert(
    alert_id: int,
    monitoring: MonitoringCollector = Depends(get_monitoring),
) -> MonitoringDashboard:
    if monitoring.store.resolve_alert(alert_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitoring alert was not found.")
    return monitoring.collect()


@app.post("/api/files/upload", response_model=FileEntry, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_capability("workflow.design"))])
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


@app.get("/api/files/{file_id}/content", dependencies=[Depends(require_capability("workflow.read"))])
async def file_content(
    file_id: int,
    store: JarvisStore = Depends(get_store),
) -> dict[str, str | None]:
    content = store.get_file_content(file_id)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No extracted text is available for this file.")
    return {"content": content}


@app.delete("/api/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_capability("workflow.design"))])
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


@app.post("/api/approvals", response_model=ApprovalState, dependencies=[Depends(require_capability("workflow.approve"))])
async def update_approval(
    request: ApprovalRequest,
    store: JarvisStore = Depends(get_store),
) -> ApprovalState:
    return store.set_approval(request.decision)


@app.get("/api/workflows/capacity", response_model=WorkflowCapacity, dependencies=[Depends(require_capability("workflow.read"))])
async def workflow_capacity(
    capacity: WorkflowCapacity = Depends(get_workflow_capacity_from_settings),
) -> WorkflowCapacity:
    return capacity


@app.get("/api/workflows", response_model=list[Workflow], dependencies=[Depends(require_capability("workflow.read"))])
async def workflows(store: JarvisStore = Depends(get_store)) -> list[Workflow]:
    return store.get_workflows()


@app.get("/api/workflows/{workflow_id}", response_model=Workflow, dependencies=[Depends(require_capability("workflow.read"))])
async def workflow(workflow_id: int, store: JarvisStore = Depends(get_store)) -> Workflow:
    result = store.get_workflow(workflow_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow was not found.")
    return result


@app.get("/api/workflows/{workflow_id}/export", dependencies=[Depends(require_capability("workflow.read"))])
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


@app.post("/api/workflows/import", response_model=WorkflowImportResult, dependencies=[Depends(require_capability("workflow.design"))])
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


@app.get("/api/workflows/placements", response_model=list[WorkflowWindowPlacement], dependencies=[Depends(require_capability("workflow.read"))])
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


@app.post("/api/workflows/reconcile-topology", response_model=TopologyReconciliation, dependencies=[Depends(require_capability("workflow.execute"))])
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


@app.post("/api/workflows", response_model=Workflow, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_capability("workflow.design"))])
async def create_workflow(
    request: WorkflowRequest,
    store: JarvisStore = Depends(get_store),
) -> Workflow:
    return document_workflow(store.create_workflow(request.title, request.description, request.attachment_ids, request.language), "workflow-created")


@app.put("/api/workflows/{workflow_id}", response_model=Workflow, dependencies=[Depends(require_capability("workflow.design"))])
async def update_workflow(workflow_id: int, request: WorkflowRequest, store: JarvisStore = Depends(get_store)) -> Workflow:
    result = store.update_workflow(workflow_id, request.title, request.description, request.attachment_ids, request.language)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow cannot be edited while active or was not found.")
    return document_workflow(result, "workflow-revised", "Prior downstream approvals were invalidated.")


@app.post("/api/workflows/{workflow_id}/review", response_model=Workflow, dependencies=[Depends(require_workflow_review_capability)])
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
        authorizer = RoleAuthorizer(settings.role_mapping_path)
        principal = authorizer.current_principal()
        try:
            authorizer.require("workflow.supervisor-approve", principal)
        except AuthorizationError as error:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
        result = store.approve_workflow_for_production(workflow_id, principal.identity)
    else:
        result = store.review_workflow(workflow_id, request.decision)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Decision is not valid for the workflow's current gate.")
    return document_workflow(result, f"review-{request.decision}")


@app.post("/api/workflows/{workflow_id}/run-test", response_model=WorkflowTestResult, dependencies=[Depends(require_capability("workflow.design"))])
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
    document_workflow(updated, "non-production-test-completed", evidence.summary)
    documentation = getattr(app.state, "workflow_documentation", None)
    if documentation is not None:
        documentation.record_test_result(updated, evidence.model_dump())
    return WorkflowTestResult(workflow=updated, evidence=evidence)


@app.post("/api/workflows/{workflow_id}/design-plan", response_model=Workflow, dependencies=[Depends(require_capability("workflow.design"))])
async def design_workflow_plan(
    workflow_id: int,
    provider: OpenAICompatibleProvider = Depends(get_provider),
    store: JarvisStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> Workflow:
    return await _generate_workflow_plan(workflow_id, provider, store, settings, finalizing=False)


async def _generate_workflow_plan(
    workflow_id: int,
    provider: OpenAICompatibleProvider,
    store: JarvisStore,
    settings: Settings,
    finalizing: bool,
) -> Workflow:
    workflow = store.get_workflow(workflow_id)
    if workflow is None or workflow.archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow was not found.")
    if workflow.state not in {"draft", "rejected", "plan_review", "design_review"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The workflow is not available for plan design.")
    tool_context = WorkflowAgentToolContext(store, workflow, SecurityControlPolicy(settings.security_control_policy_path))
    messages = [
        ChatMessage(role="system", content=WORKFLOW_ARCHITECT_INSTRUCTIONS),
        ChatMessage(role="user", content="Inspect this workflow through the provided tools, then create or reevaluate its plan."),
    ]
    routed = None
    plan = ""
    questions: list[dict] = []
    for attempt in range(2):
        try:
            routed = await provider.chat_for_task_with_tools("reasoning", messages, tool_context.definitions, tool_context.invoke)
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
    return document_workflow(result, "workflow-plan-generated", "Final plan ready for approval." if finalizing and not questions else "Plan requires review.")


@app.put("/api/workflows/{workflow_id}/clarifications/{question_id}", response_model=Workflow, dependencies=[Depends(require_capability("workflow.design"))])
async def answer_one_workflow_clarification(
    workflow_id: int,
    question_id: str,
    request: WorkflowClarificationAnswerRequest,
    store: JarvisStore = Depends(get_store),
) -> Workflow:
    result = store.save_clarification_answer(workflow_id, question_id, request.answer)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The question is unavailable or the workflow is not in design review.")
    return document_workflow(result, "clarification-answer-submitted", f"Question {question_id} answered; answer content omitted from process log.")


@app.post("/api/workflows/{workflow_id}/complete-design-review", response_model=Workflow, dependencies=[Depends(require_capability("workflow.design"))])
async def complete_workflow_design_review(
    workflow_id: int,
    provider: OpenAICompatibleProvider = Depends(get_provider),
    store: JarvisStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> Workflow:
    if store.begin_workflow_reevaluation(workflow_id) is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Every required question must be submitted before updating the draft.")
    return await _generate_workflow_plan(workflow_id, provider, store, settings, finalizing=True)


@app.post("/api/workflows/{workflow_id}/generate-implementation", response_model=Workflow, dependencies=[Depends(require_capability("workflow.design"))])
async def generate_workflow_implementation(
    workflow_id: int,
    provider: OpenAICompatibleProvider = Depends(get_provider),
    store: JarvisStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> Workflow:
    workflow = store.get_workflow(workflow_id)
    if workflow is None or workflow.archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow was not found.")
    if workflow.state != "test_plan_approved" or not workflow.plan_text or not workflow.test_plan_text:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The workflow plan and non-production test plans must be approved before implementation generation.")
    language = "PowerShell" if workflow.language == "powershell" else "C#"
    async def delegate_local_agent(role: str, prompt: str) -> dict[str, str]:
        task = "code" if role == "implementation" else "reasoning"
        result = await provider.chat_for_task(task, [
            ChatMessage(role="system", content=f"You are a bounded A.E.G.I.S.-9 {role} sub-agent. Analyze only the supplied subtask. You have no tools or production authority. Return concise evidence, risks, and recommendations to the parent workflow agent."),
            ChatMessage(role="user", content=prompt),
        ])
        return {"content": result.content[:20000], "provider": result.route.provider, "model": result.route.model}
    tool_context = ApprovedWorkflowImplementationToolContext(
        store,
        workflow,
        SecurityControlPolicy(settings.security_control_policy_path),
        settings.workflow_artifact_root,
        settings.workflow_test_output_limit,
        delegate_local_agent,
        settings.max_process_memory_mb,
        settings.max_process_cpu_percent,
        settings.max_child_processes,
    )
    messages = [
        ChatMessage(role="system", content=workflow_implementer_instructions(language)),
        ChatMessage(role="user", content=f"Approved workflow plan, revision {workflow.revision}:\n{workflow.plan_text}\n\nApproved non-production test plans:\n{workflow.test_plan_text}"),
    ]
    try:
        routed = await provider.chat_for_task_with_tools("code", messages, tool_context.definitions, tool_context.invoke, max_turns=12)
    except ProviderError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    finally:
        tool_context.close()
    result = store.save_workflow_implementation(workflow_id, routed.content, routed.route.provider, routed.route.model)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow approval changed before the implementation could be saved.")
    return document_workflow(result, "workflow-implementation-generated", "Implementation content omitted from process log.")


@app.post("/api/workflows/{workflow_id}/generate-test-plans", response_model=Workflow, dependencies=[Depends(require_capability("workflow.design"))])
async def generate_workflow_test_plans(
    workflow_id: int,
    provider: OpenAICompatibleProvider = Depends(get_provider),
    store: JarvisStore = Depends(get_store),
) -> Workflow:
    workflow = store.get_workflow(workflow_id)
    if workflow is None or workflow.archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow was not found.")
    if workflow.state != "plan_approved" or not workflow.plan_text:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The final workflow plan must be user-approved before test-plan design.")
    messages = [
        ChatMessage(role="system", content="You are the A.E.G.I.S.-9 test architect. Design at least two detailed, non-production test plans for the approved workflow. Include objective, environment/isolation, prerequisites, setup, test data, ordered steps, expected result, evidence to retain, pass/fail criteria, cleanup, negative/failure cases, and rollback. Do not execute tests or generate production commands. Do not include credentials. Return clear Markdown for explicit user approval."),
        ChatMessage(role="user", content=f"Approved workflow plan, revision {workflow.revision}:\n{workflow.plan_text}"),
    ]
    try:
        routed = await provider.chat_for_task("reasoning", messages)
    except ProviderError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    result = store.save_workflow_test_plan(workflow_id, routed.content, routed.route.provider, routed.route.model)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow approval changed before test plans could be saved.")
    return document_workflow(result, "workflow-test-plans-generated", "Test plans are ready for explicit user approval.")


@app.put("/api/workflows/{workflow_id}/schedule", response_model=Workflow, dependencies=[Depends(require_capability("workflow.approve"))])
async def schedule_workflow(workflow_id: int, request: WorkflowScheduleRequest, store: JarvisStore = Depends(get_store)) -> Workflow:
    result = store.set_workflow_schedule(workflow_id, request.model_dump())
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A workflow must be awaiting supervisor review before its approval-bound schedule can be recorded.")
    return document_workflow(result, "workflow-schedule-recorded")


@app.post("/api/workflows/{workflow_id}/execute", response_model=WorkflowRun, status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_capability("workflow.execute"))])
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
        run = await manager.start(workflow, request.trigger, getpass.getuser())
        document_workflow(store.get_workflow(workflow_id) or workflow, "workflow-execution-started", f"Run {run.id}; trigger={request.trigger}.")
        return run
    except (OSError, ValueError, WorkflowExecutionError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@app.get("/api/workflows/{workflow_id}/runs", response_model=list[WorkflowRun], dependencies=[Depends(require_capability("workflow.read"))])
async def list_workflow_runs(workflow_id: int, store: JarvisStore = Depends(get_store)) -> list[WorkflowRun]:
    if store.get_workflow(workflow_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow was not found.")
    return store.get_workflow_runs(workflow_id)


@app.get("/api/workflow-runs/{run_id}", response_model=WorkflowRun, dependencies=[Depends(require_capability("workflow.read"))])
async def get_workflow_run(run_id: int, store: JarvisStore = Depends(get_store)) -> WorkflowRun:
    run = store.get_workflow_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow run was not found.")
    return run


@app.get("/api/workflow-runs/{run_id}/events", response_model=list[WorkflowRunEvent], dependencies=[Depends(require_capability("workflow.read"))])
async def list_workflow_run_events(run_id: int, after_sequence: int = 0, store: JarvisStore = Depends(get_store)) -> list[WorkflowRunEvent]:
    if store.get_workflow_run(run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow run was not found.")
    return store.get_workflow_run_events(run_id, after_sequence)


@app.get("/api/notifications", response_model=list[NotificationOutboxItem], dependencies=[Depends(require_capability("workflow.read"))])
async def notification_history(
    category: str | None = None,
    limit: int = 100,
    store: JarvisStore = Depends(get_store),
) -> list[NotificationOutboxItem]:
    return store.get_notification_outbox_items(category, limit)


@app.post("/api/notifications/{item_id}/retry", response_model=NotificationOutboxItem, dependencies=[Depends(require_capability("monitoring.configure"))])
async def retry_notification(item_id: int, store: JarvisStore = Depends(get_store)) -> NotificationOutboxItem:
    item = store.retry_notification_outbox_item(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a failed notification can be retried.",
        )
    return item


@app.post("/api/workflow-runs/{run_id}/cancel", response_model=WorkflowRun, dependencies=[Depends(require_capability("workflow.execute"))])
async def cancel_workflow_run(run_id: int, manager: WorkflowExecutionManager = Depends(get_workflow_execution)) -> WorkflowRun:
    run = manager.cancel(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow run is not active or cannot be cancelled.")
    return run


@app.post("/api/workflow-runs/{run_id}/retry", response_model=WorkflowRun, status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_capability("workflow.execute"))])
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


@app.delete("/api/workflows/{workflow_id}", response_model=Workflow, dependencies=[Depends(require_capability("workflow.design"))])
async def archive_workflow(workflow_id: int, store: JarvisStore = Depends(get_store)) -> Workflow:
    result = store.archive_workflow(workflow_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active workflows must be stopped before archival.")
    return document_workflow(result, "workflow-archived")


@app.post("/api/workflows/{workflow_id}/approve", response_model=Workflow, dependencies=[Depends(require_capability("workflow.approve"))])
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
    return document_workflow(workflow, "legacy-workflow-approved")


@app.post("/api/workflows/{workflow_id}/actions", response_model=WorkflowTransition, dependencies=[Depends(require_capability("workflow.execute"))])
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
    document_workflow(transition.workflow, f"workflow-action-{request.action}")
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
