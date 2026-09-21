# Operational monitoring handoff

## Unified Operations Monitoring Center direction — 2026-09-03

These collectors and their specialized windows will feed a separate,
movable/resizable Operations Monitoring Center. They are not being replaced or
merged internally. The center will normalize target health, collector health,
alerts, workflow/schedule state, and navigation while retaining source-native
evidence and failure detail. See `OPERATIONS-MONITORING-CENTER-PLAN.md`.

## Implemented foundation

A.E.G.I.S.-9 exposes dedicated cinematic Operations windows for Xerox FreeFlow
Core, MoveIT Automation, and Server Status. The collectors are read-only and
configuration-driven.

FreeFlow inventory is stored in `config/freeflow-servers.json`. The registered
servers are:

- `BSOXERALB001` — Primary
- `BSOXERALB002` — Secondary

The discovered application endpoints are configured as
`http://BSOXERALB001/FreeFlowCore` and
`http://BSOXERALB002/FreeFlowCore`. Both currently return HTTP 401 Windows
authentication challenges, which confirms that IIS and the protected FreeFlow
application route are available without storing a FreeFlow password in A.E.G.I.S.

When configured, each portal check records the final HTTP response, response
latency, expected page-content match, status, diagnostic detail, and check time.
Configured endpoints that cannot be reached create deduplicated FreeFlow alerts.

Remote Windows server telemetry now uses read-only PowerShell remoting/CIM with
the current operator domain identity. It collects CPU load, available memory,
fixed-disk capacity, and stopped non-delayed automatic services concurrently.
Set `JARVIS_SERVER_REMOTE_CIM_ENABLED=true` only on workstations whose approved
operator identity has remote read access. The corrected monitoring hub hostname
is `BSOC-HPC-001`.

## Details still needed

FreeFlow:

- Whether HTTP 401 route availability is sufficient, or whether an authenticated
  application/API health transaction is required

MoveIT execution history is now read from the installed Web Admin report endpoint,
`POST /api/v1/reports/taskruns`, using the existing read-only bearer token. The
monitor requests the last five days, retains the latest run per task, and
normalizes Success, No Transfer, and Failure results. The legacy log share remains
as a fallback only. `No xfers` is normal unless MOVEit reports a failure. A task
failure alert stays active through later `No xfers` runs and resolves automatically
only after a confirmed `Success`; the original failure and resolution details remain
in alert history.

Credentials belong only in the git-ignored `.env` or managed secret storage.
Never put them in `config/freeflow-servers.json`, documentation, commits, or logs.
