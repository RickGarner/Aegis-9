# Daily workflow automation requirements

## Objective

A.E.G.I.S.-9 will provide a local-first workflow center for designing, testing,
approving, scheduling, supervising, and auditing recurring operational tasks.
Generated workflows may use PowerShell or C#, but generated code must never move
directly from an AI response into production execution.

## Command-center panel

The cinematic command center will contain a workflow panel with:

- the three most recently active workflows and their current status
- a scrollable queue of workflows awaiting user or supervisor action
- **New**, **Edit**, **Delete**, and **Approve** commands
- clear badges for draft, test, user approval, supervisor approval, schedule, and
  execution state

Selecting a workflow opens a separate supervised workflow window. Running and
monitoring workflows should show live steps, output, health, timing, and errors
when the underlying tool exposes that information.

## Authoring experience

The new-workflow window will accept a natural-language request and staged file
attachments. A.E.G.I.S.-9 will:

1. extract and analyze the supplied material
2. draft a structured plan describing triggers, inputs, actions, outputs, risks,
   required permissions, stop conditions, and expected results
3. ask focused clarification questions when material information is missing
4. incorporate the answers into a revised, versioned plan
5. generate a PowerShell or C# implementation only after plan approval
6. present generated code, dependencies, permissions, and an execution preview
   before any test is allowed

Editing creates a new immutable revision and sends materially changed code or
permissions back through testing and approval.

## Approval and promotion gates

Workflow state must distinguish these gates rather than treating approval as an
immediate start command:

`draft` -> `planning` -> `needs_clarification` -> `plan_review` -> `building` ->
`test_ready` -> `testing` -> `test_passed`/`test_failed` -> `user_accepted` or
`rejected` -> `supervisor_pending` -> `approved` -> `scheduled` -> `queued` ->
`running` -> `completed`/`failed`/`paused`/`stopped`.

- The user may accept or reject the plan, generated implementation, and test
  result.
- User acceptance does not authorize production use.
- A supervisor must approve the exact immutable revision, permission manifest,
  and schedule before production execution.
- Any material revision invalidates prior test and supervisor approvals.
- Rejecting a workflow preserves its audit history and returns it for revision or
  archival; it does not silently delete it.

## Testing and execution isolation

- Tests run only in an approved non-production profile.
- Test and production credentials, targets, working directories, and environment
  variables must be separate.
- PowerShell runs with constrained arguments and an explicit command/module
  allowlist.
- C# is built into a versioned artifact before execution; build output and hashes
  are retained with the revision.
- Network, filesystem, process, and credential access are declared in a
  permission manifest and denied unless approved.
- Cancellation, timeout, retry, output limits, and rollback/compensation behavior
  are defined before production approval.

## Scheduling and conditions

After supervisor approval, the user can define:

- one-time, daily, weekly, interval, or calendar-based triggers
- timezone and daylight-saving behavior
- reason/purpose for the schedule
- prerequisite/start conditions
- skip, delay, retry, and missed-run behavior
- maximum runtime and concurrency policy
- stop, pause, and resume conditions
- notification and escalation rules
- next eligible run after a stop condition clears

The scheduler must re-check approval, revision hash, prerequisites, and safety
policy immediately before every production run. A workflow that no longer meets
its conditions remains visible as blocked or deferred; it is not reported as a
successful run.

## Workflow windows

- **View/Run:** status, current step, live output, monitoring visualization,
  history, approvals, schedule, pause/resume/stop, and test/run controls.
- **Create/Edit:** conversational request, attachments, clarification thread,
  structured plan, generated code, revision comparison, and validation results.
- **Delete:** complete workflow identity and impact summary, schedules and active
  runs affected, typed or explicit confirmation, and a final confirmation step.
  Active workflows must be stopped safely before archival/deletion.
- **Approval:** revision hash, code diff, permissions, targets, credentials by
  reference, test evidence, risks, schedule, and accept/reject decision.

Deletion should default to recoverable archival. Permanent removal is a separate,
audited administrative operation.

## Persistence and audit requirements

Store durable, related records for workflow definitions, immutable revisions,
source attachments, clarification messages, plans, generated artifacts, test
runs, production runs, schedules, conditions, approval decisions, permission
manifests, events, and notifications. Every decision records actor, role, time,
revision, and rationale where supplied.

## Current implementation mapping

Already present:

- SQLite workflow records and basic lifecycle states
- awaiting-approval queue and basic approve/pause/resume/stop transitions
- monitor-aware active-workflow capacity and queue promotion
- native workflow status window
- staged-file attachment IDs on workflow creation
- local activity logging

Implemented in the initial interface/domain slice on 2026-08-30:

- three-recent and scrollable awaiting-action dashboard lists
- dedicated create/edit, approval, schedule, and two-step archive windows
- PowerShell/C# implementation selection and document staging in the designer
- revision increments that invalidate approval state after edits
- explicit test, user-acceptance, supervisor, and scheduling gates
- schedule capture for trigger, expression, timezone, reason, prerequisites, and
  stop conditions
- recoverable archival that refuses active workflow removal
- backend safety-gate tests
- task-aware model selection that routes plan design to the best available
  reasoning model and approved-plan implementation to the best available coding
  model
- persisted plan and implementation provider/model identity for operator review
- enforcement that implementation generation cannot occur before plan approval
- structured AI clarification questions with required/optional status and
  selectable options
- a dedicated answer window with text and selection inputs, required-answer
  validation, persisted responses, and automatic plan re-evaluation
- repeated clarification cycles until the planning model returns no unresolved
  material questions
- an explicit Workflow Design Review stage that automatically starts initial
  plan analysis, displays unresolved-question status, and withholds plan approval
  until all questions have been answered and the plan has been re-evaluated
- a persistent split-pane review surface with the plan beside its questions,
  per-question text/choice input and individual answer submission, locked
  submitted answers, and an Update Draft command enabled only after all required
  answers are stored
- mandatory tentative-plan review even when the model reports zero questions;
  only Final Submit/Update Draft can request the question-free final plan
- malformed or truncated model JSON is treated as incomplete, with unresolved
  statements converted to questions instead of allowing an approval bypass
- final plan approval automatically starts coding-model implementation and asks
  for at least two non-production test plans
- portable `.aegisworkflow` export/import with stable cross-computer identity,
  workflow lifecycle state, plans, generated implementation, clarification
  questions/answers, schedule, audit entries, and extracted attachment context
- conflict protection that refuses to overwrite an equal or newer local
  revision; imported active workflows are paused and detached from monitor slots
  until the operator explicitly resumes them

Not yet present:

- extracting generated PowerShell/C# into immutable runnable artifact files (the
  generated implementation is currently persisted for review)
- immutable revisions, permission manifests, or code signing/hashing
- test environment and user-acceptance gate
- authenticated supervisor identity and authorization (the lifecycle gate exists)
- scheduler execution, condition evaluator, and missed-run policy (schedule capture exists)
- actual workflow runner, live step/output stream, history, retry, or recovery
- workflow-specific notification/escalation delivery

## Delivery sequence

1. Expand the domain model, database migrations, lifecycle policy, and audit log.
2. Replace the compact dashboard creator with the requested workflow panel.
3. Add view, create/edit, delete, and approval windows.
4. Add AI plan/clarification/revision APIs using staged-file content.
5. Add isolated PowerShell and C# build/test runners with permission manifests.
6. Add user acceptance and independent supervisor approval.
7. Add scheduling, conditional execution, live event streaming, and history.
8. Harden cancellation, retry, recovery, secrets, notifications, and packaging.
