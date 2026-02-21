from __future__ import annotations

import asyncio
import sys
import types
from contextlib import nullcontext
from pathlib import Path
from typing import Any


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
        raise RuntimeError("workflow activity executor is not patched")

    activity_mod.defn = _defn  # type: ignore[attr-defined]
    workflow_mod.defn = _defn  # type: ignore[attr-defined]
    workflow_mod.run = _run  # type: ignore[attr-defined]
    workflow_mod.unsafe = _Unsafe()  # type: ignore[attr-defined]
    workflow_mod.execute_activity = _unsupported  # type: ignore[attr-defined]
    common_mod.RetryPolicy = RetryPolicy  # type: ignore[attr-defined]

    temporalio_mod.activity = activity_mod  # type: ignore[attr-defined]
    temporalio_mod.workflow = workflow_mod  # type: ignore[attr-defined]
    temporalio_mod.common = common_mod  # type: ignore[attr-defined]

    sys.modules["temporalio"] = temporalio_mod
    sys.modules["temporalio.activity"] = activity_mod
    sys.modules["temporalio.workflow"] = workflow_mod
    sys.modules["temporalio.common"] = common_mod


_install_temporal_stubs()

from worker.config import Settings
from worker.temporal import activities, workflows


def _patch_activity_runtime(
    monkeypatch: Any,
    *,
    tmp_path: Path,
    fallback_mode: str,
    captured: dict[str, Any],
):
    settings = Settings(
        sqlite_path=str((tmp_path / "state.db").resolve()),
        database_url="postgresql+psycopg://postgres:postgres@localhost:5432/video_analysis",
        pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
        pipeline_artifact_root=str((tmp_path / "artifacts").resolve()),
    )
    monkeypatch.setattr(activities.Settings, "from_env", classmethod(lambda cls: settings))

    class _FakeSQLiteStore:
        def __init__(self, _sqlite_path: str):
            self.sqlite_path = _sqlite_path

    class _FakePGStore:
        get_job_calls = 0

        def __init__(self, _database_url: str):
            self.database_url = _database_url

        def get_job_with_video(self, *, job_id: str) -> dict[str, Any]:
            type(self).get_job_calls += 1
            return {
                "job_id": job_id,
                "platform": "youtube",
                "video_uid": "video-uid",
                "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Demo",
                "published_at": None,
                "mode": fallback_mode,
                "overrides_json": {"lang": "zh-CN"},
            }

    async def _fake_run_pipeline(
        _settings: Settings,
        _sqlite_store: Any,
        _pg_store: Any,
        *,
        job_id: str,
        attempt: int,
        mode: str = "full",
    ) -> dict[str, Any]:
        captured["job_id"] = job_id
        captured["attempt"] = attempt
        captured["mode"] = mode
        return {
            "job_id": job_id,
            "attempt": attempt,
            "mode": mode,
            "final_status": "succeeded",
            "steps": {},
            "artifact_dir": str((tmp_path / "artifacts").resolve()),
            "artifacts": {},
        }

    monkeypatch.setattr(activities, "SQLiteStateStore", _FakeSQLiteStore)
    monkeypatch.setattr(activities, "PostgresBusinessStore", _FakePGStore)
    monkeypatch.setattr("worker.pipeline.runner.run_pipeline", _fake_run_pipeline)
    return _FakePGStore


def _patch_workflow_execute_activity(monkeypatch: Any) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []

    async def _execute_activity(activity_fn: Any, payload: Any, **_: Any) -> dict[str, Any]:
        if activity_fn is workflows.mark_running_activity:
            return {"job_id": str(payload), "attempt": 1, "status": "running"}
        if activity_fn is workflows.run_pipeline_activity:
            payloads.append(dict(payload))
            return await activities.run_pipeline_activity(payload)
        if activity_fn is workflows.mark_succeeded_activity:
            return {"status": "succeeded", "db_status": "succeeded"}
        if activity_fn is workflows.mark_failed_activity:
            return {"status": "failed"}
        if activity_fn is workflows.send_video_digest_activity:
            return {"ok": True, "status": "sent"}
        raise AssertionError(f"unexpected activity: {activity_fn}")

    monkeypatch.setattr(workflows.workflow, "execute_activity", _execute_activity)
    return payloads


def test_process_job_workflow_explicit_mode_reaches_runner(monkeypatch: Any, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}
    fake_pg = _patch_activity_runtime(
        monkeypatch,
        tmp_path=tmp_path,
        fallback_mode="full",
        captured=captured,
    )
    payloads = _patch_workflow_execute_activity(monkeypatch)

    result = asyncio.run(
        workflows.ProcessJobWorkflow().run(
            {
                "job_id": "job-explicit-mode",
                "mode": "text_only",
                "overrides": {"lang": "zh-CN"},
            }
        )
    )

    assert payloads[0]["mode"] == "text_only"
    assert payloads[0]["overrides"] == {"lang": "zh-CN"}
    assert captured["mode"] == "text_only"
    assert result["pipeline"]["mode"] == "text_only"
    assert fake_pg.get_job_calls == 0


def test_process_job_workflow_db_mode_reaches_runner_when_mode_missing(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}
    fake_pg = _patch_activity_runtime(
        monkeypatch,
        tmp_path=tmp_path,
        fallback_mode="refresh_llm",
        captured=captured,
    )
    payloads = _patch_workflow_execute_activity(monkeypatch)

    result = asyncio.run(workflows.ProcessJobWorkflow().run("job-db-mode"))

    assert "mode" not in payloads[0]
    assert captured["mode"] == "refresh_llm"
    assert result["pipeline"]["mode"] == "refresh_llm"
    assert fake_pg.get_job_calls == 1
