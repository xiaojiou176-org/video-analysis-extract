from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from worker.config import Settings
from worker.pipeline import runner


class _FakeSQLiteStore:
    def get_checkpoint(self, _: str) -> dict[str, Any] | None:
        return None

    def mark_step_running(self, **_: Any) -> None:
        return None

    def mark_step_finished(self, **_: Any) -> None:
        return None

    def update_checkpoint(self, **_: Any) -> None:
        return None

    def get_latest_step_run(self, **_: Any) -> dict[str, Any] | None:
        return None


class _FakePGStore:
    def get_job_with_video(self, *, job_id: str) -> dict[str, Any]:
        return {
            "job_id": job_id,
            "job_status": "running",
            "job_kind": "phase2_ingest_stub",
            "idempotency_key": "idem",
            "video_id": "video-id",
            "platform": "youtube",
            "video_uid": "video-uid",
            "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "title": "Demo",
            "published_at": None,
        }


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
        pipeline_artifact_root=str((tmp_path / "artifact-root").resolve()),
        pipeline_llm_input_mode="auto",
        gemini_api_key=None,
    )


def _build_ctx(tmp_path: Path, *, settings: Settings | None = None) -> runner.PipelineContext:
    current_settings = settings or _make_settings(tmp_path)
    work_dir = tmp_path / "work"
    cache_dir = work_dir / "cache"
    download_dir = work_dir / "downloads"
    frames_dir = work_dir / "frames"
    artifacts_dir = tmp_path / "artifacts"
    cache_dir.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return runner.PipelineContext(
        settings=current_settings,
        sqlite_store=_FakeSQLiteStore(),  # type: ignore[arg-type]
        pg_store=_FakePGStore(),  # type: ignore[arg-type]
        job_id="job",
        attempt=1,
        job_record={},
        work_dir=work_dir,
        cache_dir=cache_dir,
        download_dir=download_dir,
        frames_dir=frames_dir,
        artifacts_dir=artifacts_dir,
    )


def test_step_llm_outline_fails_when_provider_unavailable_by_default(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path)
    state = {
        "metadata": {"title": "Demo"},
        "title": "Demo",
        "transcript": "hello",
        "comments": {"top_comments": []},
        "frames": [],
        "media_path": "",
        "source_url": "https://www.youtube.com/watch?v=demo",
        "llm_input_mode": "text",
        "llm_policy": {},
    }

    execution = asyncio.run(runner._step_llm_outline(ctx, state))

    assert execution.status == "failed"
    assert execution.reason == "gemini_api_key_missing"


def test_step_llm_outline_allows_local_fallback_when_strict_flags_disabled(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PIPELINE_LLM_HARD_REQUIRED", "false")
    monkeypatch.setenv("PIPELINE_LLM_FAIL_ON_PROVIDER_ERROR", "false")

    ctx = _build_ctx(tmp_path)
    state = {
        "metadata": {"title": "Demo"},
        "title": "Demo",
        "transcript": "hello",
        "comments": {"top_comments": []},
        "frames": [],
        "media_path": "",
        "source_url": "https://www.youtube.com/watch?v=demo",
        "llm_input_mode": "text",
        "llm_policy": {},
    }

    execution = asyncio.run(runner._step_llm_outline(ctx, state))

    assert execution.status == "succeeded"
    assert execution.degraded is True
    assert execution.output["provider"] == "local_rule"


def test_run_pipeline_marks_degraded_when_non_llm_step_degraded(monkeypatch: Any, tmp_path: Path) -> None:
    async def _ok(_: runner.PipelineContext, __: dict[str, Any]) -> runner.StepExecution:
        return runner.StepExecution(status="succeeded")

    async def _degraded(_: runner.PipelineContext, __: dict[str, Any]) -> runner.StepExecution:
        return runner.StepExecution(
            status="succeeded",
            reason="subtitle_unavailable",
            degraded=True,
            state_updates={"transcript": ""},
        )

    async def _write(_: runner.PipelineContext, __: dict[str, Any]) -> runner.StepExecution:
        return runner.StepExecution(
            status="succeeded",
            state_updates={"artifact_dir": str((tmp_path / "artifacts").resolve())},
        )

    monkeypatch.setattr(runner, "_step_fetch_metadata", _ok)
    monkeypatch.setattr(runner, "_step_download_media", _ok)
    monkeypatch.setattr(runner, "_step_collect_subtitles", _degraded)
    monkeypatch.setattr(runner, "_step_collect_comments", _ok)
    monkeypatch.setattr(runner, "_step_extract_frames", _ok)
    monkeypatch.setattr(runner, "_step_llm_outline", _ok)
    monkeypatch.setattr(runner, "_step_llm_digest", _ok)
    monkeypatch.setattr(runner, "_step_write_artifacts", _write)

    result = asyncio.run(
        runner.run_pipeline(
            _make_settings(tmp_path),
            _FakeSQLiteStore(),  # type: ignore[arg-type]
            _FakePGStore(),  # type: ignore[arg-type]
            job_id="job-degraded",
            attempt=1,
            mode="full",
        )
    )

    assert result["final_status"] == "degraded"


def test_run_pipeline_marks_failed_when_llm_step_failed(monkeypatch: Any, tmp_path: Path) -> None:
    async def _ok(_: runner.PipelineContext, __: dict[str, Any]) -> runner.StepExecution:
        return runner.StepExecution(status="succeeded")

    async def _llm_failed(_: runner.PipelineContext, __: dict[str, Any]) -> runner.StepExecution:
        return runner.StepExecution(
            status="failed",
            reason="llm_provider_unavailable",
            error="llm_provider_unavailable",
            degraded=True,
        )

    async def _write(_: runner.PipelineContext, __: dict[str, Any]) -> runner.StepExecution:
        return runner.StepExecution(
            status="succeeded",
            state_updates={"artifact_dir": str((tmp_path / "artifacts").resolve())},
        )

    monkeypatch.setattr(runner, "_step_fetch_metadata", _ok)
    monkeypatch.setattr(runner, "_step_download_media", _ok)
    monkeypatch.setattr(runner, "_step_collect_subtitles", _ok)
    monkeypatch.setattr(runner, "_step_collect_comments", _ok)
    monkeypatch.setattr(runner, "_step_extract_frames", _ok)
    monkeypatch.setattr(runner, "_step_llm_outline", _llm_failed)
    monkeypatch.setattr(runner, "_step_llm_digest", _ok)
    monkeypatch.setattr(runner, "_step_write_artifacts", _write)

    result = asyncio.run(
        runner.run_pipeline(
            _make_settings(tmp_path),
            _FakeSQLiteStore(),  # type: ignore[arg-type]
            _FakePGStore(),  # type: ignore[arg-type]
            job_id="job-llm-failed",
            attempt=1,
            mode="refresh_llm",
        )
    )

    assert result["final_status"] == "failed"
    assert result["steps"]["llm_outline"]["status"] == "failed"


def test_execute_step_uses_pipeline_llm_max_retries(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setenv("PIPELINE_LLM_MAX_RETRIES", "1")
    ctx = _build_ctx(tmp_path, settings=Settings(pipeline_retry_attempts=5))

    calls = {"count": 0}

    async def _flaky(_: runner.PipelineContext, __: dict[str, Any]) -> runner.StepExecution:
        calls["count"] += 1
        if calls["count"] == 1:
            return runner.StepExecution(
                status="failed",
                reason="timeout",
                error="timeout",
                degraded=True,
            )
        return runner.StepExecution(status="succeeded")

    state: dict[str, Any] = {
        "llm_policy": {},
        "steps": {},
        "degradations": [],
        "llm_media_input": {"video_available": False, "frame_count": 0},
    }

    step_record = asyncio.run(
        runner._execute_step(
            ctx,
            state,
            step_name="llm_outline",
            step_func=_flaky,
            critical=False,
            resume_hint=False,
            force_run=True,
        )
    )

    assert calls["count"] == 2
    assert step_record["status"] == "succeeded"
    assert step_record["retry_meta"]["attempts"] == 2
    assert step_record["retry_meta"]["retries_configured"] == 1
