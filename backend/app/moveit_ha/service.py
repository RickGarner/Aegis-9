import json
from pathlib import Path

from .models import HaStatus, MoveItHaConfig, PairObservation
from .state_machine import evaluate


class PrivilegedMoveItAdapter:
    """Fixed-function boundary. Operations remain unavailable until onsite validation."""

    def __getattr__(self, operation: str):
        raise RuntimeError(f"MOVEit HA operation '{operation}' is not bound to a version-validated adapter; no change was made.")


class MoveItHaService:
    def __init__(self, config_path: Path, state_path: Path):
        self.config_path = config_path
        self.state_path = state_path
        self.config = MoveItHaConfig.model_validate_json(config_path.read_text(encoding="utf-8"))
        self.admin = PrivilegedMoveItAdapter()

    def status(self, observation: PairObservation | None = None) -> HaStatus:
        recovery_started_at = None
        if self.state_path.exists():
            try:
                recovery_started_at = json.loads(self.state_path.read_text(encoding="utf-8")).get("recoveryStartedAt")
            except (OSError, ValueError, AttributeError):
                recovery_started_at = None
        result = evaluate(self.config, observation, recovery_started_at=recovery_started_at)
        self._persist(result)
        return result

    def _persist(self, status: HaStatus) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(status.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
        temporary.replace(self.state_path)
