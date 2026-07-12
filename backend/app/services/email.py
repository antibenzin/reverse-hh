"""Email delivery with SMTP or console fallback."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(*, to: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        logger.info("EMAIL to=%s subject=%s body=%s", to, subject, body)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_user or "noreply@reverse-hh.local"
    message["To"] = to
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        if settings.smtp_user:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
