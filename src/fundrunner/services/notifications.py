"""Utility helpers for sending email and Discord notifications."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from fundrunner.utils.config import (
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    NOTIFICATION_EMAIL,
    DISCORD_WEBHOOK_URL,
)

logger = logging.getLogger(__name__)


def send_email(subject: str, body: str) -> None:
    """Send an email notification using SMTP settings."""
    if not SMTP_SERVER or not NOTIFICATION_EMAIL:
        return
    msg = MIMEMultipart()
    msg["From"] = SMTP_USERNAME
    msg["To"] = NOTIFICATION_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            if SMTP_USERNAME and SMTP_PASSWORD:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as exc:  # pragma: no cover - log only
        logger.error("Email notification failed: %s", exc)


def send_discord(message: str) -> None:
    """Send a Discord notification if webhook configured."""
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(
            DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10
        )
    except Exception as exc:  # pragma: no cover - log only
        logger.error("Discord notification failed: %s", exc)


def notify(subject: str, message: str) -> None:
    """Send an alert via all configured channels."""
    send_email(subject, message)
    send_discord(f"**{subject}**\n{message}")
