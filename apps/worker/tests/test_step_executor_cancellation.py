from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from worker.config import Settings
from worker.pipeline import step_executor
from worker.pipeline.types import PipelineContext, StepExecution


class _FakeProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None
        self.killed = False
        self.waited = False
        self.pid = 12345

    async def communicate(self) -> tuple[bytes, bytes]:
        await asyncio.sleep(30)
        self.returncode = 0
        return b"ok", b""

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    async def wait(self) -> int:
        self.waited = True
        return self.returncode or 0


def _build_ctx(tmp_path: Path, *, timeout: int) -> PipelineContext:
    settings = Settings(
        pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
        pipeline_artifact_root=str((tmp_path / "artifact-root").resolve()),
        pipeline_subprocess_timeout_seconds=timeout,
    )
    work_dir = tmp_path / "work"
    cache_dir = work_dir / "cache"
    download_dir = work_dir / "downloads"
    frames_dir = work_dir / "frames"
    artifacts_dir = tmp_path / "artifacts"
    cache_dir.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return PipelineContext(
        settings=settings,
        sqlite_store=None,  # type: ignore[arg-type]
        pg_store=None,  # type: ignore[arg-type]
        job_id="job",
        attempt=1,
        job_record={},
        work_dir=work_dir,
        cache_dir=cache_dir,
        download_dir=download_dir,
        frames_dir=frames_dir,
        artifacts_dir=artifacts_dir,
    )


def test_run_command_kills_subprocess_on_timeout(monkeypatch, tmp_path: Path) -> None:
    fake_process = _FakeProcess()

    async def _fake_create_subprocess_exec(*_args, **_kwargs):
        return fake_process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_create_subprocess_exec)
    ctx = _build_ctx(tmp_path, timeout=1)

    result = asyncio.run(step_executor.run_command(ctx, ["sleep", "30"]))

    assert result.ok is False
    assert result.reason == "timeout"
    assert fake_process.killed is True
    assert fake_process.waited is True


def test_run_command_terminates_process_group_on_timeout(monkeypatch, tmp_path: Path) -> None:
    fake_process = _FakeProcess()
    signals: list[int] = []

    async def _fake_create_subprocess_exec(*_args, **_kwargs):
        return fake_process

    def _fake_killpg(_pid: int, sig: int) -> None:
        signals.append(sig)
        fake_process.returncode = -sig

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_create_subprocess_exec)
    monkeypatch.setattr(step_executor.os, "killpg", _fake_killpg)
    ctx = _build_ctx(tmp_path, timeout=1)

    result = asyncio.run(step_executor.run_command(ctx, ["sleep", "30"]))

    assert result.ok is False
    assert result.reason == "timeout"
    assert signals
    assert fake_process.waited is True


def test_run_command_kills_subprocess_on_cancellation(monkeypatch, tmp_path: Path) -> None:
    fake_process = _FakeProcess()

    async def _fake_create_subprocess_exec(*_args, **_kwargs):
        return fake_process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_create_subprocess_exec)
    ctx = _build_ctx(tmp_path, timeout=60)

    async def _runner() -> None:
        task = asyncio.create_task(step_executor.run_command(ctx, ["sleep", "30"]))
        await asyncio.sleep(0.01)
        task.cancel()
        await task

    try:
        asyncio.run(_runner())
    except asyncio.CancelledError:
        pass
    else:
        raise AssertionError("expected asyncio.CancelledError to propagate")

    assert fake_process.killed is True
    assert fake_process.waited is True


class _FakeSQLiteStore:
    def __init__(self) -> None:
        self.started: list[dict[str, Any]] = []
        self.finished: list[dict[str, Any]] = []

    def mark_step_running(self, **payload: Any) -> None:
        self.started.append(dict(payload))

    def mark_step_finished(self, **payload: Any) -> None:
        self.finished.append(dict(payload))

    def update_checkpoint(self, **_payload: Any) -> None:
        return None

    def get_latest_step_run(self, **_payload: Any) -> dict[str, Any] | None:
        return None


def test_execute_step_marks_failed_when_cancelled(monkeypatch, tmp_path: Path) -> None:
    sqlite_store = _FakeSQLiteStore()
    ctx = _build_ctx(tmp_path, timeout=30)
    ctx = PipelineContext(
        settings=ctx.settings,
        sqlite_store=sqlite_store,  # type: ignore[arg-type]
        pg_store=ctx.pg_store,  # type: ignore[arg-type]
        job_id=ctx.job_id,
        attempt=ctx.attempt,
        job_record=ctx.job_record,
        work_dir=ctx.work_dir,
        cache_dir=ctx.cache_dir,
        download_dir=ctx.download_dir,
        frames_dir=ctx.frames_dir,
        artifacts_dir=ctx.artifacts_dir,
    )
    state: dict[str, Any] = {"degradations": [], "steps": {}}

    async def _cancelled_step(_ctx: PipelineContext, _state: dict[str, Any]) -> StepExecution:
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            step_executor.execute_step(
                ctx,
                state,
                step_name="fetch_metadata",
                step_func=_cancelled_step,
                critical=False,
            )
        )

    assert len(sqlite_store.started) == 1
    assert len(sqlite_store.finished) == 1
    assert sqlite_store.finished[0]["status"] == "failed"
    assert sqlite_store.finished[0]["error_payload"]["reason"] == "cancelled"
