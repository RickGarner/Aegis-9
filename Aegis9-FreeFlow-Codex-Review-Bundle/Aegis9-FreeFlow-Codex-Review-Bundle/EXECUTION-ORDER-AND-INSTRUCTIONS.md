# AEGIS 9 FreeFlow Core Integration Bundle
## Codex-review-first execution guide

**Purpose:** Add the initial Xerox FreeFlow Core integration to the current AEGIS 9 repository without assuming that the repository still matches the older architecture known when this bundle was designed.

**Important operating rule:** **Codex should review this entire bundle against the current AEGIS source before any script is run with `-Apply`.** The scripts intentionally default to dry-run or read-only behavior.

## Scope of this first implementation

This package implements the lowest-risk foundation:

- FreeFlow Core JMF endpoint health.
- Vendor-documented `KnownDevices` discovery.
- Backend endpoints for status, devices, workflows, queues, jobs, and capabilities.
- A feature-flagged JMF `Status` / `QueueInfo` job-enumeration path.
- A WPF/.NET API client and DTO layer.
- Environment configuration.
- Unit/compile/build validation.
- Rollback support.

It deliberately does **not** enable:

- job hold/release/abort/remove/retry,
- workflow modification,
- printer mutation,
- direct FreeFlow database changes,
- arbitrary PowerShell against the FreeFlow server,
- automatic remediation.

Those should be added only after Codex validates the exact installed FreeFlow Core SDK/version and the current AEGIS policy/workflow framework.

## Why this is conservative

Xerox publicly documents that FreeFlow Core accepts JMF connections on port 7751 and that `KnownDevices` returns workflows and queues. Xerox also states that the complete supported JMF command/signal/JDF set is defined by the FreeFlow Core SDK. The scripts therefore enable only the clearly documented discovery path by default.

`Status` with queue information is present as a feature-flagged candidate for job enumeration, but remains disabled until verified against the installed SDK.

## Required prerequisites

- Windows PowerShell 5.1 or PowerShell 7.
- Git.
- Python used by the AEGIS backend.
- .NET SDK used by the AEGIS desktop project.
- Current AEGIS repository already checked out locally.
- Network access from the AEGIS backend machine to the FreeFlow Core JMF gateway, normally TCP 7751.
- Codex review of the current repository.

## Execution order

### Phase A — Codex review only; no source modification

1. `00-Preflight-AegisFreeFlow.ps1`
2. `Run-Codex-Review-DryRun.ps1`
3. Codex reviews:
   - the preflight JSON,
   - detected backend entry point,
   - detected WPF project,
   - generated source contained in scripts,
   - existing AEGIS integration/client/monitoring conventions,
   - current Git diff/status.

Example:

```powershell
Set-ExecutionPolicy -Scope Process Bypass

$Repo = "D:\Development\Aegis-Developer-Studio"
$FreeFlow = "FREEFLOW01"

.\00-Preflight-AegisFreeFlow.ps1 `
    -RepoPath $Repo `
    -FreeFlowHost $FreeFlow

.\Run-Codex-Review-DryRun.ps1 `
    -RepoPath $Repo `
    -FreeFlowHost $FreeFlow
```

No `-Apply` is used in Phase A.

### Phase B — Create safety snapshot

After Codex approves the design:

```powershell
.\01-Create-SafetySnapshot.ps1 -RepoPath $Repo
```

If the repository is intentionally dirty, Codex should inspect the changes before allowing:

```powershell
.\01-Create-SafetySnapshot.ps1 `
    -RepoPath $Repo `
    -AllowDirty
```

A clean working tree is preferred.

### Phase C — Backend module

First dry-run again:

```powershell
.\02-Install-FreeFlowBackend.ps1 -RepoPath $Repo
```

Then apply only after Codex approval:

```powershell
.\02-Install-FreeFlowBackend.ps1 `
    -RepoPath $Repo `
    -Apply
```

This creates a self-contained module under the detected FastAPI application directory:

```text
integrations/
  freeflow/
    __init__.py
    config.py
    models.py
    jmf.py
    service.py
    api.py
    test_jmf.py
```

The installer refuses to overwrite an existing non-generated file.

### Phase D — Register the FastAPI router

Dry-run:

```powershell
.\03-Register-FreeFlowBackend.ps1 -RepoPath $Repo
```

Codex must check whether current AEGIS uses a central API/router registry. If so, Codex should adapt this step to that convention rather than append directly to `main.py`.

If the direct registration is appropriate:

```powershell
.\03-Register-FreeFlowBackend.ps1 `
    -RepoPath $Repo `
    -Apply
```

The script uses explicit begin/end markers so the change is auditable and reversible.

### Phase E — Install desktop client scaffold

Dry-run:

```powershell
.\04-Install-FreeFlowDesktopClient.ps1 -RepoPath $Repo
```

Apply:

```powershell
.\04-Install-FreeFlowDesktopClient.ps1 `
    -RepoPath $Repo `
    -Apply
```

This intentionally installs only:

- `FreeFlowModels.cs`
- `FreeFlowClient.cs`
- a desktop wiring note

It does **not** edit `MonitorWindow`, startup, DI, or `MonitoringClient.cs`. Codex should integrate the client into the current AEGIS desktop conventions after inspecting the latest code.

### Phase F — Configure FreeFlow

Start with job enumeration disabled:

```powershell
.\05-Configure-FreeFlow.ps1 `
    -RepoPath $Repo `
    -FreeFlowHost "FREEFLOW01"
```

Review the proposed block, then:

```powershell
.\05-Configure-FreeFlow.ps1 `
    -RepoPath $Repo `
    -FreeFlowHost "FREEFLOW01" `
    -Apply
```

This writes:

```text
AEGIS_FREEFLOW_ENABLED=true
AEGIS_FREEFLOW_BASE_URL=http://FREEFLOW01:7751/FreeFlowCore
AEGIS_FREEFLOW_TIMEOUT_SECONDS=10
AEGIS_FREEFLOW_VERIFY_TLS=true
AEGIS_FREEFLOW_ENABLE_STATUS_QUERY=false
AEGIS_FREEFLOW_ALLOW_MUTATIONS=false
```

Do not set `AEGIS_FREEFLOW_ALLOW_MUTATIONS=true`; v1 intentionally contains no mutating API implementation.

### Phase G — Direct JMF verification

Run a direct vendor-interface test:

```powershell
.\06-Test-FreeFlowJmf.ps1 `
    -FreeFlowHost "FREEFLOW01" `
    -OutputDirectory "."
```

This saves the exact request and response XML for Codex/operations review.

If `/FreeFlowCore` is not accepted in your installation, Codex may retest the documented root gateway:

```powershell
.\06-Test-FreeFlowJmf.ps1 `
    -FreeFlowHost "FREEFLOW01" `
    -JmfPath "/" `
    -OutputDirectory "."
```

### Phase H — Validate source

```powershell
.\07-Validate-AegisFreeFlow.ps1 `
    -RepoPath $Repo
```

This performs:

- Python `compileall`.
- FreeFlow JMF unit tests.
- .NET desktop build when the desktop project can be uniquely detected.

If the AEGIS backend is already running:

```powershell
.\07-Validate-AegisFreeFlow.ps1 `
    -RepoPath $Repo `
    -BackendUrl "http://127.0.0.1:8000"
```

The live API check should show `healthy=true` only when AEGIS can reach the configured FreeFlow gateway.

## API surface installed

```text
GET /api/integrations/freeflow/status
GET /api/integrations/freeflow/devices
GET /api/integrations/freeflow/workflows
GET /api/integrations/freeflow/queues
GET /api/integrations/freeflow/jobs
GET /api/integrations/freeflow/capabilities
```

`/jobs` returns a deliberate unsupported response until the Status/QueueInfo feature is enabled.

## Enabling the experimental job query

Only after Codex validates the exact FreeFlow SDK behavior:

```powershell
.\05-Configure-FreeFlow.ps1 `
    -RepoPath $Repo `
    -FreeFlowHost "FREEFLOW01" `
    -EnableStatusQuery `
    -Apply
```

Then rerun validation.

If FreeFlow rejects that query, turn it back off by rerunning configuration without `-EnableStatusQuery`.

## Rollback

Always dry-run first:

```powershell
.\90-Rollback-AegisFreeFlow.ps1 -RepoPath $Repo
```

After review:

```powershell
.\90-Rollback-AegisFreeFlow.ps1 `
    -RepoPath $Repo `
    -Apply
```

Rollback removes only generated files still carrying the generated marker, the marker-scoped FastAPI registration, and the marker-scoped `.env` block. It refuses to delete a generated directory if Codex or a developer has added non-generated files to it.

## What Codex should improve after reviewing current AEGIS

Codex should prefer existing AEGIS infrastructure over the standalone scaffolding wherever appropriate:

1. Reuse the existing configuration/settings system rather than duplicate environment parsing if one exists.
2. Register the router through the current API registry if one exists.
3. Reuse the current `MonitoringClient.cs` / backend client abstraction.
4. Map FreeFlow health into the existing AEGIS monitoring state model.
5. Persist observations through the current SQLite/storage abstractions if operational history is desired.
6. Route alerts through the current alert/audit/notification subsystem.
7. Add the UI using current AEGIS visual and view-model conventions.
8. Add cancellation, approvals, policy, and audit before any future mutation command.
9. Validate JMF response samples from the actual FreeFlow server and replace heuristic workflow/queue classification with exact SDK fields.
10. Add printer IPP/SNMP adapters as separate providers rather than overloading JMF with device telemetry it does not expose reliably.

## Production gate

Do not promote this connector beyond read-only monitoring until all of the following are true:

- current AEGIS build passes,
- FreeFlow JMF capture is validated,
- workflows/queues are parsed correctly for your FreeFlow release,
- job enumeration is validated or left disabled,
- no secrets or document payloads are logged,
- operations approves firewall/service-account requirements,
- monitoring is stable across backend restarts,
- Codex adds tests consistent with the current repository test framework.

