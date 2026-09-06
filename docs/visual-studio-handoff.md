# Jarvis Visual Studio 2022 Handoff

> **2026-09-06 continuity note:** The product is now A.E.G.I.S.-9. Use
> `docs/handoff.md` as the latest project-wide checkpoint. Current validation is
> 97 backend tests plus a clean WPF build. This document remains the Visual
> Studio-specific setup reference.

> **Branch requirement:** Before opening the solution, run `git fetch origin`
> and confirm `git branch --show-current` returns
> `feature/workflow-automation-monitoring-2026-08-31`. `main` contains the older pre-cinematic UI.
> See `docs/CURRENT-VERSION.md` for the authoritative handoff and file map.

## Purpose

This document is the handoff for continuing Jarvis Desktop in Visual Studio 2022. The production operator experience is a native Windows WPF application. This folder (`D:\Jarvis_Desktop`) is a standalone, independent checkout: it bundles its own copy of `backend/`, `config/`, and `.venv`. The React dashboard has moved to the separate `D:\Jarvis_Web` folder/repository and is not required to run Jarvis on Windows.

## Solution

Open `Aegis-9.sln` in Visual Studio 2022. The solution currently contains:

- `desktop/Aegis.Desktop/Aegis.Desktop.csproj`

The project targets `.NET 8` with `net8.0-windows` and enables WPF. Do not retarget it just because a newer Visual Studio or SDK is installed. Retarget only when there is a tested runtime requirement.

The Python backend is intentionally not represented as a .NET project. It remains a separate FastAPI service in `backend/` and is the API boundary for the desktop client.

On a new computer, run the branch-owned bootstrap at
`deployment/windows/Install-Aegis9Workstation.ps1` before debugging. Do not
reconstruct Ollama, LiteLLM, Kokoro, LM Studio, or their Windows services from
older notes. Validate with `deployment/windows/Test-Aegis9Workstation.ps1`.

## Runtime architecture

```text
Aegis.Desktop.exe (WPF)
    -> http://127.0.0.1:8000
        -> FastAPI backend
            -> local LM Studio or Ollama provider
            -> SQLite state and audit data
            -> MoveIT monitoring
            -> Windows host monitoring
            -> workflow supervisor
            -> bounded local artifact generator for approved/generated files
```

The WPF client must not open browser windows for command, monitoring, or workflow supervision. Native WPF windows are used for the command center, MoveIT monitoring, Server Status monitoring, and managed workflows.

## Start the backend

From the repository root, create or update `.env` from `.env.example`, then run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

## Recent handoff updates (migration work completed so far)

- 2026-08-31: continued the cinematic application on
  `feature/workflow-automation-monitoring-2026-08-31` with FreeFlow/Qualys
  monitoring and the staged daily-workflow Design Review, model routing,
  approval, test, and scheduling foundation. See
  `docs/MIGRATION-2026-08-31.md`.

- Added a lightweight backend launcher and app startup integration so the WPF shell can auto-start a packaged Python FastAPI backend when installed. See desktop/Aegis.Desktop/BackendLauncher.cs and App.xaml.cs.
- MonitoringClient now includes a CheckHealthAsync(CancellationToken) helper used by the UI to poll the backend readiness endpoint before updating status.
- The WPF client creates the main window only after backend startup/readiness checks complete.
- Native chat, session, files, alerts, settings, provider health, and workflow attachment contracts are implemented in `MonitoringClient.cs`.
- Native avatar presence and local preferences are implemented in the main/settings windows and `UserPreferences.cs`.
- Local avatar/voice scaffolding now includes WebView2 avatar host messaging, avatar metadata contracts, Kokoro speech service interfaces, persisted selected avatar/voice settings, and a native fallback when the 3D or TTS runtime is unavailable.
- The saved avatar is now loaded automatically into the main WPF command-center presence panel through an inline local WebView2 host; saving a new avatar in Settings refreshes that panel, while model/runtime errors restore the native placeholder.
- The current male/female development avatars are being created in Blender 5.2 using the MakeHuman/MPFB path documented in `docs/avatar-onboarding-playbook.md`.
- `/api/chat` now has a bounded local artifact generation path for recognized script/file requests; the first implemented case creates `storage/generated/scripts/add-two-numbers.ps1` for the PowerShell add-two-numbers prompt before falling back to the configured LLM.
- The MonitorWindow was hardened to avoid crashes when theme resource keys (GreenBrush/AmberBrush) are missing; it falls back to system brushes.
- Dev scripts added to simplify local runs and the migration workflow:
  - scripts/start-backend.ps1 — creates/activates a venv, installs backend dependencies, and starts uvicorn. Use dot-sourcing with the -Activate switch to persist venv activation in your current shell: `. .\scripts\start-backend.ps1 -Activate`.
  - scripts/create-migration-branch.ps1 — historical helper that scaffolded a migration branch and moved the `frontend/` tree to `archive/frontend/`. Superseded by the 2026-08-25 physical split into `D:\Jarvis_Desktop` and `D:\Jarvis_Web`; kept only for reference.
- Minimal installer scaffolding added under desktop/installer (installer.wxs and README) to begin packaging the WPF app and bundled backend.

## New environment variables and developer toggles

- JARVIS_DEVELOPER_MODE (when set to "1" or "true") prevents the WPF app from auto-launching the bundled backend so developers can run the backend manually during development.
- JARVIS_MONITORING_URL can override the backend base URL the WPF app uses (defaults to http://127.0.0.1:8000).

## How to run locally (quick)

1. From the repo root, create and activate the venv and start the backend (recommended):

   - Dot-source the helper (activates venv in your shell and starts uvicorn):
     . .\scripts\start-backend.ps1 -Activate

   - Or manually:
     python -m venv .venv
     Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
     . .\.venv\Scripts\Activate.ps1
     pip install -r backend/requirements.txt
     cd backend
     python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend

2. Run the WPF client in developer mode (prevents auto-launch):

   $env:JARVIS_DEVELOPER_MODE = "1"
   dotnet build Aegis-9.sln --no-restore
   Start-Process desktop\Aegis.Desktop\bin\Debug\net8.0-windows\Aegis.Desktop.exe

3. Verify health and monitoring endpoints:

   curl http://127.0.0.1:8000/health
   curl http://127.0.0.1:8000/api/monitoring

If the WPF UI reports the backend is unavailable, confirm the backend process is running and reachable and check backend/logs for errors.

Keep the backend terminal running while debugging the WPF application.

## Build and run

From Visual Studio:

1. Open `Aegis-9.sln`.
2. Set `Jarvis.Desktop` as the startup project.
3. Select `Debug` and `Any CPU`.
4. Press `F5`.

From a Developer PowerShell or repository terminal:

```powershell
dotnet build Aegis-9.sln --no-restore
Start-Process desktop\Aegis.Desktop\bin\Debug\net8.0-windows\Aegis.Desktop.exe
```

The WPF client reads its backend URL from `desktop/Aegis.Desktop/appsettings.json`. The current development value is `http://127.0.0.1:8000`.

## Native UI surfaces

- `MainWindow.xaml`: command center, chat, session restoration, workflow creation, workflow approval, and monitor launch buttons.
- `MonitorWindow.xaml`: shared native window with MoveIT Automation and Server Status modes.
- `WorkflowWindow.xaml`: native workflow supervision surface with refresh, approval, pause, resume, and stop actions.
- `MonitoringClient.cs`: HTTP client and JSON DTOs used by the WPF application.

The backend already owns durable workflow state, approval gating, queue promotion, monitor capacity, and display-topology reconciliation. Keep those rules in the backend; the WPF application should display state and send user commands.

## Porting remaining web features

The React implementation that used to live alongside this project (now at `D:\Jarvis_Web\frontend\src\App.tsx`) is the historical behavior reference for any remaining porting work. Port behavior into WPF rather than adding new browser dependencies.

Priority order:

1. Native tray behavior and persisted window placement.
2. Production installer packaging with bundled backend runtime.
3. Licensed local 3D avatar hosting, voice, research, and workflow execution.

The FastAPI endpoints and JSON fields should remain the shared contract. Add or update C# DTOs in `MonitoringClient.cs` when an API contract changes.

## Existing monitoring behavior

MoveIT monitoring is read-only and polls the configured task catalog every five minutes. Recent logs are correlated from the configured five-day log root when available.

Server monitoring currently provides live local host metrics and starter rows for the configured remote servers. Remote rows remain `Agent not connected` until the ServerMonitoring agent or hub feed is connected.

Monitoring actions are intentionally pending until an approved action catalog exists. Do not infer remediation from an alert.

## Validation checklist

- `dotnet build Aegis-9.sln --no-restore` succeeds.
- The backend starts without import errors.
- `GET http://127.0.0.1:8000/health` returns `status: ok`.
- The WPF command center starts without the React dev server.
- Chat uses the backend and restores persisted session messages.
- MoveIT and Server Status open as separate native WPF windows.
- Workflows can be created, approved, opened, paused, resumed, and stopped from native WPF.
- Staged files can be uploaded, previewed, attached to chat/workflows, and removed from native WPF.
- The avatar reacts to idle, hover, click, thinking, and response states.
- The PowerShell add-two-numbers prompt creates `storage/generated/scripts/add-two-numbers.ps1` and the script runs with sample numeric inputs.
- No production WPF code calls `window.open`, starts Vite, or depends on a browser tab.

## Known limitations

- External browser and desktop automation execution is not implemented.
- Local artifact generation is currently intentionally narrow; broader file/script creation still needs approval/allowlist policy before general use.
- MoveIT execution-history endpoints returned 404 during verification; log-based evidence is used when available.
- Remote server metrics require the original ServerMonitoring agent/hub transport.
- SMTP delivery and the monitoring action catalog still require production verification and approval.
- The React frontend has moved to the separate `D:\Jarvis_Web` folder/repository and is kept there for comparison and API testing.
