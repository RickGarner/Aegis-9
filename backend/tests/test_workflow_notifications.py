import json
import tempfile
from pathlib import Path

from app.config import Settings
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
