# MOVEit HA Onsite Discovery Requirements

**Date:** 2026-09-22  
**Status:** BLOCKED - Requires onsite credential and version discovery  
**Priority:** External Integration (Priority 2)

---

## Executive Summary

The MOVEit HA pair (BSOAUTALB001/BSOAUTALB002) is configured for high availability with a shared Microsoft SQL Server database. A.E.G.I.S.-9 has implemented read-only monitoring and governed failback capabilities, but onsite discovery is required to:

1. Verify exact MOVEit version and build number
2. Discover service account credentials for PowerShell remoting
3. Validate Web Admin API authentication method
4. Confirm SQL Server connection details
5. Test failback workflow in controlled environment

---

## Discovered Infrastructure

### Server Configuration

| Attribute | Primary | Secondary |
|-----------|---------|-----------|
| Hostname | BSOAUTALB001 | BSOAUTALB002 |
| Web Admin Port | 443 (HTTPS) | 443 (HTTPS) |
| Web Admin Path | `/WebAdmin` | `/WebAdmin` |
| Database | Shared SQL Server | Shared SQL Server |
| Preferred Role | Primary | Secondary |

### Current Monitoring State

- **Read-only monitoring:** Implemented via `/api/v1/reports/taskruns` endpoint
- **Authentication:** Bearer token (read-only scope)
- **Service discovery:** PowerShell CIM remoting (requires operator domain identity)
- **Failback state:** Observe mode only (automatic failback disabled)

---

## Discovery Requirements

### 1. MOVEit Version and Build Number

**Why needed:**  
A.E.G.I.S.-9 needs exact version to:
- Select correct API endpoints and payload formats
- Validate compatibility with failback workflow
- Determine supported PowerShell cmdlets

**Discovery method:**

```powershell
# Method 1: Web Admin UI (requires authenticated session)
# Navigate to /WebAdmin/ and check About page

# Method 2: API endpoint (if supported)
curl -k -H "Authorization: Bearer <token>" https://BSOAUTALB001/WebAdmin/api/v1/system/info

# Method 3: Windows service properties
Get-Service -Name "*MoveIt*" | Select-Object Name, Status, StartType

# Method 4: File version check (requires file system access)
Get-Item "C:\Program Files\Progress\MOVEit*\*\Moveit.Web.exe" | Select-Object VersionInfo
```

**Expected output format:**
```
Version: 23.0.0.1234
Build: 20231215
Edition: Automation
```

---

### 2. Service Account Credentials

**Why needed:**  
PowerShell remoting/CIM queries require domain credentials with:
- Read access to Windows services on both servers
- Read access to MOVEit service configuration
- Read access to SQL Server service status

**Discovery method:**

```powershell
# Test current operator identity
Test-WSMan -ComputerName BSOAUTALB001
Test-WSMan -ComputerName BSOAUTALB002

# If fails, identify required service account
# Common MOVEit service account patterns:
# - MOVEitService
# - Progress MOVEit
# - Domain\moveit_svc
# - Domain\moveit_admin
```

**Required credentials:**
- Domain account with local read access to both servers
- OR service account used by MOVEit services
- OR dedicated monitoring account with restricted permissions

**Security note:**  
Credentials must be stored in:
- `.env` file (git-ignored)
- Windows Credential Manager
- Azure Key Vault (if integrated)
- NEVER in config files, documentation, or commits

---

### 3. Web Admin API Authentication

**Why needed:**  
The `/api/v1/reports/taskruns` endpoint requires authentication. Current implementation uses bearer token, but exact token source and refresh strategy must be documented.

**Discovery method:**

```powershell
# Check for stored credentials in MOVEit configuration
Get-Content "C:\Program Files\Progress\MOVEit*\*\web.config" | Select-String "connectionStrings|appSettings"

# Check Windows service logon account
Get-WmiObject -Class Win32_Service -Filter "Name LIKE '%MoveIt%'" | Select-Object Name, StartMode, StartName

# Check IIS application pool identity
& "C:\Windows\System32\inetsrv\appcmd.exe" list apppool /text:name,state,startMode,processModel.identityType
```

**Expected authentication methods:**
- HTTP Basic Auth (username/password)
- Windows Authentication (NTLM/Kerberos)
- Bearer token (JWT or opaque token)
- API key in header

---

### 4. SQL Server Connection Details

**Why needed:**  
A.E.G.I.S.-9 monitors MOVEit HA via SQL Server queries to:
- Verify node health and role
- Check replication status
- Validate failback eligibility

**Discovery method:**

```powershell
# Check MOVEit database configuration
Get-Content "C:\Program Files\Progress\MOVEit*\*\Moveit.Web.exe.config" | Select-String "Data Source|Database|User ID|Password"

# Check SQL Server service
Get-Service -Name "*MSSQL*" | Select-Object Name, DisplayName, Status, StartName

# Check SQL Server instance name
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL"
```

**Expected connection string format:**
```
Data Source=BSOC-SQL-001\MOVEIT;Initial Catalog=Moveit_Database;User ID=moveit_reader;Password=***;Encrypt=True;TrustServerCertificate=False
```

**Required SQL permissions:**
- `VIEW SERVER STATE` for node health
- `SELECT` on MOVEit database tables (read-only)
- No write permissions required

---

### 5. Failback Workflow Validation

**Why needed:**  
A.E.G.I.S.-9 implements governed failback with safety checks:
- Drain active tasks before failback
- Validate shared SQL connectivity
- Confirm runtime role before promotion
- Partner communication verification

**Discovery method:**

```powershell
# Test failback prerequisites on preferred primary
# 1. Service can be stopped gracefully
Test-ServiceGracefulStop -ComputerName BSOAUTALB001 -ServiceName "Moveit.Web"

# 2. Service can be started
Test-ServiceStart -ComputerName BSOAUTALB001 -ServiceName "Moveit.Web"

# 3. Runtime role can be queried
Get-MoveitRuntimeRole -ComputerName BSOAUTALB001

# 4. Partner link health can be verified
Get-MoveitPartnerHealth -ComputerName BSOAUTALB001
```

**Failback safety checks:**
- No running tasks during failback window
- Shared SQL Server accessible from both nodes
- Runtime role matches expected state
- Partner node communication healthy
- Kill switch not active
- Maintenance mode not enabled

---

## Onsite Discovery Checklist

### Pre-Discovery Preparation

- [ ] Confirm operator domain identity has PowerShell remoting access
- [ ] Verify firewall allows WinRM (port 5985/5986) between workstations and MOVEit servers
- [ ] Prepare git-ignored `.env` file for credential storage
- [ ] Confirm network connectivity to BSOAUTALB001 and BSOAUTALB002
- [ ] Prepare MOVEit Web Admin credentials (if separate from domain identity)

### Discovery Execution

- [ ] **Step 1:** Verify MOVEit version and build number
- [ ] **Step 2:** Identify MOVEit service account and validate PowerShell remoting
- [ ] **Step 3:** Test Web Admin API authentication method
- [ ] **Step 4:** Extract SQL Server connection details
- [ ] **Step 5:** Validate failback prerequisites
- [ ] **Step 6:** Test read-only monitoring queries
- [ ] **Step 7:** Document all discovered values in `.env` file

### Post-Discovery Validation

- [ ] Update `backend/app/moveit_ha/service.py` with discovered values
- [ ] Test monitoring queries against live servers
- [ ] Validate failback workflow in observe mode
- [ ] Run `backend/tests/test_moveit_ha.py` to verify implementation
- [ ] Document any deviations from expected configuration

---

## Known Constraints

### Security Constraints

1. **No write access:** A.E.G.I.S.-9 monitoring is read-only. Failback requires explicit user approval.
2. **Credential isolation:** All credentials stored in git-ignored `.env` or managed secret storage.
3. **Least privilege:** Service accounts used for monitoring have minimal required permissions.
4. **Fail-closed:** If monitoring fails, A.E.G.I.S.-9 assumes unknown state and does not auto-failback.

### Technical Constraints

1. **Windows-only:** MOVEit runs on Windows Server. PowerShell remoting required.
2. **Shared database:** Both nodes use same SQL Server instance. Replication must be validated.
3. **Web Admin API:** Version-dependent API endpoints. Exact version must be discovered.
4. **Service dependencies:** MOVEit depends on IIS, SQL Server, and Windows services.

---

## Handoff Notes

**Current implementation status:**
- ✅ Read-only monitoring via `/api/v1/reports/taskruns`
- ✅ Node health tracking via PowerShell CIM
- ✅ Failback state machine implemented (observe mode)
- ✅ Safety checks for drain, role validation, partner communication
- ⏳ Onsite credential discovery required
- ⏳ Exact version and build number unknown
- ⏳ SQL Server connection details unknown
- ⏳ Web Admin API authentication method not fully validated

**Next steps:**
1. Schedule onsite discovery window with infrastructure team
2. Prepare discovery script from `scripts/onsite-discovery.py`
3. Execute discovery checklist
4. Update configuration and validate monitoring
5. Test failback workflow in controlled environment

---

## Related Files

- `backend/app/moveit_ha/models.py` - HA state machine and configuration models
- `backend/app/moveit_ha/service.py` - MOVEit service monitoring implementation
- `backend/app/moveit_ha/state_machine.py` - Failback state machine logic
- `scripts/onsite-discovery.py` - Onsite discovery script
- `docs/OPERATIONS-MONITORING-CENTER-PLAN.md` - Operations monitoring architecture

---

## References

- Progress MOVEit Automation Documentation: https://www.progress.com/moveit-automation
- MOVEit HA Configuration Guide: Progress documentation (requires account)
- CIP4 JDF Schema: http://www.cip4.org
- PowerShell Remoting: https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_remoting
