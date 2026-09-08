# Codex Review Checklist — AEGIS 9 FreeFlow Core

Use this checklist before any `-Apply` execution.

## Repository compatibility

- [ ] Confirm the active repository, branch, and commit SHA.
- [ ] Confirm working tree state and review all local modifications.
- [ ] Confirm the current FastAPI entry point.
- [ ] Confirm the FastAPI app object name.
- [ ] Determine whether AEGIS now uses an API/router registry.
- [ ] Confirm `backend/app/integrations/...` matches current project conventions.
- [ ] Confirm the current configuration mechanism (.env, pydantic settings, config service, etc.).
- [ ] Confirm the current WPF desktop project.
- [ ] Confirm whether `MonitoringClient.cs` or a replacement abstraction already owns backend HTTP traffic.
- [ ] Confirm DI/view-model/UI patterns.

## Python/backend review

- [ ] Review `config.py` and migrate it into existing settings infrastructure if appropriate.
- [ ] Review `jmf.py` for compatibility with the installed Python version.
- [ ] Confirm XML namespace and content type with actual FreeFlow responses.
- [ ] Capture and inspect a real `KnownDevices` response.
- [ ] Replace heuristic workflow/queue classification with exact attributes from the installed SDK.
- [ ] Keep raw JMF XML out of routine logs.
- [ ] Confirm timeout/error handling matches AEGIS monitoring conventions.
- [ ] Confirm API response shapes fit current AEGIS naming/versioning conventions.
- [ ] Confirm router registration style.
- [ ] Run existing backend tests plus generated tests.

## FreeFlow-specific review

- [ ] Confirm installed FreeFlow Core version.
- [ ] Obtain/check the corresponding FreeFlow Core SDK.
- [ ] Confirm JMF endpoint path: `/FreeFlowCore`, `/`, or both.
- [ ] Confirm TCP port 7751 or environment-specific secure gateway.
- [ ] Confirm `KnownDevices` returned workflow/queue fields.
- [ ] Validate `Status` + `StatusQuParams QueueInfo=true` before enabling job enumeration.
- [ ] Leave job mutation disabled until each command is verified against the installed SDK.
- [ ] Do not write directly to the FreeFlow database.

## Desktop review

- [ ] Reuse current AEGIS HTTP client infrastructure.
- [ ] Reuse current monitoring status types if practical.
- [ ] Integrate with current MonitorWindow/view model architecture.
- [ ] Match current AEGIS visual styling.
- [ ] Show unsupported capabilities as unavailable, not failed.
- [ ] Do not show hold/release/cancel buttons in v1.

## Security/governance

- [ ] Confirm no credentials are committed to source.
- [ ] Confirm operational XML is not logged unnecessarily.
- [ ] Confirm mutating capability remains false.
- [ ] Map future mutations to AEGIS policy/approval/audit infrastructure.
- [ ] Ensure the model/FERAL never receives unrestricted FreeFlow/PowerShell access.

## Acceptance

- [ ] Clean build.
- [ ] Existing tests pass.
- [ ] Generated JMF tests pass.
- [ ] AEGIS `/status` endpoint works.
- [ ] `KnownDevices` succeeds against real Core.
- [ ] Workflow discovery is accurate.
- [ ] Queue discovery is accurate.
- [ ] Backend failure is graceful when Core is offline.
- [ ] Desktop remains functional when FreeFlow is disabled.
- [ ] Rollback dry-run is correct.
