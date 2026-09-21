import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from app.config import Settings
from app.credential_broker import ProtectedCredential
from app.storage import JarvisStore
from app.workflow_notifications import WorkflowNotificationWorker


def create_outbox_item(store: JarvisStore) -> int:
    with store._connect() as connection:
        cursor = connection.execute(
            "INSERT INTO notification_outbox(category,subject,payload_json) VALUES('workflow-run','Workflow complete',?)",
            (json.dumps({"workflow_id": 7, "run_id": 11, "status": "succeeded"}),),
        )
        return int(cursor.lastrowid)


def test_notification_delivery_is_disabled_by_default() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = JarvisStore(Path(directory) / "aegis.db")
        store.initialize()
        item_id = create_outbox_item(store)
        worker = WorkflowNotificationWorker(
            store,
            Settings(JARVIS_WORKFLOW_NOTIFICATION_DELIVERY_ENABLED=False),
            sender=lambda _: None,
        )

        assert worker.deliver_one() == "disabled"
        with store._connect() as connection:
            assert connection.execute("SELECT status FROM notification_outbox WHERE id=?", (item_id,)).fetchone()["status"] == "pending"


def test_notification_delivery_marks_item_sent() -> None:
    delivered = []
    with tempfile.TemporaryDirectory() as directory:
        store = JarvisStore(Path(directory) / "aegis.db")
        store.initialize()
        item_id = create_outbox_item(store)
        settings = Settings(JARVIS_WORKFLOW_NOTIFICATION_DELIVERY_ENABLED=True)
        worker = WorkflowNotificationWorker(store, settings, sender=delivered.append)

        assert worker.deliver_one() == "sent"
        assert delivered[0].payload["workflow_id"] == 7
        with store._connect() as connection:
            row = connection.execute("SELECT status,attempts,sent_at FROM notification_outbox WHERE id=?", (item_id,)).fetchone()
        assert row["status"] == "sent"
        assert row["attempts"] == 1
        assert row["sent_at"]


def test_notification_failure_retries_then_becomes_terminal() -> None:
    def fail(_):
        raise OSError("relay unavailable")

    with tempfile.TemporaryDirectory() as directory:
        store = JarvisStore(Path(directory) / "aegis.db")
        store.initialize()
        item_id = create_outbox_item(store)
        settings = Settings(
            JARVIS_WORKFLOW_NOTIFICATION_DELIVERY_ENABLED=True,
            JARVIS_WORKFLOW_NOTIFICATION_MAX_ATTEMPTS=2,
            JARVIS_WORKFLOW_NOTIFICATION_RETRY_SECONDS=15,
        )
        worker = WorkflowNotificationWorker(store, settings, sender=fail)

        assert worker.deliver_one() == "pending"
        with store._connect() as connection:
            connection.execute("UPDATE notification_outbox SET available_at=CURRENT_TIMESTAMP WHERE id=?", (item_id,))
        assert worker.deliver_one() == "failed"
        with store._connect() as connection:
            row = connection.execute("SELECT status,attempts,last_error FROM notification_outbox WHERE id=?", (item_id,)).fetchone()
        assert row["status"] == "failed"
        assert row["attempts"] == 2
        assert "relay unavailable" in row["last_error"]


def test_notification_history_is_bounded_and_parses_payloads() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = JarvisStore(Path(directory) / "aegis.db")
        store.initialize()
        first_id = create_outbox_item(store)
        create_outbox_item(store)

        items = store.get_notification_outbox_items("workflow-run", limit=1)

        assert len(items) == 1
        assert items[0].id > first_id
        assert items[0].payload["run_id"] == 11


def test_only_failed_notifications_can_be_requeued() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = JarvisStore(Path(directory) / "aegis.db")
        store.initialize()
        item_id = create_outbox_item(store)
        assert store.retry_notification_outbox_item(item_id) is None
        with store._connect() as connection:
            connection.execute(
                "UPDATE notification_outbox SET status='failed',attempts=5,last_error='relay unavailable' WHERE id=?",
                (item_id,),
            )

        retried = store.retry_notification_outbox_item(item_id)

        assert retried is not None
        assert retried.status == "pending"
        assert retried.attempts == 0
        assert retried.last_error == ""


@patch("app.workflow_notifications.resolve_credential")
@patch("app.workflow_notifications.smtplib.SMTP")
def test_authenticated_smtp_uses_protected_credential(smtp_factory: Mock, resolve: Mock) -> None:
    resolve.return_value = ProtectedCredential("protected-sender", "protected-secret")
    smtp = smtp_factory.return_value
    smtp.__enter__.return_value = smtp
    with tempfile.TemporaryDirectory() as directory:
        store = JarvisStore(Path(directory) / "aegis.db")
        store.initialize()
        item_id = create_outbox_item(store)
        item = next(item for item in store.get_notification_outbox_items(limit=10) if item.id == item_id)
        worker = WorkflowNotificationWorker(store, Settings())

        worker._send_email(item)

    resolve.assert_called_once_with("Aegis-9/SMTP/Alerts", None, None)
    smtp.login.assert_called_once_with("protected-sender", "protected-secret")
    smtp.send_message.assert_called_once()
