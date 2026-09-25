# External Integration Status Dashboard

**Date:** 2026-09-22  
**Status:** Priority 2 - Externally Blocked Operations  
**Purpose:** Track status of external integrations requiring onsite discovery and validation

---

## Integration Overview

| Integration | Status | Blocker | Next Action | Owner |
|-------------|--------|---------|-------------|-------|
| MOVEit HA | ✅ Discovery Complete | Service account password | Schedule onsite credential validation | Infrastructure Team |
| FreeFlow Core | ✅ Discovery Complete | Job operations not tested | Test KnownMessages and job control | User/Onsite Team |
| Offline .NET SDK | ⏳ Not Provisioned | Offline package acquisition | Source offline .NET packages | DevOps Team |
| Windows Sandbox Runner | ⏳ Not Implemented | Disposable runner spec | Implement sandbox spec | Aegis Team |

---

## MOVEit HA Integration

### Current State

```
┌─────────────────────────────────────────────────────────────────┐
│ MOVEit HA Pair: BSOAUTALB001 / BSOAUTALB002                    │
│ Mode: Observe (automatic failback disabled)                     │
│ Monitoring: Read-only via /api/v1/reports/taskruns             │
│ Authentication: Bearer token (read-only scope)                  │
└─────────────────────────────────────────────────────────────────┘

Status: ✅ DISCOVERY COMPLETE
```

### Discovery Results

| Requirement | Status | Details |
|-------------|--------|---------|
| MOVEit version/build | ✅ Discovered | Web Admin SPA at root URL |
| Service account credentials | ✅ Discovered | .\moveitsvc (password requires onsite) |
| Web Admin API auth method | ✅ Discovered | HTTPS endpoints confirmed |
| SQL Server connection | ✅ Discovered | BSOSQAALB001 (10.30.67.108) |
| Failback prerequisites | ⏳ Pending | Requires onsite validation |

### Discovered Infrastructure

**Production Network (10.30.67.x/25):**
- **BSOAUTALB001** (10.30.67.105) - MOVEit Automation (Currently Secondary after failover)
- **BSOAUTALB002** (10.30.67.106) - MOVEit Automation (Currently Primary after failover)
- **BSOSQAALB001** (10.30.67.108) - MOVEit Automation SQL Server
- **BSOTRNALB001** (10.30.67.111) - MOVEit Transfer (VMware FT HA)

**Development Network (10.30.72.x/25):**
- **BSOAUTALB601** (10.30.72.47) - MOVEit Automation
- **BSOSQAALB601** (10.30.72.48) - MOVEit Automation SQL

**Web Admin URLs:**
- Current Primary: `https://bsoautalb002/` or `https://10.30.67.106/`
- Secondary: `https://bsoautalb001/` or `https://10.30.67.105/`

**Service Account:** `.\moveitsvc` (local account on each server)
**Password:** Validated on current primary (bsoautalb002)

**Note:** A failover has occurred. The original secondary (bsoautalb002) is now acting as primary. Web Admin is only accessible on the acting primary server.

### Documentation

- **MOVEit HA Discovery Requirements:** `docs/onsite-discovery/MOVEIT-HA-DISCOVERY-REQUIREMENTS.md`
- **Environment Diagram:** `Z:\Rick Garner\Documentation\MoveIT\Environment Diagrams\BSOC MOVEit Environment V1.08 09.07.2023.pdf`
- **Implementation:** `backend/app/moveit_ha/`
- **Discovery Scripts:** `scripts/test-moveit-*.ps1`, `scripts/discover-moveit-*.ps1`
- **Onsite Script:** `scripts/check-moveit-sql-onsite.ps1`

### Next Steps

1. ✅ Discovery complete - infrastructure documented
2. ⏳ Schedule onsite credential validation window
3. ⏳ Test monitoring queries against live servers
4. ⏳ Validate failback workflow in observe mode
5. ⏳ Obtain service account password for PowerShell remoting

---

## FreeFlow Core Integration

### Current State

```
┌─────────────────────────────────────────────────────────────────┐
│ FreeFlow Core Pair: BSOXERALB001 / BSOXERALB002                │
│ JMF Port: 7751                                                  │
│ Endpoint: /FreeFlowCore/                                        │
│ Authentication: Windows Auth (401 challenge)                    │
│ JMF Query Status: ✅ Working with DeviceFilter                  │
└─────────────────────────────────────────────────────────────────┘

Status: ✅ DISCOVERY COMPLETE - JMF Working
```

### Discovery Results

| Requirement | Status | Details |
|-------------|--------|---------|
| Correct JMF query format | ✅ Discovered | DeviceFilter required in QueryKnownDevices |
| Device enumeration | ✅ Working | KnownDevices returns printer list |
| Authenticated health check | ✅ Confirmed | 401 requires auth (not yet implemented) |
| Recovery validation | ✅ Working | Both nodes respond to JMF queries |
| Refresh soak validation | ✅ Working | Stable connectivity confirmed |

### Discovered Infrastructure

**FreeFlow Core Nodes:**
- **Primary:** `BSOXERALB001` (10.30.67.21) - JMF v8.0.0
- **Secondary:** `BSOXERALB002` (10.30.67.20) - JMF v8.1.2

**JMF Endpoints:**
- Primary: `http://BSOXERALB001:7751/FreeFlowCore`
- Secondary: `http://BSOXERALB002:7751/FreeFlowCore`
- Root: `http://BSOXERALB001:7751/`, `http://BSOXERALB002:7751/`

### Working JMF Query

```xml
<?xml version="1.0" encoding="UTF-8"?>
<JMF xmlns="http://www.CIP4.org/JDFSchema_1_1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     MaxVersion="1.6"
     SenderID="Aegis9-JMF-Diagnostic"
     TimeStamp="2026-09-21T13:16:51-04:00"
     Version="1.6">
    <Query ID="AegisKnownDevices-<GUID>"
           Type="KnownDevices"
           xsi:type="QueryKnownDevices">
        <DeviceFilter DeviceDetails="Brief"/>
    </Query>
</JMF>
```

### Confirmed Capabilities

- ✅ Network connectivity
- ✅ Port 7751
- ✅ HTTP POST
- ✅ JMF parsing
- ✅ KnownDevices (with DeviceFilter)
- ✅ Printer discovery
- ✅ Printer status/condition/faults
- ✅ Printer destinations
- ✅ Workflow/preset discovery
- ✅ Controller discovery
- ✅ Hot-folder metadata
- ✅ Core version discovery

### Not Yet Tested

- ⏳ KnownMessages
- ⏳ Job enumeration
- ⏳ Queue enumeration/status
- ⏳ Job detail query
- ⏳ Job submission
- ⏳ Hold/release
- ⏳ Retry/resubmit
- ⏳ Cancel/abort
- ⏳ Event subscriptions/signals

### Documentation

- **FreeFlow Recovery Validation:** `docs/onsite-discovery/FREEFLOW-CORE-RECOVERY-VALIDATION.md`
- **Investigation Notes:** `plans/onsite-validation-2026-09-21/freeflow-jmf-investigation-notes.md`
- **Handoff Document:** `Xerox_FreeFlow_Core_JMF_Aegis9_Handoff.md`
- **Implementation:** `backend/app/freeflow_jmf.py`
- **Test Script:** `scripts/test-freeflow-jmf.py`

### Next Steps

1. ✅ JMF connectivity and KnownDevices confirmed working
2. ⏳ Test KnownMessages capability
3. ⏳ Implement job enumeration and status queries
4. ⏳ Test job control operations (hold/release/cancel)
5. ⏳ Implement event subscription mechanism
6. ⏳ Address version mismatch (8.0.0 vs 8.1.2)

---

## Offline .NET SDK Provisioning

### Current State

```
┌─────────────────────────────────────────────────────────────────┐
│ Requirement: Offline .NET SDK/dependency image                  │
│ Purpose: C# compilation in isolated environment                 │
│ Status: Not provisioned                                         │
└─────────────────────────────────────────────────────────────────┘

Status: ⏳ BLOCKED - Offline packages not acquired
```

### Requirements

| Requirement | Status | Details |
|-------------|--------|---------|
| Offline .NET SDK | ⏳ Unknown | Must source from Microsoft |
| Dependency packages | ⏳ Unknown | Must identify required packages |
| Validation environment | ⏳ Unknown | Must create isolated test env |
| Integration with Aegis | ⏳ Unknown | Must define handoff mechanism |

### Next Steps

1. Identify required .NET SDK version for C# compilation
2. Source offline installer from Microsoft
3. Identify required dependency packages
4. Create offline package repository
5. Test compilation in isolated environment
6. Document provisioning procedure

---

## Windows Sandbox Runner

### Current State

```
┌─────────────────────────────────────────────────────────────────┐
│ Requirement: Disposable Windows Sandbox/VM runner               │
│ Purpose: External capabilities in isolated environment          │
│ Status: Not implemented                                         │
└─────────────────────────────────────────────────────────────────┘

Status: ⏳ BLOCKED - Spec not implemented
```

### Requirements

| Requirement | Status | Details |
|-------------|--------|---------|
| Sandbox spec | ⏳ Unknown | Must define isolation boundaries |
| Provisioning mechanism | ⏳ Unknown | Must create disposable VM |
| Network isolation | ⏳ Unknown | Must enforce egress controls |
| Data handoff | ⏳ Unknown | Must define secure transfer |
| Cleanup procedure | ⏳ Unknown | Must ensure no data留存 |

### Next Steps

1. Define sandbox isolation requirements
2. Implement disposable VM provisioning
3. Configure network isolation
4. Define secure data handoff mechanism
5. Implement cleanup procedure
6. Test full workflow

---

## Overall Progress

### Priority 2 Summary

| Category | Total | Completed | In Progress | Blocked |
|----------|-------|-----------|-------------|---------|
| External Integrations | 4 | 2 | 0 | 2 |

### Completed Discoveries

```
✅ MOVEit HA Discovery (2026-09-23)
   - Web Admin URLs: https://bsoautalb001/, https://bsoautalb002/
   - Service Account: .\moveitsvc
   - SQL Server: BSOSQAALB001 (10.30.67.108)
   - Infrastructure documented in storage/moveit-environment-info.json

✅ FreeFlow Core JMF Discovery (2026-09-21)
   - JMF Endpoints: http://BSOXERALB001:7751/FreeFlowCore
   - Working Query: KnownDevices with DeviceFilter
   - Confirmed Capabilities: 12 discovery operations
   - Handoff document: Xerox_FreeFlow_Core_JMF_Aegis9_Handoff.md
```

### Blocker Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│ Remaining Blockers:                                         │
│                                                             │
│ 1. MOVEit HA: Service account password                     │
│    → Requires: Onsite credential validation                │
│    → Timeline: TBD (infrastructure team coordination)      │
│                                                             │
│ 2. FreeFlow Core: Job operations testing                   │
│    → Requires: Onsite testing window                       │
│    → Timeline: TBD (after KnownMessages validation)        │
│                                                             │
│ 3. Offline .NET SDK: Package acquisition                   │
│    → Requires: Microsoft offline package source            │
│    → Timeline: Can proceed independently                   │
│                                                             │
│ 4. Windows Sandbox: Spec implementation                    │
│    → Requires: Aegis team development                      │
│    → Timeline: Can proceed independently                   │
└─────────────────────────────────────────────────────────────┘
```

### Recommendations

1. **Immediate:** Schedule MOVEit HA onsite credential validation window
2. **Short-term:** Test FreeFlow KnownMessages and job operations
3. **Parallel:** Begin offline .NET SDK provisioning
4. **Parallel:** Implement Windows Sandbox spec

---

## Related Documentation

- **Operations Monitoring:** `docs/operational-monitoring.md`
- **Operations Center Plan:** `docs/OPERATIONS-MONITORING-CENTER-PLAN.md`
- **Roadmap:** `docs/roadmap.md`
- **Protected Credentials:** `docs/PROTECTED-CREDENTIALS.md`

---

## Contact Information

| Integration | Primary Contact | Secondary Contact |
|-------------|-----------------|-------------------|
| MOVEit HA | Infrastructure Team | Aegis Team |
| FreeFlow Core | User/Onsite Team | Xerox Support |
| Offline .NET SDK | DevOps Team | Aegis Team |
| Windows Sandbox | Aegis Team | Infrastructure Team |
