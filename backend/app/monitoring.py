import json
import shutil
import subprocess
import sys
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import psutil
import httpx
from pydantic import BaseModel, Field

from app.config import Settings


Severity = Literal["info", "warning", "error"]
MonitorStatus = Literal["healthy", "warning", "error", "unavailable"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class MoveItTask(BaseModel):
    name: str
    task_id: str = ""
    description: str = ""
    schedule_status: str = "Unknown"
    last_run_status: str = "Unavailable"
    status: str
    detail: str
    last_run_at: str | None = None
    log_url: str | None = None


class MoveItLogEntry(BaseModel):
    task_name: str
    captured_at: str
    status: str
    log_url: str | None = None
    detail: str = "MoveIT execution history is not available from this endpoint."


class MoveItMonitor(BaseModel):
    status: MonitorStatus
    adapter: str
    cadence_minutes: int = 5
    last_checked_at: str
    detail: str
    tasks: list[MoveItTask] = Field(default_factory=list)
    recent_logs: list[MoveItLogEntry] = Field(default_factory=list)


class ServerMetric(BaseModel):
    key: str
    label: str
    value: float | None = None
    display_value: str
    detail: str
    status: MonitorStatus
    threshold: str = "30%"


class ServerService(BaseModel):
    name: str
    status: str
    detail: str


class ServerMonitor(BaseModel):
    status: MonitorStatus
    last_checked_at: str
    detail: str
    metrics: list[ServerMetric] = Field(default_factory=list)
    stopped_automatic_services: list[ServerService] = Field(default_factory=list)
    filesystem_audit: list["FilesystemAuditEvent"] = Field(default_factory=list)
    servers: list["ServerInventory"] = Field(default_factory=list)
    total_disk: str = "Unavailable"
    free_disk: str = "Unavailable"


class ServerInventory(BaseModel):
    name: str
    address: str
    role: str
    status: str
    total_disk: str = "Unavailable"
    free_disk: str = "Unavailable"
    threshold_status: str = "Unavailable"
    cpu: str = "Unavailable"
    memory: str = "Unavailable"
    automatic_services: str = "Unavailable"


class MonitoringAlert(BaseModel):
    id: int
    source: str
    severity: Severity
    title: str
    detail: str
    status: str
    created_at: str
    resolved_at: str | None = None


class FilesystemAuditEvent(BaseModel):
    id: int
    path: str
    change_type: str
    detail: str
    created_at: str


class MonitoringDashboard(BaseModel):
    generated_at: str
    moveit: MoveItMonitor
    server: ServerMonitor
    alerts: list[MonitoringAlert] = Field(default_factory=list)


class MonitoringActionRequest(BaseModel):
    source: Literal["moveit", "server"]
    issue: str = Field(min_length=1, max_length=120)


class MonitoringActionResult(BaseModel):
    status: Literal["pending", "not_configured"]
    detail: str
    source: str
    issue: str


class MoveItAdapter:
    """Read-only MoveIT client using the verified legacy API contract."""

    def __init__(self, settings: Settings) -> None:
        self._servers = [server.strip() for server in settings.moveit_servers.split(",") if server.strip()]
        self._username = settings.moveit_username
        self._password = settings.moveit_password
        self._verify_tls = settings.moveit_verify_tls
        self._log_root = settings.moveit_log_root

    def collect(self, checked_at: str) -> MoveItMonitor:
        if not self._username or not self._password:
            return MoveItMonitor(
                status="unavailable",
                adapter="moveit-rest",
                last_checked_at=checked_at,
                detail="MoveIT credentials are not configured. Set JARVIS_MOVEIT_USERNAME and JARVIS_MOVEIT_PASSWORD.",
            )
        if not self._servers:
            return MoveItMonitor(status="unavailable", adapter="moveit-rest", last_checked_at=checked_at, detail="No MoveIT servers are configured.")

        errors: list[str] = []
        for server in self._servers:
            try:
                with httpx.Client(timeout=20, verify=self._tls_context()) as client:
                    token = self._authenticate(client, server)
                    response = client.get(
                        f"https://{server}/api/v1/tasks",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    response.raise_for_status()
                    tasks = self._parse_tasks(response.json())
                    recent_logs = self._collect_recent_logs(tasks)
                status: MonitorStatus = "warning" if any(task.status.lower() in {"failed", "error", "missed"} for task in tasks) else "healthy"
                return MoveItMonitor(
                    status=status,
                    adapter=f"moveit-rest:{server}",
                    last_checked_at=checked_at,
                    detail=f"Live task catalog retrieved from {server}; {len(tasks)} task(s) returned.",
                    tasks=tasks,
                    recent_logs=recent_logs,
                )
            except (httpx.HTTPError, ValueError, KeyError) as error:
                errors.append(f"{server}: {error}")

        return MoveItMonitor(
            status="unavailable",
            adapter="moveit-rest",
            last_checked_at=checked_at,
            detail="MoveIT servers unavailable or rejected the request. " + " | ".join(errors),
        )

    def _tls_context(self) -> bool | ssl.SSLContext:
        if self._verify_tls:
            return True
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers("DEFAULT:@SECLEVEL=0")
        return context

    def _authenticate(self, client: httpx.Client, server: str) -> str:
        response = client.post(
            f"https://{server}/api/v1/token",
            data={"grant_type": "password", "username": self._username, "password": self._password},
        )
        if response.is_error:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            detail = payload.get("error_description") or payload.get("error") if isinstance(payload, dict) else None
            if detail:
                raise ValueError(f"MoveIT authentication failed: {detail}")
            response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token") or payload.get("token")
        if not isinstance(token, str) or not token:
            raise ValueError("MoveIT authentication response did not contain access_token or token")
        return token

    @staticmethod
    def _parse_tasks(payload: object) -> list[MoveItTask]:
        if isinstance(payload, dict):
            raw_tasks = payload.get("tasks") or payload.get("items") or []
        else:
            raw_tasks = payload
        if not isinstance(raw_tasks, list):
            raise ValueError("MoveIT task response did not contain a task list")

        tasks: list[MoveItTask] = []
        for raw_task in raw_tasks:
            if not isinstance(raw_task, dict):
                continue
            name = str(raw_task.get("name") or raw_task.get("Name") or raw_task.get("taskName") or raw_task.get("id") or raw_task.get("ID") or "Unnamed task")
            info = raw_task.get("Info") if isinstance(raw_task.get("Info"), dict) else {}
            description = str(info.get("Description") or raw_task.get("description") or raw_task.get("Description") or "")
            schedule_status = "Enabled" if str(raw_task.get("Scheduled", "")).upper() == "ENABLED" else "Disabled"
            raw_status = raw_task.get("status") or raw_task.get("Status") or raw_task.get("state") or raw_task.get("State")
            if raw_status is None:
                raw_status = "Scheduled" if schedule_status == "Enabled" else "Disabled"
            status = str(raw_status)
            last_run = raw_task.get("lastRunAt") or raw_task.get("lastRunTime") or raw_task.get("lastRun")
            detail = str(raw_task.get("message") or raw_task.get("Message") or raw_task.get("errorMessage") or raw_task.get("Info") or "Live task status returned by MoveIT.")
            task_id = str(raw_task.get("ID") or raw_task.get("id") or "")
            tasks.append(MoveItTask(name=name, task_id=task_id, description=description, schedule_status=schedule_status, last_run_status="Unavailable", status=status, detail=detail, last_run_at=str(last_run) if last_run else None))
        return tasks

    def _collect_recent_logs(self, tasks: list[MoveItTask]) -> list[MoveItLogEntry]:
        if not self._log_root.exists():
            return []
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=5)
        entries: list[MoveItLogEntry] = []
        for task in tasks:
            if not task.task_id:
                continue
            task_directory = self._log_root / task.task_id
            if not task_directory.is_dir():
                continue
            try:
                files = [path for path in task_directory.rglob("*") if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) >= cutoff]
            except OSError:
                continue
            for path in sorted(files, key=lambda candidate: candidate.stat().st_mtime, reverse=True):
                status = self._infer_log_status(path)
                captured_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
                task.last_run_at = captured_at
                task.last_run_status = status
                task.log_url = str(path)
                entries.append(MoveItLogEntry(task_name=task.name, captured_at=captured_at, status=status, log_url=str(path), detail=f"Task ID {task.task_id}"))
        return entries

    @staticmethod
    def _infer_log_status(path: Path) -> str:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[-12000:].lower()
        except OSError:
            return "Unavailable"
        if "no transfer" in text or "no files transferred" in text:
            return "No Transfer"
        if any(term in text for term in ("failed", "failure", "error")):
            return "Failure"
        if any(term in text for term in ("success", "completed", "succeeded")):
            return "Success"
        return "Unknown"


class LocalServerAdapter:
    def __init__(self, inventory_path: Path) -> None:
        self._inventory = self._load_inventory(inventory_path)

    def collect(self, checked_at: str, audit_events: list[FilesystemAuditEvent]) -> ServerMonitor:
        disk = shutil.disk_usage(Path.cwd().anchor or Path.cwd())
        disk_available_percent = disk.free / disk.total * 100 if disk.total else None
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk_status = self._threshold_status(disk_available_percent)
        cpu_status = self._threshold_status(100 - cpu_percent)
        memory_status = self._threshold_status(memory.available / memory.total * 100 if memory.total else None)
        stopped_services = self._stopped_automatic_services()
        metrics = [
            ServerMetric(
                key="disk_available",
                label="Disk available",
                value=round(disk_available_percent, 1) if disk_available_percent is not None else None,
                display_value=f"{disk_available_percent:.1f}%" if disk_available_percent is not None else "Unavailable",
                detail=f"{disk.free / (1024 ** 3):.1f} GB free of {disk.total / (1024 ** 3):.1f} GB" if disk.total else "Disk data unavailable",
                status=disk_status,
            ),
            ServerMetric(
                key="cpu",
                label="CPU",
                value=round(cpu_percent, 1),
                display_value=f"{cpu_percent:.1f}%",
                detail=f"{100 - cpu_percent:.1f}% capacity remaining; warning below 30% remaining.",
                status=cpu_status,
            ),
            ServerMetric(
                key="memory_available",
                label="Memory available",
                value=round(memory.available / memory.total * 100, 1) if memory.total else None,
                display_value=f"{memory.available / memory.total * 100:.1f}%" if memory.total else "Unavailable",
                detail=f"{memory.available / (1024 ** 3):.1f} GB available; warning below 30% remaining." if memory.total else "Memory data unavailable",
                status=memory_status,
            ),
        ]
        has_warning = any(metric.status == "warning" for metric in metrics) or bool(stopped_services)
        return ServerMonitor(
            status="warning" if has_warning else "healthy",
            last_checked_at=checked_at,
            detail=f"Local host metrics from {sys.platform}; {len(stopped_services)} automatic service issue(s) detected.",
            metrics=metrics,
            stopped_automatic_services=stopped_services,
            filesystem_audit=audit_events,
            total_disk=f"{disk.total / (1024 ** 3):.1f} GB" if disk.total else "Unavailable",
            free_disk=f"{disk.free / (1024 ** 3):.1f} GB" if disk.total else "Unavailable",
        )

    @staticmethod
    def _threshold_status(available_percent: float | None) -> MonitorStatus:
        if available_percent is None:
            return "unavailable"
        return "healthy" if available_percent >= 30 else "warning"

    @staticmethod
    def _stopped_automatic_services() -> list[ServerService]:
        if sys.platform != "win32":
            return []
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Get-CimInstance Win32_Service | Where-Object {$_.StartMode -eq 'Auto' -and $_.State -ne 'Running'} | Select-Object Name,State,StartMode | ConvertTo-Json -Compress",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True)
            if not result.stdout.strip():
                return []
            rows = json.loads(result.stdout)
            if isinstance(rows, dict):
                rows = [rows]
            return [
                ServerService(
                    name=str(row.get("Name", "Unknown service")),
                    status=str(row.get("State", "Unknown")),
                    detail="Configured for automatic start but is not running.",
                )
                for row in rows
                if isinstance(row, dict)
            ]
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            return [ServerService(name="Windows service query", status="unavailable", detail="Automatic service state could not be queried.")]

    @staticmethod
    def _load_inventory(inventory_path: Path) -> list[tuple[str, str, str]]:
        try:
            payload = json.loads(inventory_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list):
            return []
        return [
            (str(item["name"]), str(item["address"]), str(item.get("role", "Monitored server")))
            for item in payload
            if isinstance(item, dict) and item.get("name") and item.get("address")
        ]


class MonitoringCollector:
    def __init__(self, store: "MonitoringStore", audit_root: Path, settings: Settings) -> None:
        self.store = store
        self.audit_root = audit_root
        self.moveit = MoveItAdapter(settings)
        self.server = LocalServerAdapter(settings.server_inventory_path)
        self.settings = settings

    def collect(self) -> MonitoringDashboard:
        checked_at = utc_now()
        self.store.capture_filesystem_changes(self.audit_root)
        audit_events = self.store.get_filesystem_audit(limit=8)
        moveit = self.moveit.collect(checked_at)
        server = self.server.collect(checked_at, audit_events)
        server.servers = self._server_inventory(server)
        snapshot_id = self.store.save_snapshot(moveit, server, checked_at)
        self.store.ensure_alert(source="moveit", severity="warning", title="MoveIT monitoring unavailable", detail=moveit.detail, active=moveit.status == "unavailable")
        server_alert_created = self.store.ensure_alert(source="server", severity="warning", title="Automatic Windows service issue detected", detail=server.detail, active=bool(server.stopped_automatic_services))
        if server_alert_created:
            self._send_alert_email("Automatic Windows service issue detected", server.detail)
        for task in moveit.tasks:
            if task.status.lower() in {"failed", "error", "missed"}:
                self.store.ensure_alert(source="moveit", severity="error", title=f"MoveIT task issue: {task.name}", detail=task.detail, active=True)
        return MonitoringDashboard(
            generated_at=checked_at,
            moveit=moveit,
            server=server,
            alerts=self.store.get_alerts(),
        )

    def _send_alert_email(self, title: str, detail: str) -> None:
        message = EmailMessage()
        message["Subject"] = f"[Jarvis Alert] {title}"
        message["From"] = self.settings.alert_email_from
        message["To"] = self.settings.alert_email_to
        message.set_content(f"Jarvis monitoring alert\n\n{title}\n\n{detail}\n\nDetected: {utc_now()}")
        try:
            smtp = smtplib.SMTP_SSL(self.settings.alert_smtp_server, self.settings.alert_smtp_port, timeout=10) if self.settings.alert_email_ssl else smtplib.SMTP(self.settings.alert_smtp_server, self.settings.alert_smtp_port, timeout=10)
            with smtp:
                smtp.send_message(message)
        except OSError:
            self.store.ensure_alert(source="server", severity="error", title="Alert email delivery failed", detail="The SMTP relay could not accept the monitoring alert.", active=True)

    def _server_inventory(self, server: ServerMonitor) -> list[ServerInventory]:
        metrics = {metric.key: metric for metric in server.metrics}
        local = __import__("platform").node()
        disk = metrics.get("disk_available")
        memory = metrics.get("memory_available")
        cpu = metrics.get("cpu")
        local_row = ServerInventory(
            name=local,
            address="127.0.0.1",
            role="Jarvis monitoring host",
            status="Needs Attention" if server.status == "warning" else "Good",
            total_disk=server.total_disk,
            free_disk=server.free_disk,
            threshold_status=disk.status.title() if disk else "Unavailable",
            cpu=cpu.display_value if cpu else "Unavailable",
            memory=memory.display_value if memory else "Unavailable",
            automatic_services="Needs Attention" if server.stopped_automatic_services else "Good",
        )
        return [local_row] + [ServerInventory(name=name, address=address, role=role, status="Agent not connected") for name, address, role in self.server._inventory if name.lower() != local.lower()]

class MonitoringStore:
    def __init__(self, connection_factory) -> None:
        self._connection_factory = connection_factory

    def save_snapshot(self, moveit: MoveItMonitor, server: ServerMonitor, captured_at: str) -> int:
        import json

        with self._connection_factory() as connection:
            cursor = connection.execute(
                "INSERT INTO monitoring_snapshots (captured_at, moveit_json, server_json) VALUES (?, ?, ?)",
                (captured_at, moveit.model_dump_json(), server.model_dump_json()),
            )
        return int(cursor.lastrowid)

    def ensure_alert(self, source: str, severity: Severity, title: str, detail: str, active: bool) -> bool:
        created = False
        with self._connection_factory() as connection:
            existing = connection.execute(
                "SELECT id FROM monitoring_alerts WHERE source = ? AND title = ? ORDER BY id DESC LIMIT 1",
                (source, title),
            ).fetchone()
            if active and existing is None:
                connection.execute(
                    "INSERT INTO monitoring_alerts (source, severity, title, detail, status) VALUES (?, ?, ?, ?, 'active')",
                    (source, severity, title, detail),
                )
                created = True
            elif active and existing is not None:
                connection.execute(
                    "UPDATE monitoring_alerts SET severity = ?, detail = ?, status = 'active', resolved_at = NULL WHERE id = ?",
                    (severity, detail, existing["id"]),
                )
            elif not active and existing is not None:
                connection.execute(
                    "UPDATE monitoring_alerts SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP, detail = ? WHERE id = ? AND status = 'active'",
                    (detail, existing["id"]),
                )
        return created

    def get_alerts(self, limit: int = 20) -> list[MonitoringAlert]:
        with self._connection_factory() as connection:
            rows = connection.execute(
                "SELECT id, source, severity, title, detail, status, created_at, resolved_at FROM monitoring_alerts WHERE status = 'active' ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [MonitoringAlert(**dict(row)) for row in rows]

    def resolve_alert(self, alert_id: int) -> MonitoringAlert | None:
        with self._connection_factory() as connection:
            connection.execute(
                "UPDATE monitoring_alerts SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'active'",
                (alert_id,),
            )
            row = connection.execute(
                "SELECT id, source, severity, title, detail, status, created_at, resolved_at FROM monitoring_alerts WHERE id = ?",
                (alert_id,),
            ).fetchone()
        return MonitoringAlert(**dict(row)) if row else None

    def capture_filesystem_changes(self, root: Path) -> None:
        if not root.exists():
            return
        current = {str(path.relative_to(root)): path.stat().st_mtime_ns for path in root.rglob("*") if path.is_file()}
        with self._connection_factory() as connection:
            previous_rows = connection.execute("SELECT path, modified_ns FROM filesystem_audit_state").fetchall()
            previous = {row["path"]: row["modified_ns"] for row in previous_rows}
            for path, modified_ns in current.items():
                if path not in previous:
                    self._insert_audit(connection, path, "created", "File appeared in monitored local storage.")
                elif previous[path] != modified_ns:
                    self._insert_audit(connection, path, "modified", "File modification time changed in monitored local storage.")
            for path in previous.keys() - current.keys():
                self._insert_audit(connection, path, "deleted", "File disappeared from monitored local storage.")
            connection.execute("DELETE FROM filesystem_audit_state")
            connection.executemany(
                "INSERT INTO filesystem_audit_state (path, modified_ns) VALUES (?, ?)", current.items()
            )

    def _insert_audit(self, connection, path: str, change_type: str, detail: str) -> None:
        connection.execute(
            "INSERT INTO filesystem_audit_events (path, change_type, detail) VALUES (?, ?, ?)",
            (path, change_type, detail),
        )

    def get_filesystem_audit(self, limit: int = 8) -> list[FilesystemAuditEvent]:
        with self._connection_factory() as connection:
            rows = connection.execute(
                "SELECT id, path, change_type, detail, created_at FROM filesystem_audit_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [FilesystemAuditEvent(**dict(row)) for row in rows]
