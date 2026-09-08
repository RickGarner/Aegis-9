# A.E.G.I.S.-9 and Aegis Developer Studio Roadmap

**Updated:** 2026-09-06

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
- observe-only MOVEit HA pair contracts and deterministic fail-closed state
  evaluation for preferred `BSOAUTALB001` / secondary `BSOAUTALB002`

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
- bind the exact-version, read-only MOVEit HA health/role/SQL adapter; then add
  incidents, UI, locking, assisted failback, rollback, and fault injection before
  automatic failback can be considered

Exit criteria: every monitored service has a documented health definition,
approved read-only credentials, alert/recovery policy, and notification test.

## Phase 6 — Governed daily workflow automation

**Status: Substantially complete; production hardening remains.**

Delivered: workflow dashboard/windows, document-assisted reasoning-model plans,
split-pane question review, individual answers, re-evaluation notifications,
final plan approval, separately generated and user-approved test plans before
independently routed implementation, immutable revisions, PowerShell/C# workflow
and test artifacts, hashes/manifests, bounded validation, restricted low-risk
PowerShell tests, explicit result acceptance, user and supervisor gates,
schedules/prerequisites, allowlisted PowerShell production execution, live
events/history/cancel/retry/recovery, recoverable archive, and portable transfer.

Each revision also receives a generated user manual, detailed redacted test-results
record, and daily lifecycle log under the local Git-ignored `Workflows` tree.

The workflow architect and post-plan implementation model now share a bounded,
provider-neutral read-only tool loop. DMR/Ollama can inspect authoritative
workflow details, submitted answers, attachment IDs, and bounded extracted text
without receiving every document in the initial prompt. Tool access is
default-deny and cannot reach unrelated uploads or production execution.

Remaining: disposable Windows/VM sandbox for C# and external capabilities,
authenticated supervisor authorization, managed secrets and non-production
credentials, artifact signing, functional adapters, advanced missed-run and
compensation policies, delivered notifications, and scheduler/reboot soak tests.
Core live DMR/Ollama workflow-tool qualification now passes. Cancellation and
context stress, induced failover, and additional-provider qualification remain.
Qualification reports are persisted locally with endpoint binding and expiry.

The workflow agent catalog now also supplies five bounded coordination tools:
`askQuestions`, `getRequestExecutionState`, `getCompletionCriteria`,
`getValidationEvidence`, and `getArtifactManifest`. They are available during
workflow planning and approved-plan implementation generation, remain
read-only, and preserve every existing user, testing, scheduling, and
supervisor gate.

The first five workflow-sandbox primitives are now available independently in
A.E.G.I.S.-9: directory listing, typed validation-session start, retained
output, exact-session cancellation, and structured failure extraction. They
are confined to a revision-specific non-production workspace. Terminal start
accepts only PowerShell syntax checking, .NET build, or .NET test against a
matching sandbox file; it does not accept arbitrary command text.

The next 15-tool sandbox parity increment is also complete: persistent
evidence-backed todos; bounded file reads; guarded create and expected-hash
edit; begin, preview, validate, commit, and rollback change-set phases; file and
text search; repository instructions; validation-recipe discovery; project
structure; and changed-file inspection. The implementation agent now has a
bounded 12-turn loop and must still return the canonical primary source for the
existing immutable artifact and approval pipeline. Local MCP, telemetry,
network policy, richer language/project adapters, and live model acceptance
remain separate increments.

Tool parity is now governed by `docs/SHARED-TOOL-PARITY-CONTRACT.json`, with an
identical Developer Studio copy. The contract records 45 implemented shared
capabilities, explicit product-only workflow context, and the outstanding
parity/platform backlog. Both test suites reject unclassified additions and
compare copies when the repositories are checked out together. Current gates
pass 91/91 Developer Studio tests and 114/114 A.E.G.I.S.-9 backend tests.

The latest shared block adds multi-file reads, transactional directory
creation, guarded whole-file and multi-file edits, test discovery, and typed
build/test/format/lint/static-analysis sessions to A.E.G.I.S.-9. These map to
existing Developer Studio tools; that block reduced the parity backlog to 31.

The following ten-tool shared block is also complete: bounded workspace
diagnostics, file outlines, dependency graphs, repository maps, ranked context,
repository summaries, and read-only Git context/history/blame/branch comparison
now run independently inside the workflow revision sandbox. Fixed Git argument
arrays and validated revisions prevent option/range injection. The authoritative
contract now records 45 shared capabilities and 21 parity-backlog items; current
gates pass 91/91 Developer Studio tests and 114/114 A.E.G.I.S.-9 backend tests.

The next ten-tool reasoning block is complete. Workflow implementation now has
offline tool-group discovery, context budgeting, symbol usages,
definitions/references, bounded lexical symbol graphs, change-impact analysis,
build/test ownership, repository-aware execution plans, evidence-backed
improvement suggestions, and deterministic repository memory. Activation is
informational and cannot expand server-granted authority. The authoritative
contract now records 55 shared capabilities and 11 parity-backlog items;
current gates pass 91/91 Developer Studio tests and 118/118 A.E.G.I.S.-9 tests.

The following ten-tool block is complete: guarded unified patches, diagnostic
comparison, recoverable deletion, no-overwrite rename/move, bounded workspace
symbols, typed validation commands, constrained non-production scaffolding,
tool search, and registry-only MCP discovery. Both products now carry the same
schema-versioned empty MCP catalog; discovery installs, starts, contacts, and
authorizes nothing. The contract records 65 shared capabilities with only
`delegateToAgentHostSession` remaining. Current gates pass 93/93 Developer
Studio tests and 123/123 A.E.G.I.S.-9 backend tests.

Portable tool parity is complete. `delegateToAgentHostSession` routes only a
bounded subtask to an A.E.G.I.S.-9-owned local planning, implementation,
testing, or review role; the delegated request receives no tools and no
production authority. Developer Studio uses its independent native agent-host
path. The contract now records 66 shared capabilities and no parity backlog.
Current gates pass 93/93 Developer Studio tests and 124/124 A.E.G.I.S.-9 tests.
The next work moves to the seven platform backlog capabilities for MCP,
telemetry, network/DLP governance, and air-gapped acceptance.

`independentLocalMcpRegistry` is now complete in both products. The shared
schema validates closed/bounded records, unique identities, profile-compatible
transport/connectivity, safe endpoints, pinned stdio executables, credential
references, risks, roles, targets, outbound fields, and mandatory write
approvals. Six platform capabilities remain. Current gates pass 94/94 Developer
Studio tests and 129/129 A.E.G.I.S.-9 backend tests.

Two more platform priorities are complete in both products:
`stdioAndLoopbackMcpLifecycle` and `networkDestinationPolicy`. Pinned stdio and
approved loopback transports now support the MCP initialization sequence,
tool listing/calling, bounded timeouts, shutdown, failure tracking, and
quarantine. Exact host/port allowlists, DNS/address classification, TLS rules,
proxy prohibition, and redirect revalidation fail closed. Catalogs are empty;
private-LAN MCP is not enabled. Three of seven platform capabilities are now
complete, four remain, and current gates pass 98/98 Developer Studio tests and
133/133 A.E.G.I.S.-9 backend tests.

Governed private-LAN MCP, local redacted telemetry, and outbound DLP/schema
enforcement are now implemented as independent foundations in both products.
Private MCP requires the local-network profile, organization-controlled
classification, exact TLS destination, approved role/target/fields, and any
required write approval. Local JSONL audit is bounded and secret-redacted; DLP
fails closed for unknown fields, secrets, protected external data, and oversized
payloads. Code-level air-gap harnesses pass, but live firewall-isolated DMR and
Ollama acceptance remains outstanding. Platform progress is 6/7. Current gates
pass 101/101 Developer Studio and 136/136 A.E.G.I.S.-9 tests.

### A.E.G.I.S. ↔ Developer Studio link

- Open an approved workflow artifact/revision in Developer Studio.
- Use Developer Studio for governed review, repair, build, and testing.
- Return hashes, build/test output, and results to the exact immutable A.E.G.I.S.
  workflow revision.
- Never allow an IDE result to bypass A.E.G.I.S. user or supervisor approval.

## Phase 7 — Safe automation and action catalog

### MCP roadmap refinement — 2026-09-06

The supplied `AEGIS9_DeveloperDesktop_MCP_Strategy_and_Implementation_Plan.md`
is adopted as design input through
`docs/mcp-strategy-roadmap-assessment.md`. It expands Priority 7F into ordered
security increments: governance, broker/registry, local pilot, internal-service,
optional public, first-party enterprise, and production-hardening phases. The
shared registry, lifecycle, governed model-call bridge, network/DLP policy,
redacted local audit, signature verification/drift display, resource limits,
and air-gap readiness harnesses are implemented. Catalogs remain empty by
default. Live pinned-server pilots, A.E.G.I.S.-9 protected credential brokering,
optional private OpenTelemetry collection, first-party enterprise MCP servers,
and firewall-isolated acceptance remain. Deployment signing instructions are in
`docs/POLICY-SIGNING.md`.

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
2. Complete live UI acceptance of the implemented authenticated read-only
   version/session/repository/provider/model/activity bridge; approval state
   remains a later write-capable increment.
3. Complete conversion pipelines, build/test evidence exchange, and workflow handoff.
4. Complete product-wide Local-Only Mode, telemetry/auth audit, outbound policy,
   and a blocked-cloud-egress acceptance test.
5. Validate packaging and multi-computer setup.

## Phase 10 — Security, stability, packaging, and release

**Status: Partial.**

Delivered foundation: approvals, audits, hashes, manifests, protected paths,
a fail-closed global mutation kill switch and default-deny adapter/capability
registry enforced at workflow execution, cancellation/retry/recovery, Developer Studio Local AI
endpoint filtering, A.E.G.I.S. workstation bootstrap, and a stable WolfForge v1
recovery line plus v2 track.

Remaining: extend the completed read-only bridge threat model to write-capable
job/evidence exchange; authenticated roles; managed secrets; workflow-artifact
signing beyond completed policy-file signing; tamper-evident audit; disposable
isolation; product-wide egress enforcement; release criteria; full UI regression/
performance/soak testing; clean-machine packaging; backup/restore; and database
migration validation.

No production-ready claim should be made until external integrations, privacy,
workflow isolation, authorization, packaging, and recovery pass documented tests.

## Current execution order — reconciled 2026-09-07

The detailed evidence and gap classifications are in
`docs/DOCUMENTATION-GAP-AND-FUTURE-IDEAS-AUDIT-2026-09-07.md`.

1. Run Developer Studio interactive acceptance on representative C#/WPF and
   PowerShell/Pester repositories, induced DMR→Ollama failover, and one approved
   pinned local MCP server.
2. Prove product-wide Local-Only Mode with public/cloud egress blocked while
   local models, native tools, local MCP, and redacted telemetry remain usable.
3. Implement authenticated roles, protected credential brokers, tamper-evident
   audit, workflow-artifact signing, grounded-output policy, and complete
   two-mode emergency stop controls.
4. Complete the scoped, replay-resistant immutable workflow job and evidence
   round trip between A.E.G.I.S.-9 and Developer Studio.
5. Complete disposable workflow isolation, safe C# execution, scheduler edge
   cases, notification delivery, backup/restore, and clean-machine packaging.
6. Perform onsite MOVEit, FreeFlow, Qualys, and Windows-server acceptance when
   internal systems and approved credentials are available.
7. Implement the normalized operations catalog, component/GPU/Event Log health,
   durable incident lifecycle, and Monitoring Center accessibility/performance.
8. Approve and implement the managed knowledge/document-library architecture;
   finish local embedding-provider, review-history, SBOM/advisory, and migration
   product integration identified by the documentation audit.
9. Resume controlled research/web intake, general automation/workspaces,
   conversions, preference memory, and final voice/avatar/lip-sync acceptance.

## Offline post-acceptance enhancement foundations — 2026-09-07

AES-256-GCM encrypted local indexing with explicit deletion, local review-history primitives, CycloneDX 1.5 generation with user-supplied offline vulnerability data, and integrity-checked selected non-secret migration bundles now have tested foundations in both products. A.E.G.I.S.-9 exposes these under `/api/local-intelligence/*`, `/api/review-history`, `/api/dependencies/offline-scan`, and `/api/migration/*`; none requires cloud transmission. Replaceable local embedding-model integration, complete ecosystem/advisory coverage, lifecycle/UI correlation, selective restore/rollback, and live acceptance remain.
