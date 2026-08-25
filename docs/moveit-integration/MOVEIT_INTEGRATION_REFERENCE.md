# MoveIT Integration Reference

This reference extracts the reusable MoveIT behavior from the original .NET Jarvis implementation at:

`D:\BSOC_CodeRepository\DEV\Src\DotNet\BSOC\Jarvis`

No credentials, tokens, or plaintext secrets are included here.

## Source files reviewed

- `Services/MoveITService.cs`
- `Core/Tools/MoveITTaskTool.cs`
- `Configuration/AppConfiguration.cs`
- `Documentation/MOVEIT_OAUTH_FIX.md`
- `Documentation/MOVEIT_HTTP_METHOD_FIX.md`
- `Documentation/MoveIT_API_ContentType_Fix.md`
- `Documentation/MoveIT_DualServer_Security.md`
- `Documentation/MoveIT_Task_Execution.md`

## Cluster behavior

The original implementation documents this MoveIT Central cluster:

- `BSOAUTALB002`: primary/read-write node; use this for task-control operations.
- `BSOAUTALB001`: secondary/read-only node; use only for status/failover behavior that has been confirmed against the environment.

The earlier source configuration sometimes listed only `BSOAUTALB002`, while other documentation describes dual-server failover. The monitor should make server priority configurable and should not retry write operations against a node known to be read-only.

## Authentication

The verified authentication contract is:

```text
POST https://<server>/api/v1/token
Content-Type: application/x-www-form-urlencoded

 grant_type=password
 username=<service-account>
 password=<secret>
```

The response may expose the token as either `access_token` or `token`. The original implementation caches the bearer token for approximately 50 minutes, but the new client should prefer the server-provided expiry when `expires_in` is present and refresh before expiry.

Use a secret provider in the new Jarvis project. Do not put a password in `.env.example`, tracked JSON, source code, logs, or API responses.

## Task execution

The strongest evidence in the original fix documentation says the working task trigger is:

```text
GET https://<server>/api/v1/tasks/run?taskName=<url-encoded-task-name>
Authorization: Bearer <token>
```

The original service also probes version-dependent variants:

```text
POST /api/v1/tasks/<identifier>/start
GET  /api/v1/tasks/<identifier>/run
POST /api/v1/tasks/<identifier>/execute
GET  /api/v1/tasks/run/<identifier>
```

The production client should not blindly probe write endpoints on every polling cycle. Put the selected endpoint and method in configuration, defaulting to the documented GET query form, and retain endpoint discovery as an explicit diagnostic operation.

## Live schema verification

Using the temporary local credentials, Jarvis successfully authenticated to `BSOAUTALB002` and retrieved 101 live task records. This MoveIT instance returns:

```text
GET /api/v1/tasks
{ "items": [...], "paging": ..., "sorting": ... }
```

Task records use capitalized fields including `Name`, `ID`, `Scheduled`, `Schedules`, `NextEID`, and `Info`. Task detail is available at:

```text
GET /api/v1/tasks/<id>
```

For the tested task, `Schedules.Schedule` was present and returned a list containing `Days`, `Frequency`, `DateListRef`, and related schedule flags.

The tested history candidates returned `404` on this instance:

```text
/api/v1/tasks/<id>/history
/api/v1/tasks/<id>/runs
/api/v1/tasks/<id>/executions
/api/v1/taskruns?taskId=<id>
/api/v1/executions?taskId=<id>
```

Therefore the current live monitor can enumerate tasks and schedules, but confirmed missed-run/failure correlation still needs the MoveIT-specific execution-history endpoint or an alternate run-history source.

Task identifiers can be configured through a case-insensitive name-to-ID mapping. Task names may contain spaces, hyphens, underscores, and punctuation, so always URL-encode them.

## Task discovery

The original service uses:

```text
GET /api/v1/tasks
```

The implementation expects a response containing a `tasks` array with `name` fields, but the response shape was not fully verified. The new client should accept these common shapes:

- `{ "tasks": [{ "id": "...", "name": "..." }] }`
- `{ "items": [{ "id": "...", "name": "..." }] }`
- A top-level array of task objects

Preserve the raw response only in controlled debug logs with secrets and authorization headers removed.

## Execution status and logs

The original implementation uses these endpoints:

```text
GET /api/v1/executions/<execution-id>
GET /api/v1/executions/<execution-id>/log
```

Status may be returned in `status` or `state`. Successful values observed/documented include:

- `Success`
- `Completed`
- `Succeeded`

Active values include:

- `Running`
- `Queued`
- `Pending`
- `InProgress`

Failure values include:

- `Failed`
- `Error`

The status response may include `message`, `errorMessage`, and `endTime`. The log endpoint returns the execution log body.

## Execution ID handling

The start response may contain one of:

- `executionId`
- `id`
- `taskRunId`

The original code also uses a task-detail response and reads `NextEID` when the start response does not return an execution ID. This is a workaround, not a guaranteed contract. If no execution ID is returned, the monitor should record the run as `started_untracked` and use task history or task detail polling if that endpoint is available.

## Status endpoint discovery evidence

The original diagnostic code probes these candidate read endpoints:

```text
GET /api/v1/tasks/<id>
GET /api/v1/tasks/<id>/history
GET /api/v1/tasks/<id>/runs
GET /api/v1/tasks/<id>/executions
GET /api/v1/tasks/<id>/status
GET /api/v1/tasks/<id>/laststatus
GET /api/v1/tasks/<id>/lastrun
GET /api/v1/taskruns?taskId=<id>
GET /api/v1/history?taskId=<id>
GET /api/v1/executions?taskId=<id>
```

The exact scheduled-history response was not established in the original source. The first live integration task should be a read-only discovery request against the primary node, capture the sanitized JSON shape, and then implement a typed parser for the confirmed endpoint.

## TLS behavior

The original .NET service accepts internal certificates for hosts containing `bsoautalb`. That behavior is unsafe to port as-is. The Python client must use the machine trust store or an explicitly configured CA certificate. Do not disable certificate validation globally.

## Failover behavior

For read-only health and status checks:

1. Try the configured primary.
2. On network failure or timeout, try the configured secondary.
3. Record which server answered.
4. Raise one alert for cluster unavailability, not one alert per retry.

For task execution:

- Do not automatically retry a non-idempotent or ambiguous task trigger after a timeout.
- A timeout after the server may have accepted the task must be recorded as `unknown`, requiring operator review.
- Retry only when the response proves that the request was not accepted, or after an explicit operator action.

## Original implementation limitations

The source implementation is useful connection evidence, but it does not implement scheduled-task monitoring. It does not reliably determine that a scheduled task was expected but failed to run, does not persist a per-task last-observed run, and does not send alert email. Those are new monitoring features for the current Jarvis backend.
