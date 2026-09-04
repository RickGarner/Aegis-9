import json
import smtplib
from email.message import EmailMessage
from typing import Callable

from app.config import Settings
from app.storage import JarvisStore, NotificationOutboxItem


class WorkflowNotificationWorker:
    def __init__(
        self,
        store: JarvisStore,
        settings: Settings,
        sender: Callable[[NotificationOutboxItem], None] | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.sender = sender or self._send_email

    def deliver_one(self) -> str:
        if not self.settings.workflow_notification_delivery_enabled:
            return "disabled"
        item = self.store.claim_notification_outbox_item()
        if item is None:
            return "idle"
        try:
            self.sender(item)
        except Exception as error:
            return self.store.fail_notification_outbox_item(
                item.id,
                f"{type(error).__name__}: {error}",
                self.settings.workflow_notification_max_attempts,
                self.settings.workflow_notification_retry_seconds,
            ) or "ignored"
        self.store.complete_notification_outbox_item(item.id)
        return "sent"

    def _send_email(self, item: NotificationOutboxItem) -> None:
        message = EmailMessage()
        message["From"] = self.settings.alert_email_from
        message["To"] = self.settings.alert_email_to
        message["Subject"] = f"A.E.G.I.S.-9: {item.subject}"
        message.set_content(json.dumps(item.payload, indent=2, sort_keys=True))
        smtp = (
            smtplib.SMTP_SSL(self.settings.alert_smtp_server, self.settings.alert_smtp_port, timeout=10)
            if self.settings.alert_email_ssl
            else smtplib.SMTP(self.settings.alert_smtp_server, self.settings.alert_smtp_port, timeout=10)
        )
        with smtp:
            smtp.send_message(message)
