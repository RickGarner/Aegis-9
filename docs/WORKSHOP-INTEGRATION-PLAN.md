# Aegis-9 / Workshop.AI integration work tracker

Started: 2026-09-24. Scope: current working tree on
`feature/workflow-automation-monitoring-2026-08-31`.

## Intended behavior and ownership

An operator enters a workflow in Aegis-9 and requests a design plan, test plans,
or implementation using Workshop's local model runtime. Aegis retains the
workflow, clarification loop, tools, review stages, approvals, tests, and
production-execution policy. Generated content is a draft, never production
authorization.

The existing integration calls an OpenAI-compatible llama-server endpoint.
It does not submit a project to Workshop's own application-level job engine.
No supported Workshop application-level job API has been established from the
inspected repository. Its availability is UNKNOWN. Complete and validate the
existing local-model integration without inventing such an API.

## Baseline findings

- Desktop already has Send to Workshop and three generation operations.
- Backend persists jobs and a transfer snapshot, then calls Aegis generation
  functions. The snapshot is retained locally, not posted as a Workshop job.
- Workshop discovery returns a boolean instead of the provider health contract
  and does not populate routes used by tool-assisted planning/implementation.
- Discovery picks the first llama-server process without verifying ownership;
  it ignores configured host/port and can choose the wrong local model.
- Workshop-labelled job endpoints use the generic provider dependency and can
  use another provider when Workshop is disabled.
- Tool qualification exists in the shared provider but is not correctly wired
  to Workshop. Chat success alone is insufficient acceptance evidence.
- Cancellation changes a database label without stopping the generation task.
  Current revision is checked at claim time, not atomically at result commit.
- Duplicate active jobs, queued-job restart recovery, actual provider/model
  provenance, and stale/cancelled result handling need lifecycle validation.
- The desktop refresh can overwrite a Workshop failure message and reset job
  selection. Readiness and operation eligibility need clearer presentation.
- An unrelated but integration-blocking session route is misregistered at the
  monitoring URL; the desktop expects `/api/session`.

## Completion plan

| ID | Work | Acceptance | Status |
|---|---|---|---|
| W1 | Correct Workshop routing, endpoint selection, health and tool qualification; prohibit other-provider fallback | Mock HTTP tests cover plain chat and multi-turn tools, unavailable/ambiguous runtime, malformed responses, and disabled integration | Implemented; automated and live inference checks passed |
| W2 | Make background jobs cancellable and revision-safe; validate stages before queueing; record actual route; handle duplicate jobs/restarts | Delayed-response tests prove cancelled/stale results cannot change a workflow; retries preserve review gates | Implemented; focused tests passed |
| W3 | Complete desktop readiness/progress/error presentation and repair session endpoint prerequisite | Focused API tests and desktop build; operator can see failure and retry the selected job | Implemented and compiled; visual/operator acceptance pending |
| W4 | Validate against the installed Workshop runtime using synthetic data | Record exact endpoint/model, qualification evidence, design -> clarification/review -> test-plan review -> implementation; no production execution | Discovery, chat, qualification, and tool-assisted planning passed; full operator sequence pending |
| W5 | Final regression and handoff | Relevant backend tests, desktop validation, configuration instructions, and acceptance evidence recorded here | Initial regression/build passed; final release acceptance pending W3/W4 |

## Validation boundaries

Use temporary databases, artifact directories, qualification stores, and mocked
HTTP in automated tests. Do not launch the normal backend merely to test it:
startup can poll configured production monitoring endpoints. Live acceptance
must use an isolated configuration and harmless synthetic workflows. Do not
read or log credentials. Do not commit or overwrite pre-existing work.

## Change and validation log

- 2026-09-24: added [the detailed manual test plan](WORKSHOP-MANUAL-TEST-PLAN.md)
  with 21 cases, synthetic requests/attachment data, UI and tracked-job paths,
  controlled API steps, expected state transitions, evidence templates, and
  separate functional acceptance. Source inspection confirmed automatic
  generation after UI approvals; these direct calls do not create queue rows.
  Manual cases remain NOT RUN; this documentation update did not change code.
- 2026-09-24: inspected repository identity, branch, status, provider methods,
  desktop handlers, queue/storage code, and existing tests. Existing Workshop
  work is modified/untracked and will be preserved. No test results yet.
- 2026-09-24: created this plan before implementation. Running Workshop and
  multiple llama-server processes were observed; ownership/model/port selection
  and end-to-end operation are not yet validated.

### Implementation completed in this work session

- Replaced the incomplete Workshop provider discovery/chat implementation with
  route registration compatible with the shared chat and native tool loop.
  Discovery now returns ProviderHealth, honors configured endpoint/model,
  validates loopback configuration, verifies Workshop process ancestry during
  automatic discovery, and rejects ambiguous routes. No other-provider fallback.
- Added Workshop-specific queue/retry dependencies; disabled Workshop cannot
  create misleading jobs serviced by another provider.
- Added task tracking/cancellation and backend shutdown cleanup. Added
  submission-stage checks and transactional prevention of duplicate active jobs.
- Added task-scoped storage guards. Before committing generated content, a
  write transaction checks job status, workflow revision, and the saved input
  snapshot, including same-revision approval/clarification changes. Workflow
  content and completed job/provider/model are committed together. Cancelled
  or stale results are rejected. Pre-start stale jobs are failed explicitly.
- Restart recovery now includes queued jobs. Retry still requires current
  workflow revision and valid approval stage. It never grants approval.
- Corrected the design-review save-state mismatch and restored `/api/session`
  instead of the accidental duplicate monitoring-route registration.
- Added a Workshop status area, preserved selected jobs across refresh, retained
  errors separately from execution output, made Retry/Cancel labels accurate,
  checked readiness before sending, and wrapped controls to fit the panel.
- Added configuration examples, setup/runbook documentation, automated provider
  and lifecycle tests, and a synthetic live validation script.

### Evidence

- Initial new async tests could not run because this virtual environment lacks
  pytest-asyncio. Tests were adapted to the already-installed AnyIO plugin with
  the asyncio backend; no dependencies were installed or changed.
- Focused routing/job tests: 38 passed. Expanded lifecycle checks: 62 passed.
- Regression command covered Workshop provider/jobs/execution, provider router,
  workflow automation/agent tools/implementation tools/lifecycle/transfer, and
  API authorization: 92 passed before the final diagnostic/concurrency changes.
- Final rerun after those changes: **93 passed in 9.71 seconds**. Reproduce with
  `.venv/Scripts/python.exe -m pytest` and the ten test modules listed above
  (`test_workshop_provider.py`, `test_workshop_jobs.py`,
  `test_workshop_execution.py`, `test_provider_router.py`,
  `test_workflow_automation.py`, `test_workflow_agent_tools.py`,
  `test_workflow_implementation_tools.py`, `test_workflow_lifecycle.py`,
  `test_workflow_transfer.py`, `test_api_authorization.py`, all under
  `backend/tests`).
- Desktop build: `dotnet build desktop/Aegis.Desktop/Aegis.Desktop.csproj
  --no-restore -p:OutputPath=D:\AEGIS\AEGIS-9\.artifacts\workshop-integration\desktop\`
  succeeded, zero errors. Two CS0067 warnings reference the pre-existing unused
  WakePhraseRecognized event (temporary WPF project and final project).
- Live `scripts/validate-workshop-local.py --generate`: exit 0. Automatically
  selected Workshop-owned PID 33664, port 44245, model
  `Qwen3.5-35B-A3B-Q4_K_M.gguf`. Another observed llama-server belonged to
  LM Studio and an independent server had no Workshop ancestry; neither was
  selected. PIDs/ports are observations, not deployment constants.
- Live chat returned `AEGIS_WORKSHOP_LOCAL_OK`. Native two-step qualification
  and continuation succeeded. The model called `read_synthetic_request` once,
  received synthetic input, and returned a plan describing an Add-Numbers
  PowerShell function. The validation executor exposed only that harmless read
  tool; no generated code or production workflow was executed.
- Repository-wide `git diff --check` reports whitespace in pre-existing edits
  (including unrelated FreeFlow/Test Lab changes). No unrelated formatting was
  performed. This is not reported as a clean repository-wide check.

### Remaining work / acceptance limits

1. Run and record the complete operator-driven desktop sequence described in
   [the setup guide](WORKSHOP-INTEGRATION-SETUP.md). Includes clarification,
   final-plan review, test-plan generation/review, implementation generation,
   non-production evidence, cancellation/retry, and UI visual inspection.
2. Validate endpoint rediscovery after Workshop restart/model reload and
   sustained larger workflow generation on the target workstation. Automatic
   discovery needs readable process ancestry; explicit configuration is the
   documented fallback. This is process discovery, not cryptographic identity.
3. Validate packaging on another workstation and choose operational timeout /
   response-token settings for larger workflows.
4. If Workshop itself must own project orchestration, establish its supported
   application-level API and add a separately specified adapter. Current work
   intentionally retains Aegis orchestration with Workshop local inference.

Cancellation disconnects/cancels Aegis work and blocks result persistence; it
does not guarantee immediate model-server GPU abort or rollback of already
completed bounded workspace tools. No service was restarted or redeployed, no
production workflow was run, and no Git branch/commit changes were made.

### Files changed by this session

Existing modified files updated narrowly: `backend/app/providers.py`,
`backend/app/config.py`, `backend/app/main.py`, `backend/app/storage.py`,
`desktop/Aegis.Desktop/MonitoringClient.cs`, `WorkflowWindow.xaml`,
`WorkflowWindow.xaml.cs`, and `.env.example`. `README.md` received documentation
links. Existing untracked `test_workshop_jobs.py` was retained unchanged.

New files: this tracker, `docs/WORKSHOP-INTEGRATION-SETUP.md`,
`backend/tests/test_workshop_provider.py`,
`backend/tests/test_workshop_execution.py`, and
`scripts/validate-workshop-local.py`.
