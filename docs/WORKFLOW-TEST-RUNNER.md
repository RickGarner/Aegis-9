# Workflow artifact and test runner

## Implemented safety boundary

A.E.G.I.S.-9 converts only fenced `powershell`, `ps1`, `csharp`, `cs`, or `c#`
source from an approved generated implementation into a versioned artifact. The
source and its permission manifest are stored under the git-ignored
`storage/workflow-artifacts/<transfer-id>/revision-<n>/<sha256>/` path. Existing
content at that hash must match exactly; otherwise preparation fails.

Every retained test run records the workflow revision, source SHA-256, profile,
permission manifest, exit code, bounded stdout/stderr, duration, status, summary,
and an evidence SHA-256 in SQLite. A workflow cannot reach `test_passed` through
a manual button; it requires retained evidence with status `passed`.

## Profiles

### Static validation (default)

- PowerShell uses the PowerShell parser without invoking the generated script.
- C# is placed in a fixed SDK-style project and built for .NET 8.
- Both processes have a bounded timeout, bounded captured output, a dedicated
  artifact working directory, and a minimal environment.

This validates syntax/buildability. It does not prove that external systems,
business behavior, credentials, UI integration, or production conditions work.

### Restricted local execution

PowerShell execution is available only when the generated permission manifest
contains no external capabilities and all detected commands are on the small
test allowlist. It runs in PowerShell Constrained Language mode, in the artifact
directory, with a minimal environment and enforced timeout/output limits.

The runner blocks restricted execution when it detects network/remote sessions,
filesystem mutation, process/service control, Active Directory operations,
credentials, absolute/UNC paths, long-running loops/delays, or unapproved
commands. C# restricted execution is blocked until an approved OS-level sandbox
is integrated; C# static build validation is available now.

Static analysis is defense in depth, not a perfect security boundary. Generated
code requesting external capabilities must be revised and tested later through
an approved disposable VM/Windows Sandbox profile with dedicated non-production
credentials and targets.

## Workflow lifecycle

1. `implementation_review`: operator reviews generated content.
2. `SUBMIT FOR TEST`: source is extracted, hashed, and permission-scanned.
3. `test_ready`: operator selects Static or Restricted profile.
4. `RUN SAFE TEST`: workflow enters `testing` and evidence is retained.
5. Passed evidence moves to `test_passed`; blocked, failed, or timed-out evidence
   moves to `test_failed`.
6. User acceptance becomes available only after `test_passed`.

This runner does not itself authorize production execution. After a static or
restricted test passes, user acceptance, an approval-bound schedule, and a
configured Windows supervisor identity are still required. The separate
production execution manager re-hashes the artifact, manifest, and schedule,
checks the explicit `config/workflow-actions.json` action profile, and retains a
run ledger, ordered output events, stdout/stderr, terminal evidence hash,
cancellation, timeout, retry, restart recovery, and a notification outbox entry.

Production execution is default-deny. A workflow type absent from the action
catalog, a changed hash, an unapproved command/capability, or an unconfigured
supervisor identity blocks launch. C# production execution remains blocked until
an approved disposable Windows sandbox profile is installed and cataloged.
