from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from worker.config import Settings
from worker.pipeline import step_executor
from worker.pipeline.types import PipelineContext, StepExecution


class _FakeSQLiteStore:
    def __init__(self) -> None:
        self.started: list[dict[str, Any]] = []
        self.finished: list[dict[str, Any]] = []
        self.checkpoints: list[dict[str, Any]] = []
        self.latest_step_run: dict[str, Any] | None = None

    def mark_step_running(self, **payload: Any) -> None:
        self.started.append(dict(payload))

    def mark_step_finished(self, **payload: Any) -> None:
        self.finished.append(dict(payload))

    def update_checkpoint(self, **payload: Any) -> None:
        self.checkpoints.append(dict(payload))

    def get_latest_step_run(self, **_: Any) -> dict[str, Any] | None:
        return self.latest_step_run


class _FakePGStore:
    def upsert_video_embeddings(self, **_: Any) -> int:
        return 0


def _make_ctx(tmp_path: Path, *, sqlite_store: _FakeSQLiteStore | None = None) -> PipelineContext:
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
        settings=Settings(
            pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
            pipeline_artifact_root=str((tmp_path / "artifact-root").resolve()),
            pipeline_subprocess_timeout_seconds=1,
        ),
        sqlite_store=(sqlite_store or _FakeSQLiteStore()),  # type: ignore[arg-type]
        pg_store=_FakePGStore(),  # type: ignore[arg-type]
        job_id="job-step-executor-extra",
        attempt=1,
        job_record={"video_id": "vid-1"},
        work_dir=work_dir,
        cache_dir=cache_dir,
        download_dir=download_dir,
        frames_dir=frames_dir,
        artifacts_dir=artifacts_dir,
    )


@dataclass
class _ModelDumpObj:
    payload: dict[str, Any]

    def model_dump(self) -> dict[str, Any]:
        return self.payload


@dataclass
class _DictObj:
    payload: dict[str, Any]

    def dict(self) -> dict[str, Any]:
        return self.payload


class _BrokenIsoObj:
    def isoformat(self) -> str:
        raise RuntimeError("broken")

    def __str__(self) -> str:
        return "broken-iso"


def test_jsonable_and_write_json_helpers(tmp_path: Path) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    payload = {
        "tuple": (1, 2),
        "set": {3, 4},
        "path": tmp_path / "demo.txt",
        "dt": now,
        "model": _ModelDumpObj(payload={"a": 1}),
        "dict_obj": _DictObj(payload={"b": 2}),
        "iso_broken": _BrokenIsoObj(),
    }
    json_ready = step_executor.jsonable(payload)
    assert json_ready["tuple"] == [1, 2]
    assert sorted(json_ready["set"]) == [3, 4]
    assert json_ready["dt"] == now.isoformat()
    assert json_ready["model"] == {"a": 1}
    assert json_ready["dict_obj"] == {"b": 2}
    assert json_ready["iso_broken"] == "broken-iso"

    output_path = tmp_path / "payload.json"
    step_executor.write_json(output_path, payload)
    loaded = json.loads(step_executor.read_text_file(output_path))
    assert loaded["model"] == {"a": 1}


def test_cache_helpers_and_skip_builder(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path)
    state = {"source_url": "https://www.youtube.com/watch?v=demo"}
    cache_info = step_executor.build_step_cache_info(ctx, state, "fetch_metadata")
    execution = StepExecution(status="succeeded", output={"ok": True}, state_updates={"x": 1})
    step_executor._write_step_cache(cache_info, execution)

    loaded, reason = step_executor._load_step_execution_from_cache(cache_info)
    assert loaded is not None
    assert reason == "cache_hit"

    cache_info["cache_path"].unlink()
    loaded_legacy, legacy_reason = step_executor._load_step_execution_from_cache(cache_info)
    assert loaded_legacy is not None
    assert legacy_reason == "legacy_cache_hit"

    cache_info_v2 = dict(cache_info)
    cache_info_v2["version"] = "v2"
    none_loaded, none_reason = step_executor._load_step_execution_from_cache(cache_info_v2)
    assert none_loaded is None
    assert none_reason is None

    skip_fn = step_executor.build_mode_skip_step("collect_subtitles", "text_only")
    skip_execution = asyncio.run(skip_fn(ctx, state))
    assert skip_execution.status == "skipped"
    assert skip_execution.reason == "mode_matrix_skip"

    failed_payload = step_executor._build_error_payload(
        StepExecution(status="failed", reason="boom", error="err")
    )
    skipped_payload = step_executor._build_error_payload(
        StepExecution(status="skipped", reason="manual_skip")
    )
    assert failed_payload == {"reason": "boom", "error": "err", "error_kind": None, "retry_meta": {}}
    assert skipped_payload == {"reason": "manual_skip", "error_kind": None, "retry_meta": {}}
    assert step_executor._build_error_payload(StepExecution(status="succeeded")) is None


def test_execute_step_uses_cache_hit_without_calling_step_func(tmp_path: Path) -> None:
    sqlite_store = _FakeSQLiteStore()
    ctx = _make_ctx(tmp_path, sqlite_store=sqlite_store)
    state: dict[str, Any] = {"steps": {}, "degradations": []}
    cache_info = step_executor.build_step_cache_info(ctx, state, "fetch_metadata")
    step_executor._write_step_cache(
        cache_info,
        StepExecution(status="succeeded", output={"cached": True}, state_updates={"from_cache": 1}),
    )
    called = {"count": 0}

    async def _should_not_run(_: PipelineContext, __: dict[str, Any]) -> StepExecution:
        called["count"] += 1
        return StepExecution(status="succeeded")

    result = asyncio.run(
        step_executor.execute_step(
            ctx,
            state,
            step_name="fetch_metadata",
            step_func=_should_not_run,
        )
    )

    assert called["count"] == 0
    assert result["status"] == "skipped"
    assert result["reason"] == "cache_hit"
    assert result["retry_meta"]["strategy"] == "cache"
    assert len(sqlite_store.checkpoints) == 1


def test_execute_step_resume_hint_recovers_checkpoint_payload(tmp_path: Path) -> None:
    sqlite_store = _FakeSQLiteStore()
    sqlite_store.latest_step_run = {
        "result_json": json.dumps(
            StepExecution(status="succeeded", output={"checkpoint": True}, state_updates={"k": "v"}).to_record()
        )
    }
    ctx = _make_ctx(tmp_path, sqlite_store=sqlite_store)
    state: dict[str, Any] = {"steps": {}, "degradations": []}

    async def _not_expected(_: PipelineContext, __: dict[str, Any]) -> StepExecution:
        raise AssertionError("step_func should not run when checkpoint can be recovered")

    result = asyncio.run(
        step_executor.execute_step(
            ctx,
            state,
            step_name="fetch_metadata",
            step_func=_not_expected,
            resume_hint=True,
        )
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "checkpoint_recovered"
    assert result["retry_meta"]["strategy"] == "checkpoint"
    assert state["k"] == "v"


def test_execute_step_retries_then_succeeds_and_writes_cache(monkeypatch: Any, tmp_path: Path) -> None:
    sqlite_store = _FakeSQLiteStore()
    ctx = _make_ctx(tmp_path, sqlite_store=sqlite_store)
    state: dict[str, Any] = {"steps": {}, "degradations": []}
    attempts = {"count": 0}
    sleep_calls: list[float] = []

    async def _fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr(step_executor.asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(step_executor, "retry_delay_seconds", lambda _policy, _retries: 0.2)

    async def _flaky_step(_: PipelineContext, __: dict[str, Any]) -> StepExecution:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return StepExecution(status="failed", reason="timeout", error="timeout")
        return StepExecution(status="succeeded", state_updates={"done": True})

    result = asyncio.run(
        step_executor.execute_step(
            ctx,
            state,
            step_name="fetch_metadata",
            step_func=_flaky_step,
            force_run=True,
        )
    )

    assert result["status"] == "succeeded"
    assert result["retry_meta"]["attempts"] == 2
    assert sleep_calls == [0.2]
    assert state["done"] is True
    cache_info = step_executor.build_step_cache_info(ctx, state, "fetch_metadata")
    assert cache_info["cache_path"].exists()
    assert cache_info["legacy_path"].exists()


def test_execute_step_sets_fatal_error_and_degradation_for_failed_critical(tmp_path: Path) -> None:
    sqlite_store = _FakeSQLiteStore()
    ctx = _make_ctx(tmp_path, sqlite_store=sqlite_store)
    state: dict[str, Any] = {"steps": {}, "degradations": []}

    def _invalid_result(_: PipelineContext, __: dict[str, Any]) -> dict[str, str]:
        return {"bad": "payload"}

    result = asyncio.run(
        step_executor.execute_step(
            ctx,
            state,
            step_name="fetch_metadata",
            step_func=_invalid_result,
            critical=True,
            force_run=True,
        )
    )

    assert result["status"] == "failed"
    assert "fatal_error" in state
    assert len(state["degradations"]) == 1


def test_execute_step_llm_hard_failure_does_not_append_degradation(tmp_path: Path) -> None:
    sqlite_store = _FakeSQLiteStore()
    ctx = _make_ctx(tmp_path, sqlite_store=sqlite_store)
    state: dict[str, Any] = {"steps": {}, "degradations": [], "llm_policy": {"hard_required": True}}

    async def _llm_fail(_: PipelineContext, __: dict[str, Any]) -> StepExecution:
        return StepExecution(status="failed", reason="llm_failed", error="provider_error")

    result = asyncio.run(
        step_executor.execute_step(
            ctx,
            state,
            step_name="llm_outline",
            step_func=_llm_fail,
            force_run=True,
        )
    )

    assert result["status"] == "failed"
    assert state["degradations"] == []


def test_execute_step_marks_custom_skips_as_degradation(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path)
    state: dict[str, Any] = {"steps": {}, "degradations": []}

    async def _skip_step(_: PipelineContext, __: dict[str, Any]) -> StepExecution:
        return StepExecution(status="skipped", reason="custom_skip_reason")

    result = asyncio.run(
        step_executor.execute_step(
            ctx,
            state,
            step_name="fetch_metadata",
            step_func=_skip_step,
            force_run=True,
        )
    )

    assert result["status"] == "skipped"
    assert len(state["degradations"]) == 1
    assert state["degradations"][0]["reason"] == "custom_skip_reason"


def test_run_command_once_handles_error_modes(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        step_executor.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )
    missing = step_executor.run_command_once(["missing-binary"], timeout_seconds=1)
    assert missing.reason == "binary_not_found"

    def _raise_timeout(*_args: Any, **_kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd=["sleep", "1"], timeout=1)

    monkeypatch.setattr(step_executor.subprocess, "run", _raise_timeout)
    timeout = step_executor.run_command_once(["sleep", "1"], timeout_seconds=1)
    assert timeout.reason == "timeout"

    monkeypatch.setattr(
        step_executor.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["cmd"],
            returncode=2,
            stdout="",
            stderr="boom",
        ),
    )
    failed = step_executor.run_command_once(["cmd"], timeout_seconds=1)
    assert failed.ok is False
    assert failed.reason == "non_zero_exit"


def test_run_command_binary_missing_and_terminate_variants(monkeypatch: Any, tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path)

    async def _raise_missing(*_args: Any, **_kwargs: Any) -> Any:
        raise FileNotFoundError

    monkeypatch.setattr(step_executor.asyncio, "create_subprocess_exec", _raise_missing)
    result = asyncio.run(step_executor.run_command(ctx, ["missing-binary"]))
    assert result.reason == "binary_not_found"

    class _Process:
        def __init__(self, *, pid: int | None = 123) -> None:
            self.returncode: int | None = None
            self.pid = pid
            self.kill_called = False
            self.wait_calls = 0

        async def wait(self) -> int:
            self.wait_calls += 1
            self.returncode = 0
            return 0

        def kill(self) -> None:
            self.kill_called = True
            self.returncode = -9

    proc_done = _Process()
    proc_done.returncode = 0
    asyncio.run(step_executor._terminate_subprocess(proc_done))
    assert proc_done.wait_calls == 0

    proc_killpg = _Process(pid=999)
    sent_signals: list[int] = []

    def _fake_killpg(_pid: int, sig: int) -> None:
        sent_signals.append(sig)

    async def _raise_wait_for(_awaitable: Any, timeout: float) -> Any:
        close_fn = getattr(_awaitable, "close", None)
        if callable(close_fn):
            close_fn()
        raise TimeoutError

    monkeypatch.setattr(step_executor.os, "killpg", _fake_killpg)
    monkeypatch.setattr(step_executor.asyncio, "wait_for", _raise_wait_for)
    asyncio.run(step_executor._terminate_subprocess(proc_killpg))
    assert sent_signals == [step_executor.signal.SIGTERM, step_executor.signal.SIGKILL]
    assert proc_killpg.wait_calls == 1

    proc_fallback = _Process(pid=None)
    asyncio.run(step_executor._terminate_subprocess(proc_fallback))
    assert proc_fallback.kill_called is True
