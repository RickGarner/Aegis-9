import json
import sqlite3
import uuid
from datetime import datetime, timezone
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
    transfer_id: str
    title: str
    description: str = ""
    attachment_ids: list[int] = Field(default_factory=list)
    state: str
    monitor_slot: int | None = None
    language: str = "powershell"
    revision: int = 1
    approval_stage: str = "draft"
    schedule: dict = Field(default_factory=dict)
    archived: bool = False
    last_run_at: str | None = None
    plan_text: str = ""
    plan_provider: str = ""
    plan_model: str = ""
    implementation_text: str = ""
    implementation_provider: str = ""
    implementation_model: str = ""
    clarification_questions: list[dict] = Field(default_factory=list)
    clarification_answers: dict[str, str] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class WorkflowTransition(BaseModel):
    workflow: Workflow
    promoted_workflow: Workflow | None = None


class WorkflowTransferPackage(BaseModel):
    schema_version: int = 1
    exported_at: str
    workflow: dict
    attachments: list[dict] = Field(default_factory=list)
    activity: list[dict] = Field(default_factory=list)


class WorkflowImportResult(BaseModel):
    action: str
    workflow: Workflow
    detail: str


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
                    transfer_id TEXT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    attachment_ids TEXT NOT NULL DEFAULT '[]',
                    state TEXT NOT NULL,
                    monitor_slot INTEGER,
                    language TEXT NOT NULL DEFAULT 'powershell',
                    revision INTEGER NOT NULL DEFAULT 1,
                    approval_stage TEXT NOT NULL DEFAULT 'draft',
                    schedule_json TEXT NOT NULL DEFAULT '{}',
                    archived INTEGER NOT NULL DEFAULT 0,
                    last_run_at TEXT,
                    plan_text TEXT NOT NULL DEFAULT '',
                    plan_provider TEXT NOT NULL DEFAULT '',
                    plan_model TEXT NOT NULL DEFAULT '',
                    implementation_text TEXT NOT NULL DEFAULT '',
                    implementation_provider TEXT NOT NULL DEFAULT '',
                    implementation_model TEXT NOT NULL DEFAULT '',
                    clarification_questions_json TEXT NOT NULL DEFAULT '[]',
                    clarification_answers_json TEXT NOT NULL DEFAULT '{}',
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
            ("language", "TEXT NOT NULL DEFAULT 'powershell'"),
            ("revision", "INTEGER NOT NULL DEFAULT 1"),
            ("approval_stage", "TEXT NOT NULL DEFAULT 'draft'"),
            ("schedule_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("archived", "INTEGER NOT NULL DEFAULT 0"),
            ("last_run_at", "TEXT"),
            ("plan_text", "TEXT NOT NULL DEFAULT ''"),
            ("plan_provider", "TEXT NOT NULL DEFAULT ''"),
            ("plan_model", "TEXT NOT NULL DEFAULT ''"),
            ("implementation_text", "TEXT NOT NULL DEFAULT ''"),
            ("implementation_provider", "TEXT NOT NULL DEFAULT ''"),
            ("implementation_model", "TEXT NOT NULL DEFAULT ''"),
            ("clarification_questions_json", "TEXT NOT NULL DEFAULT '[]'"),
            ("clarification_answers_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("transfer_id", "TEXT"),
        ):
            if column not in existing_columns:
                connection.execute(f"ALTER TABLE workflows ADD COLUMN {column} {definition}")
        missing_transfer_ids = connection.execute("SELECT id FROM workflows WHERE transfer_id IS NULL OR transfer_id = ''").fetchall()
        for row in missing_transfer_ids:
            connection.execute("UPDATE workflows SET transfer_id = ? WHERE id = ?", (str(uuid.uuid4()), row["id"]))
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_workflows_transfer_id ON workflows(transfer_id)")

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

    def create_workflow(self, title: str, description: str = "", attachment_ids: list[int] | None = None, language: str = "powershell") -> Workflow:
        attachment_ids = attachment_ids or []
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO workflows (transfer_id, title, description, attachment_ids, state, language, approval_stage) VALUES (?, ?, ?, ?, 'draft', ?, 'draft')",
                (str(uuid.uuid4()), title, description, json.dumps(attachment_ids), language),
            )
            connection.execute(
                "INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)",
                ("workflow", f"Workflow '{title}' created as a draft.", "info"),
            )
            row = connection.execute(
                f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return self._workflow_from_row(row)

    @staticmethod
    def _workflow_columns() -> str:
        return "id, transfer_id, title, description, attachment_ids, state, monitor_slot, language, revision, approval_stage, schedule_json, archived, last_run_at, plan_text, plan_provider, plan_model, implementation_text, implementation_provider, implementation_model, clarification_questions_json, clarification_answers_json, created_at, updated_at"

    @staticmethod
    def _workflow_from_row(row: sqlite3.Row) -> Workflow:
        values = dict(row)
        values["attachment_ids"] = json.loads(values.get("attachment_ids") or "[]")
        values["schedule"] = json.loads(values.pop("schedule_json", None) or "{}")
        values["clarification_questions"] = json.loads(values.pop("clarification_questions_json", None) or "[]")
        values["clarification_answers"] = json.loads(values.pop("clarification_answers_json", None) or "{}")
        values["archived"] = bool(values.get("archived"))
        return Workflow(**values)

    def get_workflow(self, workflow_id: int) -> Workflow | None:
        with self._connect() as connection:
            row = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        return self._workflow_from_row(row) if row else None

    def reset_invalid_workflow_plan(self, workflow_id: int) -> Workflow | None:
        with self._connect() as connection:
            current = connection.execute(
                "SELECT title, state FROM workflows WHERE id = ? AND archived = 0",
                (workflow_id,),
            ).fetchone()
            if current is None or current["state"] not in {"design_review", "needs_clarification", "plan_review"}:
                return None
            connection.execute(
                """UPDATE workflows SET state='draft', approval_stage='draft', plan_text='', plan_provider='', plan_model='',
                clarification_questions_json='[]', clarification_answers_json='{}', updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (workflow_id,),
            )
            connection.execute(
                "INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)",
                ("workflow-ai", f"Empty AI plan rejected for '{current['title']}'; workflow returned to draft.", "warning"),
            )
            row = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        return self._workflow_from_row(row)

    def export_workflow(self, workflow_id: int) -> WorkflowTransferPackage | None:
        with self._connect() as connection:
            row = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
            if row is None:
                return None
            workflow = self._workflow_from_row(row)
            attachments = []
            for file_id in workflow.attachment_ids:
                file_row = connection.execute(
                    "SELECT name, size, content_type, status, extracted_text, created_at FROM files WHERE id = ?",
                    (file_id,),
                ).fetchone()
                if file_row:
                    attachments.append(dict(file_row))
            activity = [
                dict(item)
                for item in connection.execute(
                    "SELECT event_type, message, tone, created_at FROM activity_logs WHERE message LIKE ? ORDER BY id",
                    (f"%'{workflow.title}'%",),
                ).fetchall()
            ]
        return WorkflowTransferPackage(
            exported_at=datetime.now(timezone.utc).isoformat(),
            workflow=workflow.model_dump(),
            attachments=attachments,
            activity=activity,
        )

    def import_workflow(self, package: WorkflowTransferPackage) -> WorkflowImportResult:
        if package.schema_version != 1:
            raise ValueError(f"Unsupported workflow package schema version {package.schema_version}.")
        incoming = Workflow.model_validate(package.workflow)
        with self._connect() as connection:
            existing_row = connection.execute(
                f"SELECT {self._workflow_columns()} FROM workflows WHERE transfer_id = ?",
                (incoming.transfer_id,),
            ).fetchone()
            if existing_row:
                existing = self._workflow_from_row(existing_row)
                if incoming.revision < existing.revision or (
                    incoming.revision == existing.revision and incoming.updated_at <= existing.updated_at
                ):
                    return WorkflowImportResult(
                        action="unchanged",
                        workflow=existing,
                        detail="The local workflow is the same revision or newer; no data was overwritten.",
                    )

            attachment_ids = []
            for attachment in package.attachments:
                cursor = connection.execute(
                    "INSERT INTO files (name, size, content_type, stored_name, status, extracted_text, created_at) VALUES (?, ?, ?, NULL, ?, ?, ?)",
                    (
                        str(attachment.get("name") or "Imported attachment"),
                        int(attachment.get("size") or 0),
                        attachment.get("content_type"),
                        str(attachment.get("status") or "extracted"),
                        attachment.get("extracted_text"),
                        str(attachment.get("created_at") or incoming.created_at),
                    ),
                )
                attachment_ids.append(cursor.lastrowid)

            imported_state = "paused" if incoming.state in {"running", "queued", "paused"} else incoming.state
            monitor_slot = None
            values = (
                incoming.transfer_id, incoming.title, incoming.description, json.dumps(attachment_ids), imported_state,
                monitor_slot, incoming.language, incoming.revision, incoming.approval_stage, json.dumps(incoming.schedule),
                int(incoming.archived), incoming.last_run_at, incoming.plan_text, incoming.plan_provider, incoming.plan_model,
                incoming.implementation_text, incoming.implementation_provider, incoming.implementation_model,
                json.dumps(incoming.clarification_questions), json.dumps(incoming.clarification_answers),
                incoming.created_at, incoming.updated_at,
            )
            if existing_row:
                workflow_id = existing_row["id"]
                connection.execute(
                    """UPDATE workflows SET transfer_id=?, title=?, description=?, attachment_ids=?, state=?, monitor_slot=?,
                    language=?, revision=?, approval_stage=?, schedule_json=?, archived=?, last_run_at=?, plan_text=?, plan_provider=?,
                    plan_model=?, implementation_text=?, implementation_provider=?, implementation_model=?, clarification_questions_json=?,
                    clarification_answers_json=?, created_at=?, updated_at=? WHERE id=?""",
                    (*values, workflow_id),
                )
                action = "updated"
            else:
                cursor = connection.execute(
                    """INSERT INTO workflows (transfer_id, title, description, attachment_ids, state, monitor_slot, language,
                    revision, approval_stage, schedule_json, archived, last_run_at, plan_text, plan_provider, plan_model,
                    implementation_text, implementation_provider, implementation_model, clarification_questions_json,
                    clarification_answers_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    values,
                )
                workflow_id = cursor.lastrowid
                action = "imported"
            for event in package.activity:
                connection.execute(
                    "INSERT INTO activity_logs (event_type, message, tone, created_at) VALUES (?, ?, ?, ?)",
                    (
                        str(event.get("event_type") or "workflow-import"),
                        str(event.get("message") or f"Imported workflow '{incoming.title}'."),
                        str(event.get("tone") or "info"),
                        str(event.get("created_at") or incoming.updated_at),
                    ),
                )
            connection.execute(
                "INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)",
                ("workflow-import", f"Workflow '{incoming.title}' {action} from a portable package.", "success"),
            )
            row = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        detail = f"Workflow {action} successfully."
        if imported_state != incoming.state:
            detail += f" Active state '{incoming.state}' was imported as paused for safety."
        return WorkflowImportResult(action=action, workflow=self._workflow_from_row(row), detail=detail)

    def update_workflow(self, workflow_id: int, title: str, description: str, attachment_ids: list[int], language: str) -> Workflow | None:
        with self._connect() as connection:
            current = connection.execute("SELECT title, state FROM workflows WHERE id = ? AND archived = 0", (workflow_id,)).fetchone()
            if current is None or current["state"] in {"running", "paused"}:
                return None
            connection.execute(
                "UPDATE workflows SET title = ?, description = ?, attachment_ids = ?, language = ?, revision = revision + 1, state = 'draft', approval_stage = 'draft', schedule_json = '{}', plan_text = '', plan_provider = '', plan_model = '', implementation_text = '', implementation_provider = '', implementation_model = '', clarification_questions_json = '[]', clarification_answers_json = '{}', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, description, json.dumps(attachment_ids), language, workflow_id),
            )
            connection.execute("INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)", ("workflow", f"Workflow '{title}' revised; prior approvals invalidated.", "warning"))
            row = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        return self._workflow_from_row(row)

    def review_workflow(self, workflow_id: int, decision: str) -> Workflow | None:
        transitions = {
            ("plan_review", "approve_plan"): ("plan_approved", "plan_approved"),
            ("implementation_review", "submit_for_test"): ("test_ready", "test_ready"),
            ("test_ready", "test_pass"): ("test_passed", "test_passed"),
            ("test_ready", "test_fail"): ("test_failed", "test_failed"),
            ("test_failed", "submit_for_test"): ("test_ready", "test_ready"),
            ("test_passed", "user_accept"): ("user_accepted", "user_accepted"),
            ("user_accepted", "request_supervisor"): ("supervisor_pending", "supervisor_pending"),
            ("supervisor_pending", "supervisor_approve"): ("approved", "approved"),
        }
        with self._connect() as connection:
            current = connection.execute("SELECT title, state FROM workflows WHERE id = ? AND archived = 0", (workflow_id,)).fetchone()
            if current is None:
                return None
            if decision == "reject" and current["state"] not in {"running", "paused", "completed"}:
                next_state, stage = "rejected", "rejected"
            else:
                transition = transitions.get((current["state"], decision))
                if transition is None:
                    return None
                next_state, stage = transition
            connection.execute("UPDATE workflows SET state = ?, approval_stage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (next_state, stage, workflow_id))
            connection.execute("INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)", ("workflow-approval", f"Workflow '{current['title']}' decision: {decision}.", "success" if decision in {"test_pass", "user_accept", "supervisor_approve"} else "warning"))
            row = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        return self._workflow_from_row(row)

    def save_workflow_plan(self, workflow_id: int, content: str, provider: str, model: str, questions: list[dict] | None = None, finalizing: bool = False) -> Workflow | None:
        questions = questions or []
        with self._connect() as connection:
            current = connection.execute("SELECT title, state FROM workflows WHERE id = ? AND archived = 0", (workflow_id,)).fetchone()
            if current is None or current["state"] not in {"draft", "rejected", "plan_review"}:
                return None
            next_state = "needs_clarification" if questions else "plan_review" if finalizing else "design_review"
            connection.execute("UPDATE workflows SET plan_text = ?, plan_provider = ?, plan_model = ?, implementation_text = '', implementation_provider = '', implementation_model = '', clarification_questions_json = ?, state = ?, approval_stage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (content, provider, model, json.dumps(questions), next_state, next_state, workflow_id))
            message = f"Final plan for '{current['title']}' is ready for approval or rejection." if finalizing and not questions else f"Plan designed for '{current['title']}' by {provider}/{model}."
            connection.execute("INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)", ("workflow-ready" if finalizing and not questions else "workflow-ai", message, "success" if finalizing and not questions else "info"))
            row = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        return self._workflow_from_row(row)

    def save_clarification_answer(self, workflow_id: int, question_id: str, answer: str) -> Workflow | None:
        with self._connect() as connection:
            current = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ? AND archived = 0", (workflow_id,)).fetchone()
            if current is None or current["state"] not in {"needs_clarification", "design_review"}:
                return None
            workflow = self._workflow_from_row(current)
            valid_ids = {str(question.get("id")) for question in workflow.clarification_questions}
            if question_id not in valid_ids:
                return None
            answers = dict(workflow.clarification_answers)
            answers[question_id] = answer.strip()
            connection.execute("UPDATE workflows SET clarification_answers_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (json.dumps(answers), workflow_id))
            connection.execute("INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)", ("workflow-clarification", f"One clarification answer submitted for '{workflow.title}'.", "info"))
            row = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        return self._workflow_from_row(row)

    def begin_workflow_reevaluation(self, workflow_id: int) -> Workflow | None:
        with self._connect() as connection:
            current = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ? AND archived = 0", (workflow_id,)).fetchone()
            if current is None or current["state"] not in {"needs_clarification", "design_review"}:
                return None
            workflow = self._workflow_from_row(current)
            missing = [str(question.get("id")) for question in workflow.clarification_questions if question.get("required", True) and not workflow.clarification_answers.get(str(question.get("id")), "").strip()]
            if missing:
                return None
            connection.execute("UPDATE workflows SET state = 'draft', approval_stage = 'reevaluating', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (workflow_id,))
            row = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        return self._workflow_from_row(row)

    def save_workflow_implementation(self, workflow_id: int, content: str, provider: str, model: str) -> Workflow | None:
        with self._connect() as connection:
            current = connection.execute("SELECT title, state FROM workflows WHERE id = ? AND archived = 0", (workflow_id,)).fetchone()
            if current is None or current["state"] != "plan_approved":
                return None
            connection.execute("UPDATE workflows SET implementation_text = ?, implementation_provider = ?, implementation_model = ?, state = 'implementation_review', approval_stage = 'implementation_review', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (content, provider, model, workflow_id))
            connection.execute("INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)", ("workflow-ai", f"Implementation generated for '{current['title']}' by {provider}/{model}.", "info"))
            row = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        return self._workflow_from_row(row)

    def set_workflow_schedule(self, workflow_id: int, schedule: dict) -> Workflow | None:
        with self._connect() as connection:
            current = connection.execute("SELECT title, state FROM workflows WHERE id = ? AND archived = 0", (workflow_id,)).fetchone()
            if current is None or current["state"] != "approved":
                return None
            connection.execute("UPDATE workflows SET schedule_json = ?, state = 'scheduled', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (json.dumps(schedule), workflow_id))
            connection.execute("INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)", ("workflow-schedule", f"Workflow '{current['title']}' scheduled.", "success"))
            row = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        return self._workflow_from_row(row)

    def archive_workflow(self, workflow_id: int) -> Workflow | None:
        with self._connect() as connection:
            current = connection.execute("SELECT title, state FROM workflows WHERE id = ? AND archived = 0", (workflow_id,)).fetchone()
            if current is None or current["state"] in {"running", "paused"}:
                return None
            connection.execute("UPDATE workflows SET archived = 1, state = 'archived', monitor_slot = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (workflow_id,))
            connection.execute("INSERT INTO activity_logs (event_type, message, tone) VALUES (?, ?, ?)", ("workflow", f"Workflow '{current['title']}' archived.", "warning"))
            row = connection.execute(f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        return self._workflow_from_row(row)

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
                f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?",
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
                f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?",
                (workflow_id,),
            ).fetchone()
        return WorkflowTransition(
            workflow=self._workflow_from_row(row),
            promoted_workflow=promoted_workflow,
        )

    def get_workflows(self) -> list[Workflow]:
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT {self._workflow_columns()} FROM workflows WHERE archived = 0 ORDER BY id DESC"
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
            f"SELECT {self._workflow_columns()} FROM workflows WHERE id = ?",
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
