"""Async email sending via aiosmtplib.

A failed send must NOT raise an exception — it should only log the error so
that form submissions always succeed even when SMTP is misconfigured.
"""
from __future__ import annotations

import logging
import ssl

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str | list[str], subject: str, body: str) -> None:
    """Send a plain-text email.  Silently drops the message if SMTP is not configured."""
    if not settings.smtp_host:
        logger.info("SMTP not configured — email skipped: %s", subject)
        return

    recipients = [to] if isinstance(to, str) else to

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=True,
        )
        logger.info("Email sent to %s: %s", recipients, subject)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send email to %s: %s", recipients, exc)


async def send_notification(subject: str, body: str) -> None:
    """Send a notification to the site's configured notify_email address."""
    targets = [e.strip() for e in settings.notify_email.split(",") if e.strip()]
    if not targets:
        logger.info("No NOTIFY_EMAIL configured — notification skipped: %s", subject)
        return
    await send_email(targets, subject, body)
