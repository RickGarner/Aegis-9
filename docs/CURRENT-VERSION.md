# A.E.G.I.S.-9 canonical version

## Planning update — 2026-09-03

A separate movable/resizable Operations Monitoring Center is now approved as
the unified read-only monitoring and navigation surface. Its Phase 0 shell is
implemented behind a disabled-by-default feature flag and is connected to the
versioned read-only normalized aggregation endpoint. Normalized snapshots are
durable with bounded retention and explicit last-known-good/staleness behavior.
The preview Systems panel now presents selectable normalized resource cards
with target/collector state, freshness, alerts, configuration, and navigation.
Existing MoveIT, Server, FreeFlow, Qualys,
and Workflow windows remain authoritative. Read
`docs/OPERATIONS-MONITORING-CENTER-PLAN.md`, then the
Enterprise evaluation and selective-adoption plan in the sibling
`Aegis-Platform` repository before changing monitoring architecture.

## Read this first

As of 2026-08-31, active development is on the Git branch:

```text
feature/workflow-automation-monitoring-2026-08-31
```

The GitHub repository is:

```text
https://github.com/RickGarner/Aegis-9
```

`main` currently contains the older pre-cinematic WPF interface. Do not use a
build from `main` to review the current A.E.G.I.S.-9 UI, avatar, voice, or
provider-routing work. The cinematic branch includes all commits from `main`
through the merge commit `95a1f506`, followed by the current workstation
bootstrap commit `2a1079f8` and later commits on this branch.

Always verify the remote branch before beginning work:

```powershell
git fetch origin
git switch feature/workflow-automation-monitoring-2026-08-31
git pull --ff-only origin feature/workflow-automation-monitoring-2026-08-31
git status --short --branch
git log -5 --oneline --decorate
```

Expected branch display:

```text
feature/workflow-automation-monitoring-2026-08-31...origin/feature/workflow-automation-monitoring-2026-08-31
```

Do not assume that `origin/HEAD`, the default GitHub branch, or an existing
local `main` checkout is the current product version.

## Current application locations

| Area | Canonical location |
|---|---|
| Visual Studio solution | `Aegis-9.sln` |
| Cinematic WPF UI | `desktop/Aegis.Desktop/MainWindow.xaml` |
| Cinematic UI behavior | `desktop/Aegis.Desktop/MainWindow.xaml.cs` |
| Cyber-lupine WebView runtime | `desktop/Aegis.Desktop/Assets/AvatarHost/` |
| Cyber-lupine models | `desktop/Aegis.Desktop/Assets/Avatars/shared/` |
| Avatar profile manifests | `desktop/Aegis.Desktop/Assets/Avatars/male/` and `female/` |
| Adaptive provider router | `backend/app/providers.py` |
| Voice-input API | `backend/app/speech_recognition.py` and `backend/app/main.py` |
| Windows speech client | `desktop/Aegis.Desktop/LocalSpeechRecognitionService.cs` |
| Kokoro speech client | `desktop/Aegis.Desktop/KokoroSpeechService.cs` |
| Workstation installer | `deployment/windows/Install-Aegis9Workstation.ps1` |
| Workstation validator | `deployment/windows/Test-Aegis9Workstation.ps1` |
| Service templates | `deployment/windows/services/` |
| Dependency manifest | `deployment/windows/dependency-manifest.json` |
| Local configuration template | `.env.example` |
| Continuity record | `docs/handoff.md` |

The legacy browser client remains a separate repository/folder named
`Jarvis_Web`. It is not the current A.E.G.I.S.-9 operator interface.

## Clean-machine setup

On a new Windows workstation, clone and select the cinematic branch before
running any installation script:

```powershell
git clone https://github.com/RickGarner/Aegis-9.git
Set-Location Aegis-9
git switch feature/workflow-automation-monitoring-2026-08-31
Set-ExecutionPolicy -Scope Process Bypass
.\deployment\windows\Install-Aegis9Workstation.ps1 -ModelProfile Core
```

The bootstrap configures Python, .NET 8, WebView2, Ollama, LiteLLM, Kokoro
ONNX, LM Studio llmster, models, repository dependencies, `.env`, and Windows
services. See `deployment/windows/README.md` before running it.

Validate after installation or after moving to another computer:

```powershell
.\deployment\windows\Test-Aegis9Workstation.ps1
```

Then launch the current UI:

```powershell
.\desktop\Aegis.Desktop\bin\Debug\net8.0-windows\Aegis.Desktop.exe
```

## Verified cinematic state on 2026-08-30

- Cinematic WPF UI and cyber-lupine avatar assets are present.
- Adaptive local/remote provider discovery is implemented.
- Ollama, LM Studio, and LiteLLM routing code is present.
- Kokoro output and Windows offline speech fallback are integrated.
- Local Faster-Whisper voice input is implemented.
- The solution builds successfully on a third Windows workstation.
- Six backend provider/speech tests pass.
- The launched cinematic executable was visually confirmed as the expected UI.

Build currently reports one duplicated compiler warning that
`LocalSpeechRecognitionService.WakePhraseRecognized` is declared but unused.
There are no build errors.

## Work still open

- Implement the tracked daily workflow automation system in
  `docs/workflow-automation-requirements.md`, including AI-assisted authoring,
  immutable revisions, isolated testing, user and supervisor approval gates,
  scheduling/conditions, execution history, and live supervision.
- Complete end-to-end UI validation of microphone capture, transcription,
  Kokoro playback, interruption, and avatar mouth/state synchronization.
- Validate the service-based bootstrap after reboot on each new workstation,
  including the user-scoped LM Studio service credential.
- Validate GPU-specific routing and the Core/Full model profiles on different
  hardware.
- Validate production alert policy for the now-connected MoveIT Task Run history feed.
- Connect the remote ServerMonitoring agent/hub feeds.
- Add the approved monitoring/workflow action catalog and notification outbox.
- Finish production packaging and installer validation.
- Implement research tools and broaden bounded artifact generation behind
  explicit approval and allowlist policies.

## Workflow automation and operational monitoring slice — 2026-08-31

This continuation branch contains the daily-workflow interface
and domain implementation. It adds recent and awaiting-action dashboard lists,
designer/edit, approval, scheduling, and two-step archive windows; PowerShell or
C# selection; document staging; revision invalidation; explicit test, user, and
supervisor gates; and schedule/condition capture. Production execution remains
disabled. Thirteen backend tests pass, and the WPF project compiles with no errors.

The workflow AI path now independently selects a reasoning model to design a
plan and a coding model to implement only an approved plan. Both provider/model
identities and their outputs are persisted and displayed for review. Code
generation before plan approval is rejected.

The planning stage also supports structured clarification questions. The UI
renders either free-text responses or selectable model-provided options, enforces
required answers, submits responses back to the reasoning model, and repeats
plan analysis until no unresolved material questions remain.

The planning response parser also handles models that ignore the requested JSON
contract and emit numbered questions under a Markdown `Clarification Questions`
heading. Those questions are converted into stored, renderable input fields so
they cannot appear only as unanswerable plan text.

Design Review now uses a persistent split-pane window rather than a transient
question popup. Every question has its own text/choice input and individual
submit command. Submitted answers lock visibly, and `Update Draft` remains
disabled until all required answers are stored. While information is missing,
Review is the only progression action; approval/rejection is presented only
after the updated draft is re-evaluated into a question-free final plan.
The review/approval lifecycle was tightened again after live validation exposed
a truncated planning-model JSON response. Tentative plans always require Design
Review and Final Submit, malformed responses cannot bypass review, and unresolved
statements such as `to be confirmed` or `not specified` become required question
inputs. Approval/rejection appears only for the question-free plan created after
Final Submit. Plan approval then automatically triggers coding-model workflow
generation with at least two test plans. Eighteen backend tests pass.

Workflow Center now supports explicit portable workflow transfer between
computers. `EXPORT` creates a versioned `.aegisworkflow` file and `IMPORT`
restores or updates the same stable workflow identity, including planning state,
answers, schedules, generated implementation, audit entries, and extracted
attachment context. Equal or older packages cannot overwrite newer local work,
and active workflows import as paused for safety. Transfer files contain workflow
content and should be handled as operational data rather than committed to Git.
See `docs/WORKFLOW-TRANSFER.md` for the operator procedure and safety rules.

The workflow test gate now extracts immutable fenced PowerShell/C# artifacts,
stores SHA-256 hashes and permission manifests, runs bounded static validation,
and retains hashed evidence. Low-risk PowerShell can optionally run under the
restricted Constrained Language profile; external-capability workflows and C#
execution remain blocked pending an approved disposable OS sandbox. Manual test
pass recording has been removed. See `docs/WORKFLOW-TEST-RUNNER.md`.

The production workflow path now binds final supervisor authorization to the
Windows identity and exact revision, source hash, permission-manifest hash, and
schedule hash. Schedules support once, daily, weekly, interval, and manual
triggers with IANA timezones and default-deny declarative prerequisites. The
execution manager revalidates the action catalog immediately before launch and
retains run history, ordered live stdout/stderr events, output hashes,
cancellation, timeouts, retry attempts, interrupted-run recovery, and terminal
notification outbox records. The native workflow window exposes these run and
history controls. Production C# and capabilities without an explicit action
profile remain blocked.

The AD Account Lockouts workflow was revised to a scheduler-owned, single-pass,
read-only collector. It uses configurable service-account exclusions, correlates
Security events 4740/4624 across domain controllers, calculates policy-based
automatic unlock timing, retains incomplete-controller warnings, and emits
structured JSON for the A.E.G.I.S.-9 workflow window. Revision 2 passed static
validation; its earlier acceptance was invalidated and must be repeated.

Operations monitoring now collects read-only remote Windows telemetry over
PowerShell remoting/CIM using the current approved domain identity. All configured
hosts report CPU, available memory, fixed-disk capacity, and non-delayed automatic
service issues. Both Xerox FreeFlow Core application routes are configured and
actively checked; their Windows authentication challenges are treated as proof
that the protected portal route is available. MoveIT execution history is now
collected from the installed Web Admin Task Run report endpoint, with the latest
confirmed result retained per task. Qualys authentication remains a configuration
dependency.

Workflow plan approval is now separated from design review. Creating a draft
opens Workflow Design Review and starts plan analysis automatically. The review
shows a prominent unresolved-question count/status, opens required answer fields,
and does not offer `Approve Reviewed Plan` until re-analysis returns no unanswered
questions.

The workflow capabilities listed as pending in the original August 31 snapshot
have since been implemented on this branch. Refer to `docs/handoff.md` and the
workflow-specific documents for the current execution and validation state.

## Aegis Developer Studio decision — 2026-09-02

Aegis Developer Studio is approved as the local-first development environment.
The separately versioned Aegis Developer Studio Code - OSS fork is the IDE foundation.
Aegis-9 owns the native slide-out Developer Studio launcher and control
surface; the full IDE will run in its own window. Naming and architecture are
complete. The WPF slide-out, checkout detection, repository browsing, and
persisted recent selection are implemented and visually accepted. Configurable
exact-path IDE discovery, selected-repository launch, existing-window focus/reuse,
and process status are implemented and await runtime acceptance. See
`docs/AEGIS-DEVELOPER-STUDIO.md` for the tracked scope, privacy boundary, and
milestone checklist.

## Multi-computer safety rules

1. Fetch before reviewing or editing.
2. Confirm the branch is `feature/workflow-automation-monitoring-2026-08-31`.
3. Read this file and `docs/handoff.md` before making changes.
4. Do not copy build output, `.venv`, `.env`, model caches, `storage`, or user
   preferences between computers through Git.
5. Do not recreate dependency/runtime work outside `deployment/windows/`
   unless the bootstrap itself is being deliberately updated.
6. Keep commits scoped and push this branch so the next workstation sees them.
7. Do not merge the cinematic branch into `main` until an explicit release
   decision is made and the cinematic build has passed final acceptance.
