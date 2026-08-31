# Native Windows Desktop

> The current native application is the cinematic A.E.G.I.S.-9 build on
> `feature/cinematic-jarvis-ui`. If this file is read from `main`, that checkout
> is the older UI. Fetch and switch branches as described in
> `docs/CURRENT-VERSION.md` before building.

Jarvis is a native Windows operations application. This folder (`D:\Jarvis_Desktop`) contains the native app, its own bundled FastAPI backend, and supporting docs. The React dashboard has moved to the separate `D:\Jarvis_Web` folder/repository and is not required at runtime.

## Window roles

### Command Center

The WPF Command Center is intentionally independent of monitoring and workflow surfaces. It is used for:

- Chat history
- Issuing commands
- Starting a new conversation
- Referencing available workflow and monitoring capabilities
- Opening the separate monitoring windows
- Native workflow intake and approval controls
- Native dependency health, session restoration, file management, activity, alerts, and settings

It does not render live MoveIT task tables or server telemetry.

### MoveIT Automation

The MoveIT monitor is a separate movable/resizable WPF window. It consumes the local FastAPI monitoring endpoint and displays:

- Task name and task ID
- Task description
- Enabled/disabled schedule status
- Last run time when available
- Last run status when available
- Most recent log path
- Scrollable logs from the last five days

The live MoveIT catalog is read-only. The current installation authenticates to `BSOAUTALB002` and returns the task catalog through `GET /api/v1/tasks`.

MOVEit logs are read from the configured root:

```text
\\BSOAUTALB002\c$\ProgramData\Ipswitch\Automation\Logs
```

Each task is correlated by its MOVEit task ID. The monitor scans the task-ID directory and includes files whose modification time is within five days. The root can be overridden with `JARVIS_MOVEIT_LOG_ROOT`.

### Server Status

The Server Status monitor is a separate movable/resizable WPF window. It lists:

- Starter server name and address
- Total disk space
- Free disk space
- Disk threshold status
- CPU
- Memory
- Automatic-service status
- Overall server status

Automatic-start services are considered expected to run. The monitor reports:

- `Good`: automatic-start services are running
- `Needs Attention`: one or more automatic-start services are stopped
- `Agent not connected`: no remote server monitoring feed is connected

The current local collector provides live data for the Jarvis host. The starter remote servers are listed until their ServerMonitoring agent/hub feed is connected.

The editable inventory is `config/monitored-servers.json`. Each entry contains `name`, `address`, and `role`. The native Command Center Workspace section opens this file and the local `.env` file through the **Edit monitoring list and MoveIT credentials** button. Restart Jarvis after changing either file.

### Assistant Avatar

The command center includes a native human-like fallback avatar with idle animation, hover attention, click moods, chat-state transitions, and local display-name/theme preferences. The next milestone is a licensed local 3D model host for male and female `.glb` or `.vrm` assets. Model files must be supplied under an explicit license and kept local.

### Workflow Supervision

Workflow supervision is native WPF. The command center creates and approves workflows, and each active workflow can open in its own `WorkflowWindow`. Pause, resume, stop, queue, monitor-slot assignment, and display-topology reconciliation are backed by the FastAPI supervisor APIs.

## Runtime architecture

```text
Jarvis.Desktop (WPF)
    -> http://127.0.0.1:8000/api/monitoring
        -> FastAPI monitoring collector
            -> MoveIT REST API and task-log UNC path
            -> local Windows CPU, memory, disk, service, and filesystem collection
            -> SQLite alert and snapshot persistence
```

The React dashboard lives in the separate `D:\Jarvis_Web` folder/repository as a legacy browser/API surface. The native WPF shell is the Windows operator entry point and does not open browser windows for command, monitoring, or workflow supervision.

## Start at home or work

1. Copy `.env.example` to `.env` if it does not exist.
2. Set `JARVIS_MOVEIT_USERNAME` and `JARVIS_MOVEIT_PASSWORD` in the ignored local `.env`; do not commit them.
3. Update `config/monitored-servers.json` for the general server inventory.
4. Start the backend manually only when developing with `JARVIS_DEVELOPER_MODE=1`; normal native startup launches it automatically:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

## Bundled backend launcher (recent changes)

The desktop shell now includes a lightweight launcher to start a packaged Python FastAPI backend when the app is installed. This was added to support a native-first delivery model where the desktop app bundles and auto-starts the backend process in production while developers continue to run the backend manually during development.

Key points
- Implementation: desktop/Jarvis.Desktop/BackendLauncher.cs — starts/stops a python process (uvicorn) and redirects stdout/stderr to logs.
- App integration: App.xaml.cs attempts to start the bundled backend on startup unless developer mode is enabled. It polls the backend health endpoint via MonitoringClient.CheckHealthAsync and shows a warning if the backend is not ready within the startup timeout.
- Logs: when launched by the app the backend appends logs to `<install-dir>\backend\logs\backend.stdout.log` and `backend.stderr.log`. Inspect these files for startup errors and tracebacks.
- Developer override: set environment variable `JARVIS_DEVELOPER_MODE=1` to prevent auto-launch and run the backend manually during development.
- Monitoring URL override: set `JARVIS_MONITORING_URL` to change the backend base URL the desktop reads (useful for testing remote or nonstandard ports).

Local developer helper scripts
- scripts/start-backend.ps1 — creates/activates a .venv, installs backend requirements, and starts uvicorn. Use dot-sourcing with `-Activate` to persist venv activation in your interactive shell: `. .\scripts\start-backend.ps1 -Activate`.

When packaging the product, the installer should place the backend folder next to the desktop executable so the launcher can find and start it using a relative path under the app install directory.

4. Build and start the desktop shell:

```powershell
dotnet build desktop\Jarvis.Desktop\Jarvis.Desktop.csproj
Start-Process desktop\Jarvis.Desktop\bin\Debug\net8.0-windows\Jarvis.Desktop.exe
```

## Current limitations

- MOVEit task history endpoints tested against this installation returned 404. Last-run state therefore comes from recognized log files when available.
- The remote MOVEit log root is accessible from the current workstation, but no files newer than five days were observed during the last check.
- Remote server rows need the original ServerMonitoring agent/hub transport before they can display live remote metrics.
- SMTP alert configuration is present and deduplicated in the backend; production delivery should be verified against the internal relay.
- Monitoring actions are intentionally deferred until the action catalog is approved.
- External automation execution is not yet connected to the native workflow windows.
