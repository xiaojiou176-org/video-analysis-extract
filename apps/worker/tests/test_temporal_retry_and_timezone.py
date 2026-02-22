from __future__ import annotations

import asyncio
import sys
import types
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

def _install_temporal_stubs() -> None:
    if "temporalio" in sys.modules:
        return

    temporalio_mod = types.ModuleType("temporalio")
    activity_mod = types.ModuleType("temporalio.activity")
    workflow_mod = types.ModuleType("temporalio.workflow")
    common_mod = types.ModuleType("temporalio.common")

    def _defn(name: str | None = None):
        def _decorator(target):
            return target

        return _decorator

    def _run(fn):
        return fn

    class _Unsafe:
        @staticmethod
        def imports_passed_through():
            return nullcontext()

    class RetryPolicy:
        def __init__(self, maximum_attempts: int = 1):
            self.maximum_attempts = maximum_attempts

    async def _unsupported(*_: Any, **__: Any) -> Any:
        raise RuntimeError("workflow function is not patched")

    activity_mod.defn = _defn  # type: ignore[attr-defined]
    workflow_mod.defn = _defn  # type: ignore[attr-defined]
    workflow_mod.run = _run  # type: ignore[attr-defined]
    workflow_mod.unsafe = _Unsafe()  # type: ignore[attr-defined]
    workflow_mod.execute_activity = _unsupported  # type: ignore[attr-defined]
    workflow_mod.sleep = _unsupported  # type: ignore[attr-defined]
    workflow_mod.now = lambda: datetime.now(timezone.utc)  # type: ignore[attr-defined]
    common_mod.RetryPolicy = RetryPolicy  # type: ignore[attr-defined]

    temporalio_mod.activity = activity_mod  # type: ignore[attr-defined]
    temporalio_mod.workflow = workflow_mod  # type: ignore[attr-defined]
    temporalio_mod.common = common_mod  # type: ignore[attr-defined]

    sys.modules["temporalio"] = temporalio_mod
    sys.modules["temporalio.activity"] = activity_mod
    sys.modules["temporalio.workflow"] = workflow_mod
    sys.modules["temporalio.common"] = common_mod


_install_temporal_stubs()

from worker.temporal import activities, workflows


class _DummyBegin:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyEngine:
    def begin(self):
        return _DummyBegin()


class _DummyPostgresStore:
    def __init__(self, _database_url: str):
        self._engine = _DummyEngine()


def test_retry_failed_deliveries_activity_schedules_retry_for_transient(monkeypatch: Any) -> None:
    captured: list[dict[str, Any]] = []
    now_utc = datetime(2026, 2, 22, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(activities, "PostgresBusinessStore", _DummyPostgresStore)
    monkeypatch.setattr(
        activities.Settings,
        "from_env",
        staticmethod(
            lambda: types.SimpleNamespace(
                database_url="postgresql://example.invalid/db",
                resend_api_key="rk_test",
                resend_from_email="digest@example.com",
            )
        ),
    )
    monkeypatch.setattr(
        activities,
        "_load_due_failed_deliveries",
        lambda _conn, *, limit: [
            {
                "delivery_id": "delivery-1",
                "kind": "video_digest",
                "recipient_email": "notify@example.com",
                "subject": "Digest",
                "payload_json": {},
                "job_id": "00000000-0000-0000-0000-000000000001",
                "attempt_count": 0,
            }
        ],
    )
    monkeypatch.setattr(
        activities,
        "_fetch_job_digest_record",
        lambda _conn, *, job_id: {
            "job_id": job_id,
            "title": "Demo",
            "video_uid": "demo",
            "platform": "youtube",
            "source_url": "https://example.com/video",
            "status": "succeeded",
            "artifact_digest_md": "",
        },
    )
    monkeypatch.setattr(activities, "_safe_read_text", lambda _path: "digest")
    monkeypatch.setattr(
        activities,
        "_send_with_resend",
        lambda **_: (_ for _ in ()).throw(RuntimeError("Resend request failed: timeout")),
    )
    def _fake_mark_delivery_state(
        _pg_store,
        *,
        delivery_id: str,
        status: str,
        error_message: str | None = None,
        provider_message_id: str | None = None,
        sent: bool = False,
        record_attempt: bool = False,
        last_error_kind: str | None = None,
        next_retry_at: datetime | None = None,
        clear_retry_meta: bool = False,
    ) -> dict[str, Any]:
        captured.append(
            {
                "delivery_id": delivery_id,
                "status": status,
                "error_message": error_message,
                "provider_message_id": provider_message_id,
                "record_attempt": record_attempt,
                "last_error_kind": last_error_kind,
                "next_retry_at": next_retry_at or now_utc + timedelta(minutes=2),
                "clear_retry_meta": clear_retry_meta,
            }
        )
        return {
            "delivery_id": delivery_id,
            "status": status,
            "attempt_count": 1,
            "next_retry_at": next_retry_at or now_utc + timedelta(minutes=2),
            "last_error_kind": last_error_kind,
        }

    monkeypatch.setattr(activities, "_mark_delivery_state", _fake_mark_delivery_state)

    payload = asyncio.run(activities.retry_failed_deliveries_activity({"limit": 10}))

    assert payload["checked"] == 1
    assert payload["retried"] == 1
    assert payload["sent"] == 0
    assert payload["failed"] == 1
    assert payload["retry_scheduled"] == 1
    assert captured[0]["status"] == "failed"
    assert captured[0]["last_error_kind"] == "transient"
    assert captured[0]["record_attempt"] is True


def test_retry_backoff_stops_for_config_error() -> None:
    error_kind, next_retry_at = activities._build_retry_failure_payload(
        error_message="RESEND_API_KEY is not configured",
        attempt_count=1,
    )

    assert error_kind == "config_error"
    assert next_retry_at is None


def test_retry_failed_deliveries_activity_marks_sent_on_recovery(monkeypatch: Any) -> None:
    captured: list[dict[str, Any]] = []

    monkeypatch.setattr(activities, "PostgresBusinessStore", _DummyPostgresStore)
    monkeypatch.setattr(
        activities.Settings,
        "from_env",
        staticmethod(
            lambda: types.SimpleNamespace(
                database_url="postgresql://example.invalid/db",
                resend_api_key="rk_test",
                resend_from_email="digest@example.com",
            )
        ),
    )
    monkeypatch.setattr(
        activities,
        "_load_due_failed_deliveries",
        lambda _conn, *, limit: [
            {
                "delivery_id": "delivery-2",
                "kind": "video_digest",
                "recipient_email": "notify@example.com",
                "subject": "Digest",
                "payload_json": {},
                "job_id": "00000000-0000-0000-0000-000000000002",
                "attempt_count": 1,
            }
        ],
    )
    monkeypatch.setattr(
        activities,
        "_fetch_job_digest_record",
        lambda _conn, *, job_id: {
            "job_id": job_id,
            "title": "Demo",
            "video_uid": "demo",
            "platform": "youtube",
            "source_url": "https://example.com/video",
            "status": "succeeded",
            "artifact_digest_md": "",
        },
    )
    monkeypatch.setattr(activities, "_safe_read_text", lambda _path: "digest")
    monkeypatch.setattr(activities, "_send_with_resend", lambda **_: "provider-msg-1")

    def _fake_mark_delivery_state(
        _pg_store,
        *,
        delivery_id: str,
        status: str,
        error_message: str | None = None,
        provider_message_id: str | None = None,
        sent: bool = False,
        record_attempt: bool = False,
        last_error_kind: str | None = None,
        next_retry_at: datetime | None = None,
        clear_retry_meta: bool = False,
    ) -> dict[str, Any]:
        captured.append(
            {
                "delivery_id": delivery_id,
                "status": status,
                "provider_message_id": provider_message_id,
                "clear_retry_meta": clear_retry_meta,
                "record_attempt": record_attempt,
            }
        )
        return {
            "delivery_id": delivery_id,
            "status": status,
            "attempt_count": 2,
            "next_retry_at": None,
            "last_error_kind": None,
        }

    monkeypatch.setattr(activities, "_mark_delivery_state", _fake_mark_delivery_state)

    payload = asyncio.run(activities.retry_failed_deliveries_activity({"limit": 10}))

    assert payload["checked"] == 1
    assert payload["retried"] == 1
    assert payload["sent"] == 1
    assert payload["failed"] == 0
    assert payload["retry_scheduled"] == 0
    assert captured[0]["delivery_id"] == "delivery-2"
    assert captured[0]["status"] == "sent"
    assert captured[0]["record_attempt"] is True
    assert captured[0]["clear_retry_meta"] is True


def test_daily_digest_workflow_uses_timezone_name_across_dst(monkeypatch: Any) -> None:
    sleeps: list[timedelta] = []
    activity_payloads: list[dict[str, Any]] = []

    async def _fake_sleep(duration: timedelta) -> None:
        sleeps.append(duration)
        if len(sleeps) >= 2:
            raise StopAsyncIteration()

    async def _fake_execute_activity(activity_fn: Any, payload: dict[str, Any], **_: Any) -> dict[str, Any]:
        if activity_fn is workflows.resolve_daily_digest_timing_activity:
            return {
                "ok": True,
                "digest_date": "2026-03-07",
                "wait_before_run_seconds": 3600,
                "wait_after_run_seconds": 82800,
                "timezone_name": "America/Los_Angeles",
                "timezone_offset_minutes": -480,
            }
        assert activity_fn is workflows.send_daily_digest_activity
        activity_payloads.append(dict(payload))
        return {"ok": True}

    monkeypatch.setattr(workflows.workflow, "sleep", _fake_sleep)
    monkeypatch.setattr(workflows.workflow, "execute_activity", _fake_execute_activity)

    with pytest.raises(StopAsyncIteration):
        asyncio.run(
            workflows.DailyDigestWorkflow().run(
                {
                    "run_once": False,
                    "local_hour": 9,
                    "timezone_name": "America/Los_Angeles",
                    "timezone_offset_minutes": -480,
                }
            )
        )

    assert activity_payloads[0]["timezone_name"] == "America/Los_Angeles"
    assert activity_payloads[0]["digest_date"] == "2026-03-07"
    assert int(sleeps[0].total_seconds()) == 3600
    # Regression guard: IANA timezone data must keep DST jump (23h instead of 24h).
    assert int(sleeps[1].total_seconds()) == 82800, (
        "Expected 23h across DST boundary; if this is 86400, check tzdata/ZoneInfo availability."
    )
