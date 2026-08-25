# Server Monitoring Reference

This reference extracts the usable server-monitoring design from:

`D:\BSOC_CodeRepository\DEV\Src\DotNet\BSOC\ServerMonitoring`

No SMTP passwords, API tokens, or other secrets are included.

## Original architecture

The original solution is split into four logical components:

- `ServerResourceMonitor`: Windows worker/agent deployed to each monitored server.
- `AIAnalysisHub`: central SignalR receiver, SQLite metrics store, AI analysis, and alert service.
- `MonitoringDashboard`: web dashboard for current metrics, history, alerts, and deployment operations.
- `SharedModels`: metric, alert, email, process, GPU, and hub contracts shared by the components.

The documented flow is:

```text
Server agent --metrics every 60 seconds--> AIAnalysisHub
AIAnalysisHub --persists/analyzes--> SQLite and local Ollama
AIAnalysisHub --publishes--> MonitoringDashboard
AIAnalysisHub --sends threshold alerts--> SMTP relay
```

The original deployment documentation identifies `BSOC-HPC-001` as the central hub/dashboard host.

## Starter server inventory

From `ServerResourceMonitor/servers-example.csv`:

| Server | IP address | Description |
|---|---:|---|
| `BSOSERVER01` | `10.30.67.10` | Primary Application Server |
| `BSOSERVER02` | `10.30.67.11` | Secondary Application Server |
| `BSOSERVER03` | `10.30.67.12` | Database Server |
| `BSOSERVER04` | `10.30.67.13` | File Server |
| `BSOSERVER05` | `10.30.67.14` | Web Server |

The solution also references deployed/central infrastructure including `BSOC-HPC-001`. Treat the CSV list as the starter monitored-server inventory and keep it configurable; do not assume every server is reachable from the Jarvis workstation.

## Metrics collected

The active `ResourceMonitor` implementation collects:

- Total CPU usage percentage.
- Memory used percentage.
- Disk usage percentage for every ready fixed drive.
- Network adapter bytes sent/received per second.
- Network bandwidth and utilization percentage.
- GPU utilization, with vendor-specific attempts for NVIDIA, AMD, and Intel, plus generic GPU discovery.
- Top CPU-consuming processes.
- Known BSOC jobs detected from process command lines.
- Business-hours context.
- Batch-window context.

The process detector recognizes these process families:

```text
powershell
pwsh
sqlcmd
bcp
CrystalReportsEngine
```

It recognizes these script/job patterns:

```text
NYSOH_Processing
ImageNet
EMedNY
WTC
FileNetZip
Mars
Certifications
```

The agent sends the metric report to the configured hub through SignalR. The current hub endpoint in the agent configuration is:

```text
http://BSOC-HPC-001:5000/metrichub
```

## Thresholds and cadence

The active agent configuration is:

| Setting | Value | Meaning |
|---|---:|---|
| CPU threshold | `80%` | Alert when CPU usage exceeds 80% |
| Memory threshold | `85%` | Alert when memory usage exceeds 85% |
| Disk threshold | `80%` | Alert when any fixed drive usage exceeds 80% |
| Collection interval | `60 seconds` | Agent metric collection cadence |
| Minimum alert interval | `15 minutes` | Non-critical email throttling interval |

The repository documents a previous disk threshold of 90% warning and 95% critical, later changed to 80% warning and 90% critical. The current agent configuration and threshold model use 80% as the single threshold. The new Jarvis project should represent warning and critical thresholds separately instead of losing this distinction.

Recommended normalized defaults for Jarvis:

```text
CPU warning: 80% used
CPU critical: 90% used
Memory warning: 85% used
Memory critical: 95% used
Disk warning: 80% used
Disk critical: 90% used
Collection interval: 60 seconds
Non-critical notification throttle: 15 minutes
```

These are extracted defaults, not a replacement for production approval.

## Alert behavior

The original alerting design includes:

- Threshold evaluation at the agent.
- Historical context held by the hub.
- Seven-day historical analysis in the AI layer.
- Awareness of business hours and batch windows.
- Suppression of expected activity when it is not critical.
- Minimum 15-minute interval between non-critical alerts.
- Critical alerts bypassing the throttle.
- Alert severity levels: Low, Medium, High, Critical.
- AI output fields for whether to alert, severity, explanation, likely cause, recommended action, expected activity, and confidence.

The current Jarvis implementation should persist alert identity and notification state so a five-minute frontend refresh or a 60-second backend collector cannot send duplicate messages indefinitely.

## SMTP configuration

The active configurations contain these SMTP values:

```text
SMTP server: 10.30.67.82
SMTP port: 25
TLS/SSL: disabled
From address (resource agent): servermonitor@bsoc.local
From address (AI hub): ai-monitor@bsoc.local
To address: admin@bsoc.local
SMTP username: unset
SMTP password: unset
```

The original implementation uses unauthenticated SMTP relay through port 25. Jarvis should make all of these values environment-configurable and should not assume unauthenticated relay is acceptable outside the internal network.

The existing temporary MoveIT recipient is separate and must not be silently substituted for the server-monitoring recipient. Keep notification channels independently configurable.

## Email behavior

`EmailNotificationService`:

1. Checks whether CPU, memory, or disk usage exceeds thresholds.
2. Suppresses the message if the last alert was less than 15 minutes ago.
3. Creates a subject containing severity/source and machine name.
4. Includes timestamp and threshold violations in the body.
5. Sends through `SmtpClient`.
6. Optionally uses SMTP credentials when configured.

The hub's AI-aware alert service adds history, known-job context, expected-activity suppression, and critical-alert bypass behavior.

## Storage and retention

The original hub configuration uses:

```text
SQLite database: metrics.db
Metric retention: 30 days
Cleanup interval: 24 hours
```

The AI analysis layer uses approximately seven days of history for context. Jarvis should separate:

- Raw metric retention.
- Alert retention.
- Filesystem audit retention.
- Notification/outbox retention.

## Deployment assumptions

Documented installation paths:

| Component | Host | Path |
|---|---|---|
| Dashboard | `BSOC-HPC-001` | `D:\BSOC Applications\ServerMonitoring\Dashboard` |
| AI hub | `BSOC-HPC-001` | `D:\BSOC Applications\ServerMonitoring\Hub` |
| Agent | Each monitored server | `D:\BSOC Applications\ServerMonitoring\Agent` |
| Metrics database | `BSOC-HPC-001` | `D:\BSOC Applications\ServerMonitoring\Hub\metrics.db` |

Documented Windows services:

```text
BSOC-MonitorDashboard
BSOC-AIAnalysisHub
BSOC-ResourceAgent
```

The Jarvis server monitor should enumerate Windows services directly and report every service whose startup mode is `Automatic` but whose current state is not `Running`. Services intentionally paused for maintenance should be suppressible through a temporary maintenance state so they do not create repeated alerts.

## Security and reliability notes

- The original SMTP configuration has TLS disabled. Keep this as an explicit internal-relay option and support TLS when available.
- The original service code uses local machine names and remote deployment scripts; Jarvis should treat server inventory and connection targets as configuration, not hard-coded actions.
- CPU/process inspection can fail due to permissions or exited processes; unavailable metrics must be represented as unavailable, not zero.
- GPU usage is vendor/driver dependent and may be unavailable.
- The original code uses a simple last-alert timestamp. Jarvis should use persisted alert keys and notification state to survive restarts.
- Automatic service monitoring requires a per-server expected-service list to avoid alerting on intentionally stopped services.
