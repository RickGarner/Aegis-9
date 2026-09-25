# Pre-test GitHub synchronization

The pre-test snapshot includes the pending application, configuration, integration,
diagnostic script, test, and documentation changes on
`feature/workflow-automation-monitoring-2026-08-31`.

## Publication preparation

- Added ignore rules for local build, publish, review, browser automation, Python
  package metadata, and debug runtime output directories. These files remain local.
- Removed hardcoded passwords from eight MoveIT credential, failback, and monitoring
  scripts. Set `AEGIS_MOVEIT_PASSWORD` in the invoking process before running them;
  scripts with a `-Password` parameter still accept an explicitly supplied value.
  Missing credentials now stop those scripts before remote operations.
- Removed password interpolation from the monitoring script's suggested command.
- Preserved original diagnostic scripts under the ignored
  `.artifacts/private-pre-push-backup/` directory. That directory contains sensitive
  local material and must not be uploaded or shared.
- Checked the pending files and the two previously unpushed commits for the
  discovered password; no remaining occurrences were found in that publishable set.

## Validation and testing status

The Workshop and related backend regression run previously passed 93 tests, and
the Release desktop build succeeded with two existing unused-event warnings.
The deployment and its validation are recorded in `PUBLISH-2026-09-24.md`.
Manual workflow acceptance remains pending; use `WORKSHOP-MANUAL-TEST-PLAN.md`.
Credential cleanup affects repository diagnostic scripts, not the published
application binaries. No MoveIT diagnostic or failback operations were executed
as part of this synchronization.

All eight modified diagnostic scripts passed PowerShell parser checks after
correcting two existing variable-before-colon interpolations in the monitoring
script. These were syntax checks only; remote operations were not run.
