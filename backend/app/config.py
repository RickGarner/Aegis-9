from functools import lru_cache
from pathlib import Path
import socket
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


WORK_LMSTUDIO_BASE_URL = "http://10.30.75.229:1234/v1"
HOME_LMSTUDIO_BASE_URL = "http://127.0.0.1:1234/v1"


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
    provider: str = Field(default="lmstudio", validation_alias="JARVIS_PROVIDER")
    provider_base_url: str | None = Field(
        default=None,
        validation_alias="JARVIS_PROVIDER_BASE_URL",
    )
    model: str = Field(
        default="qwen3-coder-30b-a3b-instruct",
        validation_alias="JARVIS_MODEL",
    )
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
        default="lmstudio,ollama,litellm",
        validation_alias="JARVIS_PROVIDER_PREFERENCE",
    )
    fallback_model: str | None = Field(
        default="qwen2.5-coder-7b-instruct",
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
    server_inventory_path: Path = Field(
        default=Path(__file__).resolve().parents[2] / "config" / "monitored-servers.json",
        validation_alias="JARVIS_SERVER_INVENTORY_PATH",
    )
    moveit_servers: str = Field(
        default="BSOAUTALB002,BSOAUTALB001",
        validation_alias="JARVIS_MOVEIT_SERVERS",
    )
    moveit_username: str | None = Field(default=None, validation_alias="JARVIS_MOVEIT_USERNAME")
    moveit_password: str | None = Field(default=None, validation_alias="JARVIS_MOVEIT_PASSWORD")
    moveit_verify_tls: bool = Field(default=True, validation_alias="JARVIS_MOVEIT_VERIFY_TLS")
    moveit_task_poll_seconds: int = Field(default=300, ge=30, validation_alias="JARVIS_MOVEIT_TASK_POLL_SECONDS")
    moveit_log_root: Path = Field(default=Path(r"\\BSOAUTALB002\c$\ProgramData\Ipswitch\Automation\Logs"), validation_alias="JARVIS_MOVEIT_LOG_ROOT")
    alert_smtp_server: str = Field(default="10.30.67.82", validation_alias="JARVIS_ALERT_SMTP_SERVER")
    alert_smtp_port: int = Field(default=25, ge=1, le=65535, validation_alias="JARVIS_ALERT_SMTP_PORT")
    alert_email_from: str = Field(default="servermonitor@bsoc.local", validation_alias="JARVIS_ALERT_EMAIL_FROM")
    alert_email_to: str = Field(default="admin@bsoc.local", validation_alias="JARVIS_ALERT_EMAIL_TO")
    alert_email_ssl: bool = Field(default=False, validation_alias="JARVIS_ALERT_EMAIL_SSL")

    @model_validator(mode="after")
    def resolve_provider_base_url(self) -> "Settings":
        if not self.server_inventory_path.is_absolute():
            self.server_inventory_path = (Path(__file__).resolve().parents[2] / self.server_inventory_path).resolve()
        if self.provider_base_url is not None or self.provider != "lmstudio":
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
