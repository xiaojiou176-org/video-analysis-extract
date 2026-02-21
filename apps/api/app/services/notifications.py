from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from html import escape

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
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

    effective_skip_reason = skip_reason
    if effective_skip_reason is None and not settings.notification_enabled:
        effective_skip_reason = "notification is disabled by environment"

    if effective_skip_reason is not None:
        delivery.status = "skipped"
        delivery.error_message = effective_skip_reason
        db.commit()
        db.refresh(delivery)
        return delivery

    try:
        provider_message_id = _send_with_resend(
            to_email=recipient_email,
            subject=subject,
            text_body=text_body,
            resend_api_key=settings.resend_api_key,
            resend_from_email=settings.resend_from_email,
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


def _send_with_resend(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    resend_api_key: str | None,
    resend_from_email: str | None,
) -> str | None:
    if not resend_api_key or not resend_api_key.strip():
        raise RuntimeError("RESEND_API_KEY is not configured")
    if not resend_from_email or not resend_from_email.strip():
        raise RuntimeError("RESEND_FROM_EMAIL is not configured")

    payload = {
        "from": resend_from_email,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
        "html": _to_html(text_body),
    }
    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "video-digestor/1.0 (+https://local.video-digestor)",
            },
            json=payload,
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        raise RuntimeError(f"Resend request failed: {exc}") from exc
    if response.status_code >= 400:
        raise RuntimeError(f"Resend API returned {response.status_code}: {response.text[:500]}")

    try:
        parsed = response.json()
    except ValueError:
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


def _render_markdown_html(text: str) -> str:
    try:
        import markdown as md  # type: ignore

        return md.markdown(
            text,
            extensions=[
                "extra",
                "fenced_code",
                "tables",
                "sane_lists",
                "nl2br",
            ],
            output_format="html5",
        )
    except Exception:
        lines = [escape(line) for line in text.splitlines()]
        return f"<div>{'<br/>'.join(lines)}</div>"


def _to_html(text: str) -> str:
    body = _render_markdown_html(text)
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<style>"
        "body{margin:0;padding:0;background:#f5f7fb;color:#0f172a;"
        "font-family:'PingFang SC','Microsoft YaHei',-apple-system,BlinkMacSystemFont,sans-serif;}"
        ".container{max-width:860px;margin:0 auto;padding:24px;}"
        ".card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:20px 24px;"
        "box-shadow:0 8px 24px rgba(15,23,42,0.06);line-height:1.65;font-size:15px;}"
        "h1,h2,h3{line-height:1.35;margin:22px 0 12px;color:#0b1324;}h1{font-size:28px;}h2{font-size:22px;}h3{font-size:18px;}"
        "p{margin:10px 0;}ul,ol{margin:8px 0 12px 22px;padding:0;}li{margin:4px 0;}"
        "code{background:#f1f5f9;padding:2px 6px;border-radius:6px;font-size:13px;}"
        "pre{background:#0f172a;color:#e2e8f0;padding:12px;border-radius:8px;overflow:auto;}"
        "pre code{background:transparent;color:inherit;padding:0;}"
        "a{color:#1d4ed8;text-decoration:none;}a:hover{text-decoration:underline;}"
        "blockquote{border-left:4px solid #94a3b8;margin:12px 0;padding:4px 0 4px 12px;color:#475569;}"
        "table{border-collapse:collapse;width:100%;margin:12px 0;}"
        "th,td{border:1px solid #dbe3ee;padding:6px 8px;text-align:left;vertical-align:top;}"
        "img{max-width:100%;height:auto;border-radius:8px;border:1px solid #e2e8f0;}"
        "hr{border:none;border-top:1px solid #e2e8f0;margin:20px 0;}"
        "</style></head><body><div class=\"container\"><article class=\"card\">"
        f"{body}</article></div></body></html>"
    )


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
