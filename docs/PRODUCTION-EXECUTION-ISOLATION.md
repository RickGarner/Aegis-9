# A.E.G.I.S.-9 Production Execution Isolation

**Status:** Implemented with Windows Sandbox  
**Products:** A.E.G.I.S.-9 and Aegis Developer Studio  
**Mode:** Local/offline by default  
**Last Updated:** 2026-09-21

## Overview

Production execution isolation provides a disposable Windows Sandbox boundary for executing untrusted or potentially dangerous code. This implementation uses Windows Sandbox with enforced resource limits, network isolation, and automatic cleanup to minimize risk when testing workflows, scripts, or compiled code.

## Security Boundaries

### Enforced Controls

| Control | Value | Purpose |
|---------|-------|---------|
| Network | Disabled | Prevents outbound connections to external systems |
| Clipboard | Disabled | Prevents data exfiltration via clipboard |
| Printer | Disabled | Prevents unauthorized printing |
| Audio Input | Disabled | Prevents microphone access |
| Video Input | Disabled | Prevents camera access |
| Protected Client | Enabled | Enables Windows Sandbox protected mode |
| Memory Limit | Configurable (default 4096 MB) | Bounded memory consumption |
| CPU Limit | Configurable (default 100%) | Bounded CPU consumption |
| Host Filesystem | Read-only input mapping | Source code never writable in sandbox |
| Credentials | None | No production credentials supplied |

### Isolation Model

1. **Source Code Isolation**: Original source files are copied into a package and mounted read-only in the sandbox. The host workspace is never mapped into the sandbox.

2. **Output Isolation**: Only the dedicated output directory is writable from the sandbox. All evidence and results are written there.

3. **Network Isolation**: Windows Sandbox networking is completely disabled at the hypervisor level.

4. **Credential Isolation**: No credentials are injected into the sandbox. Any code requiring authentication will fail.

## Workflow

### Operator Flow

1. **Select Source**: Operator selects PowerShell or C# source files (up to 500 KB per file, 100 files total, 2 MB aggregate).

2. **Create Plan**: A.E.G.I.S.-9 analyzes source for dangerous patterns (filesystem mutation, network access, remote execution, database access, process creation, environment modification). The plan includes:
   - Risk level (low/medium/high/critical)
   - Detected capabilities and findings
   - Synthetic test inputs
   - Resource limits

3. **Review and Approve Package**: Operator reviews the generated package manifest, which includes:
   - Source file hashes (SHA-256)
   - Detected capabilities
   - Enforced restrictions
   - Resource limits
   - Test plan details

4. **Launch Sandbox**: Operator explicitly approves sandbox launch. Windows Sandbox starts with the configured restrictions.

5. **Execute Tests**: The sandbox runner automatically:
   - Copies source files to working directory
   - Parses PowerShell files for syntax errors
   - Builds C# projects (offline, no restore)
   - Generates evidence.json with results

6. **Close and Review**: Operator closes the sandbox. Evidence is reviewed through the API or UI.

7. **Cleanup**: Automatic cleanup removes sandbox-generated output.

## API Endpoints

### Create Test Plan

```http
POST /api/test-lab/plan
Content-Type: application/json

{
  "files": {
    "script.ps1": "Write-Host 'Hello'"
  }
}
```

**Response:**
```json
{
  "id": "uuid",
  "risk": "low",
  "capabilities": {
    "network": false,
    "credentials": false,
    "hostWrite": false
  },
  "findings": [],
  "testCases": [...]
}
```

### Create Test Package

```http
POST /api/test-lab/package
Content-Type: application/json

{
  "files": {
    "script.ps1": "Write-Host 'Hello'"
  },
  "plan": { ... },
  "approved": true
}
```

**Response:**
```json
{
  "planId": "uuid",
  "packagePath": "storage/test-lab/uuid",
  "configurationPath": "storage/test-lab/uuid/AegisTestLab.wsb",
  "status": "ready-for-explicit-launch",
  "executed": false,
  "capabilities": { ... }
}
```

### Launch Sandbox

```http
POST /api/test-lab/launch
Content-Type: application/json

{
  "package_path": "storage/test-lab/uuid"
}
```

**Response:**
```json
{
  "sessionId": "uuid",
  "packagePath": "storage/test-lab/uuid",
  "status": "launched",
  "processId": 12345,
  "timeoutSeconds": 300
}
```

### Get Session Status

```http
GET /api/test-lab/session/{session_id}
```

**Response:**
```json
{
  "sessionId": "uuid",
  "packagePath": "storage/test-lab/uuid",
  "status": "running",
  "launchedAt": "2026-09-21T10:00:00+00:00",
  "completedAt": null,
  "cleanupDone": false
}
```

### Cleanup Session

```http
POST /api/test-lab/session/{session_id}/cleanup
```

**Response:**
```json
{
  "status": "cleaned",
  "sessionId": "uuid",
  "actions": ["Removed output directory: ..."],
  "errors": []
}
```

### List Sessions

```http
GET /api/test-lab/sessions
```

**Response:**
```json
{
  "sessions": [...],
  "count": 1
}
```

## Resource Limits

### Memory Limit

Configurable via `resourceLimits.memoryMB` in the test plan. Default: 4096 MB.

```json
{
  "resourceLimits": {
    "memoryMB": 2048
  }
}
```

### CPU Limit

Configurable via `resourceLimits.cpuPercent` in the test plan. Default: 100%.

```json
{
  "resourceLimits": {
    "cpuPercent": 50
  }
}
```

## Detection Rules

The Test Lab analyzer detects the following dangerous patterns:

| Risk Level | Category | Pattern Examples | Control |
|------------|----------|------------------|---------|
| Critical | Destructive Filesystem | `Remove-Item`, `Directory.Delete`, `File.Delete` | Use only synthetic files in disposable sandbox |
| Critical | Remote Execution | `Invoke-Command`, `Enter-PSSession`, `Process.Start` | Block production credentials and all network access |
| High | System Mutation | `Set-ItemProperty`, `New-Service`, `Register-ScheduledTask` | Mock operation or use disposable VM |
| High | Network | `Invoke-WebRequest`, `HttpClient`, `TcpClient` | Networking disabled; use isolated mock endpoint |
| High | Database | `SqlConnection`, `Invoke-Sqlcmd`, `ExecuteNonQuery` | Replace with ephemeral synthetic fixture |
| Medium | Process | `Start-Process`, `System.Diagnostics.Process` | Record child processes, enforce limits |
| Medium | Environment | `GetEnvironmentVariable`, `$env:`, `Environment.SetEnvironmentVariable` | Provide only synthetic environment values |

## Windows Sandbox Requirements

### Prerequisites

- Windows 11 Enterprise, Pro, or Education (Windows 10 Enterprise/Pro with specific builds)
- Windows Sandbox feature enabled:
  ```powershell
  Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Sandbox -NoRestart
  ```
- Virtualization enabled in BIOS/UEFI
- Hyper-V enabled

### Verification

```powershell
# Check if Windows Sandbox is available
Test-Path "C:\Windows\System32\WindowsSandbox.exe"

# Check virtualization status
systeminfo | findstr /C:"Hyper-V"
```

## Storage

Test Lab packages are stored under `JARVIS_TEST_LAB_ROOT` (default: `storage/test-lab`). Each plan has its own directory containing:

- `input/` - Source files, test plan, synthetic data, manifest, runner script
- `output/` - Sandbox-generated evidence (removed on cleanup)
- `AegisTestLab.wsb` - Windows Sandbox configuration file

## Limitations

### What Test Lab Does NOT Do

1. **Does not prove arbitrary code is safe**: Windows Sandbox is the security boundary, not the AI review or pattern scanner.

2. **Does not execute submitted code**: PowerShell scripts are parsed, not executed. C# projects are built but not run.

3. **Does not handle malware analysis**: Not designed for reverse engineering or malware analysis.

4. **Does not support production credentials**: No credentials are injected; code requiring authentication will fail.

5. **Does not connect to real infrastructure**: Network is disabled; external dependencies must be mocked.

### What Requires Separate Approval

- Malware analysis or reverse engineering
- Kernel driver testing
- Tests requiring production identity or credentials
- Tests that must contact real infrastructure
- Tests requiring network access (requires separate approved harness)

## Implementation Files

### Backend

- `backend/app/test_lab.py` - Test Lab planning, packaging, sandbox launch/cleanup
- `backend/app/main.py` - API endpoints for Test Lab
- `backend/tests/test_test_lab.py` - Unit tests for Test Lab functionality

### Configuration

- `JARVIS_TEST_LAB_ROOT` environment variable or `test_lab_root` setting

### Sandbox Configuration

- `sandbox_configuration()` - Generates Windows Sandbox .wsb configuration
- `SANDBOX_RUNNER` - PowerShell script executed inside sandbox

## Security Considerations

### Fail-Closed Design

- Unknown capabilities are denied by default
- Network access is disabled unless explicitly approved (not implemented in this release)
- Credential injection is never performed
- Sandbox launch requires explicit user approval

### Audit Trail

- All Test Lab operations are logged to the audit store
- Package manifests include source file hashes
- Session tracking records launch, completion, and cleanup events

### Isolation Verification

- Network disabled at hypervisor level
- Clipboard, printer, audio, video all disabled
- Protected Client mode enabled
- Read-only input mapping prevents host filesystem modification

## Future Enhancements

- [ ] Network access simulation via isolated mock endpoints
- [ ] Credential injection for non-production environments
- [ ] C# runtime execution (currently build-only)
- [ ] Custom sandbox profiles for different risk levels
- [ ] Integration with external VM infrastructure for higher isolation
- [ ] Automated evidence analysis and risk scoring
- [ ] Sandbox session recording and replay

## References

- [A.E.G.I.S. Test Lab Documentation](./AEGIS-TEST-LAB.md)
- [Implementation Checklist](./implementation-checklist.md)
- [Workflow Test Runner](./WORKFLOW-TEST-RUNNER.md)
