# FreeFlow Core and Qualys monitoring handoff

## Implemented foundation

A.E.G.I.S.-9 now exposes dedicated cinematic Operations windows for Xerox
FreeFlow Core and Qualys vulnerabilities alongside MoveIT Automation and Server
Status. Both collectors are read-only and configuration-driven.

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

Qualys initially uses the read-only VM/VMDR host detection endpoint and requests
New, Active, and Re-Opened findings. Results are sorted by severity descending:

1. Severity 5 — Urgent
2. Severity 4 — Critical
3. Severity 3 — Serious, when the configured minimum is lowered to 3

The default minimum is severity 4. Urgent findings create error-level alerts;
Critical findings create warning-level alerts. No remediation is executed.

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

Qualys:

- Product/module (VMDR, WAS, CSAM, or other)
- Subscription platform/API base URL
- Approved read-only API account or token method
- Asset tags/groups/IP scope
- Whether prioritization should use classic severity, QDS, QVSS, or a combined policy
- Polling cadence and notification/digest recipients

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
