# A.E.G.I.S.-9 Handoff

## Repository and product rename — 2026-09-02

The GitHub repository is now `RickGarner/Aegis-9`. The solution and WPF project
are `Aegis-9.sln` and `desktop/Aegis.Desktop/Aegis.Desktop.csproj`. The former
repository was renamed in place and its history was preserved. See
`docs/REBRAND-MIGRATION-2026-09-02.md`.

Aegis Developer Studio is the separate former WolfForge/VSCode repository at
`RickGarner/Aegis-Developer-Studio`. Shared contracts and the multi-root
workspace live in the private `RickGarner/Aegis-Platform` repository.

## Critical current-version notice — 2026-08-31

The canonical A.E.G.I.S.-9 application is currently developed on
`feature/workflow-automation-monitoring-2026-08-31`, not `main`. GitHub's default branch and
`origin/HEAD` may still select `main`, which contains the older WPF interface.
That older interface is not evidence that the cinematic UI was lost.

Every new computer must begin with:

```powershell
git fetch origin
git switch feature/workflow-automation-monitoring-2026-08-31
git pull --ff-only origin feature/workflow-automation-monitoring-2026-08-31
```

Read `docs/CURRENT-VERSION.md` for the canonical file map, workstation setup,
verified state, and remaining work. Use
`deployment/windows/Install-Aegis9Workstation.ps1` for a clean machine and
`deployment/windows/Test-Aegis9Workstation.ps1` to validate it.

The cinematic branch contains the August 29 cinematic UI and cyber-lupine
avatar commits, the August 30 local voice/adaptive provider work, the merge of
the latest `main`, and the reproducible workstation bootstrap. The primary
current implementation areas are:

- `desktop/Aegis.Desktop/MainWindow.xaml` and `.xaml.cs` — cinematic UI
- `desktop/Aegis.Desktop/Assets/AvatarHost/` — local avatar renderer
- `desktop/Aegis.Desktop/Assets/Avatars/shared/` — cyber-lupine GLB assets
- `backend/app/providers.py` — adaptive provider routing
- `backend/app/speech_recognition.py` — local voice-input backend
- `desktop/Aegis.Desktop/LocalSpeechRecognitionService.cs` — WPF voice input
- `deployment/windows/` — authoritative dependency/service bootstrap

The older sections below remain useful implementation history, but statements
that call `main` the intended branch, describe the avatar as placeholder-only,
or say local voice/provider routing is only scaffolding are superseded by this
notice and `docs/CURRENT-VERSION.md`.

## 2026-08-31 continuation summary

This branch preserves the cinematic UI and adds the current workflow automation
and operational monitoring work. It starts from `feature/cinematic-jarvis-ui`;
that branch and `main` remain unchanged recovery points.

Completed today:

- Added read-only Xerox FreeFlow Core and Qualys Operations windows and backend
  collectors. FreeFlow registers `BSOXERALB001` primary and `BSOXERALB002`
  secondary; exact portal details remain intentionally unconfigured.
- Rebuilt Workflow Center with recent activity, awaiting-action queue, and
  create/edit/review/delete/approval/schedule surfaces.
- Added durable revisions, file attachments, PowerShell/C# selection, separate
  reasoning/coding model routing, and test/user/supervisor gates.
- Enforced draft, tentative plan, Design Review, individual answers, Final
  Submit/Update Draft, AI re-evaluation, final plan approval/rejection,
  implementation/test-plan generation, final approval, and scheduling order.
- Added split-pane Design Review with plan and questions visible together. Each
  question has its own text/choice input and individual submit command.
- Prevented malformed/truncated model responses and unresolved assumptions from
  bypassing Design Review.
- Added durable `workflow-ready` activity events and operator/dashboard
  notifications when re-evaluation is ready for approval or needs more answers.
- Verified 18 backend tests and a successful WPF build with zero errors.

Continue by reading `docs/workflow-automation-requirements.md`,
`docs/operational-monitoring.md`, and `docs/MIGRATION-2026-08-31.md`.

## Aegis Developer Studio decision — 2026-09-02

The local development environment is approved under the product name **Aegis
Developer Studio**. The renamed Aegis Developer Studio Code - OSS fork at the separate
`RickGarner/Aegis-Developer-Studio` repository is its implementation foundation. Aegis will add a
native slide-out launcher/control panel; the full IDE will open in its own native
window and later report repository, model, build/test, and approval state back to
Aegis through an authenticated local bridge.

Status: architecture and naming are complete. The native WPF slide-out panel,
Developer Studio checkout detection, folder browsing, and persisted recent-repository
selection are implemented and visually accepted. Configurable exact-path IDE
discovery, safe selected-repository launch, existing-window focus/reuse, and
process status are implemented and await runtime acceptance. The authenticated
local bridge is the next milestone.
Developer Studio is not yet product-wide local-only because cloud-capable paths remain
as its default chat agent, so Local-Only Mode is a release requirement rather
than a completed privacy guarantee. See `docs/AEGIS-DEVELOPER-STUDIO.md`.

## Session Summary

This document exists to provide continuity between development sessions and between different machines. It captures the project state, environment details, current progress, known issues, and the next actions to continue with.

## Current Machine / Environment

- Machine: Home workstation
- Original handoff date: 2026-08-25; canonical branch update: 2026-08-31
- Environment: Visual Studio 2022 solution with native WPF shell and live monitoring
- Project: A.E.G.I.S.-9
- Recommended local path: `D:\Aegis\Aegis-9`
- Repository: https://github.com/RickGarner/Aegis-9
- Current development branch: `feature/workflow-automation-monitoring-2026-08-31`

## Current Status

The planning phase and the first Phase 1 implementation slice are complete. The local dashboard, backend API, model integration, SQLite state, and workflow supervision control plane are implemented and verified.

Current implementation includes:
- Visual Studio 2022 solution at `Aegis-9.sln` with `desktop/Aegis.Desktop` as the startup project
- .NET 8 WPF desktop shell at `desktop/Aegis.Desktop`
- independent native Command Center for chat and issued commands
- separate native MoveIT Automation and Server Status windows
- native WorkflowWindow for workflow approval and lifecycle controls
- FastAPI backend and typed environment configuration
- OpenAI-compatible provider abstraction, provider health check, and local chat API
- default work configuration for LM Studio at `10.30.75.229:1234/v1`
- React/Vite dashboard at `http://127.0.0.1:5173`
- SQLite persistence at `storage/jarvis.db`
- persisted messages, activity logs, staged-file metadata, approval decisions, workflows, and topology fingerprint
- monitor-aware workflow capacity, queueing, pause/resume/stop, automatic queued-workflow promotion, and display reconciliation
- named Jarvis-managed workflow views opened as native WPF windows from the command center
- live MoveIT task catalog from `BSOAUTALB002`, with 101 tasks currently returned
- MoveIT task IDs, descriptions, enabled/disabled schedule state, and configured five-day log-root scanning
- Server Status inventory for BSOSERVER01 through BSOSERVER05 plus the local Jarvis host
- local CPU, memory, disk, automatic-service, and filesystem audit monitoring
- SMTP alert delivery for newly detected automatic-service issues, with persisted alert deduplication
- Vite dev server configured with `server.host: true` so it binds both IPv4 (`127.0.0.1`) and IPv6 (`::1`) loopback, not just IPv6
- native startup now probes backend health first and automatically launches Uvicorn from either the packaged backend runtime or the repository `.venv` when the backend is unavailable
- native startup waits for backend readiness before creating the main window
- native dependency health checks report LM Studio, Ollama, and LiteLLM reachability
- native provider requests use camelCase JSON, bounded response tokens, primary-model timeout, and fallback-model retry
- native chat entries are selectable and read-only; Enter-to-send is configurable and persisted locally
- native avatar presence supports human-like WPF rendering, hover/click reactions, chat states, and persisted name/theme preferences
- local 3D avatar host window with avatar.json/manifest-driven male/female profile selection, WebView2 virtual-host mapping, versioned JSON messages, and native fallback when licensed models are unavailable
- saved avatar selection now initializes an inline WebView2 avatar in the main command-center presence panel at startup and refreshes immediately after Settings Save; the native WPF avatar is restored on runtime/model failure
- avatar/voice service scaffolding with persisted avatar ID, male/female voice IDs, lip-sync preference, Kokoro local endpoint configuration, cancellable speech flow, and graceful TTS failure handling
- local artifact generation for recognized script/file requests; current implemented request creates `storage/generated/scripts/add-two-numbers.ps1` for the PowerShell add-two-numbers prompt
- avatar authoring note: the operator is creating the development avatars in Blender 5.2 using the MakeHuman/MPFB path described in the avatar docs

## Repository Split

On 2026-08-25 the combined `D:\Jarvis` checkout was split into two independent, standalone folders/repositories:

- `D:\Jarvis_Desktop` (this folder) — the native WPF Command Center, its bundled FastAPI backend, MoveIT/server monitoring, workflow supervision, and the avatar. This is the production operator experience.
- `D:\Jarvis_Web` — the React/Vite dashboard plus its own independent copy of the FastAPI backend, kept as a legacy/reference browser client.

Each folder contains its own full copy of `backend/`, `config/`, `.env`, and a working `.venv`, so each stands up completely on its own without the other folder present. Both were verified independently after the split: the desktop app auto-started its own backend and the web dashboard's dev-server proxy reached its own backend successfully.

The `frontend/` folder referenced elsewhere in this document has moved to `D:\Jarvis_Web\frontend` and no longer exists in this folder. Older notes below that mention `frontend/...` paths describe historical work performed before the split; treat them as history, not as paths present in this checkout.

## Provider Strategy

The project is designed to work with local models without cloud token dependence.

Recommended local providers:
- Ollama
- LM Studio
- LiteLLM as the compatibility layer

Design intent:
- the app uses a provider abstraction layer
- the app should be portable between home and work machines
- environment-specific config changes should not require core code changes

## Current Files

Core project files:
- desktop/Aegis.Desktop/Aegis.Desktop.csproj
- desktop/Aegis.Desktop/MainWindow.xaml
- desktop/Aegis.Desktop/MonitorWindow.xaml
- desktop/Aegis.Desktop/MonitoringClient.cs
- desktop/Aegis.Desktop/MonitorWindow.xaml.cs
- README.md
- .env.example
- backend/app/main.py
- backend/app/config.py
- backend/app/providers.py
- backend/app/storage.py
- backend/app/supervisor.py
- docs/roadmap.md
- docs/mvp-plan.md
- docs/ui-spec.md
- docs/implementation-checklist.md
- docs/provider-architecture.md
- docs/phase-1-next-steps.md
- docs/handoff.md
- docs/workflow-supervision.md

## Completed Work

- Created and verified the FastAPI local assistant service.
- Created and verified the React command-center dashboard.
- Connected the dashboard through FastAPI to the remote LM Studio model.
- Added local SQLite persistence and restoration on dashboard reload.
- Added workflow capacity based on detected Windows monitors, limited by configuration and a hard maximum of six.
- Added workflow lifecycle controls and safe queue promotion.
- Added managed workflow views and safe display-topology reconciliation.
- Created a local `.env` (git-ignored) pointing the backend at this machine's LM Studio instance instead of the work AI workstation.
- Added a real multipart file upload endpoint (`POST /api/files/upload`) with a 25 MB limit and an extension allowlist (txt, md, csv, json, log, pdf, docx).
- Added text extraction for uploaded files (plain text, PDF via pypdf, DOCX via python-docx) with a 50,000-character cap, persisted in SQLite alongside the file's metadata.
- Added `GET /api/files/{file_id}/content` to fetch a file's full extracted text.
- Added native WPF API client operations for chat, session restoration, workflow creation, approval, and lifecycle actions.
- Added native session restoration for activity logs, staged files, attachment state, and approval state.
- Added native file preview/removal and backend file deletion with stored-content cleanup.
- Added native alert list/resolution and operator activity presentation.
- Added native workflow attachment propagation from staged context.
- Added native `WorkflowWindow` and replaced the WPF workflow placeholder with backend-backed controls.
- Added `attachment_ids` on `POST /api/chat`; the backend now prepends selected files' extracted text as a system message before calling the provider.
- Updated the dashboard drop zone to perform real uploads (drag/drop and click-to-browse), show per-file status/preview, and let the operator toggle which staged files are attached to the next chat message.
- Fixed `.env.example` to match the actual `JARVIS_*` settings read by `backend/app/config.py` (it previously referenced unused variable names).
- Added editable `config/monitored-servers.json` inventory and native Settings access to the server list and local `.env`.
- Added native session restoration, file preview/removal, alert resolution, activity display, workflow attachment propagation, and composer preferences.
- Fixed `frontend/vite.config.ts` (`server.host: true`): the dev server was listening only on `::1` (IPv6), so `http://127.0.0.1:5173` was refused in Edge while `http://localhost:5173` happened to work. Both addresses now respond.
- Added local 3D avatar host integration with WebView2, local-only runtime files, avatar metadata contracts, male/female placeholder manifests, host fallback states, and settings/preferences for avatar and voice selection.
- Added `AvatarService`, `AvatarProtocol`, `AvatarDefinition`, `AvatarVisualState`, `KokoroSpeechService`, and speech request/result contracts to centralize avatar state, speech playback requests, and host messaging.
- Added avatar asset validation script support for `avatar.json` and legacy `manifest.json`; current validation intentionally fails until real male/female GLB files are present and license fields are updated.
- Added bounded backend artifact generation for the prompt asking Jarvis to create a PowerShell script that adds two user-entered numbers. The generated file is written to `storage/generated/scripts/add-two-numbers.ps1`.

## Verified State

- The intended git remote for this folder is `https://github.com/RickGarner/Aegis-9.git` on `main` (attach with `git remote add origin` if this folder is not yet a git repository).
- Local API is `http://127.0.0.1:8000`. The React dashboard mentioned in older notes now runs from the separate `D:\Jarvis_Web` folder.
- Current host detects four monitor work areas; effective workflow capacity is four with the default limit of six.
- Provider health and real LM Studio chat were verified against `qwen3-coder-30b-a3b-instruct` (work) and `deepseek/deepseek-r1-0528-qwen3-8b` (home, this session).
- Prior browser checks verified persisted chat, workflow lifecycle controls, monitor placement, managed workflow views, and topology reconciliation.
- Visual Studio solution and WPF build verified with `dotnet build Aegis-9.sln --no-restore`.
- Backend artifact generator smoke-tested through `/api/chat`; the PowerShell add-two-numbers prompt returns `local-artifact-generator` and creates `storage/generated/scripts/add-two-numbers.ps1`.
- Generated PowerShell script was executed with sample inputs `2` and `3`; it printed `The sum of 2 and 3 is 5`.
- Avatar validation script correctly reports the current expected blockers: missing `jarvis-male.glb`, missing `jarvis-female.glb`, and placeholder `redistributionAllowed: false` metadata.
- File upload verified end-to-end via curl: uploaded a `.txt` file, confirmed `status: extracted` with a correct preview, then sent a chat request with `attachment_ids` and confirmed the extracted text was injected as chat context.
- Frontend type-checks cleanly (`npx tsc --noEmit`) after the file-intake UI changes.

## Open Items / Next Up

Native monitoring is now visible, but the following items remain:

1. Confirm the MOVEit execution-history endpoint for this installation. The known REST history candidates returned 404; task catalog and task detail work.
2. Confirm recent MOVEit log retention/access. The remote log root is reachable, but the newest files currently observed are older than five days.
3. Connect the five remote starter servers through the existing ServerMonitoring agent/hub feed; the native table currently reports them as `Agent not connected`.
4. Add SMTP delivery verification and a notification outbox/retry policy.
5. Replace temporary MoveIT credentials with a service account and move them to managed secret storage.
6. Implement the approved monitoring/workflow action catalog.
7. Finish production packaging and installer validation.

File intake (upload, extraction, full native preview, delete, and chat/workflow attachment) is implemented. The next session should continue with:

1. add drag-from-webpage / URL capture as a research intake source
2. begin the research workflow (search tool, page fetch, source tracking)
3. finish Blender 5.2 MakeHuman/MPFB male/female avatar exports and place the resulting GLB/VRM files in the avatar asset folders
4. add the pinned local renderer dependency (`model-viewer.min.js`) and validate `scripts/validate-avatar-assets.ps1`
5. package or launch the Kokoro local voice runtime and complete voice output/lip-sync
6. expand local artifact generation beyond the initial bounded PowerShell add-two-numbers path behind approval/allowlist boundaries
7. add workflow execution tools behind approval and allowlist boundaries

Avatar integration note:
- The command center now supports launching a local 3D host window via Ctrl+click on the avatar panel (when enabled in settings).
- Assets are loaded from `desktop/Aegis.Desktop/Assets/Avatars/<profile>/avatar.json` with `manifest.json` fallback and only render when redistribution is explicitly permitted.
- The current development avatars are being created in Blender 5.2. Keep exported model filenames aligned with each avatar's `avatar.json` (`jarvis-male.glb` and `jarvis-female.glb` unless intentionally changed).
- Missing model files, missing local renderer files, missing WebView2 runtime, or unsupported formats automatically fall back to the native WPF avatar.

The WPF client automatically starts the backend when it is not already healthy. The React frontend now lives in the separate `D:\Jarvis_Web` folder/repository and is not required for native development; it should not be treated as the production launch path.

## Environment Notes

At home:
- local Ollama or LM Studio should be the default runtime

At work:
- the more powerful AI workstation should be used as the stronger local inference machine
- same app logic should be used with different runtime config

## Known Risks / Considerations

- multi-machine development requires clear handoff notes
- local model availability differs between home and work systems
- LiteLLM at port `4000` was reachable but returned HTTP 500 during verification; LM Studio and Ollama endpoints were healthy
- native workflow window placement and persistence still need to be completed
- external browser or desktop automation is not implemented and must remain behind approval flows
- UI and backend should stay decoupled to reduce risk during environment switching

## Recommended Next Session Start Point

Begin with:
- open `Aegis-9.sln` in Visual Studio 2022 and set `Aegis.Desktop` as the startup project
- verify the native MoveIT and Server Status windows on the home workstation
- connect or deploy the remote ServerMonitoring agent feed
- identify the MoveIT run-history endpoint or confirm log-based status parsing
- add native tray behavior and persisted window placement
- add a dedicated file preview/detail view in the dashboard

## Notes for Future Sessions

Keep this file updated after each major work block.

Use this file as the continuity record for any resume work after moving between machines or environments.

## Final Reminder

This project is designed as a local-first personal assistant and should not rely on paid cloud token APIs for the MVP. Do not let workflow tools create, move, or close unrelated user windows.
