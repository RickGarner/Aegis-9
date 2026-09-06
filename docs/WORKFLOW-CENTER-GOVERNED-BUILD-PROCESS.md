# Workflow Center Governed Build Process

All A.E.G.I.S.-9 workflows now follow the engineering procedure used for the MOVEit HA auto-failback specification.

## Mandatory sequence

1. **Initial request saved:** The user supplies instructions and documents. No code or production action is created.
2. **Read-only architecture:** A.E.G.I.S.-9 selects a qualified reasoning model. It examines the authoritative request through bounded read-only tools and creates a detailed implementation specification.
3. **Clarification review:** The user submits every required answer individually. A.E.G.I.S.-9 reevaluates the complete evidence and produces the final plan.
4. **User workflow-plan approval:** The user explicitly approves or rejects the final workflow plan. No code is built at this gate.
5. **Test-plan design and approval:** A qualified reasoning model creates multiple detailed non-production test plans. The user reviews and explicitly approves or rejects those plans. Test-plan approval authorizes the build, not testing or production.
6. **Implementation of workflow and tests:** A qualified coding model implements only the approved workflow plan and approved test plans. The resulting workflow and test artifacts enter implementation review.
7. **Non-production testing and retained evidence:** Approved tests are run through bounded profiles. Plan identity, inputs, output, pass/fail criteria, results, artifact hashes, permission manifests, and evidence hashes are retained. Failures return the implementation for revision and invalidate downstream approvals.
8. **User test-result acceptance:** The user accepts or rejects the exact tested implementation and results. Acceptance does not grant production authority.
9. **Schedule and conditions:** The trigger, purpose, timezone, start/stop conditions, prerequisites, and applicable cooldowns are recorded.
10. **User promotion request and supervisor production approval:** The user requests production promotion. An authorized supervisor independently approves the exact revision, artifact hash, permission-manifest hash, test evidence, and schedule hash.
11. **Production eligibility:** Only the bound supervisor-approved revision may be scheduled or executed. Any material edit invalidates testing and approvals.

## Automatic workflow documentation

Every lifecycle stage refreshes a user manual and appends a redacted process event:

- `Aegis-9/Workflows/<WorkflowName>_v001/USER-MANUAL.md`
- `Aegis-9/Workflows/Logs/<WorkflowName>_YYYYMMDD.log`

Revision numbers use three digits and increase after material edits. Manuals describe the purpose, approved plan, usage procedure, questions/answers status, configuration, schedule, permission boundaries, artifact identity, tests, and approvals. Logs contain timestamps and stage changes but omit workflow source, answer content, credentials, and secrets. The `Workflows` runtime tree is excluded from Git because workflow material may contain internal operational information.

## Required plan quality

Plans must separate verified facts, assumptions, and missing environment details. Where applicable they include deterministic states and safety gates, least-privilege fixed-function adapters, dry-run/observe-only rollout, audit and kill-switch behavior, failure recovery, non-production and fault-injection tests, acceptance criteria, rollback, and an operations handoff.

AI models can propose and implement workflows. They do not decide whether an ambiguous or unsafe production state is acceptable. Unknown safety state fails closed, and secrets must not be included in prompts, plans, logs, evidence, or source code.
