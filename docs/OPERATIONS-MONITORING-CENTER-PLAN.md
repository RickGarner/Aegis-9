# A.E.G.I.S.-9 Operations Monitoring Center plan

**Status:** Phase 0 / Increment 1 in progress; preview disabled by default
**Added:** 2026-09-02  
**Owner:** A.E.G.I.S.-9  
**Related plan:** Aegis Platform `docs/ENTERPRISE-AI-SELECTIVE-ADOPTION-PLAN.md`

## Purpose

Create one movable, resizable, expandable native monitoring window that gives
operators a reliable overview of all systems, alerts, workflows, schedules, and
Aegis components. Existing specialized monitoring windows remain authoritative
for platform-specific detail and actions.

The center is an aggregation and navigation surface, not a replacement for the
MoveIT, Server, FreeFlow, Qualys, Workflow, or Developer Studio windows.

## Initial monitored areas

- MoveIT Automation
- Windows servers
- Xerox FreeFlow Core primary and secondary
- Qualys vulnerabilities
- Workflow runs, approvals, prerequisites, and schedules
- A.E.G.I.S.-9 backend and local model providers
- Aegis Developer Studio and the future authenticated bridge
- Monitoring collector health

Future monitors join through contracts rather than direct changes to the window.

## Window behavior

- Separate native WPF window opened from the A.E.G.I.S.-9 dashboard.
- Movable, resizable, maximizable, and usable on a second monitor.
- Persist window bounds, monitor, layout mode, selected view, filters, and sort.
- Support compact, standard, and wallboard layouts.
- Refresh asynchronously without freezing the UI.
- Preserve the last good snapshot while clearly marking stale or failed data.
- Double-click or use Open Details to navigate to the corresponding specialized
  window and selected resource.
- Never execute production actions merely because an alert appears.

## Proposed layout

```text
┌────────────────── Operations Monitoring Center ──────────────────┐
│ Overall │ Critical │ Degraded │ Unknown │ Healthy │ Last refresh │
├───────────────┬──────────────────────────┬────────────────────────┤
│ Systems       │ Alerts / activity        │ Selected details       │
│ and views     │ severity-first timeline  │ evidence and history   │
│               │                          │ related workflow       │
├───────────────┴──────────────────────────┴────────────────────────┤
│ Collector health │ stale sources │ active runs │ next schedules   │
└──────────────────────────────────────────────────────────────────┘
```

## Core views

### Overview

- Overall status calculated from normalized target and collector states.
- Counts for Critical, Degraded, Unreachable, Unauthorized, Misconfigured,
  Unknown, Healthy, and Disabled.
- Active incidents and recently recovered resources.
- Failed, stale, or disabled collectors.
- Active workflows and upcoming schedules.
- Global automation kill-switch state when implemented.

### Systems

- Searchable and filterable list/tree grouped by platform, environment,
  criticality, owner, status, location, or primary/secondary role.
- Resource cards display status, last observation, alert count, and collector
  state.
- Selection shows evidence, recent history, related workflows, schedules, and
  available authorized actions.

### Alerts and incidents

- Unified severity-first queue across monitoring providers.
- Qualys severity 5 then 4 findings naturally sort with other critical alerts.
- Store source, resource, severity, first seen, last seen, acknowledgement,
  owner, evidence, related workflow/runbook, escalation, and recovery state.
- Deduplicate recurring observations without losing occurrence history.
- Separate active, acknowledged, suppressed-by-policy, and recovered items.

### Workflows and schedules

- Running, queued, paused, failed, awaiting-input, awaiting-review,
  awaiting-user-approval, awaiting-supervisor-approval, blocked, and completed
  workflows.
- Missed, disabled, blocked, and upcoming schedules.
- Prerequisite failures, retry state, cancellation, and last evidence.
- Navigation into the existing Workflow Center and status windows.

### Monitoring health

Target health and observation health are separate:

- **Target state:** What the latest valid evidence says about the system.
- **Collector state:** Whether evidence was collected successfully and recently.

A healthy last snapshot with a failed or stale collector must display as stale
or unknown, never current healthy.

## Normalized contracts

Every monitor registers a descriptor and returns snapshots through a common
backend contract.

### Monitor descriptor

- Monitor ID, version, display name, and source type
- Owner, environment, criticality, and service tier
- Supported resource and signal types
- Collection interval and stale-after duration
- Credential-reference ID, required role, and adapter ID
- Read-only and controlled-action capabilities
- Related workflow/runbook IDs
- Enabled state and configuration health

### Observation

- Monitor, resource, and observation IDs
- Collected-at and valid-until timestamps
- Normalized state and source-native state
- Summary, metrics, evidence references, and diagnostic code
- Collector state and duration
- Correlation/run ID
- Redaction classification

### Normalized states

- Healthy
- Degraded
- Critical
- Unreachable
- Unauthorized
- Misconfigured
- Unknown
- Disabled

### Alert

- Stable alert/deduplication key
- Source, resource, severity, title, and bounded description
- First seen, last seen, occurrence count, and evidence
- Active, acknowledged, recovered, or policy-suppressed state
- Owner, acknowledgement, notes, escalation, and notification delivery state
- Related workflow/runbook and optional recommended action

## Architecture

### Backend

- Add an operations catalog that normalizes existing monitor registrations.
- Add aggregation endpoints for summary, resources, observations, alerts,
  workflows/schedules, and collector health.
- Reuse existing collectors and persistence initially; do not rewrite them.
- Add adapter interfaces so future collectors register without UI branching.
- Perform refreshes in bounded concurrent background work with cancellation,
  timeout, per-source error isolation, and durable last-known-good snapshots.
- Publish lightweight update notifications; retain polling fallback.

### WPF client

- Add a dedicated `OperationsMonitoringCenterWindow` and view models.
- Use virtualized lists for resources, alerts, and history.
- Keep platform-specific formatting in registered detail providers.
- Reuse existing commands to open specialized windows.
- Marshal updates onto the UI dispatcher in batches.
- Apply saved bounds only after validating the current monitor topology.

### Aegis Platform and Developer Studio

- Aegis Platform owns only shared bridge/status schemas and compatibility
  fixtures, not monitoring data or the WPF UI.
- Developer Studio reports authenticated product/provider/workspace/activity
  status through the future bridge.
- The Monitoring Center consumes that read-only status as another monitor.
- Developer Studio never receives monitoring production authority.

## Safety and authorization

- Initial release is observational and navigational.
- Acknowledgement and configuration changes require backend authorization.
- Restarts, task control, vulnerability actions, service changes, and production
  workflow actions must use registered adapters and existing approval gates.
- All actions honor the global kill switch when implemented.
- The dashboard never interprets missing, stale, unauthorized, or failed data as
  healthy.
- Secrets never appear in observations, evidence previews, logs, or exports.
- UI hiding is not authorization; direct API calls enforce the same policy.

## Delivery increments

### Increment 1 — Read-only shell and contracts

- Window shell, navigation, layout persistence, and placeholder empty states.
- Normalized descriptor, observation, state, and alert contracts.
- Summary and collector-health endpoints.
- Feature flag defaults off until acceptance.

### Increment 2 — Existing monitor aggregation

- Register MoveIT, Windows Server, FreeFlow, and Qualys collectors.
- Show summary, resources, alerts, evidence, staleness, and collector failures.
- Navigate to existing specialized windows.
- Preserve current specialized-window behavior.

### Increment 3 — Workflow and schedule status

- Aggregate active workflow lifecycle states and upcoming schedules.
- Show prerequisites, missed/blocked runs, retries, and approvals.
- Navigate to workflow review, approval, schedule, and run-status windows.

### Increment 4 — Aegis component health

- Add backend, model-provider, voice-runtime, and local dependency status.
- Add authenticated Developer Studio/bridge status after the read-only bridge is
  implemented.

### Increment 5 — Operations catalog adoption

- Adopt the strongest Enterprise AI application-catalog concepts.
- Add owners, environment, criticality, service tier, credential references,
  escalation policy, and related workflow/runbook metadata.
- Add GPU and bounded Event Log monitoring after their separate review.

### Increment 6 — Incident and notification lifecycle

- Add acknowledgement, assignment, notes, escalation, and recovery workflow.
- Add durable delivery outbox, retry, recipients, digests, and visible delivery
  state.
- Keep automated remediation out of scope until adapter governance is accepted.

### Increment 7 — Authorized controlled actions

- Surface only actions registered by the Aegis adapter catalog.
- Show risk, environment, required role, approval state, and simulation option.
- Route every action through workflow governance, audit, and kill-switch checks.

## Acceptance tests

- Window opens, moves, resizes, maximizes, and restores safely across monitor
  changes.
- Large lists remain responsive and use bounded memory.
- Each current monitor appears with the same source data as its specialized
  window.
- Target and collector states remain distinct.
- Stale, timed-out, unauthorized, malformed, and unavailable sources fail
  visibly and independently.
- Alert deduplication and recovery remain correct.
- Severity ordering is deterministic.
- Filters, selection, navigation, and saved layout restore correctly.
- Workflow and schedule states match the backend source of truth.
- Direct unauthorized API actions fail even if manually invoked.
- No secret or sensitive payload is emitted in logs or exports.
- Existing monitoring and workflow test suites remain green.

## Relationship to selective Enterprise adoption

The Monitoring Center changes the adoption order by giving the normalized
operations catalog and monitoring enhancements a defined destination. It does
not change the rule that bridge security, authenticated roles, audit integrity,
kill-switch behavior, and adapter policy must precede write-capable actions.

Recommended combined order:

1. Build the read-only Monitoring Center shell and normalized contracts.
2. Connect existing Aegis monitors and workflows without changing collectors.
3. Implement authenticated bridge status and show Developer Studio health.
4. Add roles, tamper-evident audit, kill switch, and adapter registry.
5. Adopt Enterprise catalog metadata and monitoring enhancements.
6. Add incident/notification lifecycle.
7. Enable governed actions only after policy acceptance.
8. Continue the Developer Studio job bridge and knowledge/RAG phases.

## Completion checklist

- [ ] Approve normalized state and alert contracts.
- [ ] Approve initial layout and navigation behavior.
- [x] Add feature flag and WPF window shell.
- [x] Add normalized snapshot, summary, and collector-health endpoints.
- [x] Add last-known-good snapshot persistence migration.
- [x] Register existing MoveIT monitor in the normalization layer.
- [x] Register existing Windows Server monitor in the normalization layer.
- [x] Register existing FreeFlow monitor in the normalization layer.
- [x] Register existing Qualys monitor in the normalization layer.
- [ ] Add workflow/schedule aggregation.
- [ ] Add backend/provider/runtime health.
- [ ] Add authenticated Developer Studio status.
- [ ] Add operations catalog metadata.
- [ ] Add incident acknowledgement and notification delivery state.
- [ ] Complete accessibility, performance, topology, and failure testing.
- [ ] Record acceptance evidence and enable by default.

## Phase 0 implementation record — 2026-09-03

The first read-only shell is implemented as
`OperationsMonitoringCenterWindow`. It provides summary placeholders, alert
display, bounded asynchronous refresh, compact/standard/wallboard modes,
topology-safe bounds restoration, and navigation to the four existing
specialized monitors. The existing `/api/monitoring/dashboard` response is used
only as a temporary compatibility source; collectors and production actions
were not changed.

The shell is guarded by `operationsMonitoringCenter.enabled` in the desktop
`appsettings.json`. The default remains `false` until the normalized contract,
layout, and failure-state behavior are accepted. Aegis Platform owns the draft
`contracts/operations-monitoring-v1.schema.json` schema and empty-state fixture.

Baseline evidence:

- A.E.G.I.S.-9 solution build succeeds on the fresh canonical clone.
- Backend tests are pending workstation dependency bootstrap; the clone has no
  `.venv` and the global Python environment does not contain `pytest`.
- Aegis Developer Studio is clean but unbootstrapped (`node_modules` absent).
- No existing monitor collector or workflow behavior was modified.

### Normalized aggregation update — 2026-09-03

The backend now exposes three additive, read-only endpoints while preserving the
legacy `/api/monitoring` response:

- `GET /api/operations/monitoring` — versioned snapshot matching the Platform
  contract
- `GET /api/operations/summary` — normalized state counts and overall state
- `GET /api/operations/collectors` — configuration and collector health

The normalization layer registers the existing MoveIT, Windows Server,
FreeFlow, and Qualys adapters without changing collection behavior. It reports
target state separately from collector state; for example, an unconfigured
credential produces an `unknown` target and a `misconfigured` collector rather
than a healthy target. The preview WPF client now consumes the versioned
snapshot endpoint.

At the initial aggregation checkpoint, 45 backend tests passed, the WPF solution
built, and an isolated live server returned contract version `1.0` with four
descriptors and four observations. Persistence was completed in the following
increment.

### Last-known-good and staleness update — 2026-09-03

Normalized snapshots now persist in `operations_monitoring_snapshots` with a
bounded retention limit of 2,500 records. The latest compatible snapshot loads
on the next collection, including after a backend restart. Invalid or older
payloads fail safely and do not block a current collection.

When a collector fails or becomes misconfigured, the normalizer may retain its
last valid target evidence while preserving the current non-healthy collector
state and diagnostic code. Evidence beyond `validUntilUtc` is marked `stale` in
both its observation and monitor descriptor. Overall status incorporates both
target and collector state, so retained healthy evidence cannot make a failed,
stale, unauthorized, or misconfigured collector appear globally healthy.

Verification now includes 48 passing backend tests, zero-error WPF compilation,
a live version `1.0` endpoint response, and persisted snapshots in the runtime
SQLite database.

### Normalized Systems view update — 2026-09-03

The preview's Systems panel now projects the normalized descriptors and
observations into selectable resource cards instead of static navigation
buttons. Each card displays target state, collector state, evidence freshness,
active-alert count, and severity-aware status color. Selection shows
configuration state, observation timing, and the normalized evidence summary.
Operators can double-click a card or use **Open Authoritative Monitor** to reach
the existing specialized window; no action authority was added.

The selected monitor survives refresh when it remains present. Large resource
sets use WPF item virtualization, and failure refreshes retain the prior visible
snapshot with an explicit unavailable or timeout message.
