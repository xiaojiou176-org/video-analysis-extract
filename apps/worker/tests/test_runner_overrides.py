from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from worker.config import Settings
from worker.pipeline import runner


def _build_ctx(tmp_path: Path, *, settings: Settings | None = None) -> runner.PipelineContext:
    current_settings = settings or Settings(
        pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
        pipeline_artifact_root=str((tmp_path / "artifacts").resolve()),
    )
    return runner.PipelineContext(
        settings=current_settings,
        sqlite_store=None,  # type: ignore[arg-type]
        pg_store=None,  # type: ignore[arg-type]
        job_id="job",
        attempt=1,
        job_record={},
        work_dir=tmp_path,
        cache_dir=tmp_path / "cache",
        download_dir=tmp_path / "download",
        frames_dir=tmp_path / "frames",
        artifacts_dir=tmp_path / "artifacts",
    )


def test_step_collect_comments_applies_overrides(monkeypatch: Any, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    class _FakeYouTubeCollector:
        def __init__(self, **kwargs: Any) -> None:
            captured["collector_kwargs"] = dict(kwargs)

        async def collect(self, *, source_url: str | None, video_uid: str | None) -> dict[str, Any]:
            captured["source_url"] = source_url
            captured["video_uid"] = video_uid
            return {
                "sort": "hot",
                "top_comments": [
                    {
                        "comment_id": "older",
                        "author": "old",
                        "content": "old",
                        "like_count": 99,
                        "published_at": "2024-01-01T00:00:00+00:00",
                        "replies": [
                            {"reply_id": "r1", "content": "1"},
                            {"reply_id": "r2", "content": "2"},
                        ],
                    },
                    {
                        "comment_id": "newer",
                        "author": "new",
                        "content": "new",
                        "like_count": 1,
                        "published_at": "2024-01-02T00:00:00+00:00",
                        "replies": [
                            {"reply_id": "r3", "content": "3"},
                            {"reply_id": "r4", "content": "4"},
                        ],
                    },
                ],
            }

    monkeypatch.setattr(runner, "YouTubeCommentCollector", _FakeYouTubeCollector)
    settings = Settings(
        youtube_api_key="test-key",
        pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
        pipeline_artifact_root=str((tmp_path / "artifacts").resolve()),
    )
    ctx = _build_ctx(tmp_path, settings=settings)
    state = {
        "platform": "youtube",
        "source_url": "https://www.youtube.com/watch?v=demo",
        "video_uid": "demo",
        "comments_policy": {"top_n": 2, "replies_per_comment": 1, "sort": "new"},
    }

    execution = asyncio.run(runner._step_collect_comments(ctx, state))

    assert execution.status == "succeeded"
    assert captured["collector_kwargs"]["top_n"] == 2
    assert captured["collector_kwargs"]["replies_per_comment"] == 1
    comments = execution.state_updates["comments"]
    assert comments["sort"] == "new"
    assert comments["top_n"] == 2
    assert comments["replies_per_comment"] == 1
    assert comments["top_comments"][0]["comment_id"] == "newer"
    assert len(comments["top_comments"][0]["replies"]) == 1


def test_step_extract_frames_applies_overrides(monkeypatch: Any, tmp_path: Path) -> None:
    (tmp_path / "frames").mkdir(parents=True, exist_ok=True)
    media_path = tmp_path / "video.mp4"
    media_path.write_bytes(b"fake-video")
    captured: dict[str, Any] = {}

    async def _fake_run_command(_: runner.PipelineContext, cmd: list[str]) -> runner.CommandResult:
        captured["cmd"] = list(cmd)
        for idx in range(2):
            (tmp_path / "frames" / f"frame_{idx:03d}.jpg").write_bytes(b"\xff\xd8\xff")
        return runner.CommandResult(ok=True, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(runner, "_run_command", _fake_run_command)
    ctx = _build_ctx(tmp_path)
    state = {
        "media_path": str(media_path.resolve()),
        "frame_policy": {"method": "scene", "max_frames": 2},
    }

    execution = asyncio.run(runner._step_extract_frames(ctx, state))

    assert execution.status == "succeeded"
    assert execution.output["method"] == "scene"
    assert execution.output["max_frames"] == 2
    cmd = captured["cmd"]
    assert "select='gt(scene,0.3)'" in cmd
    assert cmd[cmd.index("-frames:v") + 1] == "2"


def test_step_llm_outline_applies_overrides(monkeypatch: Any, tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_gemini_generate(
        _settings: Settings,
        _prompt: str,
        *,
        media_path: str | None = None,
        frame_paths: list[str] | None = None,
        llm_input_mode: str = "auto",
        model: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        response_schema: dict[str, Any] | None = None,
        response_mime_type: str | None = None,
        thinking_level: str | None = None,
        include_thoughts: bool | None = None,
        use_context_cache: bool = True,
        enable_function_calling: bool = True,
    ) -> tuple[str | None, str]:
        calls.append(
            {
                "media_path": media_path,
                "frame_paths": list(frame_paths or []),
                "llm_input_mode": llm_input_mode,
                "model": model,
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "response_schema": response_schema,
                "response_mime_type": response_mime_type,
                "thinking_level": thinking_level,
                "include_thoughts": include_thoughts,
                "use_context_cache": use_context_cache,
                "enable_function_calling": enable_function_calling,
            }
        )
        return (
            '{"title":"Demo","tldr":[],"highlights":[],"recommended_actions":[],"risk_or_pitfalls":[],"chapters":[],"timestamp_references":[]}',
            "text",
        )

    monkeypatch.setattr(runner, "_gemini_generate", _fake_gemini_generate)
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
        "llm_policy": {
            "model": "gemini-2.0-flash",
            "temperature": 0.2,
            "max_output_tokens": 1024,
        },
    }

    execution = asyncio.run(runner._step_llm_outline(ctx, state))

    assert execution.status == "succeeded"
    assert calls
    first = calls[0]
    assert first["model"] == "gemini-2.0-flash"
    assert first["temperature"] == 0.2
    assert first["max_output_tokens"] == 1024


def test_cache_signature_includes_override_policies(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path)
    base_state = {
        "source_url": "https://www.youtube.com/watch?v=demo",
        "platform": "youtube",
        "video_uid": "demo",
        "comments_policy": {"top_n": 10, "replies_per_comment": 2, "sort": "hot"},
        "media_path": str((tmp_path / "video.mp4").resolve()),
        "frame_policy": {"method": "fps", "max_frames": 6},
        "title": "Demo",
        "metadata": {},
        "transcript": "hello",
        "comments": {"top_comments": []},
        "frames": [],
        "llm_input_mode": "auto",
        "llm_media_input": {"video_available": False, "frame_count": 0},
        "llm_policy": {"model": "gemini-1.5-flash", "temperature": None, "max_output_tokens": None},
        "outline": {},
    }

    comment_sig_1 = runner._build_step_cache_info(ctx, base_state, "collect_comments")["signature"]
    changed_comments = dict(base_state)
    changed_comments["comments_policy"] = {"top_n": 3, "replies_per_comment": 2, "sort": "hot"}
    comment_sig_2 = runner._build_step_cache_info(ctx, changed_comments, "collect_comments")["signature"]
    assert comment_sig_1 != comment_sig_2

    frame_sig_1 = runner._build_step_cache_info(ctx, base_state, "extract_frames")["signature"]
    changed_frames = dict(base_state)
    changed_frames["frame_policy"] = {"method": "scene", "max_frames": 6}
    frame_sig_2 = runner._build_step_cache_info(ctx, changed_frames, "extract_frames")["signature"]
    assert frame_sig_1 != frame_sig_2

    llm_sig_1 = runner._build_step_cache_info(ctx, base_state, "llm_outline")["signature"]
    changed_llm = dict(base_state)
    changed_llm["llm_policy"] = {
        "model": "gemini-2.0-flash",
        "temperature": 0.2,
        "max_output_tokens": 1024,
    }
    llm_sig_2 = runner._build_step_cache_info(ctx, changed_llm, "llm_outline")["signature"]
    assert llm_sig_1 != llm_sig_2
