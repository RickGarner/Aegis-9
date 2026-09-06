from functools import lru_cache
from pathlib import Path
import socket
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


WORK_LMSTUDIO_BASE_URL = "http://10.30.75.229:1234/v1"
HOME_LMSTUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
DMR_BASE_URL = "http://10.30.75.229:12434/engines/v1"


def _work_lmstudio_is_reachable() -> bool:
    try:
        with socket.create_connection(("10.30.75.229", 1234), timeout=0.25):
            return True
    except OSError:
        return False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["auto", "work", "home"] = Field(
        default="auto",
        validation_alias="JARVIS_ENVIRONMENT",
    )
    provider: str = Field(default="dmr", validation_alias="JARVIS_PROVIDER")
    provider_base_url: str | None = Field(
        default=None,
        validation_alias="JARVIS_PROVIDER_BASE_URL",
    )
    model: str = Field(
        default="docker.io/ai/qwen3-coder:30b-a3b-q4_K_M",
        validation_alias="JARVIS_MODEL",
    )
    dmr_base_url: str = Field(default=DMR_BASE_URL, validation_alias="JARVIS_DMR_BASE_URL")
    lmstudio_base_url: str = Field(default="http://127.0.0.1:1234/v1", validation_alias="JARVIS_LMSTUDIO_BASE_URL")
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", validation_alias="JARVIS_OLLAMA_BASE_URL")
    litellm_base_url: str = Field(default="http://127.0.0.1:4000/v1", validation_alias="JARVIS_LITELLM_BASE_URL")
    litellm_api_key: str | None = Field(default=None, validation_alias="JARVIS_LITELLM_API_KEY")
    remote_provider_host: str = Field(default="10.30.75.229", validation_alias="JARVIS_REMOTE_PROVIDER_HOST")
    local_provider_host: str = Field(default="127.0.0.1", validation_alias="JARVIS_LOCAL_PROVIDER_HOST")
    provider_discovery_enabled: bool = Field(default=True, validation_alias="JARVIS_PROVIDER_DISCOVERY_ENABLED")
    provider_discovery_timeout_seconds: float = Field(
        default=2.5,
        ge=0.5,
        le=15,
        validation_alias="JARVIS_PROVIDER_DISCOVERY_TIMEOUT_SECONDS",
    )
    provider_retry_count: int = Field(default=1, ge=0, le=3, validation_alias="JARVIS_PROVIDER_RETRY_COUNT")
    provider_preference: str = Field(
        default="dmr,ollama",
        validation_alias="JARVIS_PROVIDER_PREFERENCE",
    )
    tool_capable_models: str = Field(
        default="dmr/docker.io/ai/qwen3-coder:30b-a3b-q4_K_M,dmr/docker.io/ai/qwen3:8b-q4_K_M,ollama/llama3.1:8b,ollama/llama3.2:latest",
        validation_alias="JARVIS_TOOL_CAPABLE_MODELS",
    )
    fallback_model: str | None = Field(
        default="llama3.1:8b",
        validation_alias="JARVIS_FALLBACK_MODEL",
    )
    request_timeout_seconds: float = Field(
        default=60,
        validation_alias="JARVIS_REQUEST_TIMEOUT_SECONDS",
    )
    max_response_tokens: int = Field(
        default=2048,
        ge=256,
        le=8192,
        validation_alias="JARVIS_MAX_RESPONSE_TOKENS",
    )
    primary_model_timeout_seconds: float = Field(
        default=20,
        ge=5,
        le=120,
        validation_alias="JARVIS_PRIMARY_MODEL_TIMEOUT_SECONDS",
    )
    whisper_model: str = Field(default="small.en", validation_alias="JARVIS_WHISPER_MODEL")
    whisper_device: str = Field(default="auto", validation_alias="JARVIS_WHISPER_DEVICE")
    whisper_compute_type: str = Field(default="auto", validation_alias="JARVIS_WHISPER_COMPUTE_TYPE")
    database_path: Path = Field(
        default=Path(__file__).resolve().parents[2] / "storage" / "jarvis.db",
        validation_alias="JARVIS_DATABASE_PATH",
    )
    workflow_window_limit: int = Field(
        default=6,
        ge=1,
        le=6,
        validation_alias="JARVIS_WORKFLOW_WINDOW_LIMIT",
    )
    upload_dir: Path = Field(
        default=Path(__file__).resolve().parents[2] / "storage" / "uploads",
        validation_alias="JARVIS_UPLOAD_DIR",
    )
    max_upload_bytes: int = Field(
        default=25 * 1024 * 1024,
        validation_alias="JARVIS_MAX_UPLOAD_BYTES",
    )
    workflow_artifact_root: Path = Field(
        default=Path(__file__).resolve().parents[2] / "storage" / "workflow-artifacts",
        validation_alias="JARVIS_WORKFLOW_ARTIFACT_ROOT",
    )
    workflow_test_timeout_seconds: int = Field(default=30, ge=5, le=300, validation_alias="JARVIS_WORKFLOW_TEST_TIMEOUT_SECONDS")
    workflow_test_output_limit: int = Field(default=64_000, ge=4_096, le=1_000_000, validation_alias="JARVIS_WORKFLOW_TEST_OUTPUT_LIMIT")
    workflow_supervisor_identities: str = Field(default="", validation_alias="JARVIS_WORKFLOW_SUPERVISOR_IDENTITIES")
    workflow_execution_timeout_seconds: int = Field(default=300, ge=10, le=3600, validation_alias="JARVIS_WORKFLOW_EXECUTION_TIMEOUT_SECONDS")
    workflow_action_catalog_path: Path = Field(default=Path("config/workflow-actions.json"), validation_alias="JARVIS_WORKFLOW_ACTION_CATALOG_PATH")
    security_control_policy_path: Path = Field(default=Path("config/security-control.json"), validation_alias="JARVIS_SECURITY_CONTROL_POLICY_PATH")
    tool_qualification_store_path: Path = Field(default=Path("storage/tool-capability-reports.json"), validation_alias="JARVIS_TOOL_QUALIFICATION_STORE_PATH")
    server_inventory_path: Path = Field(
        default=Path(__file__).resolve().parents[2] / "config" / "monitored-servers.json",
        validation_alias="JARVIS_SERVER_INVENTORY_PATH",
    )
    server_remote_cim_enabled: bool = Field(default=False, validation_alias="JARVIS_SERVER_REMOTE_CIM_ENABLED")
    server_remote_cim_timeout_seconds: int = Field(default=45, ge=10, le=180, validation_alias="JARVIS_SERVER_REMOTE_CIM_TIMEOUT_SECONDS")
    freeflow_inventory_path: Path = Field(default=Path("config/freeflow-servers.json"), validation_alias="JARVIS_FREEFLOW_INVENTORY_PATH")
    freeflow_timeout_seconds: float = Field(default=10, ge=1, le=60, validation_alias="JARVIS_FREEFLOW_TIMEOUT_SECONDS")
    freeflow_verify_tls: bool = Field(default=True, validation_alias="JARVIS_FREEFLOW_VERIFY_TLS")
    qualys_base_url: str | None = Field(default=None, validation_alias="JARVIS_QUALYS_BASE_URL")
    qualys_username: str | None = Field(default=None, validation_alias="JARVIS_QUALYS_USERNAME")
    qualys_password: str | None = Field(default=None, validation_alias="JARVIS_QUALYS_PASSWORD")
    qualys_verify_tls: bool = Field(default=True, validation_alias="JARVIS_QUALYS_VERIFY_TLS")
    qualys_minimum_severity: int = Field(default=4, ge=1, le=5, validation_alias="JARVIS_QUALYS_MINIMUM_SEVERITY")
    qualys_max_findings: int = Field(default=200, ge=10, le=1000, validation_alias="JARVIS_QUALYS_MAX_FINDINGS")
    developer_studio_bridge_url: str = Field(default="http://127.0.0.1:8765", validation_alias="JARVIS_DEVELOPER_STUDIO_BRIDGE_URL")
    developer_studio_bridge_token: str | None = Field(default=None, validation_alias="AEGIS_BRIDGE_TOKEN")
    developer_studio_bridge_timeout_seconds: float = Field(default=3, ge=0.5, le=15, validation_alias="JARVIS_DEVELOPER_STUDIO_BRIDGE_TIMEOUT_SECONDS")
    moveit_servers: str = Field(
        default="BSOAUTALB001,BSOAUTALB002",
        validation_alias="JARVIS_MOVEIT_SERVERS",
    )
    workflow_documentation_root: Path = Field(
        default=Path("Workflows"), validation_alias="JARVIS_WORKFLOW_DOCUMENTATION_ROOT"
    )
    moveit_ha_config_path: Path = Field(default=Path("config/moveit-ha.json"), validation_alias="JARVIS_MOVEIT_HA_CONFIG_PATH")
    moveit_ha_state_path: Path = Field(default=Path("storage/moveit-ha-state.json"), validation_alias="JARVIS_MOVEIT_HA_STATE_PATH")
    moveit_username: str | None = Field(default=None, validation_alias="JARVIS_MOVEIT_USERNAME")
    moveit_password: str | None = Field(default=None, validation_alias="JARVIS_MOVEIT_PASSWORD")
    moveit_verify_tls: bool = Field(default=True, validation_alias="JARVIS_MOVEIT_VERIFY_TLS")
    moveit_task_poll_seconds: int = Field(default=300, ge=30, validation_alias="JARVIS_MOVEIT_TASK_POLL_SECONDS")
    moveit_log_root: Path = Field(default=Path(r"\\BSOAUTALB002\c$\ProgramData\Ipswitch\Automation\Logs"), validation_alias="JARVIS_MOVEIT_LOG_ROOT")
    moveit_history_days: int = Field(default=5, ge=1, le=30, validation_alias="JARVIS_MOVEIT_HISTORY_DAYS")
    moveit_history_max_records: int = Field(default=10_000, ge=100, le=50_000, validation_alias="JARVIS_MOVEIT_HISTORY_MAX_RECORDS")
    alert_smtp_server: str = Field(default="10.30.67.82", validation_alias="JARVIS_ALERT_SMTP_SERVER")
    alert_smtp_port: int = Field(default=25, ge=1, le=65535, validation_alias="JARVIS_ALERT_SMTP_PORT")
    alert_email_from: str = Field(default="servermonitor@bsoc.local", validation_alias="JARVIS_ALERT_EMAIL_FROM")
    alert_email_to: str = Field(default="admin@bsoc.local", validation_alias="JARVIS_ALERT_EMAIL_TO")
    alert_email_ssl: bool = Field(default=False, validation_alias="JARVIS_ALERT_EMAIL_SSL")
    workflow_notification_delivery_enabled: bool = Field(default=False, validation_alias="JARVIS_WORKFLOW_NOTIFICATION_DELIVERY_ENABLED")
    workflow_notification_max_attempts: int = Field(default=5, ge=1, le=20, validation_alias="JARVIS_WORKFLOW_NOTIFICATION_MAX_ATTEMPTS")
    workflow_notification_retry_seconds: int = Field(default=60, ge=15, le=86400, validation_alias="JARVIS_WORKFLOW_NOTIFICATION_RETRY_SECONDS")

    @model_validator(mode="after")
    def resolve_provider_base_url(self) -> "Settings":
        if not self.server_inventory_path.is_absolute():
            self.server_inventory_path = (Path(__file__).resolve().parents[2] / self.server_inventory_path).resolve()
        if not self.freeflow_inventory_path.is_absolute():
            self.freeflow_inventory_path = (Path(__file__).resolve().parents[2] / self.freeflow_inventory_path).resolve()
        if not self.workflow_artifact_root.is_absolute():
            self.workflow_artifact_root = (Path(__file__).resolve().parents[2] / self.workflow_artifact_root).resolve()
        if not self.workflow_documentation_root.is_absolute():
            self.workflow_documentation_root = (Path(__file__).resolve().parents[2] / self.workflow_documentation_root).resolve()
        if not self.workflow_action_catalog_path.is_absolute():
            self.workflow_action_catalog_path = (Path(__file__).resolve().parents[2] / self.workflow_action_catalog_path).resolve()
        if not self.security_control_policy_path.is_absolute():
            self.security_control_policy_path = (Path(__file__).resolve().parents[2] / self.security_control_policy_path).resolve()
        if not self.tool_qualification_store_path.is_absolute():
            self.tool_qualification_store_path = (Path(__file__).resolve().parents[2] / self.tool_qualification_store_path).resolve()
        if not self.moveit_ha_config_path.is_absolute():
            self.moveit_ha_config_path = (Path(__file__).resolve().parents[2] / self.moveit_ha_config_path).resolve()
        if not self.moveit_ha_state_path.is_absolute():
            self.moveit_ha_state_path = (Path(__file__).resolve().parents[2] / self.moveit_ha_state_path).resolve()
        if self.provider_base_url is not None:
            return self

        if self.provider == "dmr":
            self.provider_base_url = self.dmr_base_url
            return self

        if self.provider != "lmstudio":
            return self

        if self.environment == "work" or (
            self.environment == "auto" and _work_lmstudio_is_reachable()
        ):
            self.provider_base_url = WORK_LMSTUDIO_BASE_URL
        else:
            self.provider_base_url = HOME_LMSTUDIO_BASE_URL
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
