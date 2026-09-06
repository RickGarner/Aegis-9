# MOVEit HA Auto-Failback Implementation Status

Updated: 2026-09-06

## Current safe implementation

The attached HA handoff has been adopted as the implementation specification. The configured pair is:

- preferred primary: `BSOAUTALB001`
- preferred secondary: `BSOAUTALB002`

The repository now contains an observe-only configuration, typed HA contracts, a deterministic state evaluator, durable JSON status persistence, a fail-closed privileged-adapter boundary, and `GET /api/monitoring/moveit-ha`. The ordinary MOVEit monitoring server order was also corrected to primary then secondary.

Automatic failback is intentionally disabled. No server was contacted and no production operation was attempted from the home network. An LLM is not involved in HA safety decisions.

## Implemented and locally verified

- Preferred/runtime role terminology and core states
- Native-failover observation without an AEGIS promotion action
- Recovery stability timer behavior
- Observe mode preventing failback eligibility
- Split-brain/ambiguous-role fail-closed behavior
- Missing-live-evidence fail-closed behavior
- Durable status snapshot write
- Version-specific privileged operations blocked until explicitly bound
- Seven focused HA tests; complete backend suite passes (91 tests)

## Required onsite discovery before live monitoring

- MOVEit Automation version/build on both nodes
- Supported authoritative runtime-role query
- Shared SQL Server/instance and database identity (credentials must not enter config, logs, UI, or model prompts)
- `Node`, `StartupRole`, `OtherHost`, and `SuppressDBRep` values on both nodes
- MOVEit Windows service name and installation/configuration/state paths
- Web Admin URL/port and required administrative ports
- Supported running-task query
- Supported graceful **Shut Down Service** invocation
- Supported **Clear Admin Rep** invocation
- WinRM/JEA availability and the least-privilege AEGIS service identity

Enter these non-secret values in `config/moveit-ha.json`. Keep `mode` set to `observe` and `failback.enabled` set to `false` during discovery and the observation acceptance period.

## Next implementation increments

1. Bind a read-only, exact-version health adapter and collect authoritative evidence from both nodes.
2. Add persisted incidents/events and recovery-timer continuity across backend restarts.
3. Surface the HA pair and timer in Monitoring Center and Workflow supervision.
4. Implement and test a narrow fixed-function admin adapter in non-production.
5. Add durable exclusive locking, the 20 preflight gates, controlled drain/failback, rollback, and full audit history.
6. Advance from observe to assisted mode only after the documented acceptance tests pass. Automatic mode requires separate formal approval.

## Validation limitation

The desktop executable was running during this work and locked its normal build output. The backend import/API route check succeeded, and all 91 backend tests passed. No desktop source was changed by this increment.
