from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable


async def retry_failed_deliveries_activity_impl(
    *,
    settings: Any,
    pg_store: Any,
    payload: dict[str, Any] | None,
    coerce_int: Callable[[Any, int], int],
    load_due_failed_deliveries: Callable[..., list[dict[str, Any]]],
    normalize_email: Callable[[Any], str | None],
    build_retry_failure_payload: Callable[..., tuple[str, datetime | None]],
    mark_delivery_state: Callable[..., dict[str, Any]],
    fetch_job_digest_record: Callable[..., dict[str, Any]],
    safe_read_text: Callable[[str | None], str | None],
    build_video_digest_markdown: Callable[[dict[str, Any], str | None], str],
    extract_daily_digest_date: Callable[[Any], Any],
    extract_timezone_name: Callable[[Any], str | None],
    extract_timezone_offset_minutes: Callable[[Any], int],
    resolve_local_digest_date: Callable[..., Any],
    load_daily_digest_jobs: Callable[..., list[dict[str, Any]]],
    build_daily_digest_markdown: Callable[..., str],
    send_with_resend: Callable[..., str],
) -> dict[str, Any]:
    payload = payload or {}
    limit = max(1, coerce_int(payload.get("limit"), fallback=50))

    with pg_store._engine.begin() as conn:  # type: ignore[attr-defined]
        due_deliveries = load_due_failed_deliveries(conn, limit=limit)

    result = {
        "ok": True,
        "checked": len(due_deliveries),
        "retried": 0,
        "sent": 0,
        "failed": 0,
        "retry_scheduled": 0,
        "attempted_delivery_ids": [item["delivery_id"] for item in due_deliveries],
    }

    for item in due_deliveries:
        delivery_id = str(item["delivery_id"])
        kind = str(item.get("kind") or "")
        recipient_email = normalize_email(item.get("recipient_email"))
        subject = str(item.get("subject") or "")
        payload_json = item.get("payload_json") if isinstance(item.get("payload_json"), dict) else {}
        base_attempt_count = int(item.get("attempt_count") or 0)
        next_attempt = base_attempt_count + 1
        result["retried"] += 1

        if recipient_email is None:
            error_message = "notification recipient email is not configured"
            error_kind, next_retry_at = build_retry_failure_payload(
                error_message=error_message,
                attempt_count=next_attempt,
            )
            failed = mark_delivery_state(
                pg_store,
                delivery_id=delivery_id,
                status="failed",
                error_message=error_message,
                sent=False,
                record_attempt=True,
                last_error_kind=error_kind,
                next_retry_at=next_retry_at,
            )
            result["failed"] += 1
            if failed.get("next_retry_at") is not None:
                result["retry_scheduled"] += 1
            continue

        try:
            if kind == "video_digest":
                job_id = str(item.get("job_id") or "").strip()
                if not job_id:
                    raise RuntimeError("missing job_id for video_digest delivery")
                with pg_store._engine.begin() as conn:  # type: ignore[attr-defined]
                    job = fetch_job_digest_record(conn, job_id=job_id)
                digest_markdown = safe_read_text(str(job.get("artifact_digest_md") or ""))
                body_markdown = build_video_digest_markdown(job, digest_markdown)
            elif kind == "daily_digest":
                digest_day = extract_daily_digest_date(payload_json)
                timezone_name = extract_timezone_name(payload_json)
                offset_minutes = extract_timezone_offset_minutes(payload_json)
                if digest_day is None:
                    digest_day = resolve_local_digest_date(
                        digest_date=None,
                        timezone_name=timezone_name,
                        offset_minutes=offset_minutes,
                    )
                with pg_store._engine.begin() as conn:  # type: ignore[attr-defined]
                    jobs = load_daily_digest_jobs(
                        conn,
                        digest_day=digest_day,
                        timezone_name=timezone_name,
                        offset_minutes=offset_minutes,
                    )
                body_markdown = build_daily_digest_markdown(
                    digest_day=digest_day,
                    timezone_name=timezone_name,
                    offset_minutes=offset_minutes,
                    jobs=jobs,
                )
            else:
                raise RuntimeError(f"unsupported retry kind: {kind}")

            provider_message_id = send_with_resend(
                to_email=recipient_email,
                subject=subject,
                text_body=body_markdown,
                resend_api_key=settings.resend_api_key,
                resend_from_email=settings.resend_from_email,
            )
        except Exception as exc:
            error_message = str(exc)
            error_kind, next_retry_at = build_retry_failure_payload(
                error_message=error_message,
                attempt_count=next_attempt,
            )
            failed = mark_delivery_state(
                pg_store,
                delivery_id=delivery_id,
                status="failed",
                error_message=error_message,
                sent=False,
                record_attempt=True,
                last_error_kind=error_kind,
                next_retry_at=next_retry_at,
            )
            result["failed"] += 1
            if failed.get("next_retry_at") is not None:
                result["retry_scheduled"] += 1
            continue

        mark_delivery_state(
            pg_store,
            delivery_id=delivery_id,
            status="sent",
            provider_message_id=provider_message_id,
            error_message=None,
            sent=True,
            record_attempt=True,
            clear_retry_meta=True,
        )
        result["sent"] += 1

    return result
