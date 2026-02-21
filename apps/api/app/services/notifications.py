from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timezone
from html import escape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import NotificationConfig, NotificationDelivery

RESEND_API_URL = "https://api.resend.com/emails"


def get_notification_config(db: Session) -> NotificationConfig:
    stmt = select(NotificationConfig).where(NotificationConfig.singleton_key == 1)
    config = db.scalar(stmt)
    if config is not None:
        return config

    config = NotificationConfig(singleton_key=1)
    db.add(config)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(stmt)
        if existing is None:
            raise
        return existing

    db.refresh(config)
    return config


def update_notification_config(
    db: Session,
    *,
    enabled: bool,
    to_email: str | None,
    daily_digest_enabled: bool,
    daily_digest_hour_utc: int | None,
    failure_alert_enabled: bool,
) -> NotificationConfig:
    config = get_notification_config(db)
    normalized_to_email = _normalize_email(to_email)

    config.enabled = enabled
    config.to_email = normalized_to_email
    config.daily_digest_enabled = daily_digest_enabled
    config.daily_digest_hour_utc = daily_digest_hour_utc
    config.failure_alert_enabled = failure_alert_enabled

    db.commit()
    db.refresh(config)
    return config


def send_test_email(
    db: Session,
    *,
    to_email: str | None = None,
    subject: str | None = None,
    body: str | None = None,
) -> NotificationDelivery:
    config = get_notification_config(db)
    recipient = _resolve_recipient_email(config, to_email)
    if recipient is None:
        raise ValueError("notification recipient email is not configured")

    return _dispatch_email(
        db,
        kind="test_email",
        recipient_email=recipient,
        subject=subject or "Video Digestor test notification",
        text_body=body or "This is a test notification from Video Digestor.",
        payload={"to_email": recipient},
        skip_reason=None,
    )


def send_failure_alert(
    db: Session,
    *,
    title: str,
    details: str,
    job_id: uuid.UUID | None = None,
    to_email: str | None = None,
) -> NotificationDelivery:
    config = get_notification_config(db)
    recipient = _resolve_recipient_email(config, to_email)
    if recipient is None:
        raise ValueError("notification recipient email is not configured")

    skip_reason: str | None = None
    if not config.enabled:
        skip_reason = "notification config is disabled"
    elif not config.failure_alert_enabled:
        skip_reason = "failure alert is disabled"

    return _dispatch_email(
        db,
        kind="failure_alert",
        recipient_email=recipient,
        subject=f"[Video Digestor] Failure alert: {title}",
        text_body=details,
        payload={"job_id": str(job_id) if job_id else None, "title": title},
        job_id=job_id,
        skip_reason=skip_reason,
    )


def send_daily_digest(
    db: Session,
    *,
    digest_markdown: str,
    digest_date: date | None = None,
    to_email: str | None = None,
    subject: str | None = None,
) -> NotificationDelivery:
    config = get_notification_config(db)
    recipient = _resolve_recipient_email(config, to_email)
    if recipient is None:
        raise ValueError("notification recipient email is not configured")

    skip_reason: str | None = None
    if not config.enabled:
        skip_reason = "notification config is disabled"
    elif not config.daily_digest_enabled:
        skip_reason = "daily digest is disabled"

    effective_date = digest_date or datetime.now(timezone.utc).date()

    return _dispatch_email(
        db,
        kind="daily_digest",
        recipient_email=recipient,
        subject=subject or f"[Video Digestor] Daily digest {effective_date.isoformat()}",
        text_body=digest_markdown,
        payload={"digest_date": effective_date.isoformat()},
        skip_reason=skip_reason,
    )


def send_video_digest(
    db: Session,
    *,
    job_id: uuid.UUID,
    digest_markdown: str,
    to_email: str | None = None,
    subject: str | None = None,
) -> NotificationDelivery:
    config = get_notification_config(db)
    recipient = _resolve_recipient_email(config, to_email)
    if recipient is None:
        raise ValueError("notification recipient email is not configured")

    skip_reason: str | None = None
    if not config.enabled:
        skip_reason = "notification config is disabled"

    return _dispatch_email(
        db,
        kind="video_digest",
        recipient_email=recipient,
        subject=subject or "[Video Digestor] Video digest",
        text_body=digest_markdown,
        payload={"job_id": str(job_id)},
        job_id=job_id,
        skip_reason=skip_reason,
    )


def send_daily_report_notification(
    db: Session,
    *,
    report_date: date | None = None,
    to_email: str | None = None,
    subject: str | None = None,
    body: str | None = None,
) -> NotificationDelivery:
    effective_date = report_date or datetime.now(timezone.utc).date()
    return send_daily_digest(
        db,
        digest_markdown=body or f"Video Digestor daily report for {effective_date.isoformat()}",
        digest_date=effective_date,
        to_email=to_email,
        subject=subject,
    )


def _dispatch_email(
    db: Session,
    *,
    kind: str,
    recipient_email: str,
    subject: str,
    text_body: str,
    payload: dict[str, object],
    job_id: uuid.UUID | None = None,
    skip_reason: str | None,
) -> NotificationDelivery:
    delivery = NotificationDelivery(
        kind=kind,
        status="queued",
        recipient_email=recipient_email,
        subject=subject,
        provider="resend",
        payload_json=payload,
        job_id=job_id,
    )
    db.add(delivery)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if kind == "video_digest" and job_id is not None:
            existing = _get_video_digest_delivery(db, job_id=job_id)
            if existing is not None:
                return existing
        raise
    db.refresh(delivery)

    if skip_reason is not None:
        delivery.status = "skipped"
        delivery.error_message = skip_reason
        db.commit()
        db.refresh(delivery)
        return delivery

    try:
        provider_message_id = _send_with_resend(
            to_email=recipient_email,
            subject=subject,
            text_body=text_body,
        )
        delivery.status = "sent"
        delivery.provider_message_id = provider_message_id
        delivery.sent_at = datetime.now(timezone.utc)
        delivery.error_message = None
    except RuntimeError as exc:
        delivery.status = "failed"
        delivery.error_message = str(exc)
        db.commit()
        db.refresh(delivery)
        raise

    db.commit()
    db.refresh(delivery)
    return delivery


def _send_with_resend(*, to_email: str, subject: str, text_body: str) -> str | None:
    resend_api_key = os.getenv("RESEND_API_KEY")
    resend_from_email = os.getenv("RESEND_FROM_EMAIL")

    if not resend_api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")
    if not resend_from_email:
        raise RuntimeError("RESEND_FROM_EMAIL is not configured")

    payload = {
        "from": resend_from_email,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
        "html": _to_html(text_body),
    }
    body = json.dumps(payload).encode("utf-8")

    request = Request(
        RESEND_API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend API returned {exc.code}: {error_body[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Resend request failed: {exc.reason}") from exc

    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError:
        return None

    message_id = parsed.get("id")
    if isinstance(message_id, str):
        return message_id
    return None


def _resolve_recipient_email(config: NotificationConfig, override_email: str | None) -> str | None:
    if override_email is not None:
        normalized_override = _normalize_email(override_email)
        if normalized_override:
            return normalized_override
    return _normalize_email(config.to_email)


def _normalize_email(raw_email: str | None) -> str | None:
    if raw_email is None:
        return None
    cleaned = raw_email.strip()
    return cleaned or None


def _to_html(text: str) -> str:
    lines = [escape(line) for line in text.splitlines()]
    html = "<br/>".join(lines)
    return f"<div>{html}</div>"


def _get_video_digest_delivery(
    db: Session,
    *,
    job_id: uuid.UUID,
) -> NotificationDelivery | None:
    stmt = (
        select(NotificationDelivery)
        .where(
            NotificationDelivery.kind == "video_digest",
            NotificationDelivery.job_id == job_id,
        )
        .order_by(NotificationDelivery.created_at.desc())
    )
    return db.scalar(stmt)
