from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from typing import Any, Self

import pytest
from worker.state.sqlite_store import SQLiteStateStore


def test_sqlite_lock_conflict_then_recovery_after_expiry(tmp_path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteStateStore(str(db_path))

    assert store.acquire_lock("phase2.poll_feeds", "worker-A", 60) is True
    assert store.acquire_lock("phase2.poll_feeds", "worker-B", 60) is False

    expired_at = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE locks SET expires_at = ? WHERE lock_key = ?",
            (expired_at, "phase2.poll_feeds"),
        )

    assert store.acquire_lock("phase2.poll_feeds", "worker-B", 60) is True


def test_sqlite_acquire_lock_allows_only_one_winner_under_real_concurrency(tmp_path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteStateStore(str(db_path))
    lock_key = "phase2.poll_feeds.concurrent"
    started = threading.Barrier(8)
    success_count = 0
    counter_lock = threading.Lock()

    def _attempt(owner: str) -> None:
        nonlocal success_count
        started.wait()
        acquired = store.acquire_lock(lock_key, owner, 60)
        if acquired:
            with counter_lock:
                success_count += 1

    threads = [
        threading.Thread(target=_attempt, args=(f"worker-{index}",), daemon=True)
        for index in range(8)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert success_count == 1


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
        def __enter__(self) -> Self:
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

    def _fake_connect() -> _FakeConn:
        return _FakeConn()

    monkeypatch.setattr(store, "_connect", _fake_connect)
    assert store.acquire_lock("phase2.poll_feeds", "worker-A", 60) is False


def test_sqlite_lock_allows_takeover_when_existing_expiry_is_invalid(tmp_path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteStateStore(str(db_path))

    assert store.acquire_lock("phase2.poll_feeds", "worker-A", 60) is True
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE locks SET expires_at = ? WHERE lock_key = ?",
            ("invalid-timestamp", "phase2.poll_feeds"),
        )

    assert store.acquire_lock("phase2.poll_feeds", "worker-B", 60) is True


def test_sqlite_mark_step_running_and_finished_are_idempotent_with_readback(tmp_path) -> None:
    store = SQLiteStateStore(str(tmp_path / "state.db"))

    store.mark_step_running(job_id="job-1", step_name="collect_comments", attempt=1, cache_key="k1")
    first = store.get_latest_step_run(job_id="job-1", step_name="collect_comments")
    assert first is not None
    assert first["status"] == "running"
    assert first["cache_key"] == "k1"

    store.mark_step_finished(
        job_id="job-1",
        step_name="collect_comments",
        attempt=1,
        status="failed",
        error_payload={"reason": "timeout"},
        error_kind="timeout",
        retry_meta={"retry": 1},
        result_payload={"ok": False},
        cache_key="k1",
    )
    failed = store.get_latest_step_run(
        job_id="job-1",
        step_name="collect_comments",
        status="failed",
        cache_key="k1",
    )
    assert failed is not None
    assert failed["error"] == {"reason": "timeout"}
    assert failed["error_kind"] == "timeout"
    assert failed["retry_meta"] == {"retry": 1}
    assert failed["result"] == {"ok": False}

    store.mark_step_finished(
        job_id="job-1",
        step_name="collect_comments",
        attempt=1,
        status="succeeded",
        result_payload={"ok": True},
        cache_key="k2",
    )
    succeeded = store.get_latest_step_run(job_id="job-1", step_name="collect_comments")
    assert succeeded is not None
    assert succeeded["status"] == "succeeded"
    assert succeeded["error"] is None
    assert succeeded["retry_meta"] is None
    assert succeeded["result"] == {"ok": True}
    assert succeeded["cache_key"] == "k2"


def test_sqlite_checkpoint_update_and_read_are_idempotent(tmp_path) -> None:
    store = SQLiteStateStore(str(tmp_path / "state.db"))

    assert store.get_checkpoint("job-1") is None

    store.update_checkpoint(
        job_id="job-1",
        last_completed_step="download_media",
        payload={"attempt": 1, "status": "running"},
    )
    first = store.get_checkpoint("job-1")
    assert first is not None
    assert first["last_completed_step"] == "download_media"
    assert first["payload"] == {"attempt": 1, "status": "running"}

    store.update_checkpoint(
        job_id="job-1",
        last_completed_step="extract_frames",
        payload={"attempt": 2, "status": "ok"},
    )
    second = store.get_checkpoint("job-1")
    assert second is not None
    assert second["last_completed_step"] == "extract_frames"
    assert second["payload"] == {"attempt": 2, "status": "ok"}


def test_sqlite_get_checkpoint_returns_none_payload_for_invalid_json(tmp_path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteStateStore(str(db_path))
    store.update_checkpoint(job_id="job-1", last_completed_step="done", payload={"k": "v"})

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("UPDATE checkpoints SET payload_json = ? WHERE job_id = ?", ("[]", "job-1"))

    payload = store.get_checkpoint("job-1")
    assert payload is not None
    assert payload["payload"] is None


def test_sqlite_next_attempt_and_invalid_status_branch(tmp_path) -> None:
    store = SQLiteStateStore(str(tmp_path / "state.db"))

    assert store.next_attempt(job_id="job-1") == 1
    store.mark_step_running(job_id="job-1", step_name="s1", attempt=1)
    assert store.next_attempt(job_id="job-1") == 2

    with pytest.raises(ValueError, match="status must be succeeded, failed, or skipped"):
        store.mark_step_finished(
            job_id="job-1",
            step_name="s1",
            attempt=1,
            status="running",
        )
