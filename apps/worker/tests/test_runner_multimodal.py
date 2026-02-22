from __future__ import annotations

from pathlib import Path
import sys
import types
from typing import Any

from worker.config import Settings
from worker.pipeline import runner


def test_gemini_multimodal_falls_back_from_video_to_frames(monkeypatch: Any, tmp_path: Path) -> None:
    video_path = tmp_path / "video.mp4"
    frame_path = tmp_path / "frame_001.jpg"
    video_path.write_bytes(b"not-a-real-video")
    frame_path.write_bytes(b"\xff\xd8\xff")

    calls: list[Any] = []

    class _FakeModels:
        def generate_content(self, *, model: str, contents: Any, config: Any) -> Any:
            calls.append({"model": model, "contents": contents, "config": config})
            if isinstance(contents, list) and any(
                isinstance(item, dict) and item.get("kind") == "video"
                for item in contents
            ):
                raise RuntimeError("video-input-failed")
            if isinstance(contents, list) and any(
                isinstance(item, dict) and str(item.get("mime_type", "")).startswith("image/")
                for item in contents
            ):
                return types.SimpleNamespace(text='{"ok":true}')
            return types.SimpleNamespace(text=None)

    class _FakeFiles:
        @staticmethod
        def upload(*, file: str) -> dict[str, str]:
            return {"kind": "video", "path": file}

    class _FakeClient:
        def __init__(self, *, api_key: str):
            self.api_key = api_key
            self.models = _FakeModels()
            self.files = _FakeFiles()

    class _FakePart:
        @staticmethod
        def from_bytes(*, data: bytes, mime_type: str) -> dict[str, Any]:
            return {"mime_type": mime_type, "size": len(data)}

    class _FakeThinkingConfig:
        def __init__(self, **kwargs: Any):
            self.kwargs = kwargs

    class _FakeGenerateContentConfig:
        def __init__(self, **kwargs: Any):
            self.kwargs = kwargs

    fake_types = types.SimpleNamespace(
        Part=_FakePart,
        ThinkingConfig=_FakeThinkingConfig,
        GenerateContentConfig=_FakeGenerateContentConfig,
    )
    fake_genai = types.ModuleType("google.genai")
    fake_genai.Client = _FakeClient  # type: ignore[attr-defined]
    fake_genai.types = fake_types  # type: ignore[attr-defined]

    fake_google = types.ModuleType("google")
    fake_google.genai = fake_genai  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)

    settings = Settings(gemini_api_key="key", pipeline_max_frames=4)
    text, media_input = runner._gemini_generate(
        settings,
        "prompt",
        media_path=str(video_path),
        frame_paths=[str(frame_path)],
        llm_input_mode="auto",
    )

    assert text == '{"ok":true}'
    assert media_input == "frames_text"
    assert len(calls) >= 2


def test_llm_cache_signature_includes_input_mode_and_media_dimension(tmp_path: Path) -> None:
    settings = Settings(
        pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
        pipeline_artifact_root=str((tmp_path / "artifact").resolve()),
    )
    ctx = runner.PipelineContext(
        settings=settings,
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

    base_state = {
        "title": "Demo",
        "metadata": {},
        "transcript": "hello",
        "comments": {"top_comments": []},
        "frames": [],
        "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "llm_input_mode": "auto",
        "llm_media_input": {"video_available": False, "frame_count": 0},
    }
    sig_1 = runner._build_step_cache_info(ctx, base_state, "llm_outline")["signature"]

    changed_mode = dict(base_state)
    changed_mode["llm_input_mode"] = "text"
    sig_2 = runner._build_step_cache_info(ctx, changed_mode, "llm_outline")["signature"]

    changed_media = dict(base_state)
    changed_media["llm_media_input"] = {"video_available": True, "frame_count": 2}
    sig_3 = runner._build_step_cache_info(ctx, changed_media, "llm_outline")["signature"]

    assert sig_1 != sig_2
    assert sig_1 != sig_3
