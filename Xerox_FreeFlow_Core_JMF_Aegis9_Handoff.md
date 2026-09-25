# Xerox FreeFlow Core JMF Integration — Findings and Next Steps

**Purpose:** Agent handoff for continuing the FreeFlow Core integration work for Aegis 9.  
**Status:** JMF connectivity and `KnownDevices` discovery are confirmed working on both FreeFlow Core nodes.  
**Date:** 2026-09-21

---

## 1. Environment

### FreeFlow Core nodes

| Role | Server | IP | JMF Endpoint | Observed FreeFlow Core Version |
|---|---|---:|---|---:|
| Primary | `BSOXERALB001` | `10.30.67.21` | `http://BSOXERALB001:7751/FreeFlowCore` | `8.0.0` |
| Secondary | `BSOXERALB002` | `10.30.67.20` | `http://BSOXERALB002:7751/FreeFlowCore` | `8.1.2` |

Both servers also responded successfully at the root JMF endpoint:

```text
http://BSOXERALB001:7751/
http://BSOXERALB002:7751/
```

For Aegis 9, standardize on:

```text
http://<server>:7751/FreeFlowCore
```

because FreeFlow Core itself advertises workflow-specific JMF URLs beneath `/FreeFlowCore/...`.

---

## 2. Original Failure

Initial JMF `KnownDevices` requests reached the FreeFlow Core JMF gateway but returned:

```text
HTTP 500 Internal Server Error
java.lang.NullPointerException
```

The secondary server provided the precise cause:

```text
Cannot invoke
"com.xerox.jdf.jmf.messages.DeviceFilter.getDeviceDetails()"
because the return value of
"com.xerox.jdf.jmf.messages.QueryKnownDevices.getDeviceFilter()"
is null
```

The stack trace showed the request successfully reached:

```text
com.xerox.gateways.jdfjmf.common.JdfJmfGateway.processQueryKnownDevices(...)
```

### Root cause

The original request was missing a required/expected `DeviceFilter` child:

```xml
<Query ID="AegisKnownDevices001"
       Type="KnownDevices"
       xsi:type="QueryKnownDevices"/>
```

FreeFlow Core's implementation did not gracefully reject the incomplete query. Instead, it dereferenced a null `DeviceFilter` and threw a `NullPointerException`.

---

## 3. Working `KnownDevices` Request

Adding:

```xml
<DeviceFilter DeviceDetails="Brief"/>
```

fixed the request.

### Working JMF XML

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

### HTTP content type

```text
application/vnd.cip4-jmf+xml
```

### Confirmed response

Both servers returned:

```text
HTTP 200
```

and a JMF response containing:

```xml
<Response
    AgentName="FreeFlow Core"
    AgentVersion="..."
    ReturnCode="0"
    Type="KnownDevices"
    xsi:type="ResponseKnownDevices">
```

This confirms a working external JMF integration path from the client workstation to both FreeFlow Core servers.

---

## 4. Confirmed Data Available Through `KnownDevices`

The current test already proves that Aegis 9 can retrieve useful operational and configuration data from FreeFlow Core.

### 4.1 FreeFlow Core identity/version

Observed:

```text
BSOXERALB001 -> AgentVersion="8.0.0"
BSOXERALB002 -> AgentVersion="8.1.2"
```

This version mismatch should be treated as a configuration/operational finding. Do not assume both nodes expose identical JMF behavior.

---

### 4.2 Printing presses

The response contains devices with:

```text
DeviceClass="PrintingPress"
```

Examples include:

```text
C75 FFPS
314A
314B
314C
314D
314E
314F
314G
314H
314I
314J
```

The response exposes fields such as:

```text
DeviceID
DeviceCondition
DeviceStatus
StatusDetails
DescriptiveName
ModelDescription
JDFVersions
```

---

### 4.3 Printer destinations / queues

The response also contains devices with:

```text
DeviceClass="PrinterDestination"
```

Examples include:

```text
C75 FFPS
BSOC-314A_HOLD
BSOC-314B_HOLD
BSOC-314C
BSOC-314D_HOLD
BSOC-314E_HOLD
BSOC-314F_HOLD
BSOC-314G_HOLD
BSOC-314H
BSOC-314H-HOLD
BSOC-314I_HOLD
BSOC-314J_HOLD
EMedNY-314F_Hold
```

These should be modeled separately from physical presses even when the `DeviceID` is similar.

---

### 4.4 Workflow / preset discovery

FreeFlow Core returns workflow-like devices as:

```text
DeviceClass="Preset"
```

Examples observed on the primary include:

```text
Pass Through
ES-03AA Books
ES-05AA Auto-Ganged Business Cards
ES-04AA Color Manage, Proof and Print
ES-03Base Cards
ES-01AP Preflight, Optimize & Print
ES-02AA Booklets & Calendars
ES-06Base Calendars
ES-01Base Preflight & Print
ES-04Base Flyers and Letters
ES-01AA Preflight, Route, Optimize & Print
ES-01V Ganged Personalized Cards
ES-02AP Booklets with Leading Banner Page
ES-02Base Business Cards
ES-05Base Booklets
Repeatable Task
PostScript Splitter
```

Each preset includes a dedicated JMF URL, for example:

```text
http://BSOXERALB001:7751/FreeFlowCore/Pass+Through/
```

This is important for future workflow-specific JMF operations.

---

### 4.5 FreeFlow Core controller

The Core controller itself is exposed as:

```text
DeviceClass="Controller"
DeviceID="FreeFlow Core"
```

Observed state:

```text
DeviceStatus="Idle"
```

This gives Aegis 9 a direct JMF-visible representation of the Core controller.

---

### 4.6 Hot-folder paths

The FreeFlow Core controller response contains Xerox-specific `GeneralID` values using:

```text
IDUsage="XRX:JDFInputURL"
```

These reveal configured input/hot-folder locations such as:

```text
D:\Xerox\FreeFlow\Core\00000000-0000-0000-0000-000000000000\Data\Hot Folders\HBE_NOTICES
D:\Xerox\FreeFlow\Core\00000000-0000-0000-0000-000000000000\Data\Hot Folders\WTC3_Print
```

Aegis should treat these paths as configuration metadata and avoid assuming they are remotely accessible from the Aegis host.

---

### 4.7 Printer fault / attention information

The secondary server returned live-looking operational data for printer `314G`:

```text
DeviceCondition="NeedsAttention"
DeviceStatus="Stopped"
StatusDetails="Pause"
```

It also returned fault text:

```text
Add Stock to Tray 1
Print Engine Fault
```

and module data similar to:

```text
Finisher A : Top Catch Tray
Finisher A : Main Stacker
bypass-tray
```

This proves `KnownDevices` is not limited to static configuration. It can expose actionable printer condition/fault information suitable for monitoring and alerting.

---

### 4.8 Xerox submission state

Physical press records include Xerox-specific general IDs such as:

```text
IDUsage="FreeFlowCore:SubmissionStatus"
```

Observed values include:

```text
Stopped
Unknown
Idle
```

This should be captured separately from the standard JMF `DeviceStatus`.

---

## 5. Data Normalization Issues Found

The connector must preserve Xerox's raw data but normalize values used for matching.

### 5.1 Leading whitespace

The secondary returned:

```text
DeviceID=" 314F"
```

with a leading space.

Recommended model:

```csharp
RawDeviceId = value;
NormalizedDeviceId = value?.Trim();
```

Do not overwrite the raw value.

---

### 5.2 Different destination names between nodes

Examples:

Primary:

```text
BSOC-314H
```

Secondary:

```text
BSOC-314H-HOLD
```

Secondary also has:

```text
EMedNY-314F_Hold
```

Do not assume primary and secondary configuration inventories are identical.

---

### 5.3 Same physical printer may appear more than once

A physical device and a FreeFlow printer destination can share a similar or identical `DeviceID`.

Therefore a unique key should not be based solely on `DeviceID`.

Recommended composite identity:

```text
Server
+ DeviceClass
+ NormalizedDeviceId
```

Possible future refinement:

```text
Server
+ DeviceClass
+ NormalizedDeviceId
+ JMFURL
```

---

## 6. Recommended Aegis 9 Read Model

Suggested internal model:

```text
FreeFlowCoreNode
    ServerName
    Address
    CoreVersion
    JmfBaseUrl
    LastSeenUtc
    IsReachable

FreeFlowDevice
    ServerName
    RawDeviceId
    NormalizedDeviceId
    DeviceClass
    DeviceCondition
    DeviceStatus
    StatusDetails
    DescriptiveName
    ModelDescription
    JdfVersions
    JmfUrl
    SubmissionStatus
    DeviceMessages[]
    Modules[]

FreeFlowWorkflow
    ServerName
    WorkflowName
    WorkflowId
    DeviceStatus
    JmfUrl

FreeFlowHotFolder
    ServerName
    WorkflowOrController
    Path

FreeFlowModuleStatus
    ModuleId
    ModuleType
    DeviceStatus
```

Do not prematurely collapse physical presses, printer destinations, presets, and the Core controller into one UI category.

---

## 7. Immediate Next Step — Query `KnownMessages`

The next priority is to determine the JMF operations that each installed FreeFlow Core version actually advertises.

Do not assume support merely because an operation exists in the CIP4 JMF standard.

### Goal

Build an evidence-based capability matrix for:

```text
BSOXERALB001 / FreeFlow Core 8.0.0
BSOXERALB002 / FreeFlow Core 8.1.2
```

### Candidate capability categories

Investigate support for:

```text
Queries
Commands
Registrations
Signals
```

Pay particular attention to operations related to:

```text
KnownMessages
QueueStatus
SubmitQueueEntry
RequestQueueEntry
HoldQueueEntry
ResumeQueueEntry
SuspendQueueEntry
AbortQueueEntry
RemoveQueueEntry
ResubmitQueueEntry
SetQueueEntryPosition
SetQueueEntryPriority
Status
```

Again: these are candidate JMF operations, not confirmed FreeFlow Core capabilities.

---

## 8. Proposed `KnownMessages` Test

Use the standard JMF endpoint:

```text
http://<server>:7751/FreeFlowCore
```

### PowerShell test harness

```powershell
Add-Type -AssemblyName System.Net.Http

$Servers = @(
    "BSOXERALB001",
    "BSOXERALB002"
)

foreach ($Server in $Servers) {

    $Uri = "http://${Server}:7751/FreeFlowCore"

    $Timestamp = [DateTimeOffset]::Now.ToString(
        "yyyy-MM-ddTHH:mm:sszzz"
    )

    $MessageId =
        "AegisKnownMessages-$([Guid]::NewGuid().ToString('N'))"

    $Xml = @"
<?xml version="1.0" encoding="UTF-8"?>
<JMF xmlns="http://www.CIP4.org/JDFSchema_1_1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     MaxVersion="1.6"
     SenderID="Aegis9-JMF-Diagnostic"
     TimeStamp="$Timestamp"
     Version="1.6">

    <Query ID="$MessageId"
           Type="KnownMessages"
           xsi:type="QueryKnownMessages">

        <KnownMsgQuParams
            Exact="false"
            ListCommands="true"
            ListQueries="true"
            ListRegistrations="true"
            ListSignals="true"/>

    </Query>

</JMF>
"@

    Write-Host ""
    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host "Server: $Server" -ForegroundColor Cyan
    Write-Host "URL   : $Uri" -ForegroundColor Cyan
    Write-Host "Query : KnownMessages" -ForegroundColor Cyan
    Write-Host "====================================================" -ForegroundColor Cyan

    $Client = [System.Net.Http.HttpClient]::new()

    try {

        $Bytes = [System.Text.Encoding]::UTF8.GetBytes($Xml)
        $Content = [System.Net.Http.ByteArrayContent]::new($Bytes)

        $Content.Headers.ContentType =
            [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse(
                "application/vnd.cip4-jmf+xml"
            )

        Write-Host "`nREQUEST:" -ForegroundColor Yellow
        Write-Host $Xml

        $Response =
            $Client.PostAsync(
                $Uri,
                $Content
            ).GetAwaiter().GetResult()

        Write-Host ""
        Write-Host "HTTP Status: $([int]$Response.StatusCode) $($Response.ReasonPhrase)"

        $Body =
            $Response.Content.ReadAsStringAsync().GetAwaiter().GetResult()

        Write-Host "`nRESPONSE:" -ForegroundColor Green
        Write-Host $Body
    }
    catch {

        Write-Host "`nREQUEST FAILED" -ForegroundColor Red
        Write-Host $_.Exception.ToString()
    }
    finally {

        $Client.Dispose()
    }
}
```

### Important

If this exact `KnownMessages` XML is rejected, do not infer that FreeFlow Core lacks `KnownMessages`.

First determine whether the query structure differs from the JDF/JMF version implemented by FreeFlow Core 8.0/8.1.2.

Capture:

```text
HTTP status
Response body
JMF ReturnCode
Xerox/Tomcat exception text
refID
AgentVersion
```

for each server.

---

## 9. Capability Matrix to Build

Populate this only with observed results.

| Capability | BSOXERALB001 8.0.0 | BSOXERALB002 8.1.2 | Evidence |
|---|---:|---:|---|
| JMF port 7751 reachable | Confirmed | Confirmed | HTTP connection |
| `/FreeFlowCore` endpoint | Confirmed | Confirmed | HTTP 200 |
| `KnownDevices` | Confirmed | Confirmed | `ReturnCode=0` |
| Physical printer discovery | Confirmed | Confirmed | `PrintingPress` |
| Printer destination discovery | Confirmed | Confirmed | `PrinterDestination` |
| Workflow/preset discovery | Confirmed | Confirmed | `Preset` |
| Core controller discovery | Confirmed | Confirmed | `Controller` |
| Printer condition/status | Confirmed | Confirmed | JMF fields |
| Printer fault text | Not yet observed | Confirmed | 314G fault text |
| Hot-folder metadata | Confirmed | To verify fully | `XRX:JDFInputURL` |
| `KnownMessages` | Unknown | Unknown | Next test |
| Queue status/query | Unknown | Unknown | Test after discovery |
| Job query/status | Unknown | Unknown | Test after discovery |
| Submit job | Unknown | Unknown | Test only after read operations |
| Hold job | Unknown | Unknown | Test only after read operations |
| Resume job | Unknown | Unknown | Test only after read operations |
| Abort/cancel job | Unknown | Unknown | Test only after read operations |
| JMF signals/events | Unknown | Unknown | Discover first |

---

## 10. Recommended Test Order

### Phase 1 — Read-only capability discovery

1. `KnownMessages`
2. `KnownDevices` with `DeviceDetails="Details"`
3. Any advertised read-only status/query operations
4. Determine whether queue entries/jobs can be enumerated
5. Determine whether workflow-specific JMF URLs return different capabilities
6. Compare behavior between Core 8.0.0 and 8.1.2

Do not move to production-changing commands until read-only behavior is understood.

---

### Phase 2 — Build read-only Aegis monitor

Implement:

```text
Node reachability
Core version
Controller status
Physical printer inventory
Printer condition
Printer state
Printer fault text
Submission status
Printer destinations
Workflow/preset inventory
Workflow JMF URLs
Hot-folder metadata
Primary-vs-secondary configuration drift
```

Recommended polling should initially be conservative until request cost is measured.

---

### Phase 3 — Job / queue discovery

If supported by the actual FreeFlow Core JMF implementation:

```text
Enumerate queue entries
Retrieve job IDs
Retrieve job state
Retrieve job destination
Retrieve workflow/preset association
Retrieve timestamps
Retrieve failure/error state
Retrieve hold state
```

Record the exact JMF request and response schema for every operation.

---

### Phase 4 — Controlled write operations

Only after supported operations are confirmed and tested outside production job flow:

```text
Submit
Hold
Release/resume
Retry/resubmit
Cancel/abort
Remove
Reprioritize
Reposition
```

Every mutating command should require:

```text
Explicit authorization
Audit logging
Request correlation ID
Original JMF request capture
JMF response capture
Timeout handling
Idempotency/retry rules
Role/permission validation
```

Do not implement automatic cancel/retry/failover actions until the behavior is verified.

---

## 11. Aegis 9 Architecture Recommendation

Suggested connector boundary:

```text
Aegis 9
   |
   +-- FreeFlowCoreConnector
          |
          +-- FreeFlowCoreNodeClient
          |      |
          |      +-- SendJmfAsync()
          |      +-- QueryKnownDevicesAsync()
          |      +-- QueryKnownMessagesAsync()
          |      +-- future queue/job operations
          |
          +-- JmfRequestFactory
          |
          +-- JmfResponseParser
          |
          +-- FreeFlowNormalizationService
          |
          +-- FreeFlowCapabilityService
          |
          +-- FreeFlowMonitoringService
          |
          +-- FreeFlowCommandService
                 |
                 +-- disabled/read-only by default
```

### Important separation

Do not mix these responsibilities:

```text
Transport
JMF XML serialization
JMF parsing
Xerox-specific normalization
Monitoring
Mutating control operations
```

This will make it easier to deal with behavioral differences between FreeFlow Core 8.0.0 and 8.1.2.

---

## 12. Error Handling Requirements

The first test exposed a FreeFlow Core behavior worth designing around:

An incomplete/invalid query can result in:

```text
HTTP 500
```

with a Java/Tomcat exception instead of a clean JMF error response.

Therefore the connector must separately track:

```text
HTTP transport status
HTTP response media type
JMF parse success
JMF ReturnCode
Xerox/Tomcat error body
Timeout
Connection failure
Malformed XML
Unsupported message type
```

Do not treat every HTTP 500 as "server unavailable."

---

## 13. Security / Safety Requirements

Until write operations are explicitly tested and authorized, the production connector should operate in:

```text
ReadOnly = true
```

Recommended configuration:

```text
EnableMonitoring = true
EnableDiscovery = true
EnableJobQueries = false/experimental
EnableJobSubmission = false
EnableJobControl = false
```

Mutating operations should never be inferred from UI state or automatically attempted as a fallback.

---

## 14. Key Questions Still Unanswered

The next agent should determine:

1. Which JMF queries does FreeFlow Core 8.0.0 advertise?
2. Which JMF queries does FreeFlow Core 8.1.2 advertise?
3. Which commands does each version advertise?
4. Does FreeFlow Core expose job/queue enumeration?
5. Can an individual job's state be queried?
6. Are held jobs distinguishable?
7. Are workflow/preset execution states queryable?
8. Are JMF signals/events supported for asynchronous monitoring?
9. Are printer faults available consistently or only for some printer interfaces?
10. Does `DeviceDetails="Details"` expose additional useful fields?
11. Are the primary and secondary servers expected to run different Core versions?
12. Are the differing printer-destination names intentional?
13. Are hot-folder lists identical between nodes?
14. Does the primary expose the same `314G` fault detail when the device is in a fault state?
15. Does FreeFlow Core require authentication for any JMF operation beyond the currently tested discovery call?
16. Which capabilities are standard CIP4 behavior versus Xerox-specific extensions?

---

## 15. Current Conclusion

The FreeFlow Core JMF endpoint is operational and suitable for further Aegis 9 integration work.

Confirmed:

```text
Network connectivity       YES
Port 7751                  YES
HTTP POST                  YES
JMF parsing                YES
KnownDevices               YES
Printer discovery          YES
Printer status             YES
Printer condition          YES
Printer fault information  YES
Printer destinations       YES
Workflow/preset discovery  YES
Controller discovery       YES
Hot-folder metadata        YES
Core version discovery     YES
```

Not yet confirmed:

```text
KnownMessages
Job enumeration
Queue enumeration/status
Job detail query
Job submission
Hold/release
Retry/resubmit
Cancel/abort
Event subscriptions/signals
```

The immediate objective is to discover the actual supported JMF surface on **both FreeFlow Core 8.0.0 and 8.1.2**, then implement the Aegis read-only connector against only those confirmed capabilities.

---

## 16. Handoff Instruction to Next Agent

Continue from the current working state. Do **not** revisit basic port connectivity or the original missing-`DeviceFilter` issue unless new evidence contradicts the confirmed results.

Start with:

```text
KnownMessages capability discovery
```

against:

```text
http://BSOXERALB001:7751/FreeFlowCore
http://BSOXERALB002:7751/FreeFlowCore
```

For every test:

1. Save the exact XML request.
2. Save the complete HTTP response.
3. Record HTTP status.
4. Record JMF `ReturnCode`.
5. Record `AgentVersion`.
6. Record supported/unsupported behavior independently per node.
7. Do not assume behavior from the CIP4 standard alone.
8. Do not execute production-changing commands until the operation is explicitly confirmed and authorized.
9. Update the capability matrix with evidence.
10. Preserve raw Xerox identifiers before normalization.

The goal is to turn this discovery work into a production-safe Aegis 9 FreeFlow Core connector with explicit capability detection rather than hard-coded assumptions.
