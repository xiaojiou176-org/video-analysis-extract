from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from worker.config import Settings
from worker.pipeline import runner


def _build_ctx(tmp_path: Path, *, settings: Settings) -> runner.PipelineContext:
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


def test_step_download_media_bilibili_auto_falls_back_to_bbdown(
    monkeypatch: Any, tmp_path: Path
) -> None:
    settings = Settings(
        pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
        pipeline_artifact_root=str((tmp_path / "artifact-root").resolve()),
        bilibili_downloader="auto",
    )
    ctx = _build_ctx(tmp_path, settings=settings)

    async def _fake_run_command(current_ctx: runner.PipelineContext, cmd: list[str]) -> runner.CommandResult:
        if cmd and cmd[0] == "yt-dlp":
            return runner.CommandResult(ok=False, returncode=1, stderr="yt failed", reason="non_zero_exit")
        media_path = current_ctx.download_dir / "bili_video.mp4"
        media_path.write_bytes(b"fake-video")
        return runner.CommandResult(ok=True, returncode=0, stdout=str(media_path.resolve()), stderr="")

    monkeypatch.setattr(runner, "_run_command", _fake_run_command)

    execution = asyncio.run(
        runner._step_download_media(
            ctx,
            {
                "platform": "bilibili",
                "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
            },
        )
    )

    assert execution.status == "succeeded"
    assert execution.output["provider"] == "bbdown"
    assert execution.state_updates["download_mode"] == "media"
    assert str(execution.state_updates["media_path"]).endswith(".mp4")


def test_step_download_media_bilibili_force_ytdlp_no_fallback(monkeypatch: Any, tmp_path: Path) -> None:
    settings = Settings(
        pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
        pipeline_artifact_root=str((tmp_path / "artifact-root").resolve()),
        bilibili_downloader="yt-dlp",
    )
    ctx = _build_ctx(tmp_path, settings=settings)

    async def _fake_run_command(_: runner.PipelineContext, __: list[str]) -> runner.CommandResult:
        return runner.CommandResult(ok=False, returncode=1, stderr="yt failed", reason="non_zero_exit")

    monkeypatch.setattr(runner, "_run_command", _fake_run_command)

    execution = asyncio.run(
        runner._step_download_media(
            ctx,
            {
                "platform": "bilibili",
                "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
            },
        )
    )

    assert execution.status == "failed"
    assert execution.output["providers_tried"] == ["yt-dlp"]
    assert execution.state_updates["download_mode"] == "text_only"


def test_step_collect_subtitles_uses_youtube_transcript_fallback(
    monkeypatch: Any, tmp_path: Path
) -> None:
    settings = Settings(
        pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
        pipeline_artifact_root=str((tmp_path / "artifact-root").resolve()),
        youtube_transcript_fallback_enabled=True,
        asr_fallback_enabled=False,
    )
    ctx = _build_ctx(tmp_path, settings=settings)

    monkeypatch.setattr(runner, "_fetch_youtube_transcript_text", lambda _: "line1\nline2")

    execution = asyncio.run(
        runner._step_collect_subtitles(
            ctx,
            {
                "platform": "youtube",
                "source_url": "https://www.youtube.com/watch?v=abc123xyz09",
                "video_uid": "",
                "media_path": "",
            },
        )
    )

    assert execution.status == "succeeded"
    assert execution.output["transcript_provider"] == "youtube_transcript_fallback"
    assert execution.state_updates["transcript"] == "line1\nline2"
    assert execution.state_updates["subtitle_files"] == []


def test_step_collect_subtitles_asr_missing_binary_degrades(monkeypatch: Any, tmp_path: Path) -> None:
    settings = Settings(
        pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
        pipeline_artifact_root=str((tmp_path / "artifact-root").resolve()),
        youtube_transcript_fallback_enabled=False,
        asr_fallback_enabled=True,
        asr_model_size="small",
    )
    ctx = _build_ctx(tmp_path, settings=settings)
    media_path = ctx.download_dir / "demo.mp4"
    media_path.write_bytes(b"fake-media")

    async def _fake_run_command(_: runner.PipelineContext, __: list[str]) -> runner.CommandResult:
        return runner.CommandResult(ok=False, reason="binary_not_found")

    monkeypatch.setattr(runner, "_run_command", _fake_run_command)

    execution = asyncio.run(
        runner._step_collect_subtitles(
            ctx,
            {
                "platform": "bilibili",
                "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
                "video_uid": "BV1xx411c7mD",
                "media_path": str(media_path.resolve()),
            },
        )
    )

    assert execution.status == "succeeded"
    assert execution.degraded is True
    assert execution.state_updates["transcript"] == ""
    assert "asr_failed:binary_not_found" in (execution.reason or "")


def test_settings_from_env_reads_new_fallback_flags(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setenv("PIPELINE_WORKSPACE_DIR", str((tmp_path / "workspace").resolve()))
    monkeypatch.setenv("PIPELINE_ARTIFACT_ROOT", str((tmp_path / "artifact-root").resolve()))
    monkeypatch.setenv("BILIBILI_DOWNLOADER", "bbdown")
    monkeypatch.setenv("YOUTUBE_TRANSCRIPT_FALLBACK_ENABLED", "false")
    monkeypatch.setenv("ASR_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("ASR_MODEL_SIZE", "base")

    settings = Settings.from_env()

    assert settings.bilibili_downloader == "bbdown"
    assert settings.youtube_transcript_fallback_enabled is False
    assert settings.asr_fallback_enabled is True
    assert settings.asr_model_size == "base"


def test_step_write_artifacts_renders_embedded_screenshots(tmp_path: Path) -> None:
    settings = Settings(
        pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
        pipeline_artifact_root=str((tmp_path / "artifact-root").resolve()),
    )
    ctx = _build_ctx(tmp_path, settings=settings)
    source_frame = ctx.frames_dir / "source_frame.jpg"
    source_frame.write_bytes(b"frame")

    execution = asyncio.run(
        runner._step_write_artifacts(
            ctx,
            {
                "title": "Demo",
                "source_url": "https://www.youtube.com/watch?v=abc123xyz09",
                "platform": "youtube",
                "video_uid": "abc123xyz09",
                "metadata": {"title": "Demo"},
                "outline": {},
                "digest": {"summary": "summary"},
                "comments": {},
                "transcript": "hello",
                "degradations": [],
                "frames": [{"path": str(source_frame.resolve()), "timestamp_s": 10}],
            },
        )
    )

    assert execution.status == "succeeded"
    digest_content = (ctx.artifacts_dir / "digest.md").read_text(encoding="utf-8")
    assert "## 关键截图" in digest_content
    assert "## 说明（降级/缺失）" in digest_content
    assert (
        "![frame-1](/api/v1/artifacts/assets?job_id=job&path=frames/frame_001.jpg)"
        in digest_content
    )

    meta_payload = json.loads((ctx.artifacts_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta_payload["frame_files"] == ["frames/frame_001.jpg"]
