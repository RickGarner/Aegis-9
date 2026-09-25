# Xerox FreeFlow Core Recovery Validation Requirements

**Date:** 2026-09-22  
**Status:** BLOCKED - Requires correct JMF query format  
**Priority:** External Integration (Priority 2)

---

## Executive Summary

The Xerox FreeFlow Core pair (BSOXERALB001/BSOXERALB002) provides print workflow management. A.E.G.I.S.-9 has implemented read-only monitoring via JMF (Job Markup Language) queries, but the correct JMF query format must be discovered from onsite resources before full validation can proceed.

**Current state:**
- ✅ Both servers reachable on port 7751
- ✅ JMF endpoint responds (HTTP 500 with current query formats)
- ⏳ Correct JMF query format unknown
- ⏳ Device enumeration not working
- ⏳ Recovery validation not tested

---

## Discovered Infrastructure

### Server Configuration

| Attribute | Primary | Secondary |
|-----------|---------|-----------|
| Hostname | BSOXERALB001 | BSOXERALB002 |
| IP Address | 10.30.67.21 | 10.30.67.20 |
| JMF Port | 7751 | 7751 |
| JMF Endpoint | `/FreeFlowCore/` | `/FreeFlowCore/` |
| Application Server | Apache Tomcat | Apache Tomcat |
| Authentication | Windows Auth (401) | Windows Auth (401) |

### Current Monitoring State

- **Endpoint reachability:** ✅ Both servers respond on port 7751
- **HTTP authentication:** Returns 401 (Windows auth challenge) - confirms IIS protection
- **JMF queries:** ❌ All tested formats return HTTP 500 Internal Server Error
- **Device enumeration:** ⏳ Blocked until correct query format discovered

---

## Problem Summary

All standard CIP4 JMF query formats tested return **HTTP 500 Internal Server Error** with server-side NullPointerException. The endpoint is reachable and responding, but the FreeFlow JMF implementation is rejecting the XML queries.

### Tested Query Formats (All Failed)

#### Format 1: CIP4 QueryKnownDevices
```xml
<?xml version="1.0" encoding="UTF-8"?>
<printSystem xmlns="http://www.CIP4.org/JDFSchema_1_1">
  <query xsi:type="QueryKnownDevices" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <maxVersion>1.2</maxVersion>
  </query>
</printSystem>
```
**Result:** HTTP 500 - NullPointerException in Xerox JDF toolkit

#### Format 2: JMF with Brief DeviceFilter
```xml
<?xml version="1.0" encoding="UTF-8"?>
<jmf version="1.0" xmlns="http://www.CIP4.org/schema/JMF/1.0">
  <query>
    <Brief>
      <DeviceFilter/>
    </Brief>
  </query>
</jmf>
```
**Result:** HTTP 500 - NullPointerException

#### Format 3: Alternate JMF Brief
Same as Format 2  
**Result:** HTTP 500 - NullPointerException

---

## Validation Requirements

### 1. Correct JMF Query Format Discovery

**Why needed:**  
FreeFlow Core uses a custom JMF implementation that may not follow standard CIP4 schemas. The correct query format must be discovered from:

- Xerox FreeFlow SDK diagnostic tools
- Workstation with FreeFlow SDK installed (user has physical access)
- FreeFlow server logs showing successful query examples
- Xerox support documentation for installed version

**Discovery methods:**

#### Method A: FreeFlow SDK Diagnostic Tools
```powershell
# If FreeFlow SDK is installed on a workstation:
# 1. Launch FreeFlow Diagnostic Tool
# 2. Connect to BSOXERALB001:7751
# 3. Use JMF query builder to construct working query
# 4. Export query XML for use in A.E.G.I.S.-9
```

#### Method B: Browser-based JMF Console
```powershell
# 1. Navigate to http://BSOXERALB001:7751/FreeFlowCore/
# 2. Look for JMF diagnostic console or SOAP UI
# 3. Test queries interactively
# 4. Capture successful query format
```

#### Method C: FreeFlow Server Logs
```powershell
# Check FreeFlow logs for successful query examples:
# - C:\Program Files\Xerox\FreeFlowCore\logs\
# - C:\Program Files\Xerox\FreeFlowCore\apache-tomcat\logs\
# - Look for POST requests with XML payloads that return 200
```

#### Method D: Xerox Support Resources
```
- Xerox Support Portal: https://www.xeroxsupport.com/
- FreeFlow Core Documentation (requires account)
- Xerox Technical Support: 1-800-823-8590
- Reference installed FreeFlow version number
```

**Expected output format:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- Working query format from FreeFlow SDK -->
<query xmlns="http://www.CIP4.org/schema/JMF/1.0">
  <!-- Correct structure for FreeFlow version X.X -->
</query>
```

---

### 2. Application/API Health Transaction

**Why needed:**  
HTTP 401 authentication challenge confirms IIS protection, but A.E.G.I.S.-9 needs to determine if:

- HTTP 401 route availability is sufficient for monitoring
- Authenticated application/API health transaction is required
- Windows authentication credentials must be configured

**Validation method:**

```python
# Test 1: Unauthenticated route check (current implementation)
requests.get("http://BSOXERALB001:7751/FreeFlowCore/", timeout=5)
# Expected: 401 Unauthorized

# Test 2: Authenticated health check (if required)
# Requires: Windows domain credentials with FreeFlow access
headers = {"Authorization": "NTLM <ntlm_token>"}
requests.get("http://BSOXERALB001:7751/FreeFlowCore/", headers=headers, timeout=5)
# Expected: 200 OK with health status
```

**Decision criteria:**
- If HTTP 401 is sufficient: Document as "route availability monitoring"
- If authenticated check required: Configure Windows auth credentials in `.env`

---

### 3. Recovery Validation

**Why needed:**  
FreeFlow Core recovery validation must confirm:

- Primary server can be restarted without data loss
- Secondary server can take over print jobs
- Job queue persists across restarts
- Client connections re-establish automatically

**Validation steps:**

#### Step 1: Pre-Recovery Baseline
```powershell
# Capture current state before recovery test
# 1. Device enumeration (once JMF query works)
# 2. Active job count
# 3. Queue status
# 4. Connected clients
```

#### Step 2: Primary Server Recovery
```powershell
# Test 1: Graceful restart of FreeFlow service
Stop-Service -Name "FreeFlowCore" -ComputerName BSOXERALB001 -Wait
Start-Service -Name "FreeFlowCore" -ComputerName BSOXERALB001 -Wait

# Test 2: Verify service is running
Get-Service -Name "FreeFlowCore" -ComputerName BSOXERALB001

# Test 3: Verify JMF endpoint responds
curl http://BSOXERALB001:7751/FreeFlowCore/
```

#### Step 3: Secondary Server Failover
```powershell
# Test 1: Verify secondary is healthy
curl http://BSOXERALB002:7751/FreeFlowCore/

# Test 2: Simulate primary failure (if HA configured)
# Monitor job queue migration to secondary

# Test 3: Verify secondary can handle print jobs
# Submit test job to secondary endpoint
```

#### Step 4: Post-Recovery Validation
```powershell
# Test 1: Device enumeration via JMF
# Test 2: Job queue integrity
# Test 3: Client reconnection
# Test 4: Print functionality
```

---

### 4. Refresh Soak Validation

**Why needed:**  
After recovery, FreeFlow Core must be validated under load to ensure:

- No memory leaks or resource exhaustion
- Job processing continues without errors
- Device status remains stable
- Client connections remain healthy

**Validation method:**

```python
# Refresh soak test (24-48 hours recommended)
# 1. Submit test jobs at regular intervals
# 2. Monitor JMF device status
# 3. Track error rates
# 4. Verify no memory growth
# 5. Confirm job queue processing

# Example soak test script:
import time
import requests
from datetime import datetime

def run_soak_test(duration_hours=24):
    end_time = datetime.now() + timedelta(hours=duration_hours)
    job_count = 0
    
    while datetime.now() < end_time:
        # Submit test job
        job_id = submit_test_job()
        job_count += 1
        
        # Monitor JMF status
        status = get_jmf_status()
        if status["error_count"] > threshold:
            raise Exception("Error threshold exceeded")
        
        # Wait before next job
        time.sleep(300)  # 5 minutes
    
    print(f"Soak test complete: {job_count} jobs processed")
```

---

## Onsite Validation Checklist

### Pre-Validation Preparation

- [ ] Confirm operator domain identity has FreeFlow access
- [ ] Verify firewall allows port 7751 between workstations and FreeFlow servers
- [ ] Prepare git-ignored `.env` file for credentials (if required)
- [ ] Confirm network connectivity to BSOXERALB001 and BSOXERALB002
- [ ] Obtain FreeFlow SDK or diagnostic tools (if available)
- [ ] Schedule maintenance window for recovery testing

### Discovery Execution

- [ ] **Step 1:** Obtain correct JMF query format from SDK/logs
- [ ] **Step 2:** Test JMF query format against BSOXERALB001
- [ ] **Step 3:** Test JMF query format against BSOXERALB002
- [ ] **Step 4:** Validate device enumeration works
- [ ] **Step 5:** Determine if authenticated health check required
- [ ] **Step 6:** Document all discovered values

### Recovery Validation

- [ ] **Step 1:** Capture pre-recovery baseline state
- [ ] **Step 2:** Gracefully restart FreeFlow service on primary
- [ ] **Step 3:** Verify service recovery and JMF endpoint
- [ ] **Step 4:** Test secondary server failover (if HA configured)
- [ ] **Step 5:** Validate job queue integrity
- [ ] **Step 6:** Confirm client reconnection

### Soak Validation

- [ ] **Step 1:** Configure soak test parameters
- [ ] **Step 2:** Run 24-hour soak test
- [ ] **Step 3:** Monitor for errors or resource issues
- [ ] **Step 4:** Generate soak test report
- [ ] **Step 5:** Document any issues found

---

## Known Constraints

### Security Constraints

1. **No write access:** A.E.G.I.S.-9 monitoring is read-only. Recovery testing requires explicit user approval.
2. **Credential isolation:** All credentials stored in git-ignored `.env` or managed secret storage.
3. **Least privilege:** Service accounts used for monitoring have minimal required permissions.
4. **Maintenance window:** Recovery testing must be scheduled during low-usage period.

### Technical Constraints

1. **Windows-only:** FreeFlow runs on Windows Server. PowerShell required for service management.
2. **Apache Tomcat:** JMF endpoint runs on Tomcat. Restart affects all JMF clients.
3. **JMF version:** FreeFlow may use custom JMF schema. Standard CIP4 formats may not work.
4. **Authentication:** Windows auth challenge returns 401. May require NTLM/Kerberos token.

---

## Handoff Notes

**Current implementation status:**
- ✅ Endpoint reachability monitoring (port 7751)
- ✅ HTTP 401 authentication challenge confirmed
- ⏳ JMF query format unknown (HTTP 500 on all tested formats)
- ⏳ Device enumeration blocked
- ⏳ Recovery validation not tested
- ⏳ Refresh soak validation not performed

**Next steps:**
1. Obtain correct JMF query format from onsite resources
2. Update `backend/app/freeflow_jmf.py` with working query
3. Test device enumeration against live servers
4. Schedule recovery validation window
5. Execute recovery and soak validation tests
6. Document results and update monitoring configuration

---

## Related Files

- `backend/app/freeflow_jmf.py` - JMF service implementation
- `scripts/test-freeflow-jmf.py` - Test script for JMF query formats
- `scripts/onsite-discovery-v2.py` - Onsite discovery script
- `plans/onsite-validation-2026-09-21/freeflow-jmf-investigation-notes.md` - Investigation notes
- `docs/operational-monitoring.md` - Operations monitoring documentation

---

## References

- Xerox FreeFlow Core Documentation: https://www.xerox.com/en-us/support/freeflow
- CIP4 JDF Schema: http://www.cip4.org
- JMF (Job Markup Language): https://en.wikipedia.org/wiki/Job_Markup_Language
- Apache Tomcat: https://tomcat.apache.org/
