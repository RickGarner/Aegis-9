# FreeFlow Core and Qualys monitoring handoff

## Implemented foundation

A.E.G.I.S.-9 now exposes dedicated cinematic Operations windows for Xerox
FreeFlow Core and Qualys vulnerabilities alongside MoveIT Automation and Server
Status. Both collectors are read-only and configuration-driven.

FreeFlow inventory is stored in `config/freeflow-servers.json`. The registered
servers are:

- `BSOXERALB001` — Primary
- `BSOXERALB002` — Secondary

Until their exact URLs and ports are entered, the UI intentionally displays
`unavailable` with `Web URL and port are awaiting configuration`. It does not
create an outage alert for an unconfigured endpoint.

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

## Details needed next session

FreeFlow:

- Exact portal URL and port for both servers
- HTTP or HTTPS and redirect behavior
- Expected text or stable health/login-page marker
- Whether internal CA trust is already installed
- Whether an authenticated application/API health check is required

Qualys:

- Product/module (VMDR, WAS, CSAM, or other)
- Subscription platform/API base URL
- Approved read-only API account or token method
- Asset tags/groups/IP scope
- Whether prioritization should use classic severity, QDS, QVSS, or a combined policy
- Polling cadence and notification/digest recipients

Credentials belong only in the git-ignored `.env` or managed secret storage.
Never put them in `config/freeflow-servers.json`, documentation, commits, or logs.
