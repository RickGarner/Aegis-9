"""Schema-level outbound allowlisting and protected-data enforcement."""

import json
import re
from typing import Any

from app.local_audit import SENSITIVE_KEY, SENSITIVE_VALUE


class DlpDenied(ValueError):
    pass


PROTECTED_FIELD = re.compile(r"(?i)(prompt|source|code|repository|telemetry|diagnostic|log|content|attachment|credential|token|secret|password|authorization|connection)")


def enforce_outbound(arguments: dict[str, Any], allowed_fields: list[str], connectivity: str) -> dict[str, Any]:
    if not isinstance(arguments, dict) or not isinstance(allowed_fields, list) or any(not isinstance(item, str) for item in allowed_fields):
        raise DlpDenied("Outbound payload or schema classification is invalid.")
    unknown = set(arguments) - set(allowed_fields)
    if unknown:
        raise DlpDenied("Outbound payload contains fields absent from the approved schema: " + ", ".join(sorted(unknown)))
    serialized = json.dumps(arguments, ensure_ascii=False)
    for key, value in arguments.items():
        if SENSITIVE_KEY.search(key) or (isinstance(value, str) and SENSITIVE_VALUE.search(value)):
            raise DlpDenied("Outbound payload contains secret or credential material.")
        if connectivity == "external-zero-protected-data" and (PROTECTED_FIELD.search(key) or (isinstance(value, str) and len(value) > 2000)):
            raise DlpDenied("Protected or unbounded data cannot be sent to an external service.")
    if len(serialized.encode("utf-8")) > 100_000:
        raise DlpDenied("Outbound payload exceeds the transport limit.")
    if connectivity not in {"local", "organization-controlled", "external-zero-protected-data"}:
        raise DlpDenied("Outbound destination is unclassified.")
    return arguments
