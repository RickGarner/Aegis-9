# A.E.G.I.S.-9 and Aegis Developer Studio: Development Status

**Audit date:** 2026-09-02  
**Purpose:** A single, evidence-based continuation guide covering the Jarvis-Desktop/A.E.G.I.S.-9 application and the separate VS Code/WolfForge project that is becoming Aegis Developer Studio.

## Executive summary

The project is no longer a single simple local-chat application. It is now two related but deliberately separate products:

1. **A.E.G.I.S.-9 (Jarvis-Desktop)** is the cinematic Windows operations command center. It owns local chat, voice and avatars, file intake, operational monitoring, governed workflow design/testing/approval/execution, and the control surface that launches Developer Studio.
2. **Aegis Developer Studio (currently branded WolfForge)** is a custom Code - OSS desktop IDE. It owns the full editor, terminal, debugging and repository-aware local AI development experience. Its source remains in a separate Git repository.

The central architecture is sound and substantial portions are implemented. The most important unfinished work is integration and production hardening: the authenticated Aegis-to-IDE bridge, full product-wide local-only enforcement, runtime acceptance of the launcher, external monitoring configuration, stronger workflow isolation, authenticated role authorization, packaging, and end-to-end acceptance testing.

## Canonical repositories and branches

| Product | Repository / local audit path | Current branch and audited commit | Important warning |
|---|---|---|---|
| A.E.G.I.S.-9 | `RickGarner/Aegis-9`; audited at `D:\Aegis\Aegis-9` | `feature/workflow-automation-monitoring-2026-08-31` at `642fac0` | `main` contains the older pre-cinematic UI. Do not use it to review current behavior. |
| WolfForge / future Aegis Developer Studio | `RickGarner/Aegis-Developer-Studio`; audited at `D:\Aegis\Aegis-Developer-Studio` | `development-v2` at `0b091b419b1` | This is a Code - OSS fork, not an extension project. Preserve upstream mergeability. |

The repositories should remain separate. Jarvis owns governance and launch/integration surfaces; the VS Code fork owns the IDE. The future local bridge should connect them without combining their source trees.

## Status definitions used here

- **Complete:** Implemented and supported by code/tests or prior user acceptance.
- **Implemented; acceptance pending:** Code exists and automated checks pass, but the intended live environment has not been fully exercised.
- **Partial:** A meaningful foundation exists, but required behavior remains.
- **Configuration blocked:** Code exists but cannot be completed or validated until site-specific endpoints, credentials, policy or infrastructure are supplied.
- **Not started:** Planned requirement with no material implementation found.

---

# Part I — A.E.G.I.S.-9 / Jarvis-Desktop

## What the application was initially intended to be

The original roadmap described a local-first personal assistant inspired by Jarvis. Its guiding principles were local execution, a full command-center UI, safe tool-based automation, explicit approval of risk, and phased development rather than unrestricted autonomy.

The initial phases were:

| Original phase | Original goal | Current assessed status |
|---|---|---|
| Phase 1 — Local Assistant Shell | Backend, simple UI, local model chat, logs and persistence | **Complete.** FastAPI, WPF command center, provider abstraction, local chat, SQLite state and activity records exist. |
| Phase 2 — File Intake and Workspace | Upload, extract, store and attach documents | **Complete for the defined file types.** Native upload/preview/delete and chat/workflow attachments exist for text, Markdown, CSV, JSON, logs, PDF and DOCX. URL/web capture is not complete. |
| Phase 3 — Research and Web Tools | Controlled search/fetch, sources and research workspace | **Not started as a complete feature.** No production research panel, browser/fetch tool chain or source-tracking workflow was found. |
| Phase 4 — Voice Interaction | Push-to-talk, local STT/TTS and voice commands | **Partial.** Faster-Whisper input, Kokoro output path and Windows fallbacks are integrated. Full live microphone/playback/interruption/lip-sync acceptance and broad voice-command routing remain. |
| Phase 5 — Safe Automation | Launching and desktop/browser actions behind approvals and logs | **Partial.** Workflow approvals, action catalog enforcement and bounded PowerShell execution exist. General browser automation and desktop interaction are not implemented. App launch now exists specifically for Developer Studio. |
| Phase 6 — Task Orchestration and Memory | Queues, planning, multi-step work and durable context | **Substantially implemented for workflows.** Workflow queues, planning, revisions, tests, approvals, scheduler and run history exist. General long-term preference memory and a broad assistant task orchestrator remain. |
| Phase 7 — Multi-Workspace and Advanced UI | Multiple contexts, cross-panel behaviors and persistent workspaces | **Mostly not started.** The command center has multiple native operational windows, but not the originally envisioned general multi-workspace system. |
| Phase 8 — Security, Stability and Hardening | Policies, sandboxing, recovery and safe stop/resume | **Partial.** Hashes, manifests, approvals, audit records, allowlisted profiles, cancellation/retry/recovery and default-deny prerequisites exist. Disposable sandboxing, signing, secret management and release hardening remain. |
| Phase 9 — Aegis Developer Studio | Governed local-first development environment launched by Aegis | **In progress.** Product design and launcher milestones exist; bridge and governed build/edit integration remain. |

The roadmap and checklist have not always been updated in lockstep. For example, Phase 2 is still labeled “next implementation milestone” in one roadmap section even though file intake is implemented. The code, newest commits, tests, `docs/CURRENT-VERSION.md`, and this audit should take precedence over stale status labels.

## Major additions made after the initial plan

### Native operations command center

The project moved beyond the initial browser-oriented shell to a native .NET 8 WPF application. Separate native surfaces were added for chat, workflows, MoveIT Automation, server health, Xerox FreeFlow Core, Qualys, settings and Developer Studio. The React/Vite client was separated into the legacy `Jarvis_Web` project and is not the production operator UI.

### Cinematic UI and cyber-lupine avatars

The accepted current interface is the cinematic WPF UI introduced on the cinematic feature line. It includes an inline WebView2 avatar host, local cyber-lupine GLB assets, male/female manifests, persisted avatar selection, native fallback behavior, visual states and local renderer messaging. Earlier handoff statements that describe only placeholder avatars are obsolete.

### Adaptive local model and voice stack

Provider discovery and task-aware routing were added for Ollama, LM Studio and LiteLLM/OpenAI-compatible endpoints. Voice additions include Faster-Whisper speech recognition, Kokoro speech output integration and Windows offline fallbacks. The Windows workstation bootstrap now installs/configures these dependencies using a model profile.

### Operational monitoring

The app grew into an operations dashboard:

- MoveIT task catalog and task-run history are collected read-only. Results normalize Success, No Transfer and Failure; recovered failures resolve after a confirmed success.
- Local and remote Windows telemetry covers CPU, available memory, fixed disks and stopped automatic services through PowerShell remoting/CIM.
- Xerox FreeFlow Core monitoring is implemented for `BSOXERALB001` (primary) and `BSOXERALB002` (secondary). The current `/FreeFlowCore` routes return Windows-authentication challenges, which are treated as evidence that IIS and the protected route are reachable.
- Qualys VM/VMDR-style vulnerability collection is scaffolded read-only and prioritizes severity 5 then 4, but production details are still required.

### Governed daily workflow automation

This was the largest later addition. The user-defined lifecycle is now represented across the backend and native UI:

1. Create a natural-language request and attach supporting documents.
2. Route plan design to a suitable reasoning model.
3. Show a split-pane Design Review with plan and unresolved questions.
4. Require each answer to be submitted individually.
5. Enable Final Submit/Update Draft only after required answers are stored.
6. Re-evaluate and notify the dashboard when the revised plan is ready or needs more input.
7. Permit final plan approval/rejection only for a question-free reviewed plan.
8. Route approved implementation generation to an independently selected coding model.
9. Extract and hash PowerShell/C# artifacts and generate at least two test plans.
10. Run bounded validation, retain evidence, require user acceptance, then bind supervisor approval to the exact revision and hashes.
11. Configure schedules and default-deny prerequisites.
12. Execute allowlisted PowerShell with live events, history, cancellation, timeout, retry, interrupted-run recovery and notifications.

Portable `.aegisworkflow` export/import was added for moving workflow definitions and their audit state between computers. Imports preserve identity and history, reject older/equal overwrites, and pause active workflows for safety.

### Aegis Developer Studio

The product name, ownership boundary and hybrid UX were approved. A native Aegis slide-out launcher now provides checkout discovery, browsing, recent repository persistence, exact-path IDE detection, selected-repository launch, focus/reuse and process status. The full IDE remains a separate process/window.

## What is complete now

### Application foundation

- Native .NET 8 WPF cinematic command center and FastAPI backend.
- SQLite persistence for conversations, files, approvals, workflows, revisions, runs, audit events and monitoring state.
- Local model abstraction and health checks for LM Studio, Ollama and LiteLLM-compatible routes.
- Backend auto-start from the WPF client and backend readiness waiting.
- Reproducible Windows workstation installer, validator, service templates and dependency manifest.
- Current clean build: `dotnet build Aegis-9.sln --no-restore` completed with **0 errors and 0 warnings** during this audit.
- Current backend suite: **43 tests passed** from the `backend` directory during this audit.

### Files, chat and context

- Upload, extraction, metadata, preview, deletion and bounded text storage.
- Attaching extracted document content to chat and workflow creation.
- Local conversation/session restoration and activity display.
- A single bounded artifact generator for the original “add two numbers” PowerShell request.

### Workflow authoring and governance

- Recent-workflow and awaiting-action dashboard panels.
- Dedicated create/edit, Design Review, approval, schedule, status and archive/delete windows.
- Required question controls, per-answer submission, plan re-evaluation and readiness notification.
- Separate reasoning-model and coding-model selection with identities persisted.
- Immutable revisions and invalidation of stale approval after material edits.
- Static PowerShell parsing and .NET 8 C# build validation with hashed evidence.
- Restricted low-risk PowerShell test execution using Constrained Language mode.
- User acceptance and supervisor approval gates.
- One-time, daily, weekly, interval and manual scheduling with timezone and prerequisites.
- Approved PowerShell execution path with stream/history/cancel/retry/recovery behavior.
- Recoverable archive and two-step destructive confirmation.
- Portable workflow transfer.

### Monitoring

- MoveIT catalog and five-day report-based task-run collection.
- Alert persistence/deduplication and recovered MoveIT failure handling.
- Remote Windows telemetry collector.
- FreeFlow inventory and reachability checks for the two named servers.
- Qualys severity-first collector foundation and native window.

### Avatar and voice foundation

- Cinematic avatar assets, manifests and WebView2 host.
- Persisted avatar/voice selection, state messages and graceful native fallback.
- Local speech transcription API/client and Kokoro/Windows speech output clients.

### Developer Studio launcher

- Accepted slide-out UI and repository chooser.
- Persisted selected/recent repositories.
- Configurable exact IDE path, checkout detection, process detection, launch and focus/reuse logic.

## What was started but is not complete

| Area | What exists | What remains |
|---|---|---|
| Voice experience | Faster-Whisper, Kokoro client/runtime path, offline fallback and avatar speech states | Live end-to-end verification of microphone capture, transcription, playback, interruption, wake/voice commands and mouth/lip synchronization. |
| Workflow isolation | Static validators, hashes, manifests and restricted low-risk PowerShell execution | Approved Windows Sandbox/disposable VM for external capabilities and C# runtime execution; dedicated non-production credentials and functional adapters. |
| Workflow production security | Revision/hash-bound supervisor gate and current Windows identity capture | Proper authenticated role/authorization source, managed secrets, artifact signing and policy administration. |
| Scheduler policy depth | Core triggers, prerequisites, execution manager and recovery | Workflow/profile-specific missed-run, compensation, escalation and advanced stop/resume policies; long-duration operational soak testing. |
| Notifications | Durable workflow terminal notification records and monitoring alerts | Delivery outbox/retry policy, SMTP acceptance, recipient/escalation configuration and operator-visible delivery state. |
| Server monitoring | Concurrent CIM/PowerShell remote collector | Deploy/connect the intended remote agent/hub feeds where remoting is not the approved production path; validate all target hosts and permissions. |
| FreeFlow | Named inventory and verified protected application routes | Decide whether a 401 reachability check is sufficient or configure an authenticated API/application transaction. |
| Qualys | Read-only collector, severity ordering, alerts and UI | Platform URL, product/module, auth method, scope, prioritization policy, cadence and recipients. This is configuration blocked. |
| MoveIT | Task catalog and report endpoint run history | Production alert-policy acceptance, retention/fallback validation and managed read-only credentials. |
| Avatars | Working cyber-lupine models and host | Final animation/movement expansion, lip sync and asset/license/package validation across clean machines. Some older Blender/MakeHuman checklist entries are superseded by the newer integrated assets. |
| Workstation portability | Installer/validator and transfer documentation | Reboot/service validation on each machine, LM Studio service credential validation, GPU routing/model-profile testing and final installer packaging. |
| Developer Studio launch | Launcher implementation passes build | Live acceptance that the configured WolfForge executable opens the selected repository and an existing instance is correctly focused/reused. |
| General memory | Short-term/session and workflow persistence | User preference/long-term assistant memory with explicit privacy and lifecycle controls. |

## What has not been started or remains materially absent

- Controlled web research: search, page fetch/browser collection, citations/source tracking and research workspace.
- General-purpose browser automation.
- General desktop interaction automation outside narrowly approved launch/execution paths.
- A generalized artifact/file generator behind an allowlist; the original hard-coded PowerShell example is not a general implementation.
- A complete general multi-workspace/cross-panel context system.
- The authenticated, versioned Aegis-to-Developer-Studio bridge.
- Developer Studio build/test evidence exchange, workflow artifact handoff and approval messages.
- Production C# workflow execution in an approved OS sandbox.
- A full administrative allowlist/denylist editor and enterprise-grade managed-secret integration.

---

# Part II — WolfForge / Aegis Developer Studio

## Initial project intent and phases

WolfForge began as a custom Windows desktop IDE derived directly from Code - OSS. The intent was to preserve the mature editor/workbench, performance and extension ecosystem while adding a distinct product identity and a first-party local AI experience that does not require GitHub Copilot.

The initial staged AI plan was:

1. Create a product-owned OpenAI-compatible provider registry/configuration model.
2. Decouple local provider registration from GitHub authentication and Copilot entitlement.
3. Validate a generic custom endpoint end to end.
4. Add Ollama, LM Studio and LiteLLM presets.
5. Connect shared chat, context, editing, tools and agent workflows with capability-aware model selection.
6. Add tests for discovery, authentication, streaming, tool calls, capability negotiation, privacy and failure handling.

Those foundational stages have been substantially implemented. Development then expanded into repository intelligence, recovery, agent/MCP integration, project conversion/scaffolding planning, proactive suggestions and explicit consent gates.

## Major additions made as development progressed

### WolfForge identity and packaging surfaces

The fork received its own wolf branding, Welcome experience, title/banner/update strings, Windows executable/tile assets and product metadata. A stable v1 recovery line exists as `release/wolfforge-v1` with tag `wolfforge-v1.0.0-baseline`; active v2 work is on `development-v2`.

### Local AI provider platform

The `extensions/local-ai` product extension supports generic OpenAI-compatible endpoints plus presets for Ollama, LM Studio, both providers and LiteLLM. It includes model discovery, authentication, SSE streaming, Responses API and Anthropic-message handling, cancellation, reasoning-tag filtering, cold-start warming, health classification, fallback, context limits and capability-aware routing.

### Repository-aware agent capabilities

Implemented capabilities include:

- Chat roles/commands for planning, implementation, review and testing.
- File search/read/create/edit and atomic multi-file edits with approval and unsaved-by-default behavior.
- Repository maps, verified repository memory and invalidation.
- Ranked workspace context with ignored/generated-file exclusion.
- Build/test ownership, diagnostics, Git state and change-impact analysis.
- Language-service symbol implementations/outgoing-call graph.
- Approved command execution with timeout and PowerShell parser/PSScriptAnalyzer validation.
- Tool-call recovery when weaker models return fenced code or malformed attempted tool JSON.
- Native MCP tool enumeration/invocation through Code - OSS approval boundaries.
- Confirmation-aware delegation to native `agent-host-*` sessions.

### V2 project creation and conversion direction

V2 added read-only Visual Studio solution/project maps, a phased project execution planner, proactive improvement suggestions and a hard “explicitly proceed” gate before project-scale mutation. Target lanes include new C#/PowerShell projects and VB.NET/C#/PowerShell conversions, including WPF, WinForms and console requirements.

### Privacy direction

Copilot and Copilot Chat are default-disabled for fresh product profiles and Local AI is preferred. `localAi.localOnly` defaults to true and rejects non-loopback/non-private-network endpoints. This is meaningful enforcement inside the Local AI layer, but it is not yet a product-wide no-egress guarantee.

## What is complete now

- Branded standalone Code - OSS fork and Windows identity assets.
- Separate upstream/origin model that permits ongoing Microsoft Code - OSS merges.
- Product-owned Local AI provider, configuration and secure-key declarations.
- Ollama, LM Studio, dual-provider, LiteLLM and custom-compatible routing.
- Streaming, cancellation, provider warmup/health, fallback and capability selection.
- Local chat without a Copilot account.
- Planning, implementation, review and test roles.
- Confirmed single- and multi-file workspace edits with safety checks.
- Repository map/memory, Visual Studio project map, context ranking, diagnostics, Git context, change impact, validation recipes and symbol graph.
- Project execution plans and proactive improvement suggestions.
- Explicit user-consent gate for project-scale scaffold/convert execution requests.
- Protected-path enforcement for instruction files, environment files and Git metadata.
- Deterministic recovery fixture, benchmarks and release matrix.
- Prior live proof that a blank profile selected a local model through HPC LM Studio and created an approved file without Copilot authentication.
- Current audit result: **47 Local AI tests passed** and the **8-check release matrix passed** on `development-v2`.

## What was started but is not complete

| Workstream | Implemented foundation | Remaining evidence or behavior |
|---|---|---|
| Native agent handoffs (Step 89) | Validated delegation tool and confirmation boundary | Live agent-host fixture proving session creation, prompt delivery, returned results and cancellation. |
| MCP E2E (Step 90) | Native tool discovery/invocation path and compiling test server | Clean live scenario for discovery, approval, auth, results, cancellation and failure handling. |
| Semantic retrieval (Step 91) | Deterministic ranking, lexical/symbol/Git/test signals and exclusions | Persistent dependency/import index, multi-root coverage, unsaved-editor context, retrieval evaluation and live measurement. |
| Git review (Step 92) | Protected paths and risk assessment | Staged/unstaged diff annotations, inline findings, secret detection, branch/conflict assistance and finding-fix loops. |
| Release validation (Step 93) | Tests, deterministic release matrix, packaging checks and benchmark framework | Explicit release criteria plus complete live UI, privacy, performance and larger-model evidence. |
| Chat/agent lifecycle | Completion race was fixed and live basic response completion was previously verified | Full inspect→plan→confirm→edit→test→repair→report flow, cancellation/resume/rollback and background session acceptance. |
| Local-only controls | Local AI endpoint guard and Copilot default-disabled | Product-wide model-picker/cloud-path removal, telemetry/auth audit, enforceable outbound allowlist and no-egress acceptance test. |
| Provider hardening | Discovery, routing, fallback and basic capability metadata | Provider-specific capability discovery, token budgeting, vision, retry/backoff, lifecycle handling, wider LM Studio/LiteLLM/model benchmarks. |
| Project creation/conversion | Topology map, planner, suggestions and execution-consent classification | Actual governed multi-project scaffolding/conversion pipeline, dependency-ordered edits, builds, tests, rollback and retained evidence. |

## What has not been started or remains materially absent

- Product-wide egress lock that can substantiate “no prompt or source leaves the approved network.”
- Removal/hiding of all cloud language-model choices in Local-Only Mode.
- Firewall/proxy allowlisting automation and an automated blocked-cloud-egress acceptance test.
- Full Visual Studio solution/project scaffolding execution for the advertised C#, WPF, WinForms and PowerShell targets.
- End-to-end VB.NET→C#, VB.NET→PowerShell and C#→PowerShell conversion delivery with build/test repair.
- Governed rename, move and delete operations with multi-file rollback.
- A release-quality settings/control surface for endpoint/model/tool/MCP policy and status.
- A stable Aegis Developer Studio product rename/migration from WolfForge. This is intentionally deferred until integration stabilizes.
- The authenticated local bridge to A.E.G.I.S.-9.

---

# Part III — Cross-project integration

## Agreed responsibility split

| Concern | A.E.G.I.S.-9 owns | Developer Studio owns |
|---|---|---|
| Product role | Operations, monitoring, workflow governance and approvals | Full development workbench |
| User surface | Cinematic command center and slide-out launcher | Separate native IDE window |
| Repositories | Repository selection, recent list and launch status | Editing and repository-aware development context |
| AI governance | Operational model routing, workflow approvals and audit | FERAL/local coding assistance and developer tools |
| Build/test evidence | Future retention, hashes, approvals and operational promotion | Build/test execution and detailed developer output |
| Integration | Versioned authenticated local bridge client/control plane | Bridge server/adapter and current IDE session status |

## Integration already done

- Product name and architecture are approved.
- The two-repository ownership boundary is documented.
- Aegis has an accepted Developer Studio slide-out panel.
- Aegis can remember repositories and contains the IDE discovery/launch/focus implementation.
- WolfForge already contains the local AI and repository tooling required to serve as the IDE foundation.

## Integration still required

1. Live-accept the milestone-2 launcher against the current `development-v2` WolfForge build.
2. Define a versioned, authenticated loopback bridge contract.
3. Report IDE running state, active repository, local provider/model health, current activity, build/test results and pending approvals to Aegis.
4. Allow Aegis to open an approved workflow implementation/artifact directory in Developer Studio.
5. Return hashed build/test evidence to the correct immutable Aegis workflow revision.
6. Define approval roles and boundaries for file mutations, commands and promotion toward operational use.
7. Ensure neither product silently falls back to cloud inference in Local-Only Mode.
8. Package and validate both products on a clean fourth machine using only documented/bootstrap inputs.

---

# Recommended continuation order

## Priority 0 — Preserve and validate the current baselines

1. Always fetch and switch to the canonical branches above before review.
2. Do not merge the Jarvis cinematic feature branch into `main` until release acceptance.
3. Preserve WolfForge `release/wolfforge-v1` and its baseline tag; continue v2 on `development-v2`.
4. Complete live acceptance of the Aegis Developer Studio launcher with the selected repository.
5. Correct stale status text in the older roadmap/handoff documents as future work changes them.

## Priority 1 — Complete the Aegis/IDE connection

1. Design the authenticated local bridge and threat model.
2. Implement minimal read-only status first: version, process/session, repository, endpoint/model and activity.
3. Add approval/event messages next.
4. Add build/test evidence and workflow artifact handoff only after the read-only bridge is stable.

## Priority 2 — Finish externally blocked operations work

1. Supply and securely configure Qualys module, platform URL, read-only authentication, scope and prioritization policy.
2. Decide the required FreeFlow health depth beyond the currently proven protected-route reachability.
3. Validate MoveIT production alert policy and managed credentials.
4. Validate remote server access/hub topology and notification delivery.

## Priority 3 — Harden workflow execution

1. Add disposable Windows/VM sandbox execution for C# and external-capability tests.
2. Implement authenticated supervisor roles and managed secret references.
3. Add artifact signing and stronger permission/action catalog administration.
4. Complete notification delivery/retry and advanced schedule/compensation policies.
5. Run long-duration scheduler, cancellation, recovery and reboot tests.

## Priority 4 — Complete WolfForge v2 and privacy gates

1. Finish persistent dependency/import indexing and diff review.
2. Produce live native-agent and MCP E2E evidence.
3. Implement governed project scaffolding and conversion rather than planning only.
4. Finish product-wide Local-Only Mode and prove blocked cloud egress.
5. Define and pass explicit release criteria.

## Priority 5 — Return to original roadmap gaps

1. Controlled web research and source tracking.
2. General browser/desktop automation behind approvals.
3. Long-term preference memory.
4. General multi-workspace context.
5. Voice/lip-sync acceptance and expanded avatar animation.

---

# Verification performed for this audit

## Jarvis-Desktop

- Confirmed canonical branch and remote alignment at `642fac0`.
- Reviewed current-version, roadmap, implementation, workflow, monitoring, migration and Developer Studio documents.
- Reviewed commit progression through cinematic UI, voice/providers, workstation bootstrap, workflow/monitoring, workflow transfer/test/execution and Developer Studio launcher.
- Ran backend tests from `backend`: **43 passed in 6.53 seconds**.
- Ran `dotnet build Aegis-9.sln --no-restore`: **build succeeded, 0 warnings, 0 errors**.
- The repository contains an untracked `dist/` transfer-output folder; this audit did not alter or remove it.

## WolfForge / VS Code fork

- Confirmed clean `development-v2` branch aligned with `origin/development-v2` at `0b091b419b1`.
- Reviewed the authoritative Code - OSS handoff, implementation status, machine handoff, living log references, commit history and Local AI manifest/tests.
- Ran `npm --prefix extensions/local-ai test`: **47 tests passed**.
- Ran `npm --prefix extensions/local-ai run release-matrix`: **all 8 checks passed**.
- Ran `git diff --check`: no whitespace errors.

Automated checks do not replace live validation of microphones, model servers, protected enterprise portals, remote hosts, scheduler soak behavior, IDE launching, agent hosts or MCP servers.

# Start-here instructions for the next computer

## A.E.G.I.S.-9

```powershell
git clone https://github.com/RickGarner/Aegis-9.git
Set-Location Jarvis-Desktop
git fetch origin
git switch feature/workflow-automation-monitoring-2026-08-31
git pull --ff-only origin feature/workflow-automation-monitoring-2026-08-31
Get-Content docs/CURRENT-VERSION.md
Get-Content docs/CROSS-PROJECT-DEVELOPMENT-STATUS-2026-09-02.md
```

For a clean machine, follow `deployment/windows/README.md`, run `Install-Aegis9Workstation.ps1`, then `Test-Aegis9Workstation.ps1`. Never copy or commit `.env`, credentials, databases, model caches or runtime secrets.

## Aegis Developer Studio / WolfForge

```powershell
git clone https://github.com/RickGarner/Aegis-Developer-Studio.git vscode
Set-Location vscode
git remote add upstream https://github.com/microsoft/vscode.git
git fetch origin
git switch development-v2
git pull --ff-only origin development-v2
Get-Content docs/project/IMPLEMENTATION-STATUS.md
Get-Content docs/project/CODE-OSS-HANDOFF.md
npm --prefix extensions/local-ai test
```

Use the Node version declared by the repository and follow `docs/project/MACHINE-HANDOFF.md` for the full Code - OSS dependency/build setup.

# Source-of-truth order

When documents disagree, use this order:

1. Current branch code and passing tests.
2. Latest commits and date-stamped current-version/handoff additions.
3. This cross-project audit.
4. Feature-specific documents.
5. Older roadmap/checklist/history sections.

Do not interpret an older unchecked box as proof that a feature is absent without checking the newer implementation and tests.
