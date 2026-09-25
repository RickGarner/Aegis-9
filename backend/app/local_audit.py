"""Bounded, redacted, local-only JSONL audit storage with tamper-evident chain."""

import hashlib
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SENSITIVE_KEY = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|authorization|credential|connectionstring|private[_-]?key)")
SENSITIVE_VALUE = re.compile(r"(?i)(bearer\s+[A-Za-z0-9._~+/-]+=*|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:password|pwd|secret|token|api[_-]?key)\s*[=:]\s*[^\s;,]+)")


def redact(value: Any, depth: int = 0) -> Any:
    if depth > 12:
        return "[REDACTED:DEPTH]"
    if isinstance(value, dict):
        return {str(key)[:200]: "[REDACTED]" if SENSITIVE_KEY.search(str(key)) else redact(item, depth + 1) for key, item in list(value.items())[:200]}
    if isinstance(value, list):
        return [redact(item, depth + 1) for item in value[:200]]
    if isinstance(value, str):
        return SENSITIVE_VALUE.sub("[REDACTED]", value[:10000])
    return value if value is None or isinstance(value, (bool, int, float)) else str(value)[:1000]


class LocalAuditStore:
    def __init__(self, path: Path, max_events: int = 5000, max_bytes: int = 10_000_000) -> None:
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_events = min(max(max_events, 100), 100000)
        self.max_bytes = min(max(max_bytes, 100000), 100_000_000)
        self._lock = threading.Lock()
        self._sequence = 0
        self._last_hash: str = "genesis"  # Genesis hash for chain start

    def append(self, event_type: str, fields: dict[str, Any]) -> dict[str, Any]:
        if not re.fullmatch(r"[a-z][a-z0-9.-]{0,127}", event_type):
            raise ValueError("Audit event type is invalid.")
        # Compute previous hash for chain linkage
        previous_hash = self._last_hash
        # Create event with chain linkage (without currentHash yet)
        event = {
            "schemaVersion": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "eventType": event_type,
            "data": redact(fields),
            "sequence": self._sequence,
            "previousHash": previous_hash,
        }
        # Compute hash from event content (without currentHash field)
        encoded_without_hash = json.dumps(event, separators=(",", ":"), ensure_ascii=True)
        current_hash = hashlib.sha256(encoded_without_hash.encode("utf-8")).hexdigest()
        # Add currentHash to event
        event["currentHash"] = current_hash
        # Write full event to file
        encoded_with_hash = json.dumps(event, separators=(",", ":"), ensure_ascii=True)
        self._sequence += 1
        self._last_hash = current_hash
        with self._lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(encoded_with_hash + "\n")
            self._compact()
        return event

    def _compact(self) -> None:
        if not self.path.exists():
            return
        if self.path.stat().st_size <= self.max_bytes:
            lines = self.path.read_text(encoding="utf-8").splitlines()
            if len(lines) <= self.max_events:
                return
        lines = self.path.read_text(encoding="utf-8").splitlines()[-self.max_events:]
        while lines and sum(len(line) + 1 for line in lines) > self.max_bytes:
            lines.pop(0)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")
        os.replace(temporary, self.path)

    def query(self, event_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000 or not self.path.exists():
            return []
        events = []
        for line in reversed(self.path.read_text(encoding="utf-8").splitlines()):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event_type is None or event.get("eventType") == event_type:
                events.append(event)
                if len(events) >= limit:
                    break
        return events

    def verify_chain(self) -> dict[str, Any]:
        """Verify the integrity of the audit chain. Returns chain status."""
        if not self.path.exists():
            return {"valid": True, "message": "No audit log exists yet", "events": 0}
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if not lines:
            return {"valid": True, "message": "Empty audit log", "events": 0}
        expected_hash = "genesis"
        valid = True
        violations = []
        for i, line in enumerate(lines):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                valid = False
                violations.append(f"Line {i + 1}: Invalid JSON")
                continue
            # Verify sequence
            if event.get("sequence") != i:
                valid = False
                violations.append(f"Line {i + 1}: Sequence mismatch (expected {i}, got {event.get('sequence')})")
            # Verify previous hash (chain linkage)
            if event.get("previousHash") != expected_hash:
                valid = False
                violations.append(f"Line {i + 1}: Chain break (expected {expected_hash[:16]}..., got {event.get('previousHash', 'MISSING')[:16]}...)")
            # Update expected hash for next event
            expected_hash = event.get("currentHash", "")
        return {
            "valid": valid,
            "message": "Chain intact" if valid else f"Chain broken: {len(violations)} violations",
            "events": len(lines),
            "violations": violations,
        }
