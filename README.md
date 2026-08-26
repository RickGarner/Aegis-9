# Jarvis Desktop

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

- FastAPI backend with a local OpenAI-compatible provider client, provider/dependency health checks, and configured model fallback
- Native .NET 8 WPF command center with automatic backend startup and readiness gating
- Native session restoration, file intake/preview/removal, activity trail, and alert resolution
- Native Settings window for the editable server inventory and local credentials
- Native workflow supervision (create, approve, pause, resume, stop) with monitor-aware placement
- Native MoveIT Automation and Server Status monitor windows
- Native human-like avatar presence with persisted display-name/theme preferences and interaction states
- Local 3D avatar host window with avatar.json/manifest-based male/female profile loading, WebView2 local virtual-host mapping, and automatic fallback to the native avatar
- Saved avatar selection loads automatically into the main command-center avatar panel at startup and remains the default until changed in Settings; the native drawing remains the fallback
- Local avatar/voice configuration scaffolding for MakeHuman/MPFB avatars, Blender 5.2 authoring, Kokoro voice IDs, lip-sync preference, and speech cancellation
- Bounded local artifact generation for recognized script/file requests; the first implemented path creates a PowerShell add-two-numbers script under local generated storage
- SQLite persistence for chat, activity logs, staged-file metadata, approvals, and workflow state

MoveIT execution-history parsing, remote server agent feeds, workflow execution actions, research tools, packaged Kokoro runtime, licensed avatar asset onboarding, and full VRM/lip-sync rendering remain in progress. See `docs/handoff.md` for the full continuity record.

## Run locally

Copy `.env.example` to `.env` if it does not already exist, and adjust provider and monitoring settings as needed.

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

- `docs/handoff.md` - continuity record and current status
- `docs/native-desktop.md` - native Windows application architecture and window roles
- `docs/visual-studio-handoff.md` - Visual Studio 2022 setup and build guidance
- `docs/workflow-supervision.md` - workflow supervision and window-management rules
- `docs/avatar-assets.md` - licensed local 3D avatar plan and asset contract
- `docs/avatar-onboarding-playbook.md` - step-by-step licensed asset and local renderer onboarding
- `docs/JARVIS_FREE_AVATAR_VOICE_IMPLEMENTATION_HANDOFF.md` - current free local avatar/voice implementation specification and status notes
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
