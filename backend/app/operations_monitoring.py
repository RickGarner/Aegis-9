from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.monitoring import MonitoringAlert, MonitoringCollector, MonitoringDashboard
from app.storage import Workflow, WorkflowNotificationState, WorkflowRun


NormalizedState = Literal[
    "healthy", "degraded", "critical", "unreachable", "unauthorized",
    "misconfigured", "unknown", "disabled",
]
CollectorState = Literal[
    "healthy", "degraded", "failed", "stale", "unauthorized",
    "misconfigured", "disabled", "unknown",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class OperationsStateCounts(ContractModel):
    healthy: int = 0
    degraded: int = 0
    critical: int = 0
    unreachable: int = 0
    unauthorized: int = 0
    misconfigured: int = 0
    unknown: int = 0
    disabled: int = 0


class OperationsSummary(ContractModel):
    overall_state: NormalizedState
    counts: OperationsStateCounts


class MonitorDescriptor(ContractModel):
    monitor_id: str
    monitor_version: str = "1.0"
    display_name: str
    source_type: str
    owner: str | None = "A.E.G.I.S.-9"
    environment: str | None = "operations"
    criticality: Literal["low", "medium", "high", "critical"] | None = None
    service_tier: str | None = None
    collection_interval_seconds: int
    stale_after_seconds: int
    credential_reference_id: str | None = None
    required_role: str | None = None
    adapter_id: str | None = None
    read_only: Literal[True] = True
    enabled: bool = True
    configuration_state: Literal["configured", "misconfigured", "unconfigured", "disabled"]
    collector_state: CollectorState
    supported_resource_types: list[str] = Field(default_factory=list)
    supported_signal_types: list[str] = Field(default_factory=list)
    related_workflow_ids: list[str] = Field(default_factory=list)


class EvidenceReference(ContractModel):
    kind: Literal["uri", "artifact", "log", "metric", "snapshot"]
    reference: str
    sha256: str | None = None
    classification: Literal["public", "internal", "restricted"] = "internal"


class MonitorObservation(ContractModel):
    observation_id: str
    monitor_id: str
    resource_id: str
    resource_type: str
    collected_at_utc: str
    valid_until_utc: str
    state: NormalizedState
    source_state: str
    summary: str
    diagnostic_code: str | None = None
    collector_state: CollectorState
    duration_ms: int = 0
    correlation_id: str | None = None
    classification: Literal["public", "internal", "restricted"] = "internal"
    metrics: dict[str, float | int | str | bool | None] = Field(default_factory=dict)
    evidence: list[EvidenceReference] = Field(default_factory=list)


class OperationsAlert(ContractModel):
    alert_id: str
    deduplication_key: str
    monitor_id: str
    resource_id: str
    severity: Literal["info", "warning", "serious", "critical"]
    title: str
    description: str
    first_seen_utc: str
    last_seen_utc: str
    occurrence_count: int = 1
    lifecycle_state: Literal["active", "acknowledged", "recovered", "policy-suppressed"] = "active"
    owner: str | None = None
    acknowledged_by: str | None = None
    acknowledged_at_utc: str | None = None
    related_workflow_id: str | None = None
    recommended_action: str | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)


class WorkflowOperationsStatus(ContractModel):
    workflow_id: int
    transfer_id: str
    title: str
    lifecycle_state: str
    approval_stage: str
    revision: int
    language: str
    trigger: str
    timezone: str
    scheduler_status: str
    scheduler_last_evaluated_at_utc: str | None = None
    deferred_reason: str = ""
    last_run_at_utc: str | None = None
    requires_action: bool = False
    navigation_target: str
    latest_run_id: int | None = None
    latest_run_status: str = "never_run"
    latest_run_attempt: int | None = None
    latest_run_started_at_utc: str | None = None
    latest_run_completed_at_utc: str | None = None
    latest_run_error: str = ""
    notification_status: str = "not_created"
    notification_attempts: int = 0
    notification_error: str = ""


class OperationsMonitoringSnapshot(ContractModel):
    contract_version: Literal["1.0"] = "1.0"
    generated_at_utc: str
    summary: OperationsSummary
    monitors: list[MonitorDescriptor]
    observations: list[MonitorObservation]
    alerts: list[OperationsAlert]
    workflows: list[WorkflowOperationsStatus] = Field(default_factory=list)


MONITORS = (
    ("moveit", "MOVEit Automation", "moveit", 300, "moveit-rest", "transfer-task"),
    ("server", "Windows Servers", "windows-server", 60, "windows-cim", "server"),
    ("freeflow", "Xerox FreeFlow Core", "freeflow-core", 60, "http-probe", "web-application"),
    ("qualys", "Qualys VMDR", "qualys-vmdr", 300, "qualys-api", "vulnerability"),
)


def build_operations_snapshot(
    dashboard: MonitoringDashboard,
    previous: OperationsMonitoringSnapshot | None = None,
    now: datetime | None = None,
    workflows: list[Workflow] | None = None,
    latest_runs: dict[int, WorkflowRun] | None = None,
    notification_states: dict[int, WorkflowNotificationState] | None = None,
) -> OperationsMonitoringSnapshot:
    monitors: list[MonitorDescriptor] = []
    observations: list[MonitorObservation] = []
    states: list[NormalizedState] = []

    for monitor_id, display_name, source_type, interval, adapter_id, resource_type in MONITORS:
        source = getattr(dashboard, monitor_id)
        target_state, collector_state, configuration_state = normalize_status(source.status, source.detail)
        monitors.append(MonitorDescriptor(
            monitor_id=monitor_id,
            display_name=display_name,
            source_type=source_type,
            criticality="high" if monitor_id != "qualys" else "critical",
            collection_interval_seconds=interval,
            stale_after_seconds=interval * 2,
            adapter_id=adapter_id,
            configuration_state=configuration_state,
            collector_state=collector_state,
            supported_resource_types=[resource_type],
            supported_signal_types=["status", "alert"],
        ))
        collected_at = normalize_timestamp(source.last_checked_at)
        observation = MonitorObservation(
            observation_id=str(uuid5(NAMESPACE_URL, f"aegis:{monitor_id}:{collected_at}")),
            monitor_id=monitor_id,
            resource_id=f"{monitor_id}:summary",
            resource_type=resource_type,
            collected_at_utc=collected_at,
            valid_until_utc=add_seconds(collected_at, interval * 2),
            state=target_state,
            source_state=source.status,
            summary=source.detail[:2048],
            diagnostic_code=diagnostic_code(collector_state),
            collector_state=collector_state,
        )
        observation = retain_last_known_good(observation, previous)
        observation = apply_staleness(observation, now or datetime.now(timezone.utc))
        observations.append(observation)
        monitors[-1].collector_state = observation.collector_state
        states.append(observation.state)

    counts = OperationsStateCounts(**{state: states.count(state) for state in OperationsStateCounts.model_fields})
    summary_states = list(states)
    summary_states.extend(
        collector_summary_state(observation.collector_state)
        for observation in observations
        if observation.collector_state != "healthy"
    )
    return OperationsMonitoringSnapshot(
        generated_at_utc=normalize_timestamp(dashboard.generated_at),
        summary=OperationsSummary(overall_state=overall_state(summary_states), counts=counts),
        monitors=monitors,
        observations=observations,
        alerts=[normalize_alert(alert) for alert in dashboard.alerts],
        workflows=[
            normalize_workflow(
                workflow,
                (latest_runs or {}).get(workflow.id),
                (notification_states or {}).get(workflow.id),
            )
            for workflow in (workflows or [])
        ],
    )


def collect_operations_snapshot(monitoring: MonitoringCollector) -> OperationsMonitoringSnapshot:
    workflow_store = monitoring.workflow_store
    previous = None
    previous_json = monitoring.store.get_latest_operations_snapshot()
    if previous_json:
        try:
            previous = OperationsMonitoringSnapshot.model_validate_json(previous_json)
        except ValueError:
            previous = None
    snapshot = build_operations_snapshot(
        monitoring.collect(),
        previous=previous,
        workflows=workflow_store.get_workflows() if workflow_store else [],
        latest_runs=workflow_store.get_latest_workflow_runs() if workflow_store else {},
        notification_states=workflow_store.get_latest_workflow_notification_states() if workflow_store else {},
    )
    monitoring.store.save_operations_snapshot(
        snapshot.model_dump_json(by_alias=True), snapshot.generated_at_utc, snapshot.contract_version
    )
    return snapshot


def normalize_workflow(
    workflow: Workflow,
    latest_run: WorkflowRun | None = None,
    notification: WorkflowNotificationState | None = None,
) -> WorkflowOperationsStatus:
    schedule = workflow.schedule
    return WorkflowOperationsStatus(
        workflow_id=workflow.id,
        transfer_id=workflow.transfer_id,
        title=workflow.title,
        lifecycle_state=workflow.state,
        approval_stage=workflow.approval_stage,
        revision=workflow.revision,
        language=workflow.language,
        trigger=str(schedule.get("trigger") or "manual"),
        timezone=str(schedule.get("timezone") or "UTC"),
        scheduler_status=workflow.scheduler_status,
        scheduler_last_evaluated_at_utc=normalize_optional_timestamp(workflow.scheduler_last_evaluated_at),
        deferred_reason=workflow.scheduler_last_deferred_reason,
        last_run_at_utc=normalize_optional_timestamp(workflow.last_run_at),
        requires_action=workflow.state in {
            "needs_clarification", "design_review", "plan_review", "implementation_review",
            "test_failed", "test_passed", "user_accepted", "supervisor_pending", "failed",
        },
        navigation_target=f"aegis://workflows/{workflow.id}",
        latest_run_id=latest_run.id if latest_run else None,
        latest_run_status=latest_run.status if latest_run else "never_run",
        latest_run_attempt=latest_run.attempt if latest_run else None,
        latest_run_started_at_utc=normalize_optional_timestamp(latest_run.started_at) if latest_run else None,
        latest_run_completed_at_utc=normalize_optional_timestamp(latest_run.completed_at) if latest_run else None,
        latest_run_error=latest_run.error if latest_run else "",
        notification_status=notification.status if notification else "not_created",
        notification_attempts=notification.attempts if notification else 0,
        notification_error=notification.last_error if notification else "",
    )


def retain_last_known_good(
    current: MonitorObservation,
    previous: OperationsMonitoringSnapshot | None,
) -> MonitorObservation:
    if current.collector_state == "healthy" or previous is None:
        return current
    prior = next(
        (item for item in previous.observations if item.monitor_id == current.monitor_id and item.state != "unknown"),
        None,
    )
    if prior is None:
        return current
    return current.model_copy(update={
        "state": prior.state,
        "source_state": prior.source_state,
        "collected_at_utc": prior.collected_at_utc,
        "valid_until_utc": prior.valid_until_utc,
        "summary": f"Last known target evidence: {prior.summary} Current collector: {current.summary}"[:2048],
        "evidence": prior.evidence,
    })


def apply_staleness(observation: MonitorObservation, now: datetime) -> MonitorObservation:
    valid_until = datetime.fromisoformat(observation.valid_until_utc.replace("Z", "+00:00"))
    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=timezone.utc)
    if now.astimezone(timezone.utc) <= valid_until or observation.collector_state != "healthy":
        return observation
    return observation.model_copy(update={
        "collector_state": "stale",
        "diagnostic_code": "collector.stale",
    })


def collector_summary_state(state: CollectorState) -> NormalizedState:
    return {
        "unauthorized": "unauthorized",
        "misconfigured": "misconfigured",
        "disabled": "disabled",
        "failed": "unknown",
        "stale": "unknown",
        "degraded": "degraded",
        "unknown": "unknown",
    }.get(state, "unknown")  # type: ignore[return-value]


def normalize_status(status: str, detail: str) -> tuple[NormalizedState, CollectorState, str]:
    native = status.lower().strip()
    message = detail.lower()
    if native == "healthy":
        return "healthy", "healthy", "configured"
    if native == "warning":
        return "degraded", "healthy", "configured"
    if native == "error":
        return "critical", "healthy", "configured"
    if "credential" in message or "not configured" in message or "awaiting configuration" in message or "no moveit servers" in message:
        return "unknown", "misconfigured", "unconfigured"
    if "unauthorized" in message or "authentication" in message:
        return "unknown", "unauthorized", "configured"
    return "unknown", "failed", "configured"


def normalize_alert(alert: MonitoringAlert) -> OperationsAlert:
    monitor_id = alert.source.lower().strip() or "unknown"
    first_seen = normalize_timestamp(alert.created_at)
    return OperationsAlert(
        alert_id=str(uuid5(NAMESPACE_URL, f"aegis:alert:{alert.id}")),
        deduplication_key=f"{monitor_id}:{alert.title.lower().strip()}",
        monitor_id=monitor_id,
        resource_id=f"{monitor_id}:summary",
        severity={"error": "critical", "warning": "warning"}.get(alert.severity, "info"),
        title=alert.title[:256],
        description=alert.detail[:2048],
        first_seen_utc=first_seen,
        last_seen_utc=first_seen,
    )


def overall_state(states: list[NormalizedState]) -> NormalizedState:
    for state in ("critical", "unreachable", "unauthorized", "misconfigured", "degraded", "unknown", "disabled", "healthy"):
        if state in states:
            return state  # type: ignore[return-value]
    return "unknown"


def diagnostic_code(collector_state: CollectorState) -> str | None:
    return None if collector_state == "healthy" else f"collector.{collector_state}"


def normalize_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_optional_timestamp(value: str | None) -> str | None:
    return normalize_timestamp(value) if value else None


def add_seconds(value: str, seconds: int) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (parsed + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")
