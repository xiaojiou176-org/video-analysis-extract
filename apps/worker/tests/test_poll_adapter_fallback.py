from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

from worker.temporal import activities_poll
from worker.temporal.activities_poll import _resolve_platform, _resolve_video_uid


def test_resolve_platform_uses_normalized_platform_first() -> None:
    platform = _resolve_platform(
        normalized={"video_platform": "youtube"},
        subscription={"platform": "rss_generic"},
    )
    assert platform == "youtube"


def test_resolve_platform_falls_back_to_subscription_platform() -> None:
    platform = _resolve_platform(
        normalized={"video_platform": None},
        subscription={"platform": "rss_generic"},
    )
    assert platform == "rss_generic"


def test_resolve_video_uid_falls_back_to_entry_hash() -> None:
    uid = _resolve_video_uid(normalized={"video_uid": "", "entry_hash": "abc123"})
    assert uid == "abc123"


def _poll_settings() -> SimpleNamespace:
    return SimpleNamespace(
        sqlite_path="/tmp/worker-state.db",
        database_url="postgresql://example.invalid/video_analysis",
        lock_ttl_seconds=90,
        request_timeout_seconds=10,
        request_retry_attempts=1,
        request_retry_backoff_seconds=0.1,
        rsshub_public_fallback_base_url=None,
        rsshub_fallback_base_urls=[],
    )


def test_run_poll_feeds_once_skips_when_pg_lock_busy(monkeypatch) -> None:
    calls = {"sqlite_acquire": 0}

    class _FakeSQLiteStore:
        def __init__(self, _path: str) -> None:
            pass

        def acquire_lock(self, _lock_key: str, _owner: str, _ttl: int) -> bool:
            calls["sqlite_acquire"] += 1
            return True

        def release_lock(self, _lock_key: str, _owner: str) -> None:
            return None

    class _FakePostgresStore:
        def __init__(self, _database_url: str) -> None:
            pass

        def try_acquire_advisory_lock(self, *, lock_key: str):
            assert lock_key == "phase2.poll_feeds"
            return True, None, None

    monkeypatch.setattr(activities_poll, "SQLiteStateStore", _FakeSQLiteStore)
    monkeypatch.setattr(activities_poll, "PostgresBusinessStore", _FakePostgresStore)

    result = asyncio.run(activities_poll.run_poll_feeds_once(_poll_settings()))

    assert result == {"ok": True, "skipped": True, "reason": "lock_not_acquired"}
    assert calls["sqlite_acquire"] == 0


def test_run_poll_feeds_once_falls_back_to_sqlite_when_pg_lock_unavailable(
    monkeypatch,
    caplog,
) -> None:
    calls = {"sqlite_acquire": 0, "sqlite_release": 0}

    class _FakeSQLiteStore:
        def __init__(self, _path: str) -> None:
            pass

        def acquire_lock(self, _lock_key: str, _owner: str, _ttl: int) -> bool:
            calls["sqlite_acquire"] += 1
            return True

        def release_lock(self, _lock_key: str, _owner: str) -> None:
            calls["sqlite_release"] += 1

    class _FakePostgresStore:
        def __init__(self, _database_url: str) -> None:
            pass

        def try_acquire_advisory_lock(self, *, lock_key: str):
            assert lock_key == "phase2.poll_feeds"
            return False, None, "advisory_unsupported:OperationalError"

        def list_subscriptions(self, *, subscription_id=None, platform=None):
            assert subscription_id is None
            assert platform is None
            return []

    monkeypatch.setattr(activities_poll, "SQLiteStateStore", _FakeSQLiteStore)
    monkeypatch.setattr(activities_poll, "PostgresBusinessStore", _FakePostgresStore)

    caplog.set_level(logging.WARNING)
    result = asyncio.run(activities_poll.run_poll_feeds_once(_poll_settings()))

    assert result["ok"] is True
    assert result["feeds_polled"] == 0
    assert calls["sqlite_acquire"] == 1
    assert calls["sqlite_release"] == 1
    assert "fallback to sqlite lock" in caplog.text


def test_run_poll_feeds_once_releases_pg_lock_when_acquired(monkeypatch) -> None:
    calls = {"pg_release": 0, "sqlite_acquire": 0}
    lease = object()

    class _FakeSQLiteStore:
        def __init__(self, _path: str) -> None:
            pass

        def acquire_lock(self, _lock_key: str, _owner: str, _ttl: int) -> bool:
            calls["sqlite_acquire"] += 1
            return True

        def release_lock(self, _lock_key: str, _owner: str) -> None:
            return None

    class _FakePostgresStore:
        def __init__(self, _database_url: str) -> None:
            pass

        def try_acquire_advisory_lock(self, *, lock_key: str):
            assert lock_key == "phase2.poll_feeds"
            return True, lease, None

        def list_subscriptions(self, *, subscription_id=None, platform=None):
            return []

        def release_advisory_lock(self, value) -> None:
            assert value is lease
            calls["pg_release"] += 1

    monkeypatch.setattr(activities_poll, "SQLiteStateStore", _FakeSQLiteStore)
    monkeypatch.setattr(activities_poll, "PostgresBusinessStore", _FakePostgresStore)

    result = asyncio.run(activities_poll.run_poll_feeds_once(_poll_settings()))

    assert result["ok"] is True
    assert calls["pg_release"] == 1
    assert calls["sqlite_acquire"] == 0
