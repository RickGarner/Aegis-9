import sqlite3
from pathlib import Path

from pydantic import BaseModel, Field

from app.providers import ChatMessage


class ActivityLog(BaseModel):
    created_at: str
    event_type: str
    message: str
    tone: str


class FileEntry(BaseModel):
    id: int | None = None
    name: str
    size: int
    content_type: str | None = None
    status: str = "staged"
    extracted_preview: str | None = None
    created_at: str | None = None


class ApprovalState(BaseModel):
    decision: str = "pending"
    updated_at: str | None = None


class Workflow(BaseModel):
    id: int
    title: str
    description: str = ""
    attachment_ids: list[int] = Field(default_factory=list)
    state: str
    monitor_slot: int | None = None
    created_at: str
    updated_at: str


class WorkflowTransition(BaseModel):
    workflow: Workflow
    promoted_workflow: Workflow | None = None


class WorkflowTopologyState(BaseModel):
    fingerprint: str | None = None
    updated_at: str | None = None


class SessionState(BaseModel):
    messages: list[ChatMessage]
    activity: list[ActivityLog]
    files: list[FileEntry]
    approval: ApprovalState


class JarvisStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    tone TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    content_type TEXT,
                    stored_name TEXT,
                    status TEXT NOT NULL DEFAULT 'staged',
                    extracted_text TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS approval_states (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    decision TEXT NOT NULL DEFAULT 'pending',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    attachment_ids TEXT NOT NULL DEFAULT '[]',
                    state TEXT NOT NULL,
                    monitor_slot INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS workflow_topology_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    fingerprint TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS monitoring_snapshots (
                    id INTEGER PRIMARY KEY,
                    captured_at TEXT NOT NULL,
                    moveit_json TEXT NOT NULL,
                    server_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS monitoring_alerts (
                    id INTEGER PRIMARY KEY,
                    source TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TEXT
                );

                CREATE TABLE IF NOT EXISTS filesystem_audit_events (
                    id INTEGER PRIMARY KEY,
                    path TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS filesystem_audit_state (
                    path TEXT PRIMARY KEY,
                    modified_ns INTEGER NOT NULL
                );
                """
            )
            connection.execute("INSERT OR IGNORE INTO approval_states (id) VALUES (1)")
            connection.execute("INSERT OR IGNORE INTO workflow_topology_state (id) VALUES (1)")
            self._migrate_files_table(connection)
            self._migrate_workflows_table(connection)

    def _migrate_files_table(self, connection: sqlite3.Connection) -> None:
        existing_columns = {row["name"] for row in connection.execute("PRAGMA table_info(files)").fetchall()}
        for column, definition in (
            ("stored_name", "TEXT"),
            ("status", "TEXT NOT NULL DEFAULT 'staged'"),
            ("extracted_text", "TEXT"),
        ):
            if column not in existing_columns:
                connection.execute(f"ALTER TABLE files ADD COLUMN {column} {definition}")

    def _migrate_workflows_table(self, connection: sqlite3.Connection) -> None:
        existing_columns = {row["name"] for row in connection.execute("PRAGMA table_info(workflows)").fetchall()}
        for column, definition in (
            ("description", "TEXT NOT NULL DEFAULT ''"),
            ("attachment_ids", "TEXT NOT NULL DEFAULT '[]'"),
        ):
            if column not in existing_columns:
                connection.execute(f"ALTER TABLE workflows ADD COLUMN {column} {definition}")

    def record_chat(self, user_message: ChatMessage, assistant_message: ChatMessage) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO messages (role, content) VALUES (?, ?)",
                (user_message.role, user_message.content),
            )
            connection.execute(
                "INSERT INTO messages (role, content) VALUES (?, ?)",
                (assistant_message.role, assistant_message.content),
            )
            connection.execute(
                "INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)",
                ("chat", "Assistant response received", "success"),
            )

    def save_uploaded_file(
        self,
        name: str,
        size: int,
        content_type: str | None,
        stored_name: str,
        extracted_text: str | None,
    ) -> FileEntry:
        status = "extracted" if extracted_text else "staged"
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO files (name, size, content_type, stored_name, status, extracted_text) VALUES (?, ?, ?, ?, ?, ?)",
                (name, size, content_type, stored_name, status, extracted_text),
            )
            connection.execute(
                "INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)",
                ("file", f"Staged {name}" + (" and extracted text context" if extracted_text else ""), "success"),
            )
            row = connection.execute(
                "SELECT id, name, size, content_type, status, substr(extracted_text, 1, 240) AS extracted_preview, created_at FROM files WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return FileEntry(**dict(row))

    def get_file_content(self, file_id: int) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT extracted_text FROM files WHERE id = ?",
                (file_id,),
            ).fetchone()
        return row["extracted_text"] if row else None

    def delete_file(self, file_id: int) -> str | None:
        with self._connect() as connection:
            row = connection.execute("SELECT name, stored_name FROM files WHERE id = ?", (file_id,)).fetchone()
            if row is None:
                return None
            connection.execute("DELETE FROM files WHERE id = ?", (file_id,))
            connection.execute("INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)", ("file", f"Removed {row['name']}", "info"))
        return row["stored_name"]

    def set_approval(self, decision: str) -> ApprovalState:
        with self._connect() as connection:
            connection.execute(
                "UPDATE approval_states SET decision = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                (decision,),
            )
            connection.execute(
                "INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)",
                ("approval", f"Approval preview {decision}; no action executed.", "success" if decision == "approved" else "warning"),
            )
            row = connection.execute(
                "SELECT decision, updated_at FROM approval_states WHERE id = 1"
            ).fetchone()
        return ApprovalState(**dict(row))

    def create_workflow(self, title: str, description: str = "", attachment_ids: list[int] | None = None) -> Workflow:
        import json

        attachment_ids = attachment_ids or []
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO workflows (title, description, attachment_ids, state) VALUES (?, ?, ?, 'awaiting_approval')",
                (title, description, json.dumps(attachment_ids)),
            )
            connection.execute(
                "INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)",
                ("workflow", f"Workflow '{title}' is awaiting approval.", "info"),
            )
            row = connection.execute(
                "SELECT id, title, description, attachment_ids, state, monitor_slot, created_at, updated_at FROM workflows WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return self._workflow_from_row(row)

    @staticmethod
    def _workflow_from_row(row: sqlite3.Row) -> Workflow:
        import json

        values = dict(row)
        values["attachment_ids"] = json.loads(values.get("attachment_ids") or "[]")
        return Workflow(**values)

    def approve_workflow(self, workflow_id: int, capacity: int) -> Workflow | None:
        with self._connect() as connection:
            workflow = connection.execute(
                "SELECT id, title, description, attachment_ids, state FROM workflows WHERE id = ?",
                (workflow_id,),
            ).fetchone()
            if workflow is None or workflow["state"] != "awaiting_approval":
                return None

            active_slots = {
                row["monitor_slot"]
                for row in connection.execute(
                    "SELECT monitor_slot FROM workflows WHERE state IN ('running', 'paused') AND monitor_slot IS NOT NULL"
                ).fetchall()
            }
            available_slot = next((slot for slot in range(1, capacity + 1) if slot not in active_slots), None)
            state = "running" if available_slot is not None else "queued"
            connection.execute(
                "UPDATE workflows SET state = ?, monitor_slot = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (state, available_slot, workflow_id),
            )
            connection.execute(
                "INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)",
                ("workflow", f"Workflow '{workflow['title']}' {state}.", "success" if state == "running" else "warning"),
            )
            row = connection.execute(
                "SELECT id, title, description, attachment_ids, state, monitor_slot, created_at, updated_at FROM workflows WHERE id = ?",
                (workflow_id,),
            ).fetchone()
        return self._workflow_from_row(row)

    def transition_workflow(
        self,
        workflow_id: int,
        action: str,
        capacity: int,
    ) -> WorkflowTransition | None:
        with self._connect() as connection:
            workflow = connection.execute(
                "SELECT id, title, description, attachment_ids, state, monitor_slot FROM workflows WHERE id = ?",
                (workflow_id,),
            ).fetchone()
            if workflow is None:
                return None

            current_state = workflow["state"]
            if action == "pause" and current_state == "running":
                next_state = "paused"
                next_slot = workflow["monitor_slot"]
            elif action == "resume" and current_state == "paused":
                next_state = "running"
                next_slot = workflow["monitor_slot"]
            elif action == "stop" and current_state in {"awaiting_approval", "queued", "running", "paused"}:
                next_state = "stopped"
                next_slot = None
            else:
                return None

            connection.execute(
                "UPDATE workflows SET state = ?, monitor_slot = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (next_state, next_slot, workflow_id),
            )
            tone = "warning" if action == "stop" else "info"
            connection.execute(
                "INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)",
                ("workflow", f"Workflow '{workflow['title']}' {next_state}.", tone),
            )
            promoted_workflow = self._promote_next_queued_workflow(connection, capacity)
            row = connection.execute(
                "SELECT id, title, description, attachment_ids, state, monitor_slot, created_at, updated_at FROM workflows WHERE id = ?",
                (workflow_id,),
            ).fetchone()
        return WorkflowTransition(
            workflow=self._workflow_from_row(row),
            promoted_workflow=promoted_workflow,
        )

    def get_workflows(self) -> list[Workflow]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, title, description, attachment_ids, state, monitor_slot, created_at, updated_at FROM workflows ORDER BY id DESC"
            ).fetchall()
        return [self._workflow_from_row(row) for row in rows]

    def reconcile_workflow_topology(self, fingerprint: str, available_slots: set[int]) -> tuple[bool, list[int]]:
        with self._connect() as connection:
            topology_row = connection.execute(
                "SELECT fingerprint FROM workflow_topology_state WHERE id = 1"
            ).fetchone()
            changed = topology_row["fingerprint"] != fingerprint
            if not changed:
                return False, []

            affected_workflows = connection.execute(
                "SELECT id, title FROM workflows WHERE state IN ('running', 'paused') AND monitor_slot IS NOT NULL"
            ).fetchall()
            requeued_workflow_ids: list[int] = []
            for workflow in affected_workflows:
                slot_row = connection.execute(
                    "SELECT monitor_slot FROM workflows WHERE id = ?", (workflow["id"],)
                ).fetchone()
                if slot_row["monitor_slot"] not in available_slots:
                    connection.execute(
                        "UPDATE workflows SET state = 'queued', monitor_slot = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (workflow["id"],),
                    )
                    connection.execute(
                        "INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)",
                        ("workflow", f"Workflow '{workflow['title']}' requeued after its display slot was removed.", "warning"),
                    )
                    requeued_workflow_ids.append(workflow["id"])

            connection.execute(
                "UPDATE workflow_topology_state SET fingerprint = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                (fingerprint,),
            )
            connection.execute(
                "INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)",
                ("topology", "Display layout changed; workflow placements reconciled.", "warning"),
            )
        return True, requeued_workflow_ids

    def get_workflow_topology_state(self) -> WorkflowTopologyState:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT fingerprint, updated_at FROM workflow_topology_state WHERE id = 1"
            ).fetchone()
        return WorkflowTopologyState(**dict(row))

    def _promote_next_queued_workflow(
        self,
        connection: sqlite3.Connection,
        capacity: int,
    ) -> Workflow | None:
        active_slots = {
            row["monitor_slot"]
            for row in connection.execute(
                "SELECT monitor_slot FROM workflows WHERE state IN ('running', 'paused') AND monitor_slot IS NOT NULL"
            ).fetchall()
        }
        available_slot = next((slot for slot in range(1, capacity + 1) if slot not in active_slots), None)
        if available_slot is None:
            return None

        queued_workflow = connection.execute(
            "SELECT id, title, description, attachment_ids FROM workflows WHERE state = 'queued' ORDER BY id LIMIT 1"
        ).fetchone()
        if queued_workflow is None:
            return None

        connection.execute(
            "UPDATE workflows SET state = 'running', monitor_slot = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (available_slot, queued_workflow["id"]),
        )
        connection.execute(
            "INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)",
            ("workflow", f"Workflow '{queued_workflow['title']}' promoted to running.", "success"),
        )
        row = connection.execute(
            "SELECT id, title, description, attachment_ids, state, monitor_slot, created_at, updated_at FROM workflows WHERE id = ?",
            (queued_workflow["id"],),
        ).fetchone()
        return self._workflow_from_row(row)

    def get_session(self, limit: int = 100) -> SessionState:
        with self._connect() as connection:
            message_rows = connection.execute(
                "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            activity_rows = connection.execute(
                "SELECT created_at, event_type, message, tone FROM activity_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            file_rows = connection.execute(
                "SELECT id, name, size, content_type, status, substr(extracted_text, 1, 240) AS extracted_preview, created_at FROM files ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            approval_row = connection.execute(
                "SELECT decision, updated_at FROM approval_states WHERE id = 1"
            ).fetchone()

        return SessionState(
            messages=[ChatMessage(**dict(row)) for row in reversed(message_rows)],
            activity=[ActivityLog(**dict(row)) for row in activity_rows],
            files=[FileEntry(**dict(row)) for row in file_rows],
            approval=ApprovalState(**dict(approval_row)),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection