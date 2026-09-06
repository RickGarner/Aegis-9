# A.E.G.I.S.-9 Handoff

## Nightly checkpoint — 2026-09-06

This is the latest continuity checkpoint for the A.E.G.I.S.-9 repository. The
active branch remains `feature/workflow-automation-monitoring-2026-08-31`.
Backend acceptance is **97/97 tests**, and the WPF desktop builds with zero
warnings and zero errors when built to an unlocked output directory.

### MOVEit HA auto-failback foundation

The repository now includes the supplied
`AEGIS9_MOVEit_HA_AutoFailback_Implementation_Handoff.md` and an initial safe
implementation under `backend/app/moveit_ha/`. The configured preferred pair
is `BSOAUTALB001` primary and `BSOAUTALB002` secondary. The implementation
currently provides typed contracts, deterministic fail-closed state evaluation,
recovery stability timing, split-brain/ambiguity rejection, durable local status,
observe-only configuration, and `GET /api/monitoring/moveit-ha`.

Automatic failback is deliberately disabled. The privileged adapter refuses all
operations until the exact installed MOVEit version, authoritative runtime-role
query, shared SQL identity, service/admin interfaces, Clear Admin Rep mechanism,
running-task query, and WinRM/JEA boundary are validated on the internal network.
No MOVEit host was contacted and no production change was attempted from home.
Use `docs/moveit-ha-implementation-status.md` for tomorrow's discovery checklist.

### Governed workflow and test lifecycle

Workflow Center now applies the MOVEit-style engineering procedure to every
workflow: read-only discovery, explicit facts/assumptions/non-goals, architecture,
deterministic gates, least privilege, phased rollout, test design, rollback,
acceptance criteria, and operations handoff. The enforced sequence is:

1. final workflow plan and explicit user approval;
2. separate AI-designed non-production test plans and explicit user approval;
3. implementation of only the approved workflow and approved tests;
4. implementation review and bounded non-production execution;
5. retained plan identity, output, results, hashes, and evidence;
6. user acceptance of the test results;
7. schedule/start/stop/condition binding and user promotion request;
8. independent supervisor approval of the exact tested revision before production.

Implementation generation fails closed unless both plan gates are recorded.
Material revisions invalidate downstream evidence and approvals. See
`docs/WORKFLOW-CENTER-GOVERNED-BUILD-PROCESS.md`.

Every workflow revision automatically receives
`Workflows/<WorkflowName>_vNNN/USER-MANUAL.md` and detailed redacted
`TEST-RESULTS.md`. Daily lifecycle events are appended to
`Workflows/Logs/<WorkflowName>_YYYYMMDD.log`. The runtime tree is intentionally
Git-ignored because it can contain internal operational information. Existing
workflows receive a manual at startup if one is missing.

### Tomorrow's recommended verification

1. Pull this branch on the internal-network machine and run the backend suite and
   WPF build.
2. Create a disposable workflow and visually verify workflow-plan approval,
   test-plan approval, implementation review, safe test, result acceptance,
   schedule, user promotion request, and supervisor gate in that order.
3. Confirm the revision folder, user manual, test-results document, and daily log.
4. Complete only the read-only MOVEit discovery fields listed in
   `docs/moveit-ha-implementation-status.md`; keep `mode=observe` and
   `failback.enabled=false`.
5. Do not bind or test privileged failback operations against production until
   exact-version methods and a non-production acceptance environment are approved.

## Provider-neutral workflow design tools — 2026-09-06

A.E.G.I.S.-9 workflow planning and post-plan implementation generation now use
the provider-neutral structured tool pattern being established in Developer
Studio. The model is offered only `get_workflow_request`,
`list_workflow_attachments`, and `read_workflow_attachment`. Requests pass
through the security-control registry; attached text is returned in bounded
slices, unrelated file IDs are rejected, unoffered tools fail closed, tool
errors support controlled model recovery, and the loop has a bounded turn
limit. No production execution adapter is exposed during workflow creation.

This replaces automatic injection of every attachment into the initial planning
prompt. The model retrieves only the authoritative context it needs, reducing
context pressure and making DMR/Ollama tool behavior observable. Backend
acceptance passes **81/81** tests plus Python compilation.

The first live wire-format checkpoint passed on this machine. Local DMR
`docker.io/ai/qwen3:8b-q4_K_M` and Ollama `llama3.1:8b` each produced the
requested native function call, serialized the required JSON argument, accepted
the returned tool result, and continued with a final assistant response. This
was followed by the stronger qualification checkpoint below.

That next core qualification increment is now implemented. Before a provider
route receives workflow tools, A.E.G.I.S.-9 runs and caches a two-step native
structured-call probe. A failed route is removed and the next qualified route
is tried. Live DMR/Qwen and Ollama/Llama 3.1 each completed steps 1 and 2 in
order and returned the required completion response. Automated coverage proves
qualification caching and removal of a failed DMR route in favor of qualified
Ollama. Cancellation/context stress and an induced live failover remain broader
acceptance items.

Qualification evidence is now durable rather than an in-memory boolean.
Versioned per-provider/model/location reports are written under ignored local
`storage/tool-capability-reports.json`, bound to a SHA-256 endpoint identity,
and expire after 24 hours when successful or five minutes when failed. Reports
record native calls, argument validity, sequential calls, continuation, and a
bounded failure reason; malformed, stale, or endpoint-mismatched records never
authorize a route. `scripts/probe-tool-providers.py` regenerates the local DMR
and Ollama evidence. Its live run qualified both configured models through
2026-09-07. Backend acceptance is now **84/84** tests.

## Developer Studio Copilot-style tool priority — 2026-09-06

The supplied `AEGIS_PRIORITY_COPILOT_STYLE_AGENT_TOOL_ARCHITECTURE.md` is now
incorporated as Developer Studio Priority 7. "Copilot-style" describes
composable Agent behavior, not a Copilot dependency. The implementation plan lives in
`docs/project/COPILOT-STYLE-TOOL-INTEROPERABILITY-PLAN.md` in the separate
Aegis Developer Studio repository. The approved approach uses public VS Code
Language Model Tool and MCP APIs: DMR/Qwen remains primary, Ollama remains the
only failover, and GitHub Copilot remains an explicitly enabled interoperability
mode rather than a provider or hidden dependency. The same provider-neutral
tools must pass with DMR and Ollama; other local providers require capability
qualification. Unknown registered tools are denied by default, and strict
offline/local-only operation must pass with external networking blocked.

Offline does not mean removing useful MCP, telemetry, or network capabilities.
Priority 7 now distinguishes air-gapped machine-only mode from data-sovereign
network mode. Local/loopback MCP, approved internal company-network MCP servers
and resources, locally stored/internal telemetry, and governed network tools
remain eligible. Authorized internal services may receive the minimum company
data needed for their approved function under identity, capability, credential,
retention, and audit policy. An external third-party tool may be
used only when its outbound request contains no protected user/project data;
third-party transmission of prompts, code, repository metadata, credentials,
telemetry, tool arguments, or results is prohibited because the provider could
retain it. The Priority 7 plan defines destination and payload classification,
redaction/DLP, retention assumptions, and acceptance requirements.

The first Priority 7 code checkpoint is implemented in Developer Studio. It
adds normalized provider tool call/result and capability contracts plus an
origin-aware, schema-fingerprinted catalog enforced during FERAL selection,
discovery, and group activation. External/extension/MCP tools are denied by
default; exact-name configuration currently permits read-only external tools
only, while scoped internal write-capable MCP remains disabled pending endpoint
and data-egress policy. Validation passes **84/84** Local AI tests, **10/10**
release checks, and the full staged extension build. A.E.G.I.S.-9 enforces its
live two-step DMR/Ollama qualification gate. Developer Studio now also fails
closed in both Auto and explicit-model routing unless capabilities declare both
tool calling and verified tool-protocol behavior; its updated validation is
**85/85** tests, **10/10** release checks, and a successful staged build.

## Security control-plane foundation — 2026-09-05

A fail-closed security policy now gates workflow execution. The versioned
`config/security-control.json` registry denies unknown adapters and undeclared
capabilities, distinguishes read-only from mutating access, and provides a
global kill switch that immediately blocks mutating adapter checks while
leaving explicitly registered read-only monitoring available. Missing,
malformed, disabled, or insufficient policy is a controlled denial.

The initial registry authorizes only the existing approved workflow-execution
capability and the read-only Developer Studio status capability; it does not
activate any new production integration. The next security increments are
authenticated roles, a tamper-evident audit chain, grounded-output policy, and
an authorized policy/kill-switch administration surface. Current A.E.G.I.S.-9
backend acceptance is **75/75** tests. The WPF Release build succeeds with zero
errors; the Debug output could not be overwritten only because the currently
open A.E.G.I.S.-9 review process was using that executable.

## Developer Studio request-permission hardening — 2026-09-05

Live existing-project testing found that progressive tool-group activation
could reintroduce scaffold/delete/move/rename after initial intent filtering.
Developer Studio now holds request permissions invariant across every tool
turn: those tools remain unavailable without a matching positive user request.
The affected `D:\StockTest` project was fully restored from Aegis recovery
storage and builds with zero warnings/errors. Developer Studio also recognizes
`.slnx` projects and passes **78/78** Local AI tests.

## Developer Studio scaffold-loop correction — 2026-09-05

The Developer Studio request `Create a Visual Studio WPF project that can
monitor the stock market` revealed repeated execution of the same scaffold
tool until the bounded turn limit. Developer Studio now permits one scaffold,
removes that tool, and continues the request with guarded multi-file
implementation/validation tools. Identical mutating calls are fingerprinted
and blocked from a second execution. Developer Studio acceptance is now
**74/74** tests plus a successful full staged extension build.

## Authenticated Developer Studio status bridge — 2026-09-05

The first read-only bridge increment is implemented locally across the three
Aegis repositories. Developer Studio exposes a loopback-only, HMAC-authenticated
status endpoint when `AEGIS_BRIDGE_TOKEN` contains at least 32 characters.
A.E.G.I.S.-9 signs requests, validates the v1 response identity, fails closed,
and adds Developer Studio as a fifth read-only Operations Monitoring Center
resource. The A.E.G.I.S.-9 launcher passes the token from its local `.env` to a
new Developer Studio process without logging it. Existing Studio processes must
be restarted to receive the token.

Automated acceptance currently passes **69/69** A.E.G.I.S.-9 backend tests and
**72/72** Developer Studio Local AI tests; the Developer Studio release matrix
remains **10/10**. A real cross-process smoke test returned authenticated
product/session/repository/provider/model/activity status. Platform owns the
strict payload schema and `docs/BRIDGE-V1-SECURITY-AND-ACCEPTANCE.md`.

Live runtime acceptance then passed with the actual applications: the normalized
API returned five monitors and five observations; `developer-studio` was
`healthy`, `configured`, and `readOnly`, reporting Developer Studio `1.134.0`,
an active session, one open repository, provider preset `both` (the managed
DMR-primary/Ollama-failover pair), and model selection `auto`. Visual confirmation
of the card in the open Monitoring Center and launcher focus/reuse remain human
acceptance items. No approval, workflow, tool, or production action crosses the
bridge in this increment.

## Clean-machine verification checkpoint — 2026-09-05

The commits below are the synchronized baseline for the next computer. Perform
this verification from three separate sibling clones; do not combine the
repositories or validate from the older `D:\Jarvis-Desktop` checkout.

| Product | Repository | Branch | Required baseline commit |
|---|---|---|---|
| A.E.G.I.S.-9 | `RickGarner/Aegis-9` | `feature/workflow-automation-monitoring-2026-08-31` | `a00b2bf42110af1a63c1ebaf1e2b2148f6b752bf` |
| Aegis Developer Studio | `RickGarner/Aegis-Developer-Studio` | `development-v2` | `76ba8e17ad38ffad2824aad123285153e8abea58` |
| Aegis Platform | `RickGarner/Aegis-Platform` | `main` | `74ee810d5efddf6c56f185502cdce775249d1875` |

### 1. Clone or update the repositories

Create `D:\Aegis` if needed. For a fresh checkout, clone each repository into
the matching folder:

```powershell
New-Item -ItemType Directory -Force D:\Aegis | Out-Null
Set-Location D:\Aegis
git clone --branch feature/workflow-automation-monitoring-2026-08-31 https://github.com/RickGarner/Aegis-9.git Aegis-9
git clone --branch development-v2 https://github.com/RickGarner/Aegis-Developer-Studio.git Aegis-Developer-Studio
git clone --branch main https://github.com/RickGarner/Aegis-Platform.git Aegis-Platform
```

For an existing checkout, fetch, switch to the branch listed above, and use a
fast-forward-only pull. Do not reset or delete local work; stop and reconcile it
if `git status --short` is not empty.

```powershell
Set-Location D:\Aegis\Aegis-9
git fetch origin --prune
git switch feature/workflow-automation-monitoring-2026-08-31
git pull --ff-only origin feature/workflow-automation-monitoring-2026-08-31
git status --short --branch
git rev-parse HEAD

Set-Location D:\Aegis\Aegis-Developer-Studio
git fetch origin --prune
git switch development-v2
git pull --ff-only origin development-v2
git status --short --branch
git rev-parse HEAD

Set-Location D:\Aegis\Aegis-Platform
git fetch origin --prune
git switch main
git pull --ff-only origin main
git status --short --branch
git rev-parse HEAD
```

Each branch must contain its required baseline commit and each working tree
must be clean before continuing. The A.E.G.I.S.-9 branch will also contain the
newer documentation-only commit that added this procedure. Verify containment
with `git merge-base --is-ancestor <required-commit> HEAD`; exit code zero is a
pass.

### 2. Prepare and verify A.E.G.I.S.-9

Read `deployment/windows/README.md` before provisioning. Docker Desktop with
Docker Model Runner is the primary model runtime; Ollama is the only active
failover. LM Studio and LiteLLM are compatibility-only and must not be enabled
for this acceptance run. Preserve a machine-specific `.env` locally and never
commit it.

On a machine that still needs prerequisites, run the installer from an elevated
PowerShell window. Omit `-InstallLegacyProviders`:

```powershell
Set-Location D:\Aegis\Aegis-9
Set-ExecutionPolicy -Scope Process Bypass
.\deployment\windows\Install-Aegis9Workstation.ps1 -ModelProfile Core
```

Then run the authoritative repository gates:

```powershell
Set-Location D:\Aegis\Aegis-9
dotnet restore Aegis-9.sln
dotnet build Aegis-9.sln --no-restore
$env:PYTHONPATH = Join-Path (Get-Location) 'backend'
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

Expected result: the solution builds with zero errors and **66/66** backend
tests pass. `Test-Aegis9Workstation.ps1` still contains legacy LM Studio and
LiteLLM service checks, so it is not the authoritative DMR-primary acceptance
gate for this checkpoint.

Confirm Docker Desktop/DMR and Ollama are reachable, then launch:

```powershell
docker model list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
Start-Process .\desktop\Aegis.Desktop\bin\Debug\net8.0-windows\Aegis.Desktop.exe
```

In the UI, confirm the cinematic A.E.G.I.S.-9 shell opens, the backend reaches
ready state, `MONITORING` appears in the top-right command bar, and the
read-only Operations Monitoring Center opens and refreshes. Also launch Aegis
Developer Studio through A.E.G.I.S.-9 and confirm the existing window is
focused or a new Studio window opens.

### 3. Prepare and verify Aegis Developer Studio

Use the Node version specified by `.nvmrc`, install dependencies on a fresh
clone, repair native modules, and install Playwright Chromium if they are not
already present:

```powershell
Set-Location D:\Aegis\Aegis-Developer-Studio
npm install
.\scripts\repair-native-modules.ps1
npx playwright install chromium
npm --prefix extensions/local-ai test
npm --prefix extensions/local-ai run release-matrix
npm run gulp compile-extensions-build
```

Expected result: **69/69** Local AI tests pass, the release matrix passes
**10/10**, and the full extension build completes with zero errors. Launch the
development workbench using `.\scripts\code.bat`. Confirm Docker Model Runner
is selected ahead of Ollama, an unverified/non-tool-capable model is not offered
for tool work, and a simple read-only repository request produces a structured
tool call rather than plain-text pretend execution.

### 4. Verify Aegis Platform and record acceptance

Aegis Platform is the shared contracts/documentation repository, not a
standalone application. Confirm its `main` checkout is clean and review
`docs/ARCHITECTURE.md` for the DMR-primary/Ollama-failover family policy.

Record the following in the appropriate latest handoff/implementation log
before beginning new development:

- computer name, Windows version, verification date, and all three commit IDs;
- Docker Desktop/DMR and Ollama versions plus the tested model names;
- A.E.G.I.S.-9 build/test results and visual monitoring-launch result;
- Developer Studio test, release-matrix, build, launch, and tool-call results;
- any failed command, relevant log path, and whether the failure is an
  environment/setup issue or a reproducible product defect.

Do not advance the baseline or start feature work until the three checkouts are
clean and the failures, if any, are documented. A successful report completes
Step 5 of the 2026-09-05 immediate checkpoint.

## Monitoring Center launcher correction — 2026-09-05

GitHub contained the complete read-only Operations Monitoring Center window and backend contract but only the earlier disabled preview launcher. The intended entry point has been restored locally: `MONITORING` is visible in the main window's top-right command bar, the feature defaults to enabled, and preview labels were removed. Live acceptance returned contract `1.0`, four read-only monitor descriptors, and four observations; the monitoring workflow list matched the authoritative workflow API. The desktop build and all 66 backend tests pass.

## DMR-primary provider policy — 2026-09-05

AI routing is standardized across the Aegis family: Docker Model Runner is primary and Ollama is the only active failover provider. A.E.G.I.S.-9 discovery now scans only those two providers, hard-prioritizes DMR regardless of task scoring, and filters discovered models through the verified native-tool-call allowlist in `JARVIS_TOOL_CAPABLE_MODELS`. The active laptop configuration selects local DMR `docker.io/ai/qwen3:8b-q4_K_M` and Ollama `llama3.1:8b` as the fallback model.

LM Studio and LiteLLM are removed from active discovery. Locally installed but noncompliant Ollama models are not uninstalled; they are excluded from application routing. See `docs/provider-architecture.md` for the authoritative allowlist and live evidence.

Validation on this machine: live A.E.G.I.S.-9 discovery selected local DMR `docker.io/ai/qwen3:8b-q4_K_M` and admitted only that model plus Ollama `llama3.1:8b` and `llama3.2:latest`; all **66/66** backend tests passed and the WPF solution built with zero errors. The workstation installer parses successfully and installs legacy LM Studio/LiteLLM services only with explicit `-InstallLegacyProviders`.

## Operations Monitoring Center and selective adoption — 2026-09-03

A.E.G.I.S.-9 will add a separate movable, resizable, expandable Operations
Monitoring Center as its one-stop monitoring space. It will aggregate MoveIT,
Windows servers, FreeFlow, Qualys, workflows/schedules, A.E.G.I.S. runtime
health, collector health, and authenticated Developer Studio status. Existing
specialized windows remain authoritative for detail and platform-specific
actions. Read `docs/OPERATIONS-MONITORING-CENTER-PLAN.md` before implementing it.

The separately cloned `EnterpriseAI-Portal` is a donor/reference system only.
The evaluation and selective-adoption plan live in the Aegis Platform repo.
No Enterprise UI, database, secret, runtime, project reference, or build
dependency is approved. Security, role authorization, audit integrity, kill
controls, and adapter policy must land before write-capable adoption.

## Repository and product rename — 2026-09-02

The GitHub repository is now `RickGarner/Aegis-9`. The solution and WPF project
are `Aegis-9.sln` and `desktop/Aegis.Desktop/Aegis.Desktop.csproj`. The former
repository was renamed in place and its history was preserved. See
`docs/REBRAND-MIGRATION-2026-09-02.md`.

Aegis Developer Studio is the separate former WolfForge/VSCode repository at
`RickGarner/Aegis-Developer-Studio`. Shared contracts and the multi-root
workspace live in the private `RickGarner/Aegis-Platform` repository.

The canonical local layout is now three real sibling clones under `D:\Aegis`.
Follow `docs/CANONICAL-LOCAL-LAYOUT-MIGRATION.md`; retain former checkout folders
until the new clones pass acceptance.

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

Phase 0 of the Operations Monitoring Center began on 2026-09-03. The native
read-only preview shell, feature flag, retained layout, safe window restoration,
and specialized-monitor navigation are implemented. It remains disabled by
default. Versioned snapshot, summary, and collector-health endpoints now
normalize the four existing collectors without rewriting them, and the preview
client consumes the normalized snapshot. The fresh clone is bootstrapped;
45 backend tests pass. Next, review the draft Platform contract and shell
layout, then add durable last-known-good normalized snapshot persistence and
explicit staleness testing.

The persistence/staleness increment was subsequently completed on 2026-09-03.
Normalized snapshots survive backend restarts with bounded retention, invalid
stored payloads fail safely, prior valid target evidence can be retained during
collector failure, and expired evidence is explicitly stale. Overall status
includes collector health. The full backend suite now has 48 passing tests and
the running API has persisted version `1.0` snapshots successfully.

The normalized Systems view is also implemented. It replaces the preview's
static monitor buttons with selectable, virtualized resource cards showing
target state, collector state, configuration, freshness, alert count, evidence
summary, and links to the authoritative specialized monitor windows. Visual
acceptance remains pending; the committed feature default is still off.

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
