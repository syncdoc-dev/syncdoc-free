"""Transactional email delivery helpers."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings
from app.models.user import User

logger = logging.getLogger(__name__)


class EmailConfigurationError(RuntimeError):
    """Raised when email delivery is not configured."""


def _ensure_email_configured() -> None:
    settings = get_settings()
    if not settings.email_enabled:
        raise EmailConfigurationError("Email delivery is disabled")
    if settings.email_provider != "smtp":
        raise EmailConfigurationError(f"Unsupported email provider: {settings.email_provider}")
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        raise EmailConfigurationError("SMTP host, username, and password must be configured")


def _build_message(*, to_address: str, subject: str, body: str) -> EmailMessage:
    settings = get_settings()
    message = EmailMessage()
    from_header = (
        f"{settings.email_from_name} <{settings.email_from_address}>"
        if settings.email_from_name
        else settings.email_from_address
    )
    message["Subject"] = subject
    message["From"] = from_header
    message["To"] = to_address
    if settings.email_reply_to:
        message["Reply-To"] = settings.email_reply_to
    message.set_content(body)
    return message


def _send_message(message: EmailMessage) -> None:
    settings = get_settings()
    _ensure_email_configured()
    smtp_host = settings.smtp_host
    smtp_username = settings.smtp_username
    smtp_password = settings.smtp_password
    if smtp_host is None or smtp_username is None or smtp_password is None:
        raise EmailConfigurationError("SMTP host, username, and password must be configured")

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(smtp_host, settings.smtp_port, timeout=20) as server:
            server.login(smtp_username, smtp_password)
            server.send_message(message)
        return

    with smtplib.SMTP(smtp_host, settings.smtp_port, timeout=20) as server:
        server.ehlo()
        if settings.smtp_use_tls:
            server.starttls()
            server.ehlo()
        server.login(smtp_username, smtp_password)
        server.send_message(message)


async def send_email(*, to_address: str, subject: str, body: str) -> None:
    message = _build_message(to_address=to_address, subject=subject, body=body)
    await asyncio.to_thread(_send_message, message)


async def send_password_reset_email(user: User, reset_url: str) -> None:
    if not user.email:
        return
    body = (
        f"Hello {user.name or user.login},\n\n"
        "We received a request to reset your SyncDoc password.\n\n"
        f"Reset your password here:\n{reset_url}\n\n"
        f"This link expires in {get_settings().password_reset_expire_minutes} minutes.\n\n"
        "If you did not request this, you can safely ignore this email.\n"
    )
    await send_email(
        to_address=user.email,
        subject="Reset your SyncDoc password",
        body=body,
    )


async def send_registration_welcome_email(user: User) -> None:
    if not user.email:
        return
    body = (
        f"Hello {user.name or user.login},\n\n"
        "Welcome to SyncDoc.\n\n"
        "Your account has been created successfully and you can now sign in to start "
        "generating documentation from your infrastructure repositories.\n\n"
        f"App URL: {get_settings().frontend_url}\n"
    )
    await send_email(
        to_address=user.email,
        subject="Welcome to SyncDoc",
        body=body,
    )


async def send_registration_notification(user: User, *, source: str) -> None:
    notify_to = get_settings().registration_notify_to
    if not notify_to:
        return

    body = (
        "A new SyncDoc user registered.\n\n"
        f"Login: {user.login}\n"
        f"Email: {user.email or 'n/a'}\n"
        f"Name: {user.name or 'n/a'}\n"
        f"Auth provider: {user.auth_provider}\n"
        f"Registration source: {source}\n"
        f"Marketing consent: {'yes' if user.marketing_opt_in else 'no'}\n"
        f"Created at: {user.created_at.isoformat()}\n"
    )
    await send_email(
        to_address=notify_to,
        subject=f"New SyncDoc registration: {user.login}",
        body=body,
    )


async def safe_send_registration_emails(user: User, *, source: str) -> None:
    for task in (
        send_registration_welcome_email(user),
        send_registration_notification(user, source=source),
    ):
        try:
            await task
        except Exception:
            logger.exception("Failed sending registration email for user %s", user.login)
