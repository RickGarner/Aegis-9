# A.E.G.I.S.-9 and Aegis Developer Studio Implementation Checklist

**Updated:** 2026-09-21 — monitoring scope and authorization/credential increment reconciled

`[x]` means implemented with current evidence. `[ ]` includes incomplete,
configuration-blocked, or live-acceptance work. Cross-product items are labeled
**A.E.G.I.S. ↔ Developer Studio**.

## Offline post-acceptance enhancements

- [x] Add encrypted, clearable offline semantic-index primitives to both products.
- [ ] Add a replaceable qualified local embedding-model provider, lifecycle controls, A.E.G.I.S. UI/workflow integration, and large-repository acceptance.
- [x] Add bounded local review-history retention and a Developer Studio review view.
- [ ] Correlate fixes, validation, identity, immutable revisions, and approvals; add tamper evidence and A.E.G.I.S. lifecycle UI.
- [x] Generate CycloneDX SBOMs and exact-version-match user-provided offline vulnerability records without network access.
- [ ] Complete transitive ecosystem/license coverage, advisory ranges, signed database provenance, suppressions, UI/history, and real-project acceptance.
- [x] Export and inspect integrity-checked, selected non-secret migration bundles without automatic application.
- [ ] Add dry-run restore, conflict/rollback, ACL/ownership, signed bundles, full product-state selection, and clean-machine restore acceptance.

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
- [x] Current backend suite: 153 tests passing on 2026-09-08.
- [x] Current WPF solution: build succeeds with 0 warnings/errors on 2026-09-07.
- [ ] Validate model profiles across different CPU/GPU hardware.
- [ ] Validate DMR primary, Ollama failover, and local services after reboot.
- [ ] Complete clean-machine production installer/package acceptance.

### Startup and desktop acceptance

- [x] Release-build the native WPF desktop and verify that it reaches the
  `A.E.G.I.S.-9 · Guardian Boot Chamber` startup surface.
- [x] Verify the startup gate calls the local health, provider, policy-integrity,
  and system-health endpoints successfully when a healthy backend is available.
- [x] Verify a missing backend enters the halted startup path and does not open
  the command center automatically.
- [x] Verify sanitized startup diagnostics can be generated beneath
  `%LOCALAPPDATA%\Aegis-9\logs`.
- [ ] Manually accept the Continue, Continue Degraded, Generate Diagnostic, and
  Close A.E.G.I.S. button flows with native desktop automation or an operator.
  The 2026-09-13 automation session exposed no native-app surface, so these
  controls were not marked accepted from process/API evidence alone.
- [ ] Resume splash avatar acceptance later; the avatar remains explicitly
  pending and is not a release pass condition for this acceptance increment.

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

- [x] Native MoveIT, Server, and FreeFlow windows.
- [x] Read-only configuration-driven collectors and deduplicated alerts.
- [x] Local/remote Windows CPU, memory, disk, filesystem, and service checks.
- [x] Approve the separate movable/resizable Operations Monitoring Center
  direction and document its contracts, increments, safety, and acceptance plan.
- [x] Implement and enable the native read-only Monitoring Center window shell.
- [x] Add normalized monitor, resource, observation, alert, and collector-health
  contracts plus aggregation endpoints.
- [x] Aggregate MoveIT, Server, and FreeFlow without replacing their
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
- [x] Add notification outbox, bounded retries, and delivery state foundation.
- [ ] Add incident-linked escalation policy and complete live notification delivery acceptance.
- [ ] Validate SMTP/recipient policy and managed secret storage.

### MoveIT

- [x] Task catalog and `/api/v1/reports/taskruns` history.
- [x] Success/No Transfer/Failure normalization and recovery-aware resolution.
- [ ] Accept production alert/recovery policy.
- [ ] Validate retention and log-share fallback.
- [ ] Replace temporary credentials with a read-only service identity.

### Xerox FreeFlow Core

- [x] Register `BSOXERALB001` primary (8.0.0 build 33969) and
  `BSOXERALB002` backup (8.1.2 build 35113); this is not an HA pair.
- [x] Check protected routes and retain response/latency/diagnostics.
- [x] Review the supplied FreeFlow Codex bundle without applying its installers;
  reject its parallel generated architecture and stale SHA-256 manifest.
- [x] Add a bounded, read-only JMF `KnownDevices` client and
  `GET /api/integrations/freeflow/devices` using the existing inventory and settings.
- [x] Configure explicit port-7751 JMF endpoints for both HA servers.
- [x] Run `KnownDevices` against both servers on the internal network: both
  `/FreeFlowCore` endpoints returned HTTP 200 without authentication after the
  standards-compliant typed query and `DeviceFilter` were added. Primary returned
  40 devices in 2.5 seconds; secondary returned 41 in 25.6 seconds.
- [x] Raise the shared FreeFlow timeout default from 10 to 30 seconds based on the
  observed secondary response time.
- [x] Confirm the installed FreeFlow Core versions on both servers.
- [ ] Confirm the matching SDK contracts against the installed 8.0.0/8.1.2
  versions.
- [x] Retain representative, sanitized `KnownDevices` and `QueueStatus` response
  fixtures for deterministic tests; all retained identifiers are synthetic.
- [x] Normalize version-confirmed workflow and queue device types into the native
  FreeFlow view and dedicated integration contracts.
- [ ] Determine whether the 8.0.0/8.1.2 version difference or configuration drift
  explains the 40-versus-41 result. The API now reports a privacy-preserving
  primary/backup comparison with shared/only/blank/duplicate counts, fails the
  comparison closed on partial results, and retains no compared identifiers.
  Live evidence remains 37 shared IDs, 2 primary-only IDs, 3 backup-only IDs,
  and no blank IDs; stale-data and recovery acceptance remain open.
- [x] Normalize live `Device/DeviceClass` values: `Preset` as workflow,
  `PrinterDestination` as queue, `PrintingPress` as printer, and `Controller` as controller.
- [x] Validate job visibility: legacy `Status/QueueInfo` returns JMF code 7, while
  the advertised `QueueStatus` query succeeds on both installed versions.
- [x] Add bounded read-only job history (newest 200 per server), 30-second caching,
  typed status/error handling, and native desktop server/device/job tables.
- [ ] Define approved read-only authentication and protected credential handling if
  required; HTTP 401 remains reachability evidence only.
- [x] Add malformed and oversized XML rejection, JMF return-code validation,
  bounded history, timeout isolation, and deterministic parser tests.
- [x] Complete deterministic timeout/outage-to-recovery acceptance and a
  100-cycle forced-refresh soak with mocked read-only JMF responses.
- [ ] Complete live outage/recovery and extended refresh-soak tests. The
  2026-09-13 off-network run was blocked because neither FreeFlow hostname could
  be resolved by the current DNS/network environment.
- [ ] Keep submission, cancellation, hold/release, queue control, and every other
  mutating JMF operation unimplemented until separately designed and approved.

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
- [x] Expose bounded workflow coordination tools for questions, execution
  state, deterministic completion gates, retained validation evidence, and
  artifact identity. Keep every tool read-only and security-policy gated.
- [x] Route model-requested questions into the existing user review process;
  tools cannot invent answers or advance user/supervisor approvals.
- [x] Add workflow-sandbox adapters for `listDirectory`, typed validation
  sessions, retained output, exact-session cancellation, and structured
  failures. Expose them only after plan and test-plan approval, within the
  revision-specific non-production workspace; never expose unrestricted host
  or production shell access to the workflow model.
- [x] Add independently persisted, workflow-revision-scoped todo management
  with evidence required before completion.
- [x] Add bounded sandbox file reads and transactional create/edit operations
  with expected-hash stale-content protection.
- [x] Require begin, preview, validation, and commit phases; support exact
  change-set rollback and changed-file inspection.
- [x] Add bounded file/text search, repository-instruction discovery, typed
  validation recipes, and project-structure inspection inside the sandbox.
- [x] Add the versioned shared-tool parity contract and automated gates. Require
  new portable tools in both products and explicit reasons for exceptions.
- [x] Add multi-file reads, transactional directory creation, guarded
  replacement/multi-file edits, test discovery, and typed build/test/format/
  lint/static-analysis tools to A.E.G.I.S.-9.
- [x] Add bounded diagnostics, outline/dependency/repository intelligence and
  fixed-argument read-only Git context/history/blame/comparison tools to the
  workflow sandbox; shared parity is now 45 tools with 21 items remaining.
- [x] Add ten offline repository-reasoning tools for progressive group
  discovery, context budgeting, symbols/impact, ownership, planning,
  suggestions, and repository memory; shared parity is now 55 tools with 11
  items remaining.
- [x] Add guarded patch/path/scaffold/typed-command operations, diagnostic
  comparison, workspace symbols, tool search, and registry-only MCP discovery;
  shared parity is now 65 tools with one item remaining.
- [x] Add identical schema-versioned, empty-by-default MCP catalog files to both
  products and ensure discovery filters disabled/unhealthy servers and grants
  no tool authority.
- [x] Complete `delegateToAgentHostSession` parity with bounded A.E.G.I.S.-9
  local-role delegation that grants neither tools nor production authority;
  shared portable parity is now 66/66 with no backlog.
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
- [x] Add A.E.G.I.S. Test Lab planning, synthetic fixtures, separate package/launch approvals, a network-disabled Windows Sandbox profile, immutable input manifests, and evidence review in both products. See `docs/AEGIS-TEST-LAB.md`.
- [x] Complete live Windows Sandbox acceptance on the current Windows 11 Enterprise workstation: restricted profile launch, read-only input mapping, dedicated evidence output, and harmless PowerShell parser evidence passed on 2026-09-07.
- [ ] Provision and accept an approved offline .NET SDK/dependency image for C# compilation. Submitted scripts remain parse-only until a separately approved behavioral harness exists.
- [ ] External-system functional adapters and non-production credentials.
- [x] Add a fail-closed backend role service for exact Windows users/groups and
  enforce Supervisor/PlatformAdministrator on workflow production approval.
- [x] Bootstrap temporary full access through the exact domain group
  `BSOC\BSOC - G - Architecture` mapped to `PlatformAdministrator`.
- [x] Enforce decision-specific backend roles across monitoring and workflow
  read, design, approval, execution, acknowledgement, and configuration APIs.
- [ ] Enforce the role service across remaining privileged non-workflow APIs, add
  governed role-policy administration, replace the temporary Architecture
  mapping with least-privilege groups, and accept production group mappings.
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
- [x] Current Local AI suite: 114 tests passing on 2026-09-07.
- [x] Current deterministic release matrix: all 14 checks passing.
- [ ] Live native-agent handoff validation.
- [ ] Live MCP discovery/approval/result/failure/cancel validation.
- [x] Assess the MCP server strategy and map it into Priority 7F phases; see
  `docs/mcp-strategy-roadmap-assessment.md`.
- [x] Implement identical local MCP registry schemas, connectivity profiles,
  fail-closed validators, and registry-only `getMcpTools` discovery in both
  products; discovery grants no authority.
- [x] Add lifecycle, health/quarantine, risk/approval metadata, credential-reference schemas, local audit, destination policy, and outbound DLP foundations.
- [x] Add a current-user Windows Credential Manager broker with non-secret
  target references and safe status/set/delete tooling.
- [x] Wire protected credential targets into MOVEit and optional
  authenticated SMTP, with protected entries taking precedence over legacy
  environment values.
- [x] Resolve authenticated HTTP MCP `credentialRef` entries from protected
  `Aegis-9/MCP/<reference>` targets at request time with explicit Basic/Bearer
  mode; keep secrets out of payloads, registries, errors, and audit events.
- [ ] Remove plaintext environment fallback after migration acceptance.
- [x] Implement pinned stdio and policy-approved loopback MCP lifecycle in both
  products with initialization, discovery/calls, timeout, stop, failure limits,
  and quarantine.
- [x] Implement exact host/port, DNS/address-class, TLS, proxy, redirect, and
  profile-aware network destination policy in both products.
- [ ] Pilot pinned local/read-only MCP servers, then approved internal services;
  keep public zero-protected-data integrations optional and disabled by default.
- [ ] Build typed first-party Windows, AD, and MOVEit MCP servers after the
  shared core and lab security gates exist; never expose arbitrary shell/SQL.
- [x] Add bounded local JSONL audit/telemetry with recursive secret redaction,
  local querying, and retention compaction in both products.
- [x] Add outbound field allowlisting and DLP denial for secrets, protected
  external data, oversized payloads, and unclassified destinations.
- [x] Gate private-LAN MCP on local-network profile, organization ownership,
  TLS destination policy, role, target, outbound fields, and approval.
- [x] Add code-level air-gap readiness scripts to both products.
- [ ] Run the readiness scripts and live DMR/Ollama/native-tool/local-MCP flows
  with public networking blocked at the OS/firewall layer; retain evidence.
- [x] Persistent metadata-only dependency/import index, multi-root and unsaved context.
- [x] Diff diagnostics and secret/protected-path/conflict findings foundation.
- [ ] Complete protected-branch assistance and live fix-review workflow acceptance.
- [x] Governed rename/move/delete and multi-file rollback.
- [x] Governed C#/WPF/WinForms/PowerShell project scaffolding foundation.
- [ ] VB.NET→C#, VB.NET→PowerShell, and C#→PowerShell conversion with repair.
- [x] DMR-first tool-capable provider filtering, failover, and preflight context budgeting.
- [x] Signed-policy verification and visible policy-drift status.
- [x] CPU, memory, child-process, output, session, and MCP concurrency budgets.
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
- [x] Add bounded directory listing, terminal-output sessions, structured test
  failures, request todos, and question/answer coordination tools.
- [ ] Prove fully offline/local-only operation with external networking blocked;
  separately test explicitly enabled Copilot interoperability without adding
  Copilot to the provider failover chain.
- [x] Add offline MCP registry/lifecycle support for local process and loopback servers plus policy foundations for governed internal-company services.
- [ ] Pilot an internal-company MCP service with exact identity, capability, data-scope, credential, retention, and audit policy.
- [x] Add redacted, bounded local telemetry storage and querying.
- [ ] Add optional loopback/private OpenTelemetry collection with cloud exporters disabled, if operationally justified.
- [x] Add a shared destination-policy layer for loopback/private network tools,
  with DNS/redirect/proxy revalidation and explicit host/port allowlists.
- [x] Add outbound schema classification and DLP/redaction enforcement; prohibit
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
