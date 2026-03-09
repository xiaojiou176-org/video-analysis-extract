from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Self

from worker.state import sqlite_store
from worker.state.sqlite_store import SQLiteStateStore


class _ModelV2:
    def model_dump(self) -> dict[str, Any]:
        return {"v2": True}


class _ModelV1:
    def dict(self) -> dict[str, Any]:
        return {"v1": True}


class _IsoValue:
    def isoformat(self) -> str:
        return "custom-iso"


class _IsoRaises:
    def isoformat(self) -> str:
        raise RuntimeError("boom")

    def __str__(self) -> str:
        return "iso-fallback"


def test_json_helpers_cover_serialization_edge_branches(tmp_path: Path) -> None:
    now = datetime(2026, 3, 1, 12, 30, tzinfo=UTC)
    payload = {
        "list": [1, 2],
        "tuple": ("a", "b"),
        "set": {"x", "y"},
        "date": date(2026, 3, 1),
        "datetime": now,
        "path": tmp_path / "artifact.txt",
        "model_v2": _ModelV2(),
        "model_v1": _ModelV1(),
        "iso": _IsoValue(),
        "fallback": object(),
    }

    dumped = sqlite_store._json_dumps(payload)
    assert dumped is not None
    loaded = sqlite_store._json_loads(dumped)
    assert loaded is not None
    assert loaded["tuple"] == ["a", "b"]
    assert sorted(loaded["set"]) == ["x", "y"]
    assert loaded["model_v2"] == {"v2": True}
    assert loaded["model_v1"] == {"v1": True}
    assert loaded["iso"] == "custom-iso"
    assert loaded["fallback"].startswith("<object object")

    assert sqlite_store._json_dumps(None) is None
    assert sqlite_store._json_loads("{broken-json") is None
    assert sqlite_store._json_fallback(now) == now.isoformat()
    assert sqlite_store._json_fallback(tmp_path / "x.txt").endswith("x.txt")
    assert sqlite_store._json_fallback(("a", "b")) == ["a", "b"]
    assert sqlite_store._json_fallback(_ModelV2()) == {"v2": True}
    assert sqlite_store._json_fallback(_ModelV1()) == {"v1": True}
    assert sqlite_store._json_fallback(_IsoValue()) == "custom-iso"
    assert sqlite_store._json_fallback(_IsoRaises()) == "iso-fallback"
    assert sqlite_store._is_expired(None) is True


class _EnsureColumnConn:
    def __init__(self) -> None:
        self.alter_sql: list[str] = []

    def execute(self, sql: str):
        if sql.startswith("PRAGMA table_info"):
            return self
        if sql.startswith("ALTER TABLE"):
            self.alter_sql.append(sql)
            return self
        raise AssertionError(f"unexpected SQL: {sql}")

    def fetchall(self) -> list[dict[str, Any]]:
        return [{"name": "existing_col"}]


def test_ensure_column_adds_missing_column() -> None:
    store = SQLiteStateStore.__new__(SQLiteStateStore)
    conn = _EnsureColumnConn()
    store._ensure_column(conn, "step_runs", "new_col", "TEXT")
    assert conn.alter_sql == ["ALTER TABLE step_runs ADD COLUMN new_col TEXT"]


def test_acquire_lock_returns_false_when_insert_race_row_disappears(monkeypatch) -> None:
    store = SQLiteStateStore.__new__(SQLiteStateStore)

    class _RaceConn:
        def __init__(self) -> None:
            self.select_count = 0

        def __enter__(self) -> Self:
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def execute(self, sql: str, params: tuple[Any, ...]):
            if sql.startswith("SELECT owner, expires_at"):
                self.select_count += 1
                return self
            if sql.startswith("INSERT INTO locks"):
                raise sqlite3.IntegrityError("race won by another worker")
            raise AssertionError(f"unexpected SQL: {sql}")

        def fetchone(self):
            return None

    race_conn = _RaceConn()
    monkeypatch.setattr(store, "_connect", lambda: race_conn)
    assert store.acquire_lock("phase2.poll_feeds", "worker-A", 60) is False


def test_get_latest_step_run_returns_none_for_missing_record(tmp_path: Path) -> None:
    store = SQLiteStateStore(str(tmp_path / "state.db"))
    assert store.get_latest_step_run(job_id="job-missing", step_name="step-x") is None

