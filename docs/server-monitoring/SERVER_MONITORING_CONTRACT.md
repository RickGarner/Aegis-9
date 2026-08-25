# Server Monitoring Contract

This contract turns the extracted ServerMonitoring behavior into implementation requirements for the current Jarvis backend.

## Server registry

Each server record should contain:

```text
name
address
description
enabled
monitoring_mode: local | remote_agent | hub
monitored_paths[]
time_zone
```

Starter records come from the original CSV:

```text
BSOSERVER01 / 10.30.67.10 / Primary Application Server
BSOSERVER02 / 10.30.67.11 / Secondary Application Server
BSOSERVER03 / 10.30.67.12 / Database Server
BSOSERVER04 / 10.30.67.13 / File Server
BSOSERVER05 / 10.30.67.14 / Web Server
```

## Metric contract

Every collection snapshot should identify:

- server
- collection timestamp in UTC
- CPU used percentage
- memory used percentage
- disk usage per volume
- network adapter counters when available
- GPU metrics when available
- top processes when permission allows
- known jobs/process context
- automatic-service issues
- collector errors and unavailable fields

`0` must not represent an unavailable metric. Use `null` plus a diagnostic detail.

## Threshold contract

Thresholds are per metric and per server, with normalized defaults:

```text
cpu_warning_percent = 80
cpu_critical_percent = 90
memory_warning_percent = 85
memory_critical_percent = 95
disk_warning_percent = 80
disk_critical_percent = 90
collection_interval_seconds = 60
noncritical_alert_interval_minutes = 15
```

A threshold crossing should be sustained for a configurable number of samples before alerting when practical. Recovery should resolve the active alert and may send a recovery email when enabled.

## Service contract

The monitor should inspect the Windows service registry on each monitored host. Every service with `StartMode=Automatic` is considered expected to run. A service issue is:

```text
expected service has StartMode=Automatic and State != Running
```

The record should include service name, display name, startup mode, current state, server, first detected time, and last detected time. A maintenance suppression may be applied temporarily by an operator, but it must have an expiry and audit entry. Disabled, manual, and delayed-start services are not alerts under this rule unless a future policy explicitly adds them.

## Filesystem audit contract

The Jarvis server monitor should support configured paths and record:

- created files
- modified files
- deleted files
- renamed files when correlation is possible
- file size and last-write metadata
- optional SHA-256 hash when configured

Do not store file contents by default. Keep filesystem audit records separate from resource metrics and alert records.

## Alerts and notification contract

Use stable condition keys, for example:

```text
server-unavailable:<server>
cpu-warning:<server>
cpu-critical:<server>
memory-warning:<server>
memory-critical:<server>:<volume>
disk-warning:<server>:<volume>
disk-critical:<server>:<volume>
service-stopped:<server>:<service>
filesystem-change:<server>:<path>:<change-type>
```

Each alert needs:

- source and server
- condition key
- severity
- title/detail
- observed value and threshold
- first/last detected timestamps
- active/resolved status
- email notification state
- operator resolution/action state

Notification rules:

- Non-critical alerts: default 15-minute throttle per condition or server.
- Critical alerts: bypass the normal throttle, with deduplication for the same condition.
- Expected batch activity may suppress medium/low resource alerts only when the source context is known.
- Email failures must remain visible as alerts and must not block metric collection.

## SMTP contract

Default extracted values:

```text
server = 10.30.67.82
port = 25
use_ssl = false
resource_agent_from = servermonitor@bsoc.local
hub_from = ai-monitor@bsoc.local
to = admin@bsoc.local
username/password = unset
```

The current Jarvis implementation should use a notification outbox and a configured email provider. SMTP credentials must come from secrets, never tracked configuration.

## Operations

The dashboard should provide:

- permanent server pane
- server selector
- metric and threshold display
- service issue list
- filesystem audit list
- active alert list
- manual refresh
- action request selector
- explicit pending/not-configured state until an approved action catalog exists

Potential future actions include recheck, acknowledge, restart an approved service, or open an audit record. No remediation should be inferred from an alert alone.
