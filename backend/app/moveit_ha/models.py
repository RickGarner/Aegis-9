from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class ContractModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HaState(StrEnum):
    UNKNOWN = "UNKNOWN"
    HEALTHY_PREFERRED = "HEALTHY_PREFERRED"
    PREFERRED_UNREACHABLE = "PREFERRED_UNREACHABLE"
    FAILED_OVER = "FAILED_OVER"
    PREFERRED_RECOVERED = "PREFERRED_RECOVERED"
    STABILITY_WAIT = "STABILITY_WAIT"
    FAILBACK_ELIGIBLE = "FAILBACK_ELIGIBLE"
    CONFIGURATION_INVALID = "CONFIGURATION_INVALID"
    AUTO_FAILBACK_PAUSED = "AUTO_FAILBACK_PAUSED"
    KILL_SWITCH_ACTIVE = "KILL_SWITCH_ACTIVE"
    MAINTENANCE_SUPPRESSED = "MAINTENANCE_SUPPRESSED"


class NodeConfig(ContractModel):
    name: str
    hostname: str
    node_number: int


class DatabaseConfig(ContractModel):
    type: Literal["mssql"] = "mssql"
    shared_database_required: bool = True
    server: str = ""
    database: str = ""
    require_suppress_db_rep: bool = True


class MonitoringConfig(ContractModel):
    poll_interval_seconds: int = Field(10, ge=5)
    request_timeout_seconds: int = Field(5, ge=1)
    consecutive_failures_for_unhealthy: int = Field(3, ge=1)
    consecutive_successes_for_recovered: int = Field(3, ge=1)
    preferred_primary_stability_seconds: int = Field(900, ge=1)


class FailbackConfig(ContractModel):
    enabled: bool = False
    cooldown_minutes: int = Field(60, ge=0)
    maximum_automatic_attempts_per_incident: int = Field(1, ge=1)
    drain_timeout_minutes: int = Field(30, ge=1)
    service_stop_timeout_seconds: int = Field(120, ge=1)
    service_start_timeout_seconds: int = Field(180, ge=1)
    post_primary_start_validation_seconds: int = Field(60, ge=1)
    post_pair_validation_seconds: int = Field(120, ge=1)
    require_no_running_tasks: bool = True
    require_shared_sql_validation: bool = True
    require_runtime_role_validation: bool = True
    require_partner_communication: bool = True


class SafetyConfig(ContractModel):
    fail_closed: bool = True
    global_kill_switch_honored: bool = True
    maintenance_mode_prevents_failback: bool = True
    manual_lockout_supported: bool = True
    require_exclusive_lock: bool = True


class EnvironmentProfile(ContractModel):
    moveit_version: str = ""
    service_name: str = ""
    web_admin_url: str = ""
    runtime_role_query: str = ""
    graceful_shutdown_method: str = ""
    clear_admin_replication_method: str = ""
    running_task_query: str = ""
    win_rm_validated: bool = False

    def missing_fields(self) -> list[str]:
        values = self.model_dump()
        return [name for name, value in values.items() if not value]


class MoveItHaConfig(ContractModel):
    enabled: bool = True
    mode: Literal["observe", "assisted", "automatic"] = "observe"
    pair_id: str
    preferred_primary: NodeConfig
    preferred_secondary: NodeConfig
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    failback: FailbackConfig = Field(default_factory=FailbackConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    environment_profile: EnvironmentProfile = Field(default_factory=EnvironmentProfile)


class NodeHealth(ContractModel):
    name: str
    preferred_role: Literal["primary", "secondary"]
    healthy: bool = False
    runtime_role: Literal["primary", "secondary", "unknown"] = "unknown"
    service_state: Literal["running", "stopped", "unknown"] = "unknown"
    admin_endpoint_reachable: bool = False
    sql_reachable: bool = False
    sql_server: str = ""
    sql_database: str = ""
    suppress_db_rep: int | None = None
    partner_link_healthy: bool = False
    running_task_count: int | None = None
    observed_at: str = Field(default_factory=utc_now)
    detail: str = ""


class PairObservation(ContractModel):
    preferred_primary: NodeHealth
    preferred_secondary: NodeHealth
    kill_switch_active: bool = False
    paused: bool = False
    maintenance_suppressed: bool = False


class HaStatus(ContractModel):
    pair_id: str
    state: HaState
    severity: Literal["healthy", "info", "warning", "critical"]
    mode: str
    auto_failback_enabled: bool
    eligible: bool = False
    reason: str
    preferred_primary: str
    preferred_secondary: str
    runtime_primary: str | None = None
    recovery_started_at: str | None = None
    healthy_seconds: int = 0
    required_stability_seconds: int = 900
    nodes: list[NodeHealth] = Field(default_factory=list)
    missing_environment_fields: list[str] = Field(default_factory=list)
    last_evaluated_at: str = Field(default_factory=utc_now)
