# A.E.G.I.S.-9 and Aegis Developer Studio Roadmap

**Updated:** 2026-09-03

**A.E.G.I.S.-9 branch:** `feature/workflow-automation-monitoring-2026-08-31`

**Developer Studio branch:** `development-v2` in the separate `RickGarner/Aegis-Developer-Studio` repository

## Product boundary

A.E.G.I.S.-9 is the local-first Windows command center for assistant interaction,
operations monitoring, governed workflows, approvals, and audit. Aegis Developer
Studio is the separate Code - OSS-based IDE currently branded WolfForge. FERAL is
the local coding/reasoning assistant within the development experience.

- **A.E.G.I.S.-9** owns the cinematic UI, backend, monitoring, workflows,
  governance, audit, and Developer Studio launcher/control surface.
- **Aegis Developer Studio** owns the editor, terminal, debugger, repository-aware Local
  AI, project planning, editing, build, and test experience.
- Cross-product features must use a versioned, authenticated local bridge. The
  repositories remain separate and must not duplicate one another's core UI.

Evidence and historical detail are in
`docs/CROSS-PROJECT-DEVELOPMENT-STATUS-2026-09-02.md`.

## Status legend

- **Complete:** Implemented and supported by current evidence.
- **Acceptance pending:** Implemented but not fully verified live.
- **Partial:** A working foundation exists; material requirements remain.
- **Configuration blocked:** Site-specific endpoints, credentials, policy, or
  infrastructure are still required.
- **Not started:** No material implementation exists.

## Phase 1 — Local assistant foundation

**Status: Complete.**

Delivered: FastAPI backend, native .NET 8 WPF cinematic command center,
provider-neutral local chat through DMR-primary/Ollama-failover endpoints,
health and fallback routing, SQLite persistence, session restoration, logs,
backend auto-start, and readiness handling.

Exit evidence: local chat works without requiring a paid cloud model; the current
backend tests and WPF build pass.

## Phase 2 — File intake and workspace context

**Status: Complete for local files; URL intake remains in Phase 3.**

Delivered: drag/drop and picker upload, size/type controls, metadata and bounded
text extraction for TXT, Markdown, CSV, JSON, logs, PDF, and DOCX, durable
storage, preview/deletion, and attachment to chat and workflow requests.

Remaining: controlled webpage/URL capture.

## Phase 3 — Controlled research and web tools

**Status: Not started.**

Required: approved search, bounded page fetching, source/citation tracking,
research workspace and saved sessions, model/tool attribution, and a permission
model before any browser automation.

Exit criteria: research results show traceable sources and every network/tool
action is visible and audited.

## Phase 4 — Voice and avatar interaction

**Status: Partial.**

Delivered: Windows-local push-to-talk foundation, Faster-Whisper transcription,
optional wake-phrase foundation, Kokoro client/runtime path, Windows speech
fallback, cancellable speech, cyber-lupine male/female GLB assets, manifests,
WebView2 host, visual states, native fallback, and persisted preferences.

Remaining: live microphone/transcription acceptance, Kokoro startup/playback and
interruption acceptance, approved voice-command routing, mouth/lip synchronization,
and clean-machine validation of expanded avatar animation/movement assets.

## Phase 5 — Operational monitoring

**Status: Partial; collectors and native windows are implemented.**

**New approved direction:** Add a separate movable, resizable, expandable
Operations Monitoring Center as the one-stop monitoring space. It will aggregate
normalized target health, collector health, alerts, workflows, schedules,
A.E.G.I.S. services, and authenticated Developer Studio status while preserving
all specialized windows. See `docs/OPERATIONS-MONITORING-CENTER-PLAN.md`.

Delivered:

- MoveIT task catalog and report-based run history with recovery-aware alerts
- local/remote Windows CPU, memory, disk, filesystem, and service checks
- FreeFlow checks for `BSOXERALB001` primary and `BSOXERALB002` secondary
- severity-first read-only Qualys collector foundation
- durable, deduplicated alerts

Delivered since the original plan: the enabled movable/resizable read-only
Operations Monitoring Center, normalized monitor/observation/alert contracts,
window/layout persistence, detail navigation, and aggregation of existing
collectors plus workflow/schedule state.

Remaining:

- aggregate A.E.G.I.S. backend/provider/voice/dependency health and authenticated
  Developer Studio status
- persist filters, sorting, and selection across topology changes
- adopt the Enterprise AI operations-catalog concepts only after the initial
  Aegis-native aggregation surface is accepted

- decide whether FreeFlow HTTP 401 protected-route reachability is sufficient or
  supply an authenticated application/API transaction
- configure Qualys module, URL, read-only authentication, asset scope,
  prioritization, cadence, and recipients
- accept MoveIT alert policy and managed service credentials
- finish approved remote agent/hub connectivity where required
- add notification delivery outbox, retry, escalation, and visible delivery state

Exit criteria: every monitored service has a documented health definition,
approved read-only credentials, alert/recovery policy, and notification test.

## Phase 6 — Governed daily workflow automation

**Status: Substantially complete; production hardening remains.**

Delivered: workflow dashboard/windows, document-assisted reasoning-model plans,
split-pane question review, individual answers, re-evaluation notifications,
final plan approval before independently routed implementation, immutable
revisions, PowerShell/C# artifacts and test plans, hashes/manifests, bounded
validation, restricted low-risk PowerShell tests, user and supervisor gates,
schedules/prerequisites, allowlisted PowerShell production execution, live
events/history/cancel/retry/recovery, recoverable archive, and portable transfer.

Remaining: disposable Windows/VM sandbox for C# and external capabilities,
authenticated supervisor authorization, managed secrets and non-production
credentials, artifact signing, functional adapters, advanced missed-run and
compensation policies, delivered notifications, and scheduler/reboot soak tests.

### A.E.G.I.S. ↔ Developer Studio link

- Open an approved workflow artifact/revision in Developer Studio.
- Use Developer Studio for governed review, repair, build, and testing.
- Return hashes, build/test output, and results to the exact immutable A.E.G.I.S.
  workflow revision.
- Never allow an IDE result to bypass A.E.G.I.S. user or supervisor approval.

## Phase 7 — Safe automation and action catalog

**Status: Partial.**

Delivered: approvals, audit, workflow permission/action enforcement, safe
pause/stop/recovery, and the specific Developer Studio launch path.

Remaining: general approved app-launch catalog, browser and desktop adapters,
administrative allowlist/denylist management, generalized artifact generation,
and rollback/compensation standards.

Exit criteria: every capability is cataloged, permissioned, logged, stoppable,
and denied when policy is absent.

## Phase 8 — Orchestration, memory, and advanced workspaces

**Status: Partial.**

Delivered: durable workflow/task state and queue, monitor-aware managed windows,
session/short-term context, and a multi-window operations layout.

Remaining: general multi-step assistant orchestration, inspectable and deletable
long-term preference memory, durable user workspaces, cross-panel context/drag
behavior, and persistent research/task context.

## Phase 9 — Aegis Developer Studio

**Status: In progress. Product rename and repository-tool priorities 1–6 are complete; bridge and broader runtime acceptance remain.**

Aegis Developer Studio provides a branded Code - OSS app; Local AI through
DMR-primary/Ollama-failover routing; capability-aware repository
plan/implement/review/test roles; approved edits; repository/project maps,
memory, context, diagnostics, Git/impact/build ownership and symbol tools; project
plans; proactive suggestions; explicit proceed gates; protected paths; recovery;
benchmarks; and a release matrix.

A.E.G.I.S. already provides the accepted slide-out panel, repository browsing,
recent selections, exact-path IDE discovery, selected-repository launch,
process state, and focus/reuse logic.

Remaining milestones:

1. Live-accept launch/focus/reuse with the `development-v2` IDE build.
2. Add an authenticated local bridge for version, session, repository,
   provider/model, activity, and approval state.
3. Complete conversion pipelines, build/test evidence exchange, and workflow handoff.
4. Complete product-wide Local-Only Mode, telemetry/auth audit, outbound policy,
   and a blocked-cloud-egress acceptance test.
5. Validate packaging and multi-computer setup.

## Phase 10 — Security, stability, packaging, and release

**Status: Partial.**

Delivered foundation: approvals, audits, hashes, manifests, protected paths,
default-deny prerequisites, cancellation/retry/recovery, WolfForge Local AI
endpoint filtering, A.E.G.I.S. workstation bootstrap, and a stable WolfForge v1
recovery line plus v2 track.

Remaining: bridge threat model, authenticated roles, managed secrets, signing,
disposable isolation, product-wide egress enforcement, release criteria, full UI
regression/performance/soak testing, clean-machine packaging, backup/restore, and
database migration validation.

No production-ready claim should be made until external integrations, privacy,
workflow isolation, authorization, packaging, and recovery pass documented tests.

## Current execution order

1. Commit, push, and clean-machine validate the 2026-09-05 baselines.
2. Implement the read-only authenticated A.E.G.I.S./Developer Studio bridge and
   display its status in the Monitoring Center.
3. Add authenticated roles, tamper-evident audit, global kill switch, grounded
   output policy, and the default-deny adapter registry.
4. Complete Qualys, FreeFlow, MoveIT, server, and notification acceptance; then
   adopt approved Enterprise operations-catalog and monitoring enhancements.
5. Add workflow sandboxing, managed secrets, and signing.
6. Connect Developer Studio build/test evidence to immutable A.E.G.I.S. workflows.
7. Finish Developer Studio agent/MCP evidence, conversion execution, and Local-Only controls.
8. Add the managed knowledge/RAG increment after its architecture decision.
9. Resume research, broader automation, preference memory, advanced workspaces,
   and final voice/lip-sync acceptance.
