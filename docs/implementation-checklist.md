# A.E.G.I.S.-9 and Aegis Developer Studio Implementation Checklist

**Updated:** 2026-09-05

`[x]` means implemented with current evidence. `[ ]` includes incomplete,
configuration-blocked, or live-acceptance work. Cross-product items are labeled
**A.E.G.I.S. ↔ Developer Studio**.

## Repository and continuity safety

- [x] Identify the canonical A.E.G.I.S. cinematic branch.
- [x] Identify Aegis Developer Studio `development-v2` as the active IDE branch.
- [x] Keep the two products in separate repositories.
- [x] Preserve older A.E.G.I.S. `main` and WolfForge v1 as recovery points.
- [x] Add a cross-project status audit and source-of-truth order.
- [x] Reconcile stale roadmap/checklist status through the 2026-09-05 checkpoint.
- [ ] Define A.E.G.I.S. release promotion/merge criteria.

## A.E.G.I.S.-9 foundation and providers

- [x] FastAPI backend and typed configuration.
- [x] Native .NET 8 WPF cinematic command center.
- [x] Local chat, logs, SQLite, and state restoration.
- [x] Backend auto-start and health/readiness handling.
- [x] DMR-primary and Ollama-failover providers; retain LM Studio/LiteLLM as inactive compatibility code.
- [x] Provider discovery, health, adaptive routing, and fallback.
- [x] Standardize family routing on DMR primary and Ollama-only failover.
- [x] Exclude providers and models without verified native tool calling.
- [x] Windows dependency manifest, installer, validator, and service templates.
- [x] Current backend suite: 97 tests passing on 2026-09-06.
- [x] Current WPF solution: build succeeds with 0 warnings/errors on 2026-09-06.
- [ ] Validate model profiles across different CPU/GPU hardware.
- [ ] Validate DMR primary, Ollama failover, and local services after reboot.
- [ ] Complete clean-machine production installer/package acceptance.

## File intake and research

- [x] Local drag/drop and picker upload with type/size controls.
- [x] Metadata and bounded extraction for TXT/MD/CSV/JSON/LOG/PDF/DOCX.
- [x] Durable preview, detach, deletion, and chat/workflow attachment.
- [ ] Controlled URL/webpage capture.
- [ ] Search provider/tool and bounded page fetcher.
- [ ] Source/citation persistence and research sessions.
- [ ] Native research panel with provider/model/tool attribution.
- [ ] Research network allowlists, limits, and audit events.

## Voice and avatar

- [x] Windows-local push-to-talk and Faster-Whisper integration.
- [x] Optional wake-phrase foundation.
- [x] Kokoro HTTP client/runtime path and Windows speech fallback.
- [x] Cancellable speech and persisted voice preferences.
- [x] Cyber-lupine male/female GLB assets and manifests.
- [x] WebView2 host, protocol, visual states, and native fallback.
- [ ] Live-validate microphone through displayed transcription.
- [ ] Live-validate Kokoro startup, playback, interruption, and fallback.
- [ ] Add approved voice-command routing.
- [ ] Synchronize mouth/lip movement with speech.
- [ ] Expand and clean-machine validate avatar animation/movement assets.

## Operational monitoring

- [x] Native MoveIT, Server, FreeFlow, and Qualys windows.
- [x] Read-only configuration-driven collectors and deduplicated alerts.
- [x] Local/remote Windows CPU, memory, disk, filesystem, and service checks.
- [x] Approve the separate movable/resizable Operations Monitoring Center
  direction and document its contracts, increments, safety, and acceptance plan.
- [x] Implement and enable the native read-only Monitoring Center window shell.
- [x] Add normalized monitor, resource, observation, alert, and collector-health
  contracts plus aggregation endpoints.
- [x] Aggregate MoveIT, Server, FreeFlow, and Qualys without replacing their
  specialized windows or collectors.
- [x] Add workflow, approval, prerequisite, and schedule status.
- [ ] Add A.E.G.I.S. backend, provider, voice/runtime, and dependency health.
- [x] Add authenticated read-only Developer Studio/bridge status and normalize it into the Monitoring Center.
- [x] Persist validated window bounds and layout mode.
- [ ] Persist filters, sorting, and selection across monitor-topology changes.
- [ ] Add incident acknowledgement, assignment, escalation, recovery, and
  notification-delivery state.
- [ ] Complete accessibility, performance, stale-data, failure-isolation, and
  large-inventory tests.
- [ ] Complete approved remote agent/hub connectivity for all production hosts.
- [ ] Add notification outbox, retry, escalation, and delivery state.
- [ ] Validate SMTP/recipient policy and managed secret storage.

### MoveIT

- [x] Task catalog and `/api/v1/reports/taskruns` history.
- [x] Success/No Transfer/Failure normalization and recovery-aware resolution.
- [ ] Accept production alert/recovery policy.
- [ ] Validate retention and log-share fallback.
- [ ] Replace temporary credentials with a read-only service identity.

### Xerox FreeFlow Core

- [x] Register `BSOXERALB001` primary and `BSOXERALB002` secondary.
- [x] Check protected routes and retain response/latency/diagnostics.
- [ ] Decide whether HTTP 401 route availability is sufficient.
- [ ] If needed, configure an authenticated API/application health transaction.

### Qualys

- [x] Native window and severity-first read-only collector foundation.
- [x] Prioritize severity 5 then 4 and create severity-based alerts.
- [ ] Supply module, platform URL, and read-only authentication.
- [ ] Define asset scope and classic severity/QDS/QVSS policy.
- [ ] Define cadence, notifications, and digest recipients.
- [ ] Run live API and alert/recovery acceptance tests.

## Workflow design and review

- [x] Durable definitions, immutable revisions, recent list, and action queue.
- [x] Create/edit/view/review/approval/schedule/archive windows.
- [x] Document-assisted reasoning-model plan generation.
- [x] Split-pane questions with individual text/choice answers.
- [x] Required-answer gating, Final Submit, and repeated re-evaluation.
- [x] Dashboard readiness/more-information notifications.
- [x] Question-free final plan approval/rejection.
- [x] Independently selected test architect after workflow-plan approval.
- [x] Separate user approval of detailed test plans before code generation.
- [x] Independently selected coding model after workflow and test-plan approval.
- [x] PowerShell/C# workflow and corresponding test implementation.
- [x] Material revision invalidates stale test and approval state.
- [x] Give workflow planning and implementation models a provider-neutral,
  security-gated read-only tool loop for request details, attachment inventory,
  bounded attached text, and clarification answers.
- [x] Deny unoffered workflow tools and prevent access to files not attached to
  the current workflow.
- [ ] Live-accept the workflow tool loop against both DMR and Ollama, including
  tool-result continuation, failover, malformed calls, and bounded-turn behavior.

## Workflow test, approval, schedule, and execution

- [x] Extract immutable artifacts and store SHA-256 hashes/manifests.
- [x] PowerShell parser validation and .NET 8 C# build validation.
- [x] Retain hashed stdout/stderr and test evidence.
- [x] Generate per-revision user manuals, redacted detailed test-results records,
  and dated lifecycle logs under the local `Workflows` tree.
- [x] Restricted low-risk PowerShell test execution.
- [x] Prevent manually fabricated test passes; fail closed when unsupported.
- [x] Separate test, user acceptance, supervisor approval, and schedule gates.
- [x] Bind supervisor decision to revision/source/manifest/schedule hashes and identity.
- [x] Once/daily/weekly/interval/manual schedules, timezone, and prerequisites.
- [x] Revalidate approvals, hashes, prerequisites, and action policy before launch.
- [x] Add a fail-closed security policy with a global mutation kill switch and
  default-deny adapter/capability registry; enforce it at workflow execution.
- [x] Allowlisted PowerShell runs with events/history/timeout/cancel/retry/recovery.
- [x] Portable `.aegisworkflow` transfer and safe conflict/import behavior.
- [ ] Disposable Windows Sandbox/VM runner for external capabilities.
- [ ] Safe C# runtime execution inside the sandbox.
- [ ] External-system functional adapters and non-production credentials.
- [ ] Authenticated supervisor roles and managed production secrets.
- [ ] Administrative UI/API for authorized security-policy changes and kill-switch status.
- [ ] Artifact signing beyond hashing.
- [ ] Advanced missed-run/compensation/escalation/concurrency/stop policies.
- [ ] Delivered workflow notifications and long-duration scheduler/reboot tests.
- [ ] Formal workflow database/artifact backup and restore validation.

## Safe automation, memory, and workspaces

- [x] Approval, audit, workflow action/permission, pause/stop/recovery foundations.
- [x] Safe application launch specifically for Developer Studio.
- [x] Short-term/session memory and monitor-aware workflow windows.
- [ ] General approved app-launch catalog.
- [ ] Browser and desktop automation adapters/policies.
- [ ] Administrative allowlist/denylist management.
- [ ] Generalize artifact generation beyond the bounded PowerShell example.
- [ ] Inspectable/correctable/deletable long-term preference memory.
- [ ] General assistant orchestration outside the workflow subsystem.
- [ ] Durable user workspaces and cross-panel context/drag behavior.

## Aegis Developer Studio foundation

- [x] Approve name, responsibility split, and separate Code - OSS foundation.
- [x] Preserve upstream architecture and create v1/v2 branch safety.
- [x] Aegis Developer Studio branding and Windows/Welcome identity, with the former WolfForge line retained only for recovery history.
- [x] Product-owned Local AI without mandatory Copilot authentication.
- [x] DMR-primary/Ollama-failover active routing plus inactive compatibility providers.
- [x] Discovery, streaming, cancellation, health, fallback, and capability routing.
- [x] Plan/implement/review/test roles and approved atomic edits.
- [x] Repository/project maps, memory, context, diagnostics, Git, impact,
  build/test ownership, and symbol tools.
- [x] Project plans, proactive suggestions, and explicit proceed gate.
- [x] Protected paths, recovery fixture, benchmarks, and release matrix.
- [x] Repository tool priorities 1–6: guarded edits/filesystem, bounded inspection, typed validation, read-only Git, and progressive context/tool budgeting.
- [x] Current Local AI suite: 69 tests passing on 2026-09-05.
- [x] Current deterministic release matrix: all 10 checks passing.
- [ ] Live native-agent handoff validation.
- [ ] Live MCP discovery/approval/result/failure/cancel validation.
- [ ] Persistent dependency/import index, multi-root and unsaved context.
- [ ] Diff annotations, inline findings, secret/branch/conflict assistance.
- [x] Governed rename/move/delete and multi-file rollback.
- [x] Governed C#/WPF/WinForms/PowerShell project scaffolding foundation.
- [ ] VB.NET→C#, VB.NET→PowerShell, and C#→PowerShell conversion with repair.
- [x] DMR-first tool-capable provider filtering, failover, and preflight context budgeting.
- [ ] Broader model/hardware benchmarks and explicit release criteria.
- [x] Developer Studio Priority 7 foundation: provider-neutral tool call/result
  and capability contracts with identical DMR/Ollama unit scenarios.
- [x] Add and enforce an origin-aware, schema-fingerprinted, default-deny
  registered-tool catalog without introducing a Copilot dependency.
- [x] Live DMR/Qwen and Ollama/Llama 3.1 probes pass native calls, valid JSON
  arguments, and continuation after tool results.
- [x] Enforce a cached two-step native qualification probe before A.E.G.I.S.-9
  workflow tool routing; remove failed routes and try the next qualified provider.
- [x] Persist versioned, expiring, endpoint-bound capability reports locally;
  reject stale, malformed, failed, and endpoint-mismatched evidence.
- [x] Add a reusable local DMR/Ollama qualification script without storing
  endpoint URLs, credentials, prompts, or tool results in the report.
- [x] Live DMR/Qwen and Ollama/Llama 3.1 each complete ordered probe steps 1 and
  2 and continue to the required final response.
- [x] Developer Studio Auto and explicit-model routing require verified tool
  protocol capability, not merely a provider/model tool-calling claim.
- [ ] Complete cancellation/context stress and induced live failover acceptance;
  apply the qualification gate to additional local providers before admission.
- [ ] Add bounded directory listing, terminal-output sessions, structured test
  failures, request todos, and question/answer coordination tools.
- [ ] Prove fully offline/local-only operation with external networking blocked;
  separately test explicitly enabled Copilot interoperability without adding
  Copilot to the provider failover chain.
- [ ] Add offline MCP registry/lifecycle support for local process and loopback
  servers; permit internal company-network MCP and resources under exact
  identity, capability, data-scope, credential, retention, and audit policy.
- [ ] Add redacted, bounded local telemetry storage/viewing and optional
  loopback/private OpenTelemetry collection with cloud exporters disabled.
- [ ] Add a shared destination-policy layer for loopback/private network tools,
  with DNS/redirect/proxy revalidation and explicit host/port allowlists.
- [ ] Add outbound schema classification and DLP/redaction enforcement; prohibit
  third-party transmission of prompts, code, repository/user data, credentials,
  telemetry, tool arguments, or results that an external provider could retain.

## A.E.G.I.S. ↔ Developer Studio integration

- [x] Approve slide-out control surface plus separate IDE window.
- [x] Visually accept the A.E.G.I.S. Developer Studio panel.
- [x] Repository browsing and persisted recent/selected repositories.
- [x] Exact-path IDE discovery, launch, process status, and focus/reuse logic.
- [ ] Live-accept launch/focus/reuse against `development-v2`.
- [x] Define the authenticated versioned loopback status bridge and threat model.
- [x] Report IDE version/session/repository/provider/model/activity to A.E.G.I.S.
- [ ] Exchange approvals without bypassing native confirmation boundaries.
- [ ] Open an approved A.E.G.I.S. workflow revision in Developer Studio.
- [ ] Return build/test output, hashes, and repair history to that exact revision.
- [ ] Keep final user/supervisor promotion authority in A.E.G.I.S.
- [ ] Package and validate the two-product setup on a clean computer.
- [x] Rename the active product and repository to Aegis Developer Studio while retaining recovery refs.

## Cross-product Local-Only Mode and security

- [x] Default-disable Copilot/Copilot Chat in fresh WolfForge profiles.
- [x] Prefer Local AI and default `localAi.localOnly` to true.
- [x] Reject public/cloud endpoints inside the Local AI layer in local-only mode.
- [ ] Remove/hide cloud model choices throughout Local-Only Mode.
- [ ] Audit/disable prompt-related cloud telemetry and authentication paths.
- [ ] Enforce firewall/proxy allowlisting for approved private services.
- [ ] Prove blocked cloud egress while local prompts/tools still work.
- [x] Add bridge authentication, replay protection, strict version negotiation,
  and least-privilege read-only status.
- [ ] Add authenticated cross-product roles and tamper-evident bridge audit.
- [ ] Complete a combined security review.

## Release readiness

## MOVEit HA auto-failback

- [x] Adopt deterministic HA specification and configure `BSOAUTALB001` as preferred primary and `BSOAUTALB002` as preferred secondary.
- [x] Add observe-only configuration, typed state contracts, fail-closed state evaluation, durable snapshot, API route, and offline tests.
- [x] Keep privileged operations and automatic failback disabled pending exact-version/on-network validation.
- [ ] Complete onsite MOVEit version, role-query, SQL identity, service, Web Admin, port, task-query, graceful-shutdown, Clear Admin Rep, and WinRM/JEA discovery.
- [ ] Bind and acceptance-test the read-only collector on the internal network.
- [ ] Add durable incidents/events, monitoring UI, exclusive lock, preflight gates, assisted failback, rollback, and fault injection.
- [ ] Obtain operations/security approval before enabling automatic failback.

## Workflow Center staged engineering standard

- [x] Apply the MOVEit HA design procedure to every AI-designed workflow: discovery, explicit assumptions/non-goals, architecture, deterministic gates, least privilege, phased rollout, tests, acceptance, rollback, and operations handoff.
- [x] Keep workflow planning read-only and prohibit executable code before explicit user plan approval.
- [x] Present plan approval as **Approve Plan + Authorize Build** with an explicit confirmation.
- [x] Require implementation review and retained non-production test evidence before user acceptance.
- [x] Require user acceptance, schedule/condition binding, and authenticated supervisor approval before production eligibility.
- [x] Require privileged actions to use fixed-function/allowlisted adapters and fail closed on unknown safety state.
- [x] Add a separate AI test-plan design stage and explicit user test-plan approval before workflow/test implementation.
- [x] Retain approved test-plan details alongside execution results and evidence before user acceptance and supervisor promotion.

- [x] Current A.E.G.I.S. backend tests and WPF build pass.
- [x] Current Aegis Developer Studio tests and release matrix pass.
- [x] Clean-machine setup and transfer boundaries are documented.
- [ ] Define a combined release acceptance matrix.
- [ ] Complete voice/avatar and monitoring/notification acceptance.
- [ ] Complete workflow sandbox/role/secret/signing/soak gates.
- [ ] Complete A.E.G.I.S./Developer Studio bridge acceptance.
- [ ] Complete product-wide Local-Only/no-egress acceptance.
- [ ] Complete full UI regression, performance, and clean-machine packaging.
- [ ] Validate backup, restore, database migration, and interrupted upgrades.
