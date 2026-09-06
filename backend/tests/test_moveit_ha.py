import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.moveit_ha.models import MoveItHaConfig, NodeHealth, PairObservation
from app.moveit_ha.service import MoveItHaService
from app.moveit_ha.state_machine import evaluate


def config(**overrides):
    payload = {
        "pairId": "production-moveit-ha", "mode": "observe",
        "preferredPrimary": {"name": "BSOAUTALB001", "hostname": "BSOAUTALB001", "nodeNumber": 1},
        "preferredSecondary": {"name": "BSOAUTALB002", "hostname": "BSOAUTALB002", "nodeNumber": 2},
    }
    payload.update(overrides)
    return MoveItHaConfig.model_validate(payload)


def observation(primary_healthy=True, primary_role="primary", secondary_role="secondary", **flags):
    return PairObservation(
        preferredPrimary=NodeHealth(name="BSOAUTALB001", preferredRole="primary", healthy=primary_healthy, runtimeRole=primary_role),
        preferredSecondary=NodeHealth(name="BSOAUTALB002", preferredRole="secondary", healthy=True, runtimeRole=secondary_role),
        **flags,
    )


class MoveItHaTests(unittest.TestCase):
    def test_preferred_topology_is_healthy(self):
        self.assertEqual("HEALTHY_PREFERRED", evaluate(config(), observation()).state)

    def test_native_failover_is_observed_but_not_commanded(self):
        result = evaluate(config(), observation(False, "unknown", "primary"))
        self.assertEqual(("FAILED_OVER", False), (result.state, result.eligible))

    def test_recovery_waits_for_stability(self):
        now = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)
        result = evaluate(config(), observation(True, "secondary", "primary"), (now - timedelta(seconds=899)).isoformat(), now)
        self.assertEqual(("STABILITY_WAIT", 899), (result.state, result.healthy_seconds))

    def test_observe_mode_never_becomes_failback_eligible(self):
        now = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)
        result = evaluate(config(), observation(True, "secondary", "primary"), (now - timedelta(seconds=1000)).isoformat(), now)
        self.assertEqual(("PREFERRED_RECOVERED", False), (result.state, result.eligible))

    def test_split_brain_fails_closed(self):
        result = evaluate(config(), observation(True, "primary", "primary"))
        self.assertEqual(("UNKNOWN", "critical", False), (result.state, result.severity, result.eligible))

    def test_missing_live_evidence_is_configuration_invalid(self):
        self.assertEqual("CONFIGURATION_INVALID", evaluate(config(), None).state)

    def test_service_persists_status_without_contacting_servers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Path(__file__).resolve().parents[2] / "config" / "moveit-ha.json"
            config_path = root / "moveit-ha.json"
            config_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            state_path = root / "state.json"
            status = MoveItHaService(config_path, state_path).status()
            self.assertEqual("CONFIGURATION_INVALID", status.state)
            self.assertEqual("BSOAUTALB001", json.loads(state_path.read_text())["preferredPrimary"])


if __name__ == "__main__":
    unittest.main()
