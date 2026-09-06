# AEGIS 9 – MOVEit Automation HA Auto-Failback
## Complete Architecture, Implementation Plan, Provider Handoff, Test Plan, and Operations Runbook

**Document version:** 1.0
**Date:** 2026-09-06
**Status:** Phase 1/2 foundation implemented; live discovery and privileged operations pending
**Target platform:** AEGIS 9 / Jarvis Desktop codebase
**Target integration:** Progress MOVEit Automation failover pair using a shared Microsoft SQL Server database

> **2026-09-06 implementation checkpoint:** A.E.G.I.S.-9 now configures
> `BSOAUTALB001` as preferred primary and `BSOAUTALB002` as preferred secondary.
> Typed HA contracts, deterministic fail-closed state evaluation, recovery timing,
> durable local status, observe-only configuration, an API status route, and
> offline tests are implemented. Automatic failback and every privileged adapter
> operation remain disabled until the exact production environment is validated.
> See `docs/moveit-ha-implementation-status.md` for the authoritative next steps.

---

# 1. Purpose

This document defines the complete technical design for adding a continuously running **MOVEit Automation High Availability (HA) monitoring and automatic failback workflow** to AEGIS 9.

The organization currently operates two Progress MOVEit Automation servers in a licensed MOVEit failover pair:

- One server is the **preferred primary**.
- The second server is the **preferred secondary**.
- MOVEit Automation already performs automatic failover if the current primary is unavailable long enough.
- MOVEit failover is intentionally one-way: after the old primary returns, it does not automatically reclaim the primary role.
- Both MOVEit Automation nodes use the **same Microsoft SQL Server database**.

The required AEGIS 9 enhancement is:

> Continuously monitor both MOVEit Automation nodes and the HA relationship. If MOVEit fails over to the preferred secondary, allow the failover node to remain primary while service is restored. When the preferred primary returns, remains healthy for a configured stability period, and all safety conditions pass, automatically execute a controlled and auditable failback so the preferred primary becomes primary again and the preferred secondary returns to secondary status.

The solution must be visible and controllable through **AEGIS 9 Monitoring** and **AEGIS 9 Workflow supervision**.

---

# 2. Primary design goals

The implementation MUST satisfy the following goals.

1. **Preserve MOVEit's native failover behavior.**
   - AEGIS does not replace MOVEit's failover mechanism.
   - MOVEit remains responsible for detecting failure and promoting the secondary.
   - AEGIS is responsible for detecting recovery and orchestrating safe failback.

2. **Prevent split-brain and duplicate task execution.**
   - At no point may AEGIS intentionally leave both nodes operating as primary.
   - AEGIS must fail closed if the observed role state is ambiguous.
   - The preferred secondary must not be started after role reassignment until the preferred primary is verified as the active primary.

3. **Do not fail back immediately when the old primary reappears.**
   - The preferred primary must remain continuously healthy for a configurable recovery/stability interval before automatic failback is eligible.

4. **Perform a controlled task drain.**
   - The current primary must stop accepting new scheduled work and running jobs should be allowed to complete before its MOVEit service is stopped.
   - The supported MOVEit **Shut Down Service** operation should be used when possible rather than abruptly stopping the Windows service.

5. **Use the existing shared MSSQL database.**
   - No SQL database copy or database merge operation is required for failback.
   - The solution must validate that both MOVEit nodes are configured for the same database before allowing automatic failback.

6. **Integrate with AEGIS 9 rather than creating a separate automation product.**
   - Use AEGIS monitoring, workflow state, persistence, audit, cancellation, kill-switch, alerts, and UI patterns.

7. **Be durable across restarts.**
   - AEGIS must persist HA state and failback workflow state.
   - A backend restart must not result in duplicate failback attempts.

8. **Be fully auditable.**
   - Every observation that triggers a state transition and every privileged action must be recorded.
   - A complete timeline must be available after a failover/failback event.

9. **Support staged rollout.**
   - Observation only.
   - Assisted/manual failback.
   - Fully automatic failback.

10. **Do not depend on an AI model to make the safety decision.**
    - The HA controller must be deterministic.
    - The model may summarize status to an operator, but it must not decide whether a failback is safe.

---

# 3. Existing AEGIS 9 architecture to extend

Current project handoff information indicates that AEGIS 9/Jarvis Desktop already includes:

- WPF desktop client on .NET 8.
- FastAPI backend.
- SQLite persistence.
- Workflow state machine.
- Workflow approvals and supervision.
- Monitoring endpoints.
- `MonitorWindow`.
- `WorkflowWindow`.
- `MonitoringClient.cs`.
- Existing MOVEit task-catalog polling and log monitoring in `monitoring.py`.
- Server inventory configuration.
- Durable workflow concepts, scheduling, cancellation, kill switch, and audit controls.

The MOVEit HA capability should therefore be implemented as an extension of those facilities, not as a separate Windows utility that bypasses AEGIS.

Recommended integration points:

```text
backend/
└── app/
    ├── main.py
    ├── monitoring.py
    ├── storage.py
    ├── moveit_ha/
    │   ├── __init__.py
    │   ├── models.py
    │   ├── config.py
    │   ├── monitor_service.py
    │   ├── state_machine.py
    │   ├── health_adapter.py
    │   ├── moveit_admin_adapter.py
    │   ├── windows_adapter.py
    │   ├── sql_adapter.py
    │   ├── failback_workflow.py
    │   ├── locking.py
    │   ├── audit.py
    │   └── notifications.py
    └── ...

desktop/
└── Jarvis.Desktop/
    ├── MonitoringClient.cs
    ├── MonitorWindow.xaml
    ├── MonitorWindow.xaml.cs
    ├── WorkflowWindow.xaml
    ├── WorkflowWindow.xaml.cs
    ├── Models/
    │   └── MoveItHaModels.cs
    └── ...
```

The exact folder structure may be adjusted to match the live repository conventions.

---

# 4. Progress MOVEit behavior that the design relies on

The implementation provider must verify these assumptions against the exact MOVEit Automation version installed in production before enabling privileged actions.

## 4.1 Native failover

Progress documents that:

- One node is primary.
- One node is secondary.
- The primary runs tasks.
- The secondary is passive and monitors/replicates the primary.
- The secondary checks the primary periodically and can promote itself when the primary becomes unavailable.
- MOVEit uses the administrative connection between nodes to help ensure that exactly one node is primary.

This AEGIS workflow must complement that mechanism, not circumvent it.

## 4.2 Recovery of the old primary

Progress documents that after the old primary returns and detects that the former secondary is now primary, the restored old primary becomes secondary instead of automatically reclaiming primary.

That behavior is the reason AEGIS failback is required.

## 4.3 MSSQL resynchronization/failback procedure

Progress documents an MSSQL resynchronization procedure for deliberately making the original primary primary again. The documented sequence includes:

1. Stop the MOVEit Automation service on the current secondary.
2. Stop the MOVEit Automation service on the current primary, using the MOVEit Admin **Shut Down Service** command if tasks may be running.
3. If manual synchronization is required, synchronize:
   - `miccfg.xml`
   - StateFiles
   - PGPPath
4. Set the desired new primary's startup role to Primary and perform **Clear Admin Rep**.
5. Set the desired new secondary's startup role to Secondary and perform **Clear Admin Rep**.
6. Start the desired primary.
7. Verify that it actually became primary.
8. Start the desired secondary.

AEGIS must implement the logical equivalent of this supported procedure.

## 4.4 Shared MSSQL configuration

Progress documents the failover registry area:

```text
HKEY_LOCAL_MACHINE\Software\Standard Networks\MOVEitCentral\Resil
```

Relevant documented values include:

```text
Node
StartupRole
OtherHost
SuppressDBRep
```

Progress documents:

```text
StartupRole = 1  -> Primary
StartupRole = 2  -> Secondary
```

and indicates that `SuppressDBRep=1` is appropriate when both nodes share the same database infrastructure instead of maintaining separate replicated databases.

AEGIS must verify the environment before using this assumption.

## 4.5 Clear Admin Rep

Progress documentation states that the **Clear Admin Rep** operation clears administrative replication commands waiting to be replicated. Older/current administrator documentation identifies the underlying backlog file as `MICMisc.blg`.

**Implementation rule:** Prefer the supported MOVEit management/configuration mechanism. Direct deletion of an internal file must be treated as a fallback implementation detail and must not be enabled in production unless the exact installed MOVEit version is validated and the approach is approved by the organization/Progress support.

## 4.6 Graceful shutdown

Progress documents **Shut Down Service** as the preferred way to cleanly stop an active MOVEit server:

- scheduler is disabled,
- running scheduled tasks are allowed to finish,
- service stops after tasks are complete.

Abruptly stopping the Windows service can terminate active jobs.

Therefore the provider must implement a supported remote/admin method to invoke this operation, or implement an equivalent safely validated administrative API action for the installed version.

---

# 5. High-level architecture

```text
                         ┌──────────────────────────┐
                         │       AEGIS 9 UI         │
                         │                          │
                         │ MonitorWindow            │
                         │ WorkflowWindow           │
                         │ Alerts / History         │
                         │ Pause / Resume           │
                         │ Failback Now             │
                         └────────────┬─────────────┘
                                      │ HTTPS/local API
                                      ▼
                    ┌──────────────────────────────────────┐
                    │            AEGIS Backend             │
                    │                                      │
                    │ MOVEit HA Monitor Service            │
                    │  - periodic read-only observation    │
                    │                                      │
                    │ HA State Machine                     │
                    │  - deterministic role/recovery logic │
                    │                                      │
                    │ Failback Workflow Runner             │
                    │  - durable privileged workflow       │
                    │                                      │
                    │ Exclusive HA Lock                    │
                    │ Audit / Events / Alerts              │
                    └──────┬─────────────┬───────────┬─────┘
                           │             │           │
             Admin/WinRM   │             │           │ SQL/read-only
                           │             │           │ validation
                           ▼             ▼           ▼
                  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
                  │  MOVEIT01    │ │  MOVEIT02    │ │ SQL SERVER   │
                  │ Preferred    │ │ Preferred    │ │ Shared DB    │
                  │ Primary      │ │ Secondary    │ │              │
                  └──────────────┘ └──────────────┘ └──────────────┘
```

---

# 6. Critical separation: monitor loop vs. failback workflow

The system should contain two different execution mechanisms.

## 6.1 Continuous HA monitor

Purpose:

- lightweight,
- read-only,
- repeatable,
- frequent,
- never changes MOVEit state.

Recommended interval:

```text
10 seconds
```

The monitor:

1. Reads both node health states.
2. Reads current roles.
3. Validates partner connectivity.
4. Validates MOVEit service health.
5. Validates shared SQL connectivity/configuration.
6. Updates a persisted HA snapshot.
7. Feeds the deterministic HA state machine.
8. Generates alerts/state transitions when necessary.
9. Starts a durable failback workflow only when eligibility changes from false to true.

The monitor must NOT create a new workflow run every poll.

## 6.2 Durable failback workflow

Created only when:

- the pair previously failed over,
- the preferred primary has recovered,
- the preferred primary has remained healthy for the required stability period,
- all failback eligibility gates pass,
- automatic failback is enabled,
- the global automation kill switch is not active,
- no failback workflow is already active,
- cooldown rules allow a new attempt.

Once created, it becomes a persisted AEGIS workflow run with:

- run ID,
- start/end times,
- state,
- current step,
- audit trail,
- evidence,
- errors,
- cancellation state,
- rollback/recovery path.

---

# 7. HA state model

AEGIS should use explicit persisted states.

Recommended enum:

```text
UNKNOWN
HEALTHY_PREFERRED
PREFERRED_UNREACHABLE
NATIVE_FAILOVER_PENDING
FAILED_OVER
PREFERRED_RECOVERED
STABILITY_WAIT
FAILBACK_ELIGIBLE

FAILBACK_LOCKED
DRAINING_CURRENT_PRIMARY
STOPPING_PREFERRED_SECONDARY
STOPPING_CURRENT_PRIMARY
VERIFYING_BOTH_STOPPED
SYNCHRONIZING_NODE_STATE
SETTING_STARTUP_ROLES
CLEARING_ADMIN_REPLICATION
STARTING_PREFERRED_PRIMARY
VERIFYING_PREFERRED_PRIMARY
STARTING_PREFERRED_SECONDARY
VERIFYING_FINAL_PAIR

FAILBACK_COMPLETE
FAILBACK_ABORTED
FAILBACK_FAILED
ROLLBACK_IN_PROGRESS
MANUAL_INTERVENTION_REQUIRED

CONFIGURATION_INVALID
AUTO_FAILBACK_PAUSED
KILL_SWITCH_ACTIVE
MAINTENANCE_SUPPRESSED
COOLDOWN
```

---

# 8. Node role terminology

Avoid ambiguous terms like "primary server" in code.

Use four explicit concepts:

```text
preferred_primary
preferred_secondary
runtime_primary
runtime_secondary
```

Example:

```text
preferred_primary = MOVEIT01
preferred_secondary = MOVEIT02

after native failover:
runtime_primary = MOVEIT02
runtime_secondary = MOVEIT01
```

This prevents a common HA programming error where configuration intent is confused with current runtime state.

---

# 9. HA state transitions

## 9.1 Normal state

Expected:

```text
MOVEIT01 = healthy, runtime primary
MOVEIT02 = healthy, runtime secondary
```

State:

```text
HEALTHY_PREFERRED
```

Action:

```text
Monitor only.
```

## 9.2 Preferred primary becomes unavailable

Observed:

```text
MOVEIT01 = unhealthy/unreachable
MOVEIT02 = still secondary or transition unknown
```

State:

```text
PREFERRED_UNREACHABLE
```

AEGIS action:

- alert,
- monitor,
- do NOT promote MOVEIT02,
- allow MOVEit native failover to operate.

## 9.3 MOVEit native failover occurs

Observed:

```text
MOVEIT01 = unavailable
MOVEIT02 = runtime primary
```

State:

```text
FAILED_OVER
```

AEGIS action:

- record failover time,
- identify current primary,
- display degraded HA status,
- continue monitoring.

## 9.4 Preferred primary returns

Observed:

```text
MOVEIT01 = healthy and runtime secondary
MOVEIT02 = healthy and runtime primary
```

State:

```text
PREFERRED_RECOVERED
```

Start stability timer.

## 9.5 Stability timer

State:

```text
STABILITY_WAIT
```

Requirement:

Preferred primary must remain continuously healthy for the complete configured interval.

Recommended default:

```text
15 minutes
```

Any health failure resets the timer.

## 9.6 Eligible for failback

State:

```text
FAILBACK_ELIGIBLE
```

AEGIS now performs a complete preflight evaluation.

If automatic mode is:

```text
observe
```

then alert only.

If mode is:

```text
assisted
```

then display:

```text
Failback ready
```

and require an authorized operator to choose **Failback Now**.

If mode is:

```text
automatic
```

then create the durable failback workflow.

---

# 10. Configuration schema

Recommended configuration file:

```text
config/moveit-ha.json
```

Example:

```json
{
  "enabled": true,
  "mode": "observe",

  "pairId": "production-moveit-ha",

  "preferredPrimary": {
    "name": "MOVEIT01",
    "hostname": "<preferred-primary-fqdn>",
    "nodeNumber": 1
  },

  "preferredSecondary": {
    "name": "MOVEIT02",
    "hostname": "<preferred-secondary-fqdn>",
    "nodeNumber": 2
  },

  "database": {
    "type": "mssql",
    "sharedDatabaseRequired": true,
    "server": "<sql-server>",
    "database": "<moveit-database>",
    "requireSuppressDbRep": true
  },

  "monitoring": {
    "pollIntervalSeconds": 10,
    "requestTimeoutSeconds": 5,
    "consecutiveFailuresForUnhealthy": 3,
    "consecutiveSuccessesForRecovered": 3,
    "preferredPrimaryStabilitySeconds": 900
  },

  "failback": {
    "enabled": false,
    "cooldownMinutes": 60,
    "maximumAutomaticAttemptsPerIncident": 1,
    "drainTimeoutMinutes": 30,
    "serviceStopTimeoutSeconds": 120,
    "serviceStartTimeoutSeconds": 180,
    "postPrimaryStartValidationSeconds": 60,
    "postPairValidationSeconds": 120,
    "requireNoRunningTasks": true,
    "requireSharedSqlValidation": true,
    "requireRuntimeRoleValidation": true,
    "requirePartnerCommunication": true
  },

  "safety": {
    "failClosed": true,
    "globalKillSwitchHonored": true,
    "maintenanceModePreventsFailback": true,
    "manualLockoutSupported": true,
    "requireExclusiveLock": true
  },

  "notifications": {
    "onFailover": true,
    "onRecovery": true,
    "onFailbackEligible": true,
    "onFailbackStart": true,
    "onFailbackSuccess": true,
    "onFailbackFailure": true
  }
}
```

Initial production deployment must use:

```json
"mode": "observe",
"failback": {
  "enabled": false
}
```

until the observation and assisted phases pass acceptance testing.

---

# 11. Health model

A node is not considered healthy merely because it answers ICMP.

Recommended `MoveItNodeHealth` model:

```text
timestamp
hostname
dns_resolved
network_reachable
windows_remote_management_reachable
moveit_service_state
moveit_admin_endpoint_reachable
moveit_runtime_role
startup_role
node_number
other_host
suppress_db_rep
sql_server
sql_database
sql_connectivity
partner_link_state
configuration_version/hash
moveit_version
running_task_count
scheduler_state
last_error
health_score
health_state
```

## 11.1 Required health gates

Before a node can be called `Healthy`:

```text
MOVEit service state is Running
AND
MOVEit administrative endpoint responds
AND
runtime role is authoritative/known
AND
SQL database is reachable
AND
failover configuration matches expected pair
AND
MOVEit version compatibility is acceptable
```

For the preferred primary recovery timer, all required gates must remain valid continuously.

---

# 12. Runtime role detection

Runtime role detection is safety-critical.

The implementation provider must identify the **authoritative supported mechanism for the installed MOVEit version**.

Preferred order:

1. Supported MOVEit Web Admin/API/administrative endpoint that explicitly reports failover status.
2. Supported MOVEit administrative protocol/client operation.
3. Supported command or local management API exposed by the installed version.
4. Read-only local system evidence only as a fallback, provided that it can unambiguously identify runtime role and is validated against Web Admin.

Do NOT infer runtime primary solely from:

```text
StartupRole
```

because `StartupRole` is desired startup behavior, not necessarily proof of the current runtime role after failover.

Automatic failback MUST remain disabled until runtime role detection is proven reliable.

---

# 13. Shared SQL validation

Before automatic failback can be armed, AEGIS must prove:

```text
Node A SQL server == Node B SQL server
Node A database   == Node B database
database type     == MSSQL
SuppressDBRep     == 1 on Node A
SuppressDBRep     == 1 on Node B
```

Where SQL connection strings contain credentials, the password must never be exposed in:

- UI,
- logs,
- workflow evidence,
- API responses,
- model prompts.

Only sanitized database identity should be persisted:

```text
server
database
authentication_mode
connectivity_state
```

---

# 14. Privileged operations adapter

All state-changing MOVEit/Windows operations should be behind one allowlisted fixed-function adapter.

Recommended interface:

```python
class MoveItHaAdminAdapter:
    async def graceful_shutdown_current_primary(self, node): ...
    async def stop_secondary_service(self, node): ...
    async def set_startup_role(self, node, role): ...
    async def clear_admin_replication(self, node): ...
    async def start_service(self, node): ...
    async def verify_runtime_role(self, node, expected_role): ...
    async def get_running_tasks(self, node): ...
```

This prevents arbitrary PowerShell execution from becoming part of the workflow.

The adapter should expose specific functions, not:

```text
execute_any_powershell(command)
```

---

# 15. Privilege model

The AEGIS backend/service account should have only the rights required to:

- query Windows services on the two MOVEit nodes,
- query failover configuration,
- invoke the approved MOVEit administrative shutdown action,
- start/stop the MOVEit Automation service,
- modify only the documented failover role setting if that approach is approved,
- invoke/perform the approved Clear Admin Rep operation,
- read required state synchronization metadata,
- access no unrelated servers.

Use:

- dedicated AD/gMSA/service identity where possible,
- constrained PowerShell remoting or JEA if WinRM is used,
- firewall allowlists,
- least privilege,
- no interactive logon,
- protected secrets.

---

# 16. Preauthorized workflow policy

Automatic failback requires privileged actions without a human approval prompt every time.

Do not disable AEGIS approval controls globally.

Create one narrow policy:

```text
policy_id: moveit-ha-auto-failback
```

Permitted targets:

```text
preferred MOVEit node
secondary MOVEit node
configured MOVEit SQL identity for read-only health validation
```

Permitted actions:

```text
read health
read failover configuration
read runtime role
read scheduler/running-task status
invoke graceful MOVEit shutdown
stop MOVEit service
set startup role
clear Admin replication backlog
start MOVEit service
verify topology
```

Any action outside this allowlist must be denied.

---

# 17. Exclusive lock

A failback must have an exclusive distributed/durable lock.

Example lock:

```text
resource = "moveit-ha:production-moveit-ha"
owner = workflow_run_id
expires = controlled lease
```

Required semantics:

- only one active failback per pair,
- lock survives transient process restarts,
- lock state stored in AEGIS persistence,
- stale lock takeover requires explicit safety checks,
- lock is not automatically discarded merely because a process crashed.

The lock prevents:

- two backend workers initiating failback,
- manual and automatic failback running simultaneously,
- duplicate failback after restart.

---

# 18. Failback eligibility gates

Every gate must pass.

```text
G01  HA configuration valid
G02  automatic failback enabled
G03  global kill switch inactive
G04  maintenance suppression inactive
G05  no active failback workflow
G06  cooldown expired
G07  current runtime primary is preferred secondary
G08  recovered node is preferred primary
G09  recovered node runtime role is secondary
G10  preferred primary healthy
G11  preferred primary stability timer complete
G12  current primary healthy
G13  shared MSSQL configuration confirmed
G14  SQL reachable
G15  SuppressDBRep validated on both nodes
G16  partner communication healthy
G17  MOVEit versions compatible
G18  no ambiguous role state
G19  exclusive HA lock acquired
G20  no manual operator lockout
```

Any failure results in:

```text
NO FAILBACK
```

with a human-readable reason.

---

# 19. Controlled failback workflow

## Step 0 – Create incident/workflow context

Record:

```text
workflow_run_id
incident_id
native_failover_detected_at
preferred_primary_recovered_at
stability_completed_at
current_runtime_primary
target_runtime_primary
configuration_snapshot_hash
```

## Step 1 – Acquire exclusive HA lock

If lock cannot be acquired:

```text
FAILBACK_ABORTED
reason = existing operation
```

## Step 2 – Final preflight revalidation

Re-read everything.

Expected immediately before failback:

```text
preferred primary   = healthy, runtime SECONDARY
preferred secondary = healthy, runtime PRIMARY
shared SQL          = healthy
```

Never rely on a health snapshot from several minutes earlier.

## Step 3 – Freeze external automation actions

AEGIS should prevent another remediation workflow from changing either MOVEit node until the HA workflow completes.

## Step 4 – Drain current runtime primary

Current runtime primary is the preferred secondary.

Required action:

```text
disable scheduling
wait for running scheduler-started tasks to complete
stop MOVEit service cleanly
```

Preferred mechanism:

```text
MOVEit Admin -> Shut Down Service
```

Monitor:

```text
scheduler state
running task count
service state
```

If tasks do not complete before timeout:

Default behavior:

```text
ABORT FAILBACK
```

Do not kill production file transfers automatically unless a separate explicit policy is later approved.

Note that MOVEit documentation warns that certain Next Action/looped jobs may require separate handling. The provider must determine how to detect these for the installed version.

## Step 5 – Stop preferred-primary service

The recovered preferred primary is currently secondary.

Stop its MOVEit Automation service.

## Step 6 – Verify both services stopped

Hard gate:

```text
MOVEIT01 MOVEit service = Stopped
MOVEIT02 MOVEit service = Stopped
```

If not:

```text
ABORT
MANUAL_INTERVENTION_REQUIRED
```

Do not modify roles while one MOVEit service is still active unless Progress documentation for the exact version explicitly permits it.

## Step 7 – Synchronize/validate node-local state

Progress MSSQL resynchronization documentation identifies:

```text
miccfg.xml
StateFiles
PGPPath
```

as state/configuration that may need synchronization.

Preferred AEGIS behavior:

1. Determine whether native administrative replication has already synchronized the recovered node.
2. Compare safe metadata/hashes.
3. If synchronized, continue.
4. If not synchronized:
   - use the supported synchronization method for the installed version, or
   - abort and require manual intervention if no validated automated method exists.

Do not blindly overwrite encrypted MOVEit configuration files.

Important:

- Key material and local registry configuration must be handled carefully.
- Never copy KeyMat values unless a documented/approved maintenance procedure requires it.
- Never log encryption keys.

## Step 8 – Set preferred startup roles

Desired:

```text
MOVEIT01 StartupRole = Primary
MOVEIT02 StartupRole = Secondary
```

Progress documents:

```text
1 = Primary
2 = Secondary
```

Implementation method must be version-approved.

Preferred order:

1. supported configuration API/tool,
2. approved automation of Config Utility semantics,
3. direct documented registry update only after exact-version validation.

Record old values before modification.

## Step 9 – Clear Admin replication backlog

Perform the equivalent of:

```text
Clear Admin Rep
```

on both nodes.

Do not clear SQL replication as part of routine shared-MSSQL failback unless the installed-version procedure specifically requires it.

Record:

```text
operation
node
time
success/failure
```

Never expose internal sensitive state.

## Step 10 – Start preferred primary only

Start MOVEit on the preferred primary.

Keep preferred secondary stopped.

## Step 11 – Verify preferred primary

Hard validation gate.

Required:

```text
service = running
administrative endpoint = healthy
runtime role = PRIMARY
SQL = healthy
configuration = valid
```

Wait for configured post-start stabilization time.

Recommended:

```text
60 seconds
```

If runtime role is not definitively PRIMARY:

```text
DO NOT START SECONDARY
```

Transition to recovery/rollback logic.

## Step 12 – Start preferred secondary

Only after Step 11 is proven.

Start MOVEit on preferred secondary.

## Step 13 – Verify final pair

Required final topology:

```text
MOVEIT01
  service = running
  runtime role = PRIMARY
  startup role = PRIMARY

MOVEIT02
  service = running
  runtime role = SECONDARY
  startup role = SECONDARY

shared SQL = healthy
partner relationship = healthy
```

## Step 14 – Post-failback hold

Observe continuously for a configured validation interval.

Recommended:

```text
120 seconds
```

No unexpected role changes may occur.

## Step 15 – Complete workflow

State:

```text
FAILBACK_COMPLETE
```

Record:

```text
duration
all actions
final topology
health evidence
incident linkage
```

Send success notification.

---

# 20. Rollback and failure behavior

Automatic rollback must be conservative.

The workflow must never create a new unsafe topology in an attempt to recover from an uncertain topology.

## 20.1 Failure before both services stop

If failure occurs before role changes:

- leave current runtime primary active if it is still safely operating,
- release only safe workflow locks,
- mark failback aborted,
- alert operator.

## 20.2 Failure after both services are stopped but before new primary starts

If roles were changed but preferred primary cannot start:

1. Keep preferred secondary stopped.
2. Determine whether the preferred primary can be safely restored.
3. If not, execute a prevalidated rollback procedure to restore:
   - preferred secondary startup role = Primary,
   - preferred primary startup role = Secondary,
   - required admin replication clearing,
   - start preferred secondary,
   - verify it is runtime primary.
4. Start preferred primary only after secondary-primary is proven, if appropriate.

If any role is ambiguous:

```text
MANUAL_INTERVENTION_REQUIRED
```

No guessing.

## 20.3 Failure after preferred primary becomes primary

If preferred primary is proven primary but secondary fails to start:

- leave preferred primary running,
- mark HA degraded,
- do not undo a healthy primary solely because secondary startup failed,
- alert operator,
- continue monitoring secondary recovery.

## 20.4 Ambiguous role state

Examples:

```text
both report primary
both roles unknown
partner communication lost during transition
one node cannot be queried
```

Action:

```text
stop automatic state-changing actions
preserve safest known running node
raise CRITICAL alert
require operator intervention
```

---

# 21. AEGIS monitoring UI

Add a dedicated MOVEit HA panel to `MonitorWindow`.

Example:

```text
┌──────────────── MOVEIT AUTOMATION HA ────────────────┐
│ Overall              HEALTHY                         │
│                                                      │
│ Preferred Primary    MOVEIT01                        │
│ Runtime Primary      MOVEIT01                        │
│                                                      │
│ MOVEIT01                                             │
│   Role               PRIMARY                         │
│   Service            RUNNING                         │
│   MOVEit             HEALTHY                         │
│   SQL                HEALTHY                         │
│   Partner Link       HEALTHY                         │
│                                                      │
│ MOVEIT02                                             │
│   Role               SECONDARY                       │
│   Service            RUNNING                         │
│   MOVEit             HEALTHY                         │
│   SQL                HEALTHY                         │
│   Partner Link       HEALTHY                         │
│                                                      │
│ Auto Failback        ARMED                           │
│ Last Failover        2026-09-05 23:17                │
│ Last Failback        2026-09-06 00:04 SUCCESS        │
│                                                      │
│ [Pause Auto-Failback] [Failback Now] [History]       │
└──────────────────────────────────────────────────────┘
```

## 21.1 During failover

```text
Overall              DEGRADED
Runtime Primary      MOVEIT02
Preferred Primary    MOVEIT01
Preferred Status     UNAVAILABLE
Auto Failback        WAITING FOR RECOVERY
```

## 21.2 During recovery timer

```text
Preferred Status     RECOVERED
Runtime Role         SECONDARY

Recovery stability:
10:42 / 15:00
```

## 21.3 During failback

```text
FAILBACK IN PROGRESS

Step 10 of 15
Starting preferred primary...

MOVEIT01  STARTING
MOVEIT02  STOPPED

DO NOT MANUALLY START MOVEIT02
```

---

# 22. WorkflowWindow integration

`WorkflowWindow` should show the detailed failback run:

```text
Run ID
Incident ID
Started
Current state
Current step
Operator / trigger source
Automatic/manual mode
Current runtime primary
Target primary
```

Timeline example:

```text
02:14:10  Preferred primary health restored
02:29:10  Stability period complete
02:29:11  Failback workflow created
02:29:11  Exclusive lock acquired
02:29:12  Preflight passed
02:29:13  Current primary drain requested
02:31:02  Running tasks = 0
02:31:05  Current primary stopped
02:31:08  Preferred primary stopped
02:31:10  Both nodes confirmed stopped
02:31:13  Startup roles set
02:31:15  Admin replication state cleared
02:31:18  Preferred primary starting
02:32:18  Preferred primary verified PRIMARY
02:32:20  Secondary started
02:33:10  Pair verified
02:35:10  Post-failback validation complete
02:35:11  SUCCESS
```

---

# 23. API design

Exact route naming should match current AEGIS conventions.

Recommended endpoints:

## Read-only

```http
GET /api/monitoring/moveit-ha
GET /api/monitoring/moveit-ha/nodes
GET /api/monitoring/moveit-ha/history
GET /api/monitoring/moveit-ha/incidents/{incident_id}
GET /api/monitoring/moveit-ha/runs/{run_id}
```

## Configuration

```http
GET  /api/monitoring/moveit-ha/config
PUT  /api/monitoring/moveit-ha/config
```

Changes must require authorized administrator access.

## Operator controls

```http
POST /api/monitoring/moveit-ha/pause
POST /api/monitoring/moveit-ha/resume
POST /api/monitoring/moveit-ha/failback
POST /api/monitoring/moveit-ha/cancel/{run_id}
POST /api/monitoring/moveit-ha/revalidate
```

Manual failback endpoint must still use the same preflight gates.

---

# 24. Suggested API response

```json
{
  "pairId": "production-moveit-ha",
  "state": "STABILITY_WAIT",
  "severity": "warning",
  "preferredPrimary": "MOVEIT01",
  "runtimePrimary": "MOVEIT02",
  "autoFailback": {
    "mode": "automatic",
    "enabled": true,
    "paused": false,
    "eligible": false,
    "reason": "Preferred primary stability timer in progress"
  },
  "recovery": {
    "startedAt": "2026-09-06T02:10:00-04:00",
    "requiredSeconds": 900,
    "healthySeconds": 642
  },
  "nodes": [
    {
      "name": "MOVEIT01",
      "preferredRole": "primary",
      "runtimeRole": "secondary",
      "service": "running",
      "moveit": "healthy",
      "sql": "healthy",
      "partnerLink": "healthy"
    },
    {
      "name": "MOVEIT02",
      "preferredRole": "secondary",
      "runtimeRole": "primary",
      "service": "running",
      "moveit": "healthy",
      "sql": "healthy",
      "partnerLink": "healthy"
    }
  ]
}
```

---

# 25. Persistence model

Recommended new tables or equivalents.

## `moveit_ha_pairs`

```text
id
pair_id
enabled
mode
preferred_primary
preferred_secondary
config_json
created_at
updated_at
```

## `moveit_ha_state`

```text
pair_id
state
severity
runtime_primary
runtime_secondary
incident_id
recovery_started_at
stability_started_at
last_poll_at
last_transition_at
state_payload_json
```

## `moveit_ha_incidents`

```text
incident_id
pair_id
detected_at
failover_at
preferred_recovered_at
failback_eligible_at
failback_started_at
resolved_at
result
details_json
```

## `moveit_ha_workflow_runs`

Reuse the existing generic workflow-run table if appropriate.

Additional metadata:

```text
pair_id
incident_id
trigger_type
preflight_snapshot
current_step
result
```

## `moveit_ha_events`

```text
event_id
pair_id
incident_id
run_id
timestamp
severity
event_type
node
message
evidence_json
previous_hash
event_hash
```

Reuse existing AEGIS hash-linked audit infrastructure when available.

---

# 26. Event taxonomy

Recommended events:

```text
MOVEIT_HA_POLL
MOVEIT_NODE_UNHEALTHY
MOVEIT_NODE_RECOVERED
MOVEIT_NATIVE_FAILOVER_DETECTED
MOVEIT_RECOVERY_TIMER_STARTED
MOVEIT_RECOVERY_TIMER_RESET
MOVEIT_FAILBACK_ELIGIBLE
MOVEIT_FAILBACK_STARTED
MOVEIT_FAILBACK_PREFLIGHT_FAILED
MOVEIT_DRAIN_STARTED
MOVEIT_DRAIN_COMPLETE
MOVEIT_SERVICE_STOPPED
MOVEIT_ROLES_UPDATED
MOVEIT_ADMIN_REP_CLEARED
MOVEIT_PREFERRED_PRIMARY_STARTED
MOVEIT_PREFERRED_PRIMARY_VERIFIED
MOVEIT_SECONDARY_STARTED
MOVEIT_PAIR_VERIFIED
MOVEIT_FAILBACK_COMPLETE
MOVEIT_FAILBACK_ABORTED
MOVEIT_FAILBACK_FAILED
MOVEIT_ROLLBACK_STARTED
MOVEIT_ROLLBACK_COMPLETE
MOVEIT_MANUAL_INTERVENTION_REQUIRED
MOVEIT_AUTO_FAILBACK_PAUSED
MOVEIT_AUTO_FAILBACK_RESUMED
```

---

# 27. Monitoring loop pseudocode

```python
async def monitor_loop(pair):
    while service_running:
        if global_shutdown:
            break

        snapshot = await collect_pair_health(pair)
        await persist_snapshot(snapshot)

        state = await state_machine.evaluate(snapshot)

        if state.changed:
            await audit_state_transition(state)
            await publish_monitoring_update(state)

        if state.failback_eligible:
            if await should_start_failback(pair, state):
                await enqueue_failback_workflow(
                    pair_id=pair.id,
                    incident_id=state.incident_id
                )

        await sleep(pair.poll_interval_seconds)
```

Important:

```text
collect_pair_health()
```

must be deterministic and read-only.

---

# 28. State machine pseudocode

```python
if config_invalid:
    return CONFIGURATION_INVALID

if kill_switch:
    return KILL_SWITCH_ACTIVE

if paused:
    return AUTO_FAILBACK_PAUSED

if preferred_primary_is_runtime_primary and secondary_is_runtime_secondary:
    clear_recovery_timer()
    return HEALTHY_PREFERRED

if preferred_primary_unhealthy and secondary_is_runtime_primary:
    return FAILED_OVER

if (
    preferred_primary_healthy
    and preferred_primary_runtime_role == SECONDARY
    and preferred_secondary_runtime_role == PRIMARY
):
    if recovery_timer_not_started:
        start_recovery_timer()
        return PREFERRED_RECOVERED

    if preferred_primary_health_broke_since_timer:
        reset_recovery_timer()
        return FAILED_OVER

    if stability_elapsed < required_stability:
        return STABILITY_WAIT

    if all_failback_gates_pass:
        return FAILBACK_ELIGIBLE

return UNKNOWN
```

---

# 29. Failback workflow pseudocode

```python
async def run_failback(ctx):

    lock = await acquire_ha_lock(ctx.pair_id)
    if not lock:
        return abort("HA lock unavailable")

    try:
        await transition(FAILBACK_LOCKED)

        preflight = await perform_preflight()
        if not preflight.safe:
            return abort(preflight.reason)

        await transition(DRAINING_CURRENT_PRIMARY)
        await graceful_shutdown(runtime_primary)

        await transition(STOPPING_PREFERRED_SECONDARY)
        await stop_service(preferred_primary)

        await transition(VERIFYING_BOTH_STOPPED)
        require(await both_services_stopped())

        await transition(SYNCHRONIZING_NODE_STATE)
        require(await validate_or_sync_node_state())

        await transition(SETTING_STARTUP_ROLES)
        await set_role(preferred_primary, PRIMARY)
        await set_role(preferred_secondary, SECONDARY)

        await transition(CLEARING_ADMIN_REPLICATION)
        await clear_admin_rep(preferred_primary)
        await clear_admin_rep(preferred_secondary)

        await transition(STARTING_PREFERRED_PRIMARY)
        await start_service(preferred_primary)

        await transition(VERIFYING_PREFERRED_PRIMARY)
        require(await verify_runtime_primary(preferred_primary))

        await transition(STARTING_PREFERRED_SECONDARY)
        await start_service(preferred_secondary)

        await transition(VERIFYING_FINAL_PAIR)
        require(await verify_final_pair())

        await transition(FAILBACK_COMPLETE)
        return success()

    except UnsafeState as exc:
        await fail_closed(exc)
        return failed(exc)

    finally:
        await release_lock_when_safe(lock)
```

---

# 30. Security requirements

## 30.1 Secrets

Never store secrets in:

```text
moveit-ha.json
source control
UI
workflow logs
audit evidence
model prompts
```

Use the existing AEGIS secret mechanism or Windows-protected credential store.

## 30.2 Remote administration

If PowerShell remoting is used:

- use HTTPS WinRM if required by policy,
- firewall source to the AEGIS service host only,
- use Kerberos/domain authentication,
- prefer JEA/constrained endpoints,
- disable arbitrary command execution.

## 30.3 API authorization

Only administrators should be able to:

```text
change HA configuration
enable automatic failback
pause/resume
invoke Failback Now
cancel a privileged run
clear manual intervention state
```

Read-only HA visibility may follow the existing AEGIS monitoring permission model.

---

# 31. Kill-switch behavior

The existing AEGIS global automation kill switch must prevent creation of new automatic failback runs.

If the kill switch becomes active while a failback is already executing:

- do not blindly terminate the workflow in the middle of a dangerous state transition,
- transition into a controlled cancellation path,
- complete only the minimum operations necessary to reach a known safe topology,
- then stop.

This is different from canceling an ordinary non-infrastructure workflow.

---

# 32. Manual pause and maintenance windows

Support:

```text
AutoFailbackPaused = true/false
```

and optional maintenance windows.

Use cases:

- MOVEit upgrade,
- Windows patching,
- SQL maintenance,
- DR exercise,
- network maintenance,
- Progress support troubleshooting.

During maintenance suppression:

- continue monitoring,
- continue recording events,
- do not automatically fail back.

Display:

```text
AUTO FAILBACK SUPPRESSED - MAINTENANCE
```

---

# 33. Cooldown and anti-flapping controls

Recommended defaults:

```text
poll interval                  10 seconds
unhealthy confirmation        3 consecutive failed observations
recovery confirmation         3 consecutive successful observations
recovery stability            15 minutes
automatic attempt limit       1 per incident
post-failback cooldown         60 minutes
```

If the preferred primary becomes unstable during the 15-minute timer:

```text
reset timer to zero
```

Do not accumulate healthy intervals across failures.

---

# 34. Alerting

AEGIS should generate alerts for:

## Informational

```text
Preferred primary recovered
Recovery stability timer started
Failback completed
```

## Warning

```text
Native failover detected
Preferred topology not active
Auto failback paused
Recovery timer reset
Secondary failed after successful failback
```

## Critical

```text
Ambiguous runtime roles
Both nodes appear primary
Shared SQL validation failed
Failback failed after role modification
Unable to establish safe runtime primary
Rollback failed
Manual intervention required
```

Integrate with existing AEGIS notification mechanisms.

---

# 35. Voice/UI behavior

If AEGIS 9 voice is enabled, voice notifications should be concise and operational.

Examples:

```text
"MOVEit failover detected. MOVEIT02 is now primary."
```

```text
"MOVEIT01 has recovered. Automatic failback validation has started."
```

```text
"MOVEit failback completed. MOVEIT01 is primary and MOVEIT02 is secondary."
```

For critical failures:

```text
"MOVEit failback stopped. Manual intervention is required."
```

Voice must never expose passwords, connection strings, registry secrets, or encryption material.

---

# 36. Implementation phases

## Phase 1 – Discovery and exact-version binding

Do not perform production writes.

Tasks:

1. Record installed MOVEit Automation version/build on both nodes.
2. Confirm both nodes run the same version.
3. Confirm shared MSSQL server/database.
4. Confirm failover Node values.
5. Confirm StartupRole values.
6. Confirm SuppressDBRep.
7. Identify authoritative runtime-role query.
8. Identify supported programmatic graceful shutdown method.
9. Identify supported programmatic Clear Admin Rep method.
10. Identify safe task/running-job query.
11. Document ports/firewall/service account requirements.
12. Verify configuration/state file locations for exact release.

**Exit criterion:** every privileged operation has a validated implementation path.

## Phase 2 – Read-only HA monitor

Implement:

- node health collector,
- runtime role detection,
- shared SQL validation,
- HA state machine,
- persistence,
- API,
- AEGIS Monitoring panel,
- event logging.

Mode:

```text
observe
```

No failback changes permitted.

**Exit criterion:** AEGIS accurately tracks real production topology for an agreed observation period.

## Phase 3 – Failover simulation

In test/non-production:

1. Start normal preferred topology.
2. Stop preferred primary using approved test process.
3. Confirm MOVEit native failover.
4. Confirm AEGIS detects:
   - preferred primary unavailable,
   - secondary promotion,
   - runtime primary change.
5. Restore preferred primary.
6. Confirm AEGIS sees it as recovered secondary.
7. Confirm 15-minute timer behavior.
8. Confirm no write action occurs.

## Phase 4 – Assisted failback

Enable:

```text
mode = assisted
```

AEGIS displays **Failback Ready**.

Operator selects:

```text
Failback Now
```

Workflow performs full automated sequence.

**Exit criterion:** repeated successful test failbacks and successful recovery from injected faults.

## Phase 5 – Automatic mode

Enable:

```text
mode = automatic
failback.enabled = true
```

Only after formal acceptance.

## Phase 6 – Production hardening

Add:

- alert routing,
- metrics/trends,
- runbooks,
- dashboards,
- backup/restore validation,
- upgrade regression tests,
- documentation.

---

# 37. Test plan

## Test 001 – Healthy topology

Initial:

```text
MOVEIT01 primary
MOVEIT02 secondary
```

Expected:

```text
HEALTHY_PREFERRED
no workflow created
```

## Test 002 – Brief network loss

Preferred primary unreachable for less than MOVEit's failover threshold.

Expected:

- AEGIS records transient degradation.
- No AEGIS failback workflow.
- If MOVEit never promotes secondary, topology returns to healthy.

## Test 003 – Native failover

Stop preferred primary long enough for MOVEit to promote secondary.

Expected:

```text
FAILED_OVER
runtime_primary = MOVEIT02
```

No AEGIS promotion command.

## Test 004 – Preferred primary recovery

Restore MOVEIT01.

Expected:

```text
MOVEIT01 runtime secondary
MOVEIT02 runtime primary
STABILITY_WAIT
```

## Test 005 – Recovery flapping

Restore MOVEIT01 for 8 minutes, fail it again.

Expected:

```text
recovery timer reset
no failback
```

## Test 006 – Full 15-minute recovery

Keep MOVEIT01 healthy for full interval.

Expected:

```text
FAILBACK_ELIGIBLE
```

## Test 007 – Shared SQL mismatch

Change test config so node database identities differ.

Expected:

```text
CONFIGURATION_INVALID
automatic failback blocked
```

## Test 008 – SuppressDBRep invalid

Set invalid test value on one node.

Expected:

```text
automatic failback blocked
```

## Test 009 – Active MOVEit jobs during failback

Trigger long-running transfer.

Initiate assisted failback.

Expected:

- scheduler drains,
- service waits,
- transfer completes,
- no abrupt task termination.

## Test 010 – Drain timeout

Create task that exceeds configured drain timeout.

Expected:

```text
FAILBACK_ABORTED
current primary remains production primary
```

## Test 011 – Runtime-role ambiguity

Make role query unavailable.

Expected:

```text
MANUAL_INTERVENTION_REQUIRED
no automatic writes
```

## Test 012 – Preferred primary fails to start

Inject service startup failure after roles are changed.

Expected:

- secondary remains stopped until safe decision,
- approved rollback path runs,
- preferred secondary is restored to runtime primary if rollback proves safe,
- otherwise manual intervention.

## Test 013 – Secondary fails to start after successful primary start

Expected:

```text
preferred primary remains active
HA state = degraded
critical/warning alert
```

## Test 014 – AEGIS backend restart during stability timer

Expected:

- timer state restored from persistence,
- no duplicate incident,
- continuity maintained.

## Test 015 – AEGIS backend restart during failback

Expected:

- durable run recovered,
- exclusive lock recovered,
- workflow resumes only from a safely revalidated step,
- no duplicate role actions.

## Test 016 – Duplicate workers

Two backend workers attempt trigger simultaneously.

Expected:

```text
one lock winner
one workflow only
```

## Test 017 – Kill switch before failback

Expected:

```text
KILL_SWITCH_ACTIVE
no workflow started
```

## Test 018 – Kill switch during failback

Expected:

- controlled safe cancellation,
- known runtime primary at conclusion,
- no unsafe mid-transition abandonment.

## Test 019 – Manual Pause

Expected:

- monitoring continues,
- failback does not start.

## Test 020 – Manual Failback Now

Mode assisted.

Expected:

- all normal safety gates still apply,
- button does not bypass validation.

---

# 38. Chaos/fault-injection testing

Before fully automatic production mode, deliberately test:

```text
network disconnect
WinRM unavailable
MOVEit Web Admin unavailable
SQL temporarily unavailable
preferred primary service won't start
secondary service won't start
admin command timeout
AEGIS process killed
server reboot during stability timer
AEGIS restart after first node stop
role query unavailable
corrupted/invalid configuration response
```

Every test must demonstrate:

```text
no duplicate production task execution caused by AEGIS
no unverified second node startup
deterministic audit trail
safe failure state
```

---

# 39. Acceptance criteria

Automatic production failback may be approved only when all of the following are true:

1. AEGIS correctly identifies preferred and runtime roles.
2. AEGIS correctly detects native failover.
3. AEGIS correctly detects preferred-primary recovery.
4. Recovery timer resets on instability.
5. Shared MSSQL identity validation works.
6. `SuppressDBRep` validation works.
7. Graceful MOVEit drain is proven.
8. Running-task detection is proven.
9. Both-services-stopped gate is proven.
10. Startup role reassignment is proven.
11. Clear Admin Rep operation is proven.
12. Preferred-primary-only startup is proven.
13. Runtime PRIMARY verification is authoritative.
14. Secondary startup only occurs after primary verification.
15. Final topology verification is proven.
16. Workflow is durable across AEGIS restart.
17. Exclusive lock prevents duplicate execution.
18. Kill switch is honored safely.
19. Pause/maintenance suppression works.
20. Audit history contains complete timeline.
21. UI accurately displays current state.
22. Rollback is demonstrated in non-production.
23. At least the agreed number of assisted failbacks succeed before automatic mode is enabled.
24. Operations/security teams approve the service account and privileges.
25. Exact MOVEit version behavior is validated against official Progress documentation and/or Progress support.

---

# 40. Provider implementation checklist

A provider receiving this document should deliver:

## Backend

- [ ] HA configuration model
- [ ] secure configuration loader
- [ ] node health collector
- [ ] runtime role detector
- [ ] shared MSSQL validator
- [ ] deterministic HA state machine
- [ ] persisted incident model
- [ ] exclusive durable lock
- [ ] privileged MOVEit adapter
- [ ] graceful shutdown implementation
- [ ] startup-role implementation
- [ ] Clear Admin Rep implementation
- [ ] service start/stop implementation
- [ ] state synchronization validation
- [ ] failback workflow
- [ ] rollback workflow
- [ ] monitoring API
- [ ] operator-control API
- [ ] audit events
- [ ] notification integration
- [ ] kill-switch integration
- [ ] tests

## Desktop

- [ ] MOVEit HA monitoring card
- [ ] node status display
- [ ] runtime/preferred role display
- [ ] recovery stability timer
- [ ] automatic-mode status
- [ ] pause/resume
- [ ] Failback Now
- [ ] workflow details link
- [ ] event/history view
- [ ] critical-warning presentation

## Operations

- [ ] deployment instructions
- [ ] service account instructions
- [ ] firewall/WinRM requirements
- [ ] rollback runbook
- [ ] disaster manual procedure
- [ ] maintenance-mode procedure
- [ ] upgrade regression checklist
- [ ] Progress-version compatibility statement

---

# 41. Non-goals

The initial implementation should NOT:

- replace MOVEit's native failover;
- perform arbitrary server remediation;
- modify the shared SQL database;
- copy/restore a SQL database;
- automatically upgrade MOVEit;
- automatically kill long-running transfers;
- use an LLM to decide HA safety;
- automatically repair an ambiguous split-brain condition;
- expose MOVEit secrets to the AI model;
- grant AEGIS unrestricted remote PowerShell access.

---

# 42. Operational runbook

## Normal

Expected:

```text
MOVEIT01 PRIMARY
MOVEIT02 SECONDARY
AEGIS state HEALTHY_PREFERRED
```

No action.

## Native failover

AEGIS reports:

```text
MOVEIT01 unavailable
MOVEIT02 PRIMARY
AEGIS state FAILED_OVER
```

Operations should investigate the failed preferred primary. AEGIS does not immediately switch back.

## Preferred primary recovered

AEGIS reports:

```text
MOVEIT01 SECONDARY / healthy
MOVEIT02 PRIMARY
stability timer active
```

No operator action is required in automatic mode.

## Automatic failback begins

AEGIS reports:

```text
FAILBACK IN PROGRESS
```

Operators should avoid manually starting/stopping either MOVEit service unless the workflow explicitly enters `MANUAL_INTERVENTION_REQUIRED`.

## Failback success

Expected:

```text
MOVEIT01 PRIMARY
MOVEIT02 SECONDARY
```

Review workflow if required.

## Manual intervention

If AEGIS displays:

```text
MANUAL_INTERVENTION_REQUIRED
```

operators should:

1. Do not start the stopped node reflexively.
2. Identify which node is definitively runtime primary.
3. Review the AEGIS workflow timeline.
4. Review MOVEit failover status in Web Admin.
5. Follow the organization's approved MOVEit MSSQL resynchronization procedure.
6. Clear the AEGIS incident only after topology is verified.

---

# 43. Upgrade policy

Every MOVEit Automation upgrade must temporarily disable automatic failback.

Procedure:

1. Set AEGIS MOVEit HA to maintenance/paused.
2. Upgrade MOVEit using the approved Progress failover upgrade procedure.
3. Confirm both nodes use the expected version.
4. Re-run integration tests:
   - runtime role detection,
   - graceful shutdown,
   - role assignment,
   - Clear Admin Rep,
   - health queries.
5. Run at least one assisted failback in test/non-production.
6. Re-enable automatic mode only after validation.

This is necessary because administrative endpoints, paths, or internal behavior can change between versions.

---

# 44. Logging requirements

Each operation must log structured data.

Example:

```json
{
  "timestamp": "2026-09-06T02:31:18-04:00",
  "pairId": "production-moveit-ha",
  "incidentId": "mih-...",
  "runId": "wf-...",
  "eventType": "MOVEIT_PREFERRED_PRIMARY_STARTED",
  "node": "MOVEIT01",
  "result": "success",
  "durationMs": 1822
}
```

Do not log:

```text
passwords
API secrets
full SQL connection strings
encrypted failover credentials
KeyMat contents
private keys
```

---

# 45. Metrics

Useful metrics:

```text
moveit_ha_node_health
moveit_ha_runtime_primary
moveit_ha_partner_link
moveit_ha_sql_health
moveit_ha_recovery_stability_seconds
moveit_ha_failover_total
moveit_ha_failback_total
moveit_ha_failback_success_total
moveit_ha_failback_failure_total
moveit_ha_failback_duration_seconds
moveit_ha_manual_intervention_total
```

These can later feed AEGIS trends/monitoring history.

---

# 46. Recommended defaults

```text
Poll interval                         10 seconds
Unhealthy threshold                  3 failed polls
Recovery confirmation                3 successful polls
Preferred-primary stability          15 minutes
Drain timeout                         30 minutes
Service stop timeout                  120 seconds
Primary startup timeout               180 seconds
Primary validation hold               60 seconds
Pair post-validation                  120 seconds
Automatic attempts / incident         1
Failback cooldown                      60 minutes
Default deployment mode               observe
```

These values must remain configurable.

---

# 47. Important implementation constraints

## Constraint A – Do not use ping as authoritative health

Ping may be supplemental only.

## Constraint B – Do not equate StartupRole with runtime role

Runtime role must be independently proven.

## Constraint C – Do not stop an active MOVEit primary abruptly if tasks may be running

Use the supported graceful shutdown mechanism.

## Constraint D – Do not start the secondary until the intended primary is verified

This is a hard safety gate.

## Constraint E – Do not let automatic failback repeatedly flap

Use recovery stability, attempt limits, and cooldown.

## Constraint F – Do not blindly synchronize encrypted/local configuration

Use supported MOVEit procedures and exact-version validation.

## Constraint G – Fail closed

Unknown state means:

```text
NO AUTOMATIC CHANGE
```

---

# 48. Decisions the implementation provider must resolve against the live environment

Before coding the privileged portion, capture these values:

```text
MOVEit version/build:
Preferred primary hostname:
Preferred secondary hostname:
SQL Server FQDN/instance:
MOVEit database name:
MOVEit Windows service name:
MOVEit installation path:
MOVEit configuration path:
StateFiles path:
PGPPath:
Web Admin URL/port:
Administrative TCP ports:
WinRM availability:
AEGIS backend service identity:
Supported runtime-role query:
Supported graceful-shutdown invocation:
Supported Clear Admin Rep invocation:
Supported running-task query:
```

The provider should add this completed environment profile to project documentation.

---

# 49. Official Progress references

The implementation provider should verify the installed release against the corresponding Progress documentation before enabling automatic state changes.

1. **MOVEit Automation 2026 – Requirements**
   https://docs.progress.com/bundle/moveit-automation-web-admin-help-2026/page/Requirements.html

2. **MOVEit Automation – How Failover Works**
   https://docs.progress.com/bundle/moveit-automation-web-admin-help-2025/page/How-Failover-Works.html

3. **MOVEit Automation 2026 – Failover Alerts**
   https://docs.progress.com/bundle/moveit-automation-web-admin-help-2026/page/Failover-Alerts.html

4. **MOVEit Automation – Resynchronization for MSSQL**
   https://docs.progress.com/bundle/moveit-automation-web-admin-help-2025/page/Resynchronization-for-MSSQL.html

5. **MOVEit Automation – System Internals**
   https://docs.progress.com/bundle/moveit-automation-web-admin-help-2025/page/System-Internals_2.html

6. **MOVEit Automation – Commands / Shut Down Service**
   https://docs.progress.com/bundle/moveit-automation-web-admin-help-2025/page/COMMANDS.html

7. **MOVEit Automation – What Failover Replicates**
   https://docs.progress.com/bundle/moveit-automation-web-admin-help-2025/page/What-Failover-Replicates.html

8. **MOVEit Automation – Failover Tab / Clear Admin Rep**
   https://docs.progress.com/bundle/moveit-automation-admin-console-help-2024/page/Failover-Tab.html

9. **MOVEit Automation 2026 – Failover setup step-by-step**
   https://docs.progress.com/bundle/moveit-automation-web-admin-help-2026/page/Step-by-Step-Instructions.html

10. **MOVEit Automation 2025 – Failover with remote SQL Server**
    https://docs.progress.com/bundle/moveit-automation-web-admin-help-2025/page/Failover-configuration-with-a-remote-SQL-Server.html

---

# 50. Final implementation requirement

The finished feature should satisfy this operational statement:

> AEGIS 9 continuously monitors the configured MOVEit Automation failover pair. MOVEit remains responsible for native failover. If the preferred primary fails and the preferred secondary becomes runtime primary, AEGIS records and monitors that condition. When the preferred primary returns as a healthy secondary and remains continuously healthy for the configured stability interval, AEGIS validates the complete HA environment. If and only if every deterministic safety gate passes, AEGIS creates one durable, locked, auditable failback workflow that gracefully drains the current primary, stops both MOVEit services, restores the preferred startup roles, clears the required administrative replication state, starts and proves the preferred primary, starts and proves the secondary, validates the final topology, and records the result. Any ambiguous or unsafe condition stops automatic state changes and requires manual intervention.

That is the required production behavior.

---

# Appendix A – Recommended initial rollout configuration

```json
{
  "enabled": true,
  "mode": "observe",
  "monitoring": {
    "pollIntervalSeconds": 10,
    "preferredPrimaryStabilitySeconds": 900
  },
  "failback": {
    "enabled": false
  }
}
```

After successful observation testing:

```json
{
  "mode": "assisted",
  "failback": {
    "enabled": true
  }
}
```

After formal acceptance:

```json
{
  "mode": "automatic",
  "failback": {
    "enabled": true
  }
}
```

---

# Appendix B – Recommended severity mapping

| Condition | Severity |
|---|---|
| Preferred topology healthy | Healthy |
| Preferred primary temporarily unreachable | Warning |
| Native failover active | Warning |
| Preferred primary recovered / stability wait | Warning |
| Failback running | Information / Maintenance |
| Secondary unavailable after successful failback | Warning |
| Configuration mismatch | Critical |
| Shared SQL validation failure | Critical |
| Runtime role unknown | Critical |
| Both nodes appear primary | Critical |
| Rollback failure | Critical |
| Manual intervention required | Critical |

---

# Appendix C – Definition of done

The feature is complete only when:

```text
[ ] Read-only monitoring is stable.
[ ] Native failover is detected correctly.
[ ] Recovery timer is durable.
[ ] Exact MOVEit version integrations are documented.
[ ] Graceful shutdown is supported and tested.
[ ] Runtime role is authoritatively detected.
[ ] Shared MSSQL validation works.
[ ] Privileged actions are allowlisted.
[ ] Failback is a durable AEGIS workflow.
[ ] Exclusive locking works.
[ ] Rollback is tested.
[ ] Kill switch works safely.
[ ] MonitorWindow integration is complete.
[ ] WorkflowWindow integration is complete.
[ ] Alerts/history are complete.
[ ] Assisted failback testing passes.
[ ] Fault-injection testing passes.
[ ] Operations and security review passes.
[ ] Automatic production mode is explicitly enabled only after acceptance.
```

---

**End of implementation handoff**
