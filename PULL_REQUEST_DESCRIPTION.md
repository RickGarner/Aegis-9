> **Historical record.** This PR description documents a past change made while `desktop/` and `frontend/` still shared one repository. On 2026-08-25 that repository was physically split into standalone `D:\Jarvis_Desktop` (this folder) and `D:\Jarvis_Web` folders/repositories. References below to `frontend/` describe history and no longer correspond to a path in this folder; see `docs/handoff.md` for the current split.

Title: Native-first migration: bundled backend launcher, health checks, and developer scripts

Summary:
This change adds initial migration work to support a native-first desktop experience where the WPF application can bundle and auto-start a Python FastAPI backend in production while preserving the developer workflow.

Key changes:
- desktop/Jarvis.Desktop/BackendLauncher.cs: lightweight launcher to start/stop the bundled Python FastAPI backend and capture logs.
- desktop/Jarvis.Desktop/App.xaml.cs: integrates the launcher on application startup, polls MonitoringClient.CheckHealthAsync for readiness, and provides environment toggles (JARVIS_DEVELOPER_MODE, JARVIS_MONITORING_URL).
- desktop/Jarvis.Desktop/MonitoringClient.cs: added CheckHealthAsync(CancellationToken) helper.
- desktop/Jarvis.Desktop/MonitorWindow.xaml.cs: hardened resource lookups with fallbacks to system brushes to avoid crashes when themed resources are missing.
- scripts/start-backend.ps1: helper to create or use .venv, install dependencies, activate the venv, and start uvicorn. Supports -Activate to dot-source activation.
- scripts/create-migration-branch.ps1: helper to create a migration branch and move frontend/ to archive/frontend/ (run locally to preserve history).
- desktop/installer/: initial WiX template and README for packaging guidance.
- docs updates: docs/visual-studio-handoff.md and docs/native-desktop.md updated with migration notes and run instructions.

Testing notes:
- Run `. .\scripts\start-backend.ps1 -Activate` from the repo root to start the backend in a venv.
- Set `$env:JARVIS_DEVELOPER_MODE = "1"` and run the desktop app from Visual Studio or Start-Process to avoid auto-launch during development.
- Verify `GET /health` and `/api/monitoring` return expected results.

Follow-up work:
- Expand the installer WiX authoring to include the harvested application and backend files.
- Add a graceful HTTP shutdown endpoint in the backend and update the launcher to call it before killing the process.
- Port web-based UI features (file upload, activity/audit views) into native WPF.

Commit message:
chore(native): add bundled backend launcher, health checks, and developer scripts

- Add BackendLauncher and App startup integration
- Add MonitoringClient.CheckHealthAsync
- Add start-backend and create-migration-branch helper scripts
- Add minimal WiX scaffolding and docs updates

Reviewed-by: [Your Name]