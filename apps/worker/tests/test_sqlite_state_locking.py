from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from worker.state.sqlite_store import SQLiteStateStore


def test_sqlite_lock_conflict_then_recovery_after_expiry(tmp_path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteStateStore(str(db_path))

    assert store.acquire_lock("phase2.poll_feeds", "worker-A", 60) is True
    assert store.acquire_lock("phase2.poll_feeds", "worker-B", 60) is False

    expired_at = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE locks SET expires_at = ? WHERE lock_key = ?",
            (expired_at, "phase2.poll_feeds"),
        )

    assert store.acquire_lock("phase2.poll_feeds", "worker-B", 60) is True


def test_sqlite_release_lock_enforces_owner_match(tmp_path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteStateStore(str(db_path))

    assert store.acquire_lock("phase2.poll_feeds", "worker-A", 60) is True
    store.release_lock("phase2.poll_feeds", "worker-B")
    assert store.acquire_lock("phase2.poll_feeds", "worker-C", 60) is False

    store.release_lock("phase2.poll_feeds", "worker-A")
    assert store.acquire_lock("phase2.poll_feeds", "worker-C", 60) is True


def test_sqlite_acquire_lock_handles_insert_race(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteStateStore(str(db_path))

    class _FakeConn:
        def __enter__(self) -> "_FakeConn":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def execute(self, sql: str, params: tuple[Any, ...]):
            if sql.startswith("SELECT owner, expires_at"):
                return self
            if sql.startswith("INSERT INTO locks"):
                raise sqlite3.IntegrityError("UNIQUE constraint failed: locks.lock_key")
            raise AssertionError(f"unexpected SQL: {sql}")

        def fetchone(self):
            return {"owner": "worker-other", "expires_at": "2999-01-01T00:00:00+00:00"}

    monkeypatch.setattr(store, "_connect", lambda: _FakeConn())
    assert store.acquire_lock("phase2.poll_feeds", "worker-A", 60) is False
