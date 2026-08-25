# MoveIT Monitoring Contract

This is the implementation contract for the MoveIT monitor in the current Jarvis backend.

## Polling

- Initial cadence: every 5 minutes.
- Polling must be cancellable during application shutdown.
- A manual refresh may run immediately, but must not create duplicate concurrent polls.
- Every poll records its start time, completion time, selected server, and outcome.

## Per-task configuration

Each monitored task needs:

```text
name
id or name identifier
schedule/time zone
expected run window or recurrence
enabled
log capture enabled
```

Task mappings can initially be read from configuration, but the long-term source should be the MoveIT task list plus an explicit monitoring allowlist.

## Required task states

The monitor should normalize MoveIT responses to:

```text
unknown
scheduled
running
succeeded
failed
missed
unavailable
```

A task is `failed` when the confirmed MoveIT execution status is a failure state.

A task is `missed` when the expected scheduled run window has elapsed and no corresponding run is observed. The implementation must use the task's configured time zone and tolerate clock skew with a configurable grace period.

A task is `unknown` when MoveIT is reachable but the run history cannot be correlated safely. Unknown is not success.

## Alerts

Create or update one active alert per condition key:

```text
moveit-cluster-unavailable
moveit-task-failed:<task-id>
moveit-task-missed:<task-id>:<expected-run-key>
moveit-task-status-unknown:<task-id>
moveit-log-capture-failed:<task-id>:<execution-id>
```

Alerts need:

- source
- severity
- task name and ID
- detected time
- expected run time when applicable
- execution ID when available
- sanitized error detail
- resolution state
- notification state

Repeated five-minute polls must update an existing active alert rather than send duplicate email every time.

## Failed-task log capture

When a task reaches a confirmed failure state:

1. Request `GET /api/v1/executions/<execution-id>/log`.
2. Create a directory below the configured MoveIT log root using a sanitized task name.
3. Write a UTF-8 log file using this format:

```text
<task-name>_<capture-utc-timestamp>_<execution-id>.log
```

4. Store the capture path and timestamp in Jarvis persistence.
5. If capture fails, retain the failure alert and create a separate log-capture alert.

Task names must be sanitized to prevent path traversal. Do not write server responses containing bearer tokens or credentials.

## Email notification

The initial temporary recipient is documented as `Richard.Garner@gdit`, but the complete routable address and SMTP transport are not present in the source tree. Keep recipient and SMTP settings configurable.

Email delivery must include:

- alert type
- task name
- expected/run timestamp
- server used
- status and error detail
- captured log path, if available
- link or identifier for the Jarvis alert

Use a notification outbox or persisted notification state so retries are controlled and the monitor does not block on SMTP indefinitely.

## Action requests

The UI may present an issue selector and submit an action request before the action catalog is approved. Until the catalog exists:

- accept the request as `pending` or `not_configured`
- record the operator, source, issue, and time
- execute nothing

Future actions should be explicit and allowlisted, such as retrying a confirmed failed task or opening a captured log. Do not retry an ambiguous timed-out trigger automatically.

## Read-only discovery phase

Before enabling production alerts, run a diagnostic mode against the primary MoveIT node that:

1. Authenticates.
2. Retrieves the task list.
3. Retrieves one known task's details.
4. Retrieves its history/runs endpoint.
5. Retrieves one known execution status.
6. Retrieves one known execution log.
7. Saves sanitized response-shape fixtures for parser tests.

No task trigger should be issued during discovery.
