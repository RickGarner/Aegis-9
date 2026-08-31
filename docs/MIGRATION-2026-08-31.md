# A.E.G.I.S.-9 continuation migration — 2026-08-31

## Canonical branch

Use `feature/workflow-automation-monitoring-2026-08-31`.

This branch starts from `feature/cinematic-jarvis-ui` at commit `0beb7a7` and
adds the August 30–31 workflow automation and operational monitoring slice. The
source cinematic branch and `main` remain unchanged recovery points.

```powershell
git fetch origin
git switch feature/workflow-automation-monitoring-2026-08-31
git pull --ff-only origin feature/workflow-automation-monitoring-2026-08-31
git status --short --branch
```

## Migrated application areas

- `backend/app/main.py`, `storage.py`, and `providers.py`: workflow design,
  clarification, model routing, lifecycle gates, scheduling contract, and audit
  events.
- `desktop/Jarvis.Desktop/Workflow*`: designer, split-pane Design Review,
  approval, archive, schedule, and supervision windows.
- `desktop/Jarvis.Desktop/MainWindow*` and `MonitoringClient.cs`: Workflow Center,
  state-aware actions, and re-evaluation notifications.
- `backend/app/monitoring.py`, `config.py`, `.env.example`, and monitor UI files:
  FreeFlow Core and Qualys read-only monitoring foundations.
- `config/freeflow-servers.json` and `config/monitored-servers.json`: Xerox
  primary/secondary inventory without credentials.
- `backend/tests/`: provider routing, workflow gates, malformed-response handling,
  individual answers, and operational monitoring coverage.

## Workflow lifecycle

1. Create request and save draft.
2. A reasoning model creates a tentative plan.
3. Review is the only progression action while information is incomplete.
4. The user reviews the plan and submits each answer individually.
5. Final Submit/Update Draft unlocks only when required answers are stored.
6. A.E.G.I.S.-9 re-evaluates documents and answers.
7. Additional questions return the workflow to Review.
8. A question-free refined plan becomes available for approval/rejection and
   produces a dashboard/operator notification.
9. Plan approval automatically selects a coding model and generates the
   PowerShell/C# implementation plus at least two non-production test plans.
10. Testing/final approval precedes supervisor approval and scheduling.

Generated code is not executed in production by this slice.

## Local data intentionally excluded

Do not migrate `.env`, SQLite databases, uploads, generated artifacts, model
caches, `.venv`, build output, logs, or user preferences through Git. Exact
FreeFlow URLs, Qualys credentials, and other secrets belong in local ignored
configuration or managed secret storage.

## Verification

```powershell
py -m pytest backend/tests -q
dotnet build Jarvis.sln --no-restore
```

Verified before push on 2026-08-31:

- 18 backend tests passed
- WPF solution built with zero errors
- backend health endpoint responded successfully
- the live AD workflow was repaired from an invalid approval state to
  `needs_clarification` with two unanswered questions and no fabricated answers

## Remaining work

- Real isolated PowerShell/C# build and test runner with retained evidence
- Executable artifact hashing/signing and immutable revision storage
- Authenticated user/supervisor identities and authorization
- Production scheduler and condition evaluator
- Live execution events, cancellation, retry, recovery, and notifications
- Exact FreeFlow portal configuration and health semantics
- Exact Qualys platform/module/authentication/scope and finding enrichment
- MOVEit execution-history correlation and remote ServerMonitoring feeds
