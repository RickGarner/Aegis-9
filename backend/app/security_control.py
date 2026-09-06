import json
from dataclasses import dataclass
from pathlib import Path


class SecurityControlError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdapterPolicy:
    adapter_id: str
    enabled: bool
    mode: str
    capabilities: frozenset[str]


class SecurityControlPolicy:
    def __init__(self, path: Path) -> None:
        self._path = path

    def require(self, adapter_id: str, capability: str, *, mutating: bool) -> AdapterPolicy:
        payload = self._load()
        if mutating and payload.get("global_kill_switch") is True:
            raise SecurityControlError("The A.E.G.I.S.-9 global kill switch blocks all mutating adapters.")
        raw_adapter = payload.get("adapters", {}).get(adapter_id)
        if not isinstance(raw_adapter, dict):
            raise SecurityControlError(f"Adapter '{adapter_id}' is not registered; default-deny policy blocked it.")
        raw_capabilities = raw_adapter.get("capabilities")
        if raw_adapter.get("mode") not in {"read-only", "read-write"} or not isinstance(raw_capabilities, list):
            raise SecurityControlError(f"Adapter '{adapter_id}' has an invalid security policy.")
        if any(not isinstance(item, str) or not item.strip() for item in raw_capabilities):
            raise SecurityControlError(f"Adapter '{adapter_id}' has an invalid security policy.")
        policy = AdapterPolicy(
            adapter_id=adapter_id,
            enabled=raw_adapter.get("enabled") is True,
            mode=raw_adapter["mode"],
            capabilities=frozenset(raw_capabilities),
        )
        if not policy.enabled:
            raise SecurityControlError(f"Adapter '{adapter_id}' is disabled by security policy.")
        if mutating and policy.mode != "read-write":
            raise SecurityControlError(f"Adapter '{adapter_id}' is not authorized for mutating operations.")
        if capability not in policy.capabilities:
            raise SecurityControlError(f"Adapter '{adapter_id}' is not authorized for capability '{capability}'.")
        return policy

    def _load(self) -> dict:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SecurityControlError(f"Security policy is unavailable or invalid: {error}") from error
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != 1
            or not isinstance(payload.get("global_kill_switch"), bool)
            or not isinstance(payload.get("adapters"), dict)
        ):
            raise SecurityControlError("Security policy schema is invalid.")
        return payload
