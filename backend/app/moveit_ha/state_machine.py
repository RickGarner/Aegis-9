from datetime import datetime, timezone

from .models import HaState, HaStatus, MoveItHaConfig, PairObservation, utc_now


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def evaluate(
    config: MoveItHaConfig,
    observation: PairObservation | None,
    recovery_started_at: str | None = None,
    now: datetime | None = None,
) -> HaStatus:
    evaluated = now or datetime.now(timezone.utc)
    missing = config.environment_profile.missing_fields()
    base = dict(
        pair_id=config.pair_id, mode=config.mode,
        auto_failback_enabled=config.failback.enabled,
        preferred_primary=config.preferred_primary.name,
        preferred_secondary=config.preferred_secondary.name,
        required_stability_seconds=config.monitoring.preferred_primary_stability_seconds,
        missing_environment_fields=missing,
        last_evaluated_at=evaluated.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )
    if not config.enabled:
        return HaStatus(state=HaState.CONFIGURATION_INVALID, severity="critical", reason="MOVEit HA monitoring is disabled.", **base)
    if observation is None:
        return HaStatus(state=HaState.CONFIGURATION_INVALID, severity="critical", reason="Live node evidence has not been collected.", **base)
    nodes = [observation.preferred_primary, observation.preferred_secondary]
    base["nodes"] = nodes
    runtime = [node.name for node in nodes if node.runtime_role == "primary"]
    base["runtime_primary"] = runtime[0] if len(runtime) == 1 else None
    if observation.kill_switch_active:
        return HaStatus(state=HaState.KILL_SWITCH_ACTIVE, severity="warning", reason="Global automation kill switch is active.", **base)
    if observation.maintenance_suppressed:
        return HaStatus(state=HaState.MAINTENANCE_SUPPRESSED, severity="info", reason="Maintenance suppression is active.", **base)
    if observation.paused:
        return HaStatus(state=HaState.AUTO_FAILBACK_PAUSED, severity="warning", reason="MOVEit HA failback is paused.", **base)
    if len(runtime) > 1:
        return HaStatus(state=HaState.UNKNOWN, severity="critical", reason="Ambiguous topology: both nodes report runtime primary.", **base)
    primary, secondary = nodes
    if primary.healthy and primary.runtime_role == "primary" and secondary.runtime_role == "secondary":
        return HaStatus(state=HaState.HEALTHY_PREFERRED, severity="healthy", reason="Preferred topology is healthy.", **base)
    if not primary.healthy:
        state = HaState.FAILED_OVER if secondary.healthy and secondary.runtime_role == "primary" else HaState.PREFERRED_UNREACHABLE
        return HaStatus(state=state, severity="warning", reason="Preferred primary is unavailable; MOVEit native failover remains authoritative.", **base)
    recovered = primary.runtime_role == "secondary" and secondary.healthy and secondary.runtime_role == "primary"
    if recovered:
        started = recovery_started_at or utc_now()
        elapsed = max(0, int((evaluated - _parse(started)).total_seconds()))
        base.update(recovery_started_at=started, healthy_seconds=elapsed)
        if elapsed < config.monitoring.preferred_primary_stability_seconds:
            return HaStatus(state=HaState.STABILITY_WAIT, severity="warning", reason="Preferred primary recovery stability timer is in progress.", **base)
        gates_ready = not missing and bool(config.database.server and config.database.database)
        eligible = gates_ready and config.failback.enabled and config.mode in {"assisted", "automatic"}
        reason = "All deterministic preflight inputs are present; failback is eligible." if eligible else "Observation continues; privileged failback is not armed or discovery inputs are incomplete."
        return HaStatus(state=HaState.FAILBACK_ELIGIBLE if eligible else HaState.PREFERRED_RECOVERED, severity="warning", eligible=eligible, reason=reason, **base)
    return HaStatus(state=HaState.UNKNOWN, severity="critical", reason="Runtime roles are unknown or inconsistent; no automatic action is permitted.", **base)
