# Server Monitoring Source Audit

## Source

`D:\BSOC_CodeRepository\DEV\Src\DotNet\BSOC\ServerMonitoring`

## Active components reviewed

- `ServerResourceMonitor/appsettings.json`
- `ServerResourceMonitor/servers-example.csv`
- `ServerResourceMonitor/Models/ResourceThresholds.cs`
- `ServerResourceMonitor/Services/ResourceMonitor.cs`
- `ServerResourceMonitor/Services/ProcessDetector.cs`
- `ServerResourceMonitor/Services/EmailNotificationService.cs`
- `ServerResourceMonitor/Worker.cs`
- `AIAnalysisHub/appsettings.json`
- `MonitoringDashboard/appsettings.json`
- `SharedModels/EmailSettings.cs`
- `MONITORING_CONFIGURATION_SUMMARY.md`
- `DISK_THRESHOLD_UPDATE.md`
- `AI_ANALYSIS_AND_ALERTING_GUIDE.md`

## Key extracted values

- Starter servers: BSOSERVER01 through BSOSERVER05, addresses 10.30.67.10 through 10.30.67.14.
- Agent-to-hub endpoint: `http://BSOC-HPC-001:5000/metrichub`.
- Collection interval: 60 seconds.
- CPU threshold: 80% usage.
- Memory threshold: 85% usage.
- Disk threshold: 80% usage.
- Documented later critical thresholds: CPU 90%, memory 95%, disk 90%.
- Non-critical alert throttle: 15 minutes.
- Metrics database: SQLite `metrics.db`.
- Raw metric retention: 30 days.
- Historical AI context: 7 days.
- SMTP relay: 10.30.67.82:25, SSL disabled.
- Resource-monitor sender: servermonitor@bsoc.local.
- AI-hub sender: ai-monitor@bsoc.local.
- Recipient: admin@bsoc.local.
- SMTP authentication fields are unset in the source configuration.

## Service monitoring interpretation

The requested policy is to monitor every Windows service configured for automatic startup. Jarvis should query `StartMode=Automatic` services and alert when `State != Running`. Manual, disabled, and delayed-start services are outside the default alert policy. Temporary maintenance suppression should be time-limited and auditable.

## Security note

SMTP is configured as an unauthenticated, non-TLS internal relay. Preserve this only as a configurable legacy-compatible option and support TLS/authenticated SMTP for production. No SMTP password was copied into the new Jarvis project.
