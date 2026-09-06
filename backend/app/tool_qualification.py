import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError


class ToolQualificationReport(BaseModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    provider: str
    model: str
    location: str
    endpoint_identity: str
    checked_at: datetime
    valid_until: datetime
    native_structured_calls: bool = False
    valid_arguments: bool = False
    sequential_calls: bool = False
    tool_result_continuation: bool = False
    qualified: bool = False
    failure_reason: str = ""


class ToolQualificationStore:
    def __init__(self, path: Path, success_ttl_hours: int = 24, failure_ttl_minutes: int = 5) -> None:
        self._path = path
        self._success_ttl = timedelta(hours=success_ttl_hours)
        self._failure_ttl = timedelta(minutes=failure_ttl_minutes)

    @staticmethod
    def endpoint_identity(chat_url: str) -> str:
        return hashlib.sha256(chat_url.encode("utf-8")).hexdigest()

    @staticmethod
    def key(provider: str, model: str, location: str, chat_url: str) -> str:
        material = f"{provider}\n{model}\n{location}\n{chat_url}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def get(self, provider: str, model: str, location: str, chat_url: str) -> ToolQualificationReport | None:
        payload = self._load()
        raw = payload.get("reports", {}).get(self.key(provider, model, location, chat_url))
        try:
            report = ToolQualificationReport.model_validate(raw)
        except ValidationError:
            return None
        now = datetime.now(timezone.utc)
        if report.valid_until <= now or report.endpoint_identity != self.endpoint_identity(chat_url):
            return None
        return report

    def save(self, provider: str, model: str, location: str, chat_url: str, *, native: bool, arguments: bool, sequential: bool, continuation: bool, failure_reason: str = "") -> ToolQualificationReport:
        now = datetime.now(timezone.utc)
        qualified = native and arguments and sequential and continuation and not failure_reason
        report = ToolQualificationReport(
            provider=provider,
            model=model,
            location=location,
            endpoint_identity=self.endpoint_identity(chat_url),
            checked_at=now,
            valid_until=now + (self._success_ttl if qualified else self._failure_ttl),
            native_structured_calls=native,
            valid_arguments=arguments,
            sequential_calls=sequential,
            tool_result_continuation=continuation,
            qualified=qualified,
            failure_reason=failure_reason[:500],
        )
        payload = self._load()
        payload.setdefault("reports", {})[self.key(provider, model, location, chat_url)] = report.model_dump(mode="json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self._path)
        return report

    def _load(self) -> dict:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get("schema_version") == 1 and isinstance(payload.get("reports"), dict):
                return payload
        except (OSError, json.JSONDecodeError):
            pass
        return {"schema_version": 1, "reports": {}}
