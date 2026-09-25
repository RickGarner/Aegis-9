# Aegis-9 and Developer Studio Bridge: Clean Machine Setup and Validation

**Version:** 1.0.0  
**Last Updated:** 2026-09-22  
**Status:** Implementation Complete

---

## Overview

This document describes the setup and validation procedure for the Aegis-9 and Developer Studio bridge on a clean machine. The bridge enables authenticated, versioned communication between the two products for workflow revision exchange, build/test evidence, and artifact handoff.

---

## Architecture

### Components

1. **Aegis-9 Bridge Server** (`backend/app/bridge_server.py`)
   - FastAPI REST server running on `http://127.0.0.1:8765`
   - Provides authenticated endpoints for IDE communication
   - Manages approval requests, workflow revisions, and evidence storage

2. **Developer Studio Bridge Client** (`src/vs/platform/agentHost/common/aegisBridgeClient.ts`)
   - TypeScript client for IDE-side communication
   - Handles workflow revision open requests and result submission
   - Authenticates all requests with HMAC-SHA256 signatures

3. **Bridge Protocol** (`backend/app/bridge_protocol.py`)
   - Versioned message envelope format (v1.0.0)
   - Payload definitions for status, approval, events, evidence, artifacts
   - HMAC-SHA256 signature computation and verification

### Security Model

- **Local-only communication**: Bridge server binds to `127.0.0.1` only
- **HMAC-SHA256 authentication**: All requests signed with shared secret
- **Replay protection**: Timestamp + nonce validation (5-minute window)
- **Fail-closed**: Missing/invalid authentication rejects requests
- **Read-only by default**: Write operations require explicit approval

---

## Prerequisites

### Aegis-9 Side

1. **Python 3.10+** with `uv` package manager
2. **Environment variables**:
   ```powershell
   $env:AEGIS_BRIDGE_SECRET = "<32+ character random string>"
   $env:JARVIS_DEVELOPER_STUDIO_BRIDGE_URL = "http://127.0.0.1:8765"
   ```
3. **Backend dependencies**:
   ```powershell
   cd D:\AEGIS\AEGIS-9
   uv sync
   ```

### Developer Studio Side

1. **Node.js 18+** and `npm`
2. **Environment variables**:
   ```powershell
   $env:AEGIS_BRIDGE_SECRET = "<same 32+ character string as Aegis-9>"
   $env:AEGIS_BRIDGE_URL = "http://127.0.0.1:8765"
   ```
3. **Build dependencies**:
   ```powershell
   cd D:\AEGIS\Aegis-Developer-Studio
   npm install
   npm run compile
   ```

---

## Setup Procedure

### Step 1: Configure Aegis-9 Bridge Secret

Generate a secure random secret for bridge authentication:

```powershell
# Generate 32-byte random secret (Base64)
$secret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
$env:AEGIS_BRIDGE_SECRET = $secret

# Save to profile for persistence
Add-Content $PROFILE "$env:AEGIS_BRIDGE_SECRET = `"$secret`""
```

### Step 2: Configure Developer Studio Bridge Secret

Use the **same secret** as Aegis-9:

```powershell
$env:AEGIS_BRIDGE_SECRET = "<copy from Aegis-9>"
$env:AEGIS_BRIDGE_URL = "http://127.0.0.1:8765"

# Save to Developer Studio environment
Add-Content $PROFILE "$env:AEGIS_BRIDGE_SECRET = `"$secret`""
Add-Content $PROFILE "$env:AEGIS_BRIDGE_URL = `"$env:AEGIS_BRIDGE_URL`""
```

### Step 3: Start Aegis-9 Backend

The bridge server starts automatically with the Aegis-9 backend:

```powershell
cd D:\AEGIS\AEGIS-9
uv run python -m app.main
```

Verify bridge server is running:

```powershell
# Check bridge endpoint (requires authentication)
# This will fail without valid signature, but confirms server is up
curl http://127.0.0.1:8765/aegis/bridge/v1/status
# Expected: 401 Unauthorized (missing auth headers)
```

### Step 4: Launch Developer Studio

```powershell
cd D:\AEGIS\Aegis-Developer-Studio
npm run start
```

The bridge client will initialize automatically if `AEGIS_BRIDGE_SECRET` is set.

---

## Validation Procedure

### Test 1: Bridge Server Health Check

```powershell
# Verify bridge server is listening
netstat -ano | findstr ":8765"

# Expected output:
# TCP    127.0.0.1:8765         0.0.0.0:0              LISTENING       <PID>
```

### Test 2: Run Bridge Protocol Tests

```powershell
cd D:\AEGIS\AEGIS-9\backend
uv run pytest tests/test_bridge_protocol.py -v

# Expected: 22 tests passed
```

### Test 3: Run Bridge Acceptance Tests

```powershell
cd D:\AEGIS\AEGIS-9\backend
uv run pytest tests/test_bridge_acceptance.py -v

# Expected: All acceptance tests passed
```

### Test 4: Verify Bridge Client in Developer Studio

1. Open Developer Studio DevTools (`Ctrl+Shift+I`)
2. Open Console tab
3. Look for bridge initialization logs:
   ```
   [AegisBridgeClient] Initialized with URL: http://127.0.0.1:8765
   [AegisBridgeClient] Secret configured: true
   ```

### Test 5: End-to-End Workflow Round-Trip

**From Aegis-9:**
1. Create a workflow revision
2. Click "Open in Developer Studio"
3. Bridge sends `WORKFLOW_REVISION_OPEN_REQUEST`

**From Developer Studio:**
1. Receive open request notification
2. Open workflow in editor
3. Run build and tests
4. Submit build/test results via bridge
5. Notify completion with recommendation

**Verify in Aegis-9:**
1. Receive completion notification
2. Review build/test evidence
3. Verify hash integrity
4. Proceed to supervisor approval

---

## Environment Variables Reference

| Variable | Aegis-9 | Developer Studio | Description |
|----------|---------|------------------|-------------|
| `AEGIS_BRIDGE_SECRET` | Required | Required | Shared HMAC secret (32+ chars) |
| `AEGIS_BRIDGE_URL` | Optional | Required | Bridge server URL (default: http://127.0.0.1:8765) |
| `JARVIS_DEVELOPER_STUDIO_BRIDGE_URL` | Required | N/A | Aegis-side URL to reach IDE bridge |
| `JARVIS_DEVELOPER_STUDIO_BRIDGE_TOKEN` | Required | N/A | Token for Aegis to authenticate IDE requests |

---

## Troubleshooting

### Bridge Server Not Starting

**Symptoms**: Port 8765 not listening, backend starts without bridge

**Diagnosis**:
```powershell
# Check if secret is configured
echo $env:AEGIS_BRIDGE_SECRET

# Check backend logs for bridge initialization
Get-Content D:\AEGIS\AEGIS-9\Workflows\logs\backend.log -Tail 50
```

**Fix**:
```powershell
# Set secret and restart
$env:AEGIS_BRIDGE_SECRET = (New-Guid).ToString()
uv run python -m app.main
```

### Bridge Client Not Initializing

**Symptoms**: No bridge logs in Developer Studio DevTools

**Diagnosis**:
```typescript
// Check if client is created
console.log(window.bridgeClient); // Should be AegisBridgeClient instance
```

**Fix**:
```powershell
# Verify environment variable
echo $env:AEGIS_BRIDGE_SECRET

# Restart Developer Studio with secret
$env:AEGIS_BRIDGE_SECRET = "<secret>"
npm run start
```

### Authentication Failures

**Symptoms**: 401 Unauthorized on all bridge requests

**Diagnosis**:
1. Verify secrets match on both sides
2. Check timestamp freshness (5-minute window)
3. Verify nonce uniqueness

**Fix**:
```powershell
# Regenerate secrets on both sides
$secret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
$env:AEGIS_BRIDGE_SECRET = $secret
```

### Replay Attack Prevention

**Symptoms**: Requests rejected with "stale timestamp"

**Diagnosis**: System clock skew > 5 minutes

**Fix**:
```powershell
# Sync clock
w32tm /resync
```

---

## Security Considerations

### Secret Management

- **Never commit secrets to version control**
- Use Windows Credential Manager for production:
  ```powershell
  # Store secret securely
  cmdkey /generic:AEGIS_BRIDGE_SECRET /user:local /pass:"<secret>"
  
  # Retrieve secret
  $secret = (Get-Command cmdkey).InvokeCommand.InvokeScript(
      [ScriptBlock]::Create('param($target) cmdkey /list | Where-Object {$_.Contains($target)} | ForEach-Object {$_}')
  )
  ```

### Local-Only Enforcement

- Bridge server binds to `127.0.0.1` only
- Firewall rules should block external access to port 8765
- Monitor for unauthorized binding attempts:
  ```powershell
  # Check for unexpected listeners
  netstat -ano | findstr ":8765"
  ```

### Audit Logging

All bridge events are logged with:
- Timestamp (UTC)
- Request ID
- Source/destination
- Action type
- Authentication status

---

## Cleanup

### Remove Bridge Configuration

```powershell
# Remove environment variables
Remove-Item Env:AEGIS_BRIDGE_SECRET
Remove-Item Env:AEGIS_BRIDGE_URL

# Remove from profile
$secret = (Get-Content $PROFILE) | Where-Object { $_ -like "*AEGIS_BRIDGE_SECRET*" }
if ($secret) {
    (Get-Content $PROFILE) | Where-Object { $_ -notlike "*AEGIS_BRIDGE_SECRET*" } | Set-Content $PROFILE
}
```

### Stop Bridge Server

```powershell
# Find bridge process
Get-Process | Where-Object { $_.MainWindowTitle -like "*Aegis*" }

# Terminate gracefully
Stop-Process -Id <PID>
```

---

## References

- [Bridge Protocol Specification](../backend/app/bridge_protocol.py)
- [Bridge Server Implementation](../backend/app/bridge_server.py)
- [Developer Studio Bridge Client](../Aegis-Developer-Studio/src/vs/platform/agentHost/common/aegisBridgeClient.ts)
- [Bridge Acceptance Tests](../backend/tests/test_bridge_acceptance.py)

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-09-22 | Aegis-9 Team | Initial release |
