# Aegis-9 / Workshop.AI manual workflow test plan

Version: 1.0 — 2026-09-24  
Status: **Ready for manual execution; results not yet recorded.**  
Scope: current working-tree integration, including the fixes documented in
[WORKSHOP-INTEGRATION-PLAN.md](WORKSHOP-INTEGRATION-PLAN.md).

## 1. Objective and completion criteria

Demonstrate that an operator can enter requirements in Aegis-9, obtain plans,
test plans, and implementation from Workshop's local model, review each stage,
and retain non-production validation evidence without granting production
authority. Also verify failed, duplicate, cancelled, or outdated background
requests do not silently switch providers or overwrite the workflow.

There are two separately reportable results:

- **Integration acceptance:** correct routing, state changes, review gates,
  job handling, and persistence. All core cases must pass.
- **Generated workflow functional acceptance:** the generated script produces
  correct results for the supplied input matrix in a disposable lab. A passing
  static syntax check does not establish this result.

Record PASS, FAIL, BLOCKED, or NOT RUN for every case. A race you could not
reproduce is NOT RUN, not PASS. An unavailable SDK/model/account is BLOCKED.
Do not infer a manual pass from the earlier automated test results.

Suggested order: prerequisites -> M01–M08 (normal UI) -> M09–M12 (tracked jobs)
-> M13–M18 (failure/recovery) -> optional M19–M21 -> evidence/sign-off.
Allow roughly 2–3 hours for core testing; model speed, questions, and retries
may extend that estimate.

## 2. Important current UI behavior

| Action | Actual behavior to expect |
|---|---|
| Workflow Center **+ NEW**, then **SAVE DRAFT** | Opens design review and automatically starts initial planning. |
| Main Workflow Center review action | Opens the design-question screen for draft/design-review states; otherwise opens approval gates. The label changes with state. |
| **FINAL SUBMIT / UPDATE DRAFT** or **UPDATE DRAFT** | Requests final plan refinement; additional clarification may still be required. |
| **APPROVE WORKFLOW PLAN** | Approves the plan, then automatically requests test-plan generation. |
| **APPROVE TEST PLANS + AUTHORIZE BUILD** | Approves test plans, then automatically requests implementation generation. |
| Supervision window **Send to Workshop** | Creates a tracked background job for the selected operation. |
| Supervision window **Review** | Opens the approval window. Use the main Workflow Center review action for clarification questions. |

The automatic/direct generation requests still use Workshop while
`JARVIS_WORKSHOP_ENABLED=true`, but **do not create Workshop background-job
rows**. Empty job history is therefore expected for those requests. Confirm
their provider/model in the saved workflow or review screen instead.

Do not click a direct generation button while testing an outstanding tracked
job. Background-job duplicate prevention does not establish that every legacy
direct-generation endpoint has the same concurrency contract.

For a pending workflow without a VIEW button, use **MONITORING**, find it in
the Operations Monitoring Center workflow list, then double-click the row to
open its supervision window. That window contains the Workshop panel. Refresh
the monitoring view if needed. If a draft cannot be opened this way, record a
navigation defect; the API procedure in section 8 can still test the backend.

## 3. Prerequisites and test isolation

### 3.1 Build and runtime

1. Use a build containing the current integration fixes, not an older installed
   executable. Record its full path, timestamp, branch, and working-tree state.
2. The previously validated build output is
   `D:\AEGIS\AEGIS-9\.artifacts\workshop-integration\desktop\Aegis.Desktop.exe`.
   Confirm it exists and is the intended build; this is not an installed release.
3. Start Workshop Desktop and load a local model supporting native tool calls.
   The previously tested model was `Qwen3.5-35B-A3B-Q4_K_M.gguf`; record the
   actual model used now. Port 44245 was an observation, not a permanent value.
4. Use one backend instance on `127.0.0.1:8000`. Several workflow windows use
   this address directly. Changing only JARVIS_MONITORING_URL does not isolate
   the workflow client. Identify the existing listener before launching; do not
   attach test UI to an operational backend or terminate an unrelated process.
5. A source change alone does not update an already-running backend or desktop.
   Restart only the designated test instances after changing their configuration.

### 3.2 Separate configuration and data

Have the test application owner prepare a dedicated test instance/configuration
before starting Aegis. Retain the original operational settings unchanged.
Environment variables override settings, but unset variables may still come
from the repository `.env`; review the effective test configuration explicitly.

| Setting / resource | Test value or requirement |
|---|---|
| `JARVIS_WORKSHOP_ENABLED` | `true` except the disabled-provider case. |
| `JARVIS_WORKSHOP_LOCAL_HOST` | `127.0.0.1`; optional explicit Workshop port and exact model if needed. |
| `JARVIS_DATABASE_PATH` | A new absolute path to a dedicated test SQLite database. |
| `JARVIS_UPLOAD_DIR` | Dedicated test uploads directory. |
| `JARVIS_WORKFLOW_ARTIFACT_ROOT` | Dedicated test artifact directory. |
| `JARVIS_WORKFLOW_DOCUMENTATION_ROOT` | Dedicated test manuals/logs directory. |
| `JARVIS_TOOL_QUALIFICATION_STORE_PATH` | Dedicated test qualification JSON file. |
| `JARVIS_AUDIT_LOG_PATH`, `JARVIS_TEST_LAB_ROOT` | Dedicated test paths if those facilities are used. |
| `JARVIS_SERVER_INVENTORY_PATH` | Absolute path to a test JSON file containing `[]`. |
| `JARVIS_FREEFLOW_INVENTORY_PATH` | Absolute path to a test JSON file containing `[]`. |
| `JARVIS_SERVER_REMOTE_CIM_ENABLED` | `false`. |
| `JARVIS_MOVEIT_SERVERS` | Empty list/string in the effective settings; no operational hosts. |
| MOVEit credentials and log root | No production credentials; no production UNC log path. Use a dedicated unused test credential target and local test log directory. |
| MOVEit HA configuration/state | Test configuration and separate state path; observation-only, no operations. |
| `JARVIS_WORKFLOW_NOTIFICATION_DELIVERY_ENABLED` | `false`. |
| Monitoring SMTP | Point only to a test sink or a verified unused loopback port. Monitoring alerts have a separate send path; disabling workflow notifications alone does not disable them. |
| Developer Studio bridge | No production bridge/token. Use an unused loopback endpoint for this test if not under test. |
| Role mapping | Authorized test identity with Operator, WorkflowDesigner, and WorkflowApprover as required. Separate identities for role-denial tests. No supervisor role needed for core testing. |
| Action catalog | Keep production scope unchanged. Do not add the synthetic workflow to the production action catalog. |

An unavailable MOVEit/FreeFlow/SMTP test monitor is expected in this isolated
configuration; record it separately from Workshop failures. The application
still performs local monitoring. No global "disable all monitoring" switch is
assumed by this plan.

If this setup is not available, you can run the standalone synthetic probe in
M01, but mark desktop acceptance BLOCKED. Do not test by changing production
inventories, policies, user roles, credentials, or workflows.

### 3.3 Run record

Fill in before testing:

| Field | Value |
|---|---|
| Run ID | `WS-MANUAL-YYYYMMDD-HHMM` |
| Tester / Windows identity / effective roles | |
| Workstation / Windows version | |
| Desktop executable path / build time | |
| Backend source version / startup time | |
| Workshop version / model ID / endpoint | |
| Request timeout / response token limit / retry count | |
| Test database, artifact, upload, documentation paths | |
| Evidence directory | |
| Production integrations isolated by / date | |

## 4. Test data

Use the prefix `WS-MANUAL-<run ID>` on every workflow. Create separate workflows
for destructive-to-test-state cases such as cancellation, revision, and restart.

### Request A — complete PowerShell requirements

Name: `WS-MANUAL-<run ID>-IntegerSum`

Language: **PowerShell**

Paste this description:

```text
Create a non-production PowerShell script accepting named parameters Left and
Right, each an integer between -1000000 and 1000000 inclusive. Output exactly
one JSON object containing left, right, and sum. Preserve the original input
values. Reject nonnumeric or out-of-range input with a clear error and a
nonzero exit code. Run without interactive prompts when invoked with valid
parameters. Do not read or write files, access the network, read credentials,
use Active Directory, change services, or start another process.

Use the attached acceptance matrix. Produce a reviewable design, at least two
non-production test plans including normal and failure cases, and a single
clearly identified PowerShell implementation. Keep any separate test harness
distinct from the workflow source. Do not deploy or execute the workflow.
This is synthetic integration testing; no production access is authorized.
```

Create a UTF-8 text file named `integer-sum-acceptance.txt`, then attach it:

```text
Attachment marker: WS-MANUAL-CONTEXT-742
Output fields: left, right, sum. One JSON object per valid invocation.
Left=2, Right=3 -> sum=5
Left=-7, Right=2 -> sum=-5
Left=0, Right=0 -> sum=0
Left=1000000, Right=1000000 -> sum=2000000
Left=-1000000, Right=-1000000 -> sum=-2000000
Left=1000001, Right=0 -> reject; nonzero exit
Left=abc, Right=3 -> reject; nonzero exit
No network, directory service, filesystem, service, or credential access.
```

The unique marker helps verify attachment retrieval. A correct plan may use
the attached requirements without repeating the marker; record evidence of
the distinctive boundary/error cases rather than demanding an exact sentence.

### Request B — deliberate clarification

Name: `WS-MANUAL-<run ID>-Clarification`

```text
Create a local script that adds two numbers. Before finalizing, ask me to
choose the input format and the output format. These are unresolved requirements;
do not assume answers. Do not access files, network, credentials, or production.
```

Answer input questions with **two named integer parameters Left and Right**.
Answer output questions with **one JSON object containing left, right, sum**.
If choices differ, choose the equivalent option and record its exact wording.

## 5. Normal desktop process — core cases

### M01 — Workshop discovery and tool readiness

1. From the repository root in PowerShell, run:

   ```powershell
   .\.venv\Scripts\python.exe scripts/validate-workshop-local.py
   .\.venv\Scripts\python.exe scripts/validate-workshop-local.py --generate
   ```

2. Save both terminal outputs and exit codes.
3. Confirm `available=true`, `provider=workshop`, `location=local`, and the
   intended loaded model. Inspect the endpoint in the detail.
4. In the generation result, confirm `read_synthetic_request` was executed and
   the model returned a plan using its result.

**Expected:** both commands exit 0. The second validates ordinary chat, native
tool qualification, and tool-result continuation. It does not start Aegis
monitoring or use its database. It ignores `.env`; use `--port` / `--model`
explicitly if testing a pinned configuration.

**Evidence:** JSON output, model/endpoint, exit codes. If this fails, investigate
before relying on desktop workflow generation.

### M02 — Startup, draft, and attachment intake

1. Launch the designated test backend/desktop. Confirm session restoration does
   not fail with missing `/api/session`; monitoring has no duplicate-route error.
2. In **WORKFLOW CENTER**, select **+ NEW**.
3. Enter Request A, choose PowerShell, and use **UPLOAD DOCUMENTS** to attach
   `integer-sum-acceptance.txt`. Verify its name appears before saving.
4. Select **SAVE DRAFT**. Record the workflow ID/revision using section 8 if
   the UI does not display the ID. Wait for automatic design generation.

**Expected:** exactly one workflow is created, the attachment is retained, and
the design-review screen opens. State progresses from `draft` to
`design_review` or `needs_clarification`. Do not expect a background job row.

**Evidence:** entered requirements, attachment list, saved ID/revision,
planning provider/model, initial plan or complete error.

### M03 — Review content and final submission

1. Inspect the tentative plan. Check named inputs, range, JSON output, error
   behavior, attached boundary cases, and absence of production side effects.
2. If questions are present, submit each required answer. Otherwise select
   **FINAL SUBMIT / UPDATE DRAFT**. With answered questions, select **UPDATE DRAFT**.
3. Wait for final refinement, then reopen the workflow review from the main
   Workflow Center.

**Expected:** a complete plan reaches `plan_review`; unresolved questions may
instead return to clarification. Approval is unavailable until review is
complete. The saved planning provider is `workshop`, with the intended model.
Requirements must not silently disappear during refinement.

**Evidence:** tentative/final plans, state transition, provider/model, any
clarification cycle. A model inventing production access is a content failure.

### M04 — Approve plan and generate test plans

1. In final plan review, select **APPROVE WORKFLOW PLAN**.
2. First decline the confirmation and verify no state or content changes.
3. Repeat and approve after reviewing the plan. Wait for the automatic test-plan
   generation; do not also use Send to Workshop.

**Expected:** `plan_approved` followed by `test_plan_review`. If generation
fails, `plan_approved` may remain and **DESIGN TEST PLANS** provides a retry path.
At least two meaningful test plans cover valid inputs, failures, isolation,
expected results, evidence, and cleanup. No implementation or execution approval
is granted by this step. Some confirmation wording mentions building code;
the actual expected next stage is test-plan generation.

**Evidence:** confirmation behavior, saved test plans, test-plan provider/model.

### M05 — Approve tests and generate implementation

1. Review the test plans against the attached matrix.
2. Select **APPROVE TEST PLANS + AUTHORIZE BUILD**; first decline, then repeat
   and approve. Wait for automatic implementation generation.
3. Review the returned code and distinguish workflow source from proposed tests.

**Expected:** `test_plan_approved` then `implementation_review`. If generation
fails, **BUILD WORKFLOW + TESTS** is available from `test_plan_approved`.
Implementation provider/model identify Workshop. The code meets the approved
scope; no run, schedule, supervisor approval, or deployment is created.

**Evidence:** implementation text, provider/model, revision, consent behavior,
any tool/output errors. A response that only describes code without supplying
a usable implementation fails this case.

### M06 — Static test and evidence retention

1. In implementation review, select **SUBMIT FOR TEST**.
2. Confirm state `test_ready` and choose **Static validation (recommended)**.
3. Select **RUN SAFE TEST** and wait for the result.
4. Inspect artifact SHA-256, evidence SHA-256, permission manifest, status,
   summary, and retained output/error information.
5. Reopen the review and confirm the same evidence is retained.

**Expected:** syntactically valid PowerShell reaches `test_passed`; invalid
source reaches `test_failed` with useful evidence. Static validation parses
the script; it does not execute the acceptance matrix. Missing hashes or a
success status for a parser failure is a defect.

**Evidence:** hashes, profile, status, exit code where available, parser errors,
test-result document and artifact path. If valid code was not generated,
record the upstream content failure and the correct test failure separately.

### M07 — User acceptance and production boundary

1. After a passed static test, review the scope of that evidence.
2. Select **USER ACCEPT** only as acceptance of this synthetic integration test,
   recording that business behavior is still unverified unless M19 was run.
3. Confirm `user_accepted` and retain a screenshot. Stop before
   **REQUEST SUPERVISOR**, scheduling, and production **Run**.

**Expected:** no supervisor approval, scheduled execution, or production run.
The generic IntegerSum workflow is not an enabled production action profile.
The production catalog currently targets the separate AD account-lockout
workflow; do not expand it to make this acceptance test run.

### M08 — Required clarification and persistence

1. Create Request B as a separate workflow.
2. Verify questions are presented for the unresolved input/output requirements.
3. Attempt an empty answer; then submit only one required answer.
4. Confirm final submission remains locked while another required answer is
   missing. Close/reopen design review and verify the saved answer persists.
5. Submit the remaining answer and choose **UPDATE DRAFT**.

**Expected:** empty answers are refused; required questions cannot be bypassed;
refinement incorporates both answers. If the model supplies no questions despite
this explicit request, record a clarification-generation failure, not a pass.

## 6. Tracked Workshop background jobs — core cases

These cases isolate the new queue. The ordinary approval UI auto-generates the
next stage, so M11/M12 use a **manual API approval** to pause at the intermediate
approved state. Those API calls record normal approvals and enforce the same
backend role checks; they do not edit the database or bypass policy.

### M09 — Queue a design job and retain provenance

1. Create another Request A workflow. Allow initial automatic planning to finish,
   then close its review. Use **EDIT** and **SAVE DRAFT** to create a new draft
   revision. Reattach the test document if needed: the editor does not currently
   repopulate its upload list from saved attachment IDs.
2. Do not reopen direct design review yet. Open **MONITORING** and double-click
   this workflow in its workflow list to reach supervision.
3. Select **Design plan** -> **Send to Workshop**. Record the new job ID.
4. Observe queued/running/completed, using **Refresh** or the approximately
   15-second refresh cadence. A fast job may skip visible intermediate states.
5. Inspect the saved plan via the main Workflow Center review action.

**Expected:** one job for this workflow/revision/operation, completed status,
actual `workshop` provider/model, saved plan in `design_review` or
`needs_clarification`. No automatic approval. The job's retained response and
workflow content agree. Evidence: job history JSON plus UI screenshot.

### M10 — Reject invalid stage requests

1. On a draft/design-review workflow, choose **Implementation** and send.
2. Repeat with **Test plans** before final plan approval.

**Expected:** descriptive stage/approval error (backend HTTP 409); no new job,
no implementation/test-plan overwrite, and no approval granted. A healthy
Workshop preflight can occur first. Confirm job counts before/after.

### M11 — Queue test plans after a manually recorded approval

1. Complete M09's clarification/final-refinement process to `plan_review`.
2. Inspect the final plan. In PowerShell, use section 8 to approve only that
   test workflow with decision `approve_plan`.
3. Verify state `plan_approved`. Do not press the direct **DESIGN TEST PLANS**.
4. In supervision, select **Test plans** -> **Send to Workshop**.

**Expected:** a distinct tracked job completes, test-plan provenance is
Workshop, and state becomes `test_plan_review`. No implementation yet.

### M12 — Queue implementation after test-plan approval

1. Review M11's test plans. Use section 8 with decision `approve_test_plan`.
2. Verify state `test_plan_approved`.
3. Select **Implementation** -> **Send to Workshop**.
4. Wait for completion, inspect implementation, and repeat static validation M06.

**Expected:** completed job with actual provider/model and retained response;
workflow reaches `implementation_review`, then testing progresses only through
explicit review actions. Job selection/errors remain visible separately from
production execution output. No production run occurs.

## 7. Failures and recovery

Use fresh disposable drafts. Never interrupt another operator's model session.
Only stop/restart Workshop or Aegis instances dedicated to this acceptance run.

### M13 — Duplicate submission (core)

1. Start a tracked design job. While it is running, attempt a second submission
   for the same workflow, from a second supervision window or section 8.
2. Inspect both responses and the job list.

**Expected:** second submission refused with conflict; at most one queued/running
job. If the first completed before the second submission, the race was not
tested: repeat or mark NOT RUN. Do not confuse two sequential valid jobs with
a duplicate-concurrency defect.

### M14 — Cancel a running job (core)

1. Save the workflow's existing plan text/revision. Submit tracked design work.
2. While the job is queued/running, select it and click **Cancel job**.
3. Wait at least the configured per-request timeout plus one UI refresh after
   cancellation, then inspect the saved workflow and job again.
4. Confirm the action changes to **Retry job**. Retry unchanged input and allow
   the new job to finish.

**Expected:** cancelled job remains cancelled; no late generated result changes
the workflow. Retry creates a new job ID and preserves the original history.
If completion won the race, cancellation should be refused; repeat the case.
Do not require immediate GPU idleness: cancellation does not prove server-side
inference termination or undo already completed bounded workspace tools.

### M15 — Revise while generation is running (core)

1. Start a tracked design job and record revision N.
2. While it runs, use the main Workflow Center **EDIT**. Change the description
   to include the unique text `REVISION-NEXT-DO-NOT-OVERWRITE`, then save.
3. Do not start another generation until the first settles. Refresh the job
   and workflow; inspect text, revision, and approvals.

**Expected:** workflow remains revision N+1 with the new requirements and
invalidated old approvals. The old job fails/stales instead of committing its
result. Retrying that old-revision job is refused. A fresh request for N+1 can
be submitted. Record NOT RUN if the original job finished before the edit.

### M16 — Workshop unavailable and recovery (core)

1. With no unrelated work running, unload the test model or close the dedicated
   Workshop instance. Leave any unrelated provider unchanged.
2. Submit from the Workshop panel. Check `/api/workshop/status` and job history.
3. Reload Workshop/model and submit again; if automatic discovery is used,
   confirm the new port can be discovered after restart.

**Expected:** preflight reports unavailable and normally creates no job. If the
model disappears after preflight, a queued job may fail instead. Neither case
silently uses DMR/Ollama/LM Studio. Recovery succeeds with the intended Workshop
model. An explicitly pinned old port must be updated and the test backend
restarted; automatic discovery is not expected to override that pin.

### M17 — Inference failure and retry (core)

1. Start a tracked design job, then interrupt only the dedicated Workshop model
   runtime while the request is outstanding.
2. Wait for the job to settle, accounting for configured retries/timeouts.
3. Capture the error, reload the model, select the failed job, and **Retry job**.

**Expected:** useful failure detail is retained; no partial result is approved
or substituted by another provider. Retry has a new ID and finishes normally
when prerequisites are restored. A shorter test-only timeout may be used to
reproduce this, with its exact value recorded and restored afterward.

### M18 — Backend restart with outstanding job (core)

1. Start a tracked job and verify queued/running state.
2. Stop only the designated test backend, then restart with the same test DB.
3. Inspect the job, workflow, and ability to retry.

**Expected:** a graceful shutdown may mark work cancelled; abrupt termination
or an unstarted queued task is recovered as failed. Accept either honest
terminal state with explanatory evidence. Nothing remains indefinitely
queued/running, silently resumes, or fabricates completion. Repeat for abrupt
termination only if necessary in the disposable test instance. If the job
completed before shutdown, the interruption case is NOT RUN.

### M19 — Generated script functional behavior (separate functional acceptance)

1. Review the exact retained PowerShell artifact from M06/M12. Verify its hash
   matches the retained evidence. Copy only reviewed synthetic artifacts into a
   disposable lab/VM with no production credentials/network.
2. Invoke the script with each row of the attachment matrix. Example inside
   that disposable environment, using the artifact's real filename:

   ```powershell
   powershell.exe -NoProfile -NonInteractive -File .\workflow.ps1 -Left 2 -Right 3
   $LASTEXITCODE
   ```

3. Record stdout, stderr, exit code, and JSON field values for every row.

**Expected:** exact sums and input fields on valid cases; nonzero exit with
clear failure on invalid cases; no prohibited side effects. Mark functional
acceptance separately from integration acceptance. Test Lab's PowerShell
parser alone does not run this matrix. The restricted workflow profile may
correctly block parameterized/generated scripts because its allowed syntax
is deliberately narrow; do not weaken policy to make it pass.

### M20 — Configuration/qualification failures (extended)

Run each variation only in the test configuration, restarting the test backend
when required. Restore the original test values between variations.

| Variation | Expected |
|---|---|
| Workshop disabled; submit using section 8 | HTTP 503, no job. General chat may use generic providers, but a Workshop-labelled job must not. |
| Pin a nonexistent model ID | Unavailable; no substitution with another model. |
| Pin a verified unused loopback port | Unavailable; no other-provider fallback. |
| Two discoverable Workshop model routes, no selection | Ambiguity message; specify port/model rather than arbitrary selection. Mark BLOCKED if the runtime cannot host this scenario. |
| Model that chats but lacks native tool calls | Chat may succeed; design/implementation fail qualification with no workflow tool execution. Test-plan text generation alone is not proof of tool capability. |
| Non-loopback host or invalid port | Configuration rejected; no connection made to that host. |

Qualification results are cached by model/endpoint. To test a changed capability,
use a new test-only qualification-store path and restart instead of deleting
shared cache files. These are negative tests, not reasons to disable qualification.

### M21 — Role denial, UI, and retained state (extended)

1. With an independently configured test identity lacking design capability,
   attempt queue/retry; expect HTTP 403. A backend uses its Windows process
   identity, so changing a UI label does not change the authenticated identity.
2. With a designer lacking approval capability, attempt plan approval; expect
   refusal. Restore the authorized test identity for the successful path.
3. Select an older failed job, wait through refresh, and verify selection and
   error details remain. Check Retry/Cancel labels and completed-job disabling.
4. Resize to minimum supported window size; verify controls, errors, and model
   details are readable. Reopen the application and confirm saved state persists.
5. Export a synthetic workflow for evidence; verify requirements, content, and
   provenance match. Do not assume workflow export includes the separate job
   table; retain job-history JSON separately.

## 8. Optional manual API observation and controlled approvals

Use these commands only against the isolated test backend. They are manual
test steps, not a request to run anything against the operational instance.
Find the test workflow by its unique title before setting its ID.

```powershell
$testApi = 'http://127.0.0.1:8000'
Invoke-RestMethod "$testApi/api/workshop/status"
Invoke-RestMethod "$testApi/api/workflows" |
    Select-Object id, title, revision, state, plan_provider, plan_model

# Replace 123 with the ID of your synthetic test workflow.
$testWorkflowId = 123
$testWorkflow = Invoke-RestMethod "$testApi/api/workflows/$testWorkflowId"
$testWorkflow | ConvertTo-Json -Depth 30
Invoke-RestMethod "$testApi/api/workflows/$testWorkflowId/workshop-jobs" |
    ConvertTo-Json -Depth 30
```

For M11, after personally reviewing the plan in `plan_review`:

```powershell
$approvalBody = @{ decision = 'approve_plan' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$testApi/api/workflows/$testWorkflowId/review" `
    -ContentType 'application/json' -Body $approvalBody
```

For M12, after personally reviewing the test plans in `test_plan_review`, use
the same request with `decision = 'approve_test_plan'`. Do not use
`supervisor_approve` in this test plan.

To reproduce queue races or test without the supervision window:

```powershell
$jobBody = @{ operation = 'design_plan' } | ConvertTo-Json
$queuedJob = Invoke-RestMethod -Method Post `
    -Uri "$testApi/api/workflows/$testWorkflowId/workshop-jobs" `
    -ContentType 'application/json' -Body $jobBody
$testJobId = $queuedJob.job.id
Invoke-RestMethod "$testApi/api/workshop-jobs/$testJobId"

# Run only when performing the cancellation case.
Invoke-RestMethod -Method Post -Uri "$testApi/api/workshop-jobs/$testJobId/cancel"

# Run only after reviewing a failed/cancelled current-revision job.
Invoke-RestMethod -Method Post -Uri "$testApi/api/workshop-jobs/$testJobId/retry"
```

Valid operation values are `design_plan`, `test_plans`, and `implementation`.
PowerShell reports non-2xx responses as errors; retain the HTTP status and
response detail instead of interpreting the terminal exception as a test crash.
Do not modify database rows to force a state transition.

## 9. Evidence, troubleshooting, and sign-off

For each case retain: case ID, workflow ID/revision, job ID where applicable,
starting state, action time, ending state, provider/model, relevant screenshots,
full error/status, and PASS/FAIL/BLOCKED/NOT RUN. Export only synthetic data.
Never include credentials or the complete operational `.env` in evidence.

Useful evidence locations: configured workflow documentation root (manuals,
process logs, TEST-RESULTS.md), artifact root (source/manifest/evidence), job APIs,
and backend stdout/stderr. The desktop-owned backend normally writes logs under
`backend/logs`; a manually launched backend may instead log to its terminal.

| Symptom | First checks |
|---|---|
| No local model found | Workshop model loaded; process ancestry accessible; correct explicit port/model; backend restarted after configuration change. |
| Chat works but plan fails | Native tool-qualification failure; exact model/endpoint; qualification evidence. |
| Model can produce a plan but output is incomplete | Response token limit, timeout, response content, model capability; do not approve an incomplete artifact. |
| No job row after approval | Normal direct/UI generation path; inspect saved provider/model. Use M09–M12 for queue coverage. |
| Request gets 403 | Windows identity running the backend and the test role mapping. |
| Request gets 409 | Workflow stage, required approval, active job, or obsolete revision. |
| Job says cancelled but GPU remains active | Check that no late workflow write occurred; server-side GPU abort is not guaranteed. |
| Static test passes but wrong arithmetic | Integration/parser success; functional/content failure. Run M19 and record separately. |
| Restricted test is blocked | Inspect permission manifest; parameterized scripts can be outside its supported syntax. |

### Execution record (copy one row per case)

| Case | Workflow / revision | Job | Expected vs actual | Result | Evidence / defect ID |
|---|---|---|---|---|---|
| M01 | N/A | N/A | | NOT RUN | |
| M02–M08 (expand to individual rows) | | | | NOT RUN | |
| M09–M18 (expand to individual rows) | | | | NOT RUN | |
| M19 | | | | NOT RUN | |
| M20–M21 (expand by variation) | | | | NOT RUN | |

### Defect template

```text
Defect ID / case:
Build, model, endpoint:
Workflow ID, revision, job ID:
Starting state and exact reproduction steps:
Expected result:
Actual result and HTTP/error detail:
Did requirements/content/approval state change incorrectly?
Evidence files:
Reproduced count / attempts:
Severity: critical / major / minor
```

Critical examples: unauthorized execution, silent non-Workshop routing for a
Workshop job, or a stale/cancelled result overwriting a workflow. Major examples:
valid workflow creation blocked, lost requirements, or unusable error/retry
behavior. Minor examples: cosmetic issues that do not hide required actions.

### Exit and cleanup

- Core M01–M18 pass, or each blocked/not-run case has an explicit owner and
  retest plan. No critical/major defect is silently waived.
- M19 has its own functional-acceptance result; optional cases are explicitly
  reported rather than included in an unqualified "all tests passed" statement.
- Record reviewer, date, integration verdict, functional verdict, and open
  defects in [the integration tracker](WORKSHOP-INTEGRATION-PLAN.md).
- Retain evidence before archiving test workflows through the UI. Stop only
  test instances, restore test-only configuration changes, and verify no jobs
  remain active. Do not delete shared runtime directories or operational data.

## 10. Source references used to prepare this plan

- `desktop/Aegis.Desktop/MainWindow.xaml` and `.xaml.cs`: entry points and automatic design opening.
- `WorkflowDesignReviewWindow.xaml.cs`: questions and final-refinement behavior.
- `WorkflowApprovalWindow.xaml.cs`: automatic test/implementation generation after approval.
- `WorkflowWindow.xaml` and `.xaml.cs`: tracked jobs, status, refresh, retry/cancel.
- `OperationsMonitoringCenterWindow.xaml.cs`: opening supervision for pending workflows.
- `backend/app/main.py`, `providers.py`, `storage.py`: endpoints, routing, queue lifecycle, commit guards.
- `backend/app/workflow_runner.py`: static/restricted profile limits.

This document describes expected behavior based on source inspection. Creating
it did not execute any manual case, restart services, or change application code.
