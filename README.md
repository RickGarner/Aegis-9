# Jarvis Desktop

> **Canonical version notice (2026-08-31):** The current A.E.G.I.S.-9
> application is on `feature/workflow-automation-monitoring-2026-08-31`. The `main` branch still
> builds the older pre-cinematic interface. New computers and review sessions
> must fetch and switch to the cinematic branch before building or assessing
> project status. Start with [`docs/CURRENT-VERSION.md`](docs/CURRENT-VERSION.md)
> and [`docs/handoff.md`](docs/handoff.md).

Jarvis Desktop is the native Windows Command Center for the Jarvis local-first personal assistant. It is a standalone application: this folder contains everything needed to build and run it, including its own copy of the FastAPI backend.

## Repository split

This folder was split out of the combined `Jarvis` checkout on 2026-08-25 so the desktop application and the legacy web dashboard can be developed, versioned, and run completely independently.

- This folder (`D:\Jarvis_Desktop`): native WPF Command Center + its own bundled backend.
- `D:\Jarvis_Web`: React/Vite dashboard + its own bundled backend, kept as a legacy/reference client.

Each folder has an independent copy of `backend/`, `config/`, `.env`, and a working Python virtual environment (`.venv`), so each one starts up on its own without the other folder present. This was verified after the split: the desktop app auto-started its own backend from this folder, and the web dashboard's dev server independently reached its own backend copy.

If you need the web dashboard, use `D:\Jarvis_Web` instead. The two folders do not share runtime state (each has its own SQLite database under `storage/`), so chat history, uploaded files, and workflows created in one are not visible in the other.

## Project structure

- `Jarvis.sln` - Visual Studio 2022 solution for the native Windows client
- `desktop/` - native Windows WPF command center, workflow, and monitoring windows, plus installer scaffolding
- `backend/` - Python backend API, orchestration, and model integrations (bundled/auto-started by the desktop app)
- `config/` - editable monitored-server inventory used by the backend's monitoring collector
- `storage/` - local SQLite database and uploaded file storage (git-ignored)
- `docs/` - planning, architecture, and native-desktop handoff documents
- `scripts/` - developer helper scripts for running the backend and building the installer

## Current status

- Cinematic A.E.G.I.S.-9 WPF command center with a cohesive dark operations layout
- Cyber-lupine WebView2 avatar runtime with local head, bust, rigged, and warrior GLB assets
- Adaptive provider discovery and routing across local/remote LM Studio, Ollama, and LiteLLM
- Local voice input through Faster-Whisper with WPF microphone capture
- Local Kokoro speech output with offline Windows speech fallback
- Reproducible Windows workstation bootstrap and validation under `deployment/windows/`
- FastAPI backend with a local OpenAI-compatible provider client, provider/dependency health checks, and configured model fallback
- Native .NET 8 WPF command center with automatic backend startup and readiness gating
- Native session restoration, file intake/preview/removal, activity trail, and alert resolution
- Native Settings window for the editable server inventory and local credentials
- Native workflow supervision (create, approve, pause, resume, stop) with monitor-aware placement
- Native MoveIT Automation and Server Status monitor windows
- Native human-like avatar presence with persisted display-name/theme preferences and interaction states
- Local 3D avatar host window with avatar.json/manifest-based male/female profile loading, WebView2 local virtual-host mapping, and automatic fallback to the native avatar
- Saved avatar selection loads automatically into the main command-center avatar panel at startup and remains the default until changed in Settings; the native drawing remains the fallback
- Wolforge Jarvis avatar is temporarily installed for both male and female profile choices, with local Idle/Blink/Listening/Thinking/Speaking/Success/Warning/Error clips
- Local avatar/voice configuration scaffolding for MakeHuman/MPFB avatars, Blender 5.2 authoring, Kokoro voice IDs, lip-sync preference, and speech cancellation
- Bounded local artifact generation for recognized script/file requests; the first implemented path creates a PowerShell add-two-numbers script under local generated storage
- SQLite persistence for chat, activity logs, staged-file metadata, approvals, and workflow state

MoveIT execution-history parsing, remote server agent feeds, workflow execution actions, research tools, production installer validation, and final end-to-end voice/avatar synchronization validation remain in progress. See `docs/CURRENT-VERSION.md` and `docs/handoff.md` for the full continuity record.

## Run locally

Copy `.env.example` to `.env` if it does not already exist, and adjust provider and monitoring settings as needed.

For a clean Windows computer, use the reproducible workstation bootstrap in
`deployment/windows/Install-Aegis9Workstation.ps1`. It installs the required
.NET/Python/WebView2 runtimes and configures Ollama, LiteLLM, LM Studio llmster,
and Kokoro as auto-start local services. See `deployment/windows/README.md` for
model profiles, disk requirements, validation, and troubleshooting.

Build and launch the native Windows shell (it starts its own backend automatically):

```powershell
dotnet restore Jarvis.sln
dotnet build Jarvis.sln --no-restore
Start-Process desktop\Jarvis.Desktop\bin\Debug\net8.0-windows\Jarvis.Desktop.exe
```

To smoke-test the first local artifact generator path, ask Jarvis:

```text
Create a PowerShell script to add together 2 numbers that the user inputs.
```

Jarvis should create `storage/generated/scripts/add-two-numbers.ps1` and report the path. Generated storage remains local runtime data and is not committed.

To run the backend manually during development (set `JARVIS_DEVELOPER_MODE=1` first to stop the app from auto-launching a second copy):

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Documentation

- `docs/CURRENT-VERSION.md` - canonical branch, current file map, verification state, and multi-computer startup rules
- `docs/handoff.md` - continuity record and current status
- `docs/native-desktop.md` - native Windows application architecture and window roles
- `docs/visual-studio-handoff.md` - Visual Studio 2022 setup and build guidance
- `docs/workflow-supervision.md` - workflow supervision and window-management rules
- `docs/avatar-assets.md` - licensed local 3D avatar plan and asset contract
- `docs/avatar-onboarding-playbook.md` - step-by-step licensed asset and local renderer onboarding
- `docs/JARVIS_FREE_AVATAR_VOICE_IMPLEMENTATION_HANDOFF.md` - current free local avatar/voice implementation specification and status notes
- `docs/WORKFLOW-TRANSFER.md` - portable workflow export/import between development computers
- `docs/WORKFLOW-TEST-RUNNER.md` - immutable workflow artifacts, permission manifests, and safe test profiles
- `docs/moveit-integration/` - extracted MoveIT API and monitoring contract
- `docs/server-monitoring/` - extracted server inventory, metrics, and SMTP reference
- `docs/roadmap.md`, `docs/mvp-plan.md`, `docs/provider-architecture.md`, `docs/implementation-checklist.md`, `docs/phase-1-next-steps.md` - project-wide planning history

## Safety principles

- No unrestricted autonomous actions without explicit approval
- All risky actions should be logged and reviewable
- Local-first: prefer local models and local data storage
- Tool action transparency: UI must show what the assistant is doing

## Next step

Complete production packaging, licensed local 3D avatar hosting, voice interaction, research tools, and the approved monitoring/workflow action catalog.
