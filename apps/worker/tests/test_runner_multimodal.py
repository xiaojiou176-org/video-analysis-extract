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
    text, media_input, meta = runner._gemini_generate(
        settings,
        "prompt",
        media_path=str(video_path),
        frame_paths=[str(frame_path)],
        llm_input_mode="auto",
    )

    assert text == '{"ok":true}'
    assert media_input == "frames_text"
    assert len(calls) >= 2
    assert isinstance(meta, dict)


def test_gemini_function_calling_loop_and_thought_metadata(monkeypatch: Any, tmp_path: Path) -> None:
    frame_path = tmp_path / "frame_001.jpg"
    frame_path.write_bytes(b"\xff\xd8\xff")

    calls: list[Any] = []
    first_round = {"value": True}

    class _FunctionCall:
        def __init__(self, name: str, args: dict[str, Any]):
            self.name = name
            self.args = args

    class _Part:
        def __init__(
            self,
            *,
            text: str | None = None,
            thought: bool = False,
            function_call: Any = None,
            signature: str | None = None,
        ):
            self.text = text
            self.thought = thought
            self.function_call = function_call
            self.signature = signature

        @staticmethod
        def from_bytes(**kwargs: Any) -> dict[str, Any]:
            return dict(kwargs)

        @staticmethod
        def from_function_response(*, name: str, response: dict[str, Any]) -> dict[str, Any]:
            return {"function_response": {"name": name, "response": response}}

    class _FakeModels:
        def generate_content(self, *, model: str, contents: Any, config: Any) -> Any:
            calls.append({"model": model, "contents": contents, "config": config})
            if first_round["value"]:
                first_round["value"] = False
                function_call = _FunctionCall(
                    name="select_supporting_frames",
                    args={"frame_summaries": [{"timestamp_s": 12, "path": "/tmp/f.jpg"}], "max_items": 1},
                )
                part_call = _Part(function_call=function_call)
                part_thought = _Part(text="internal", thought=True, signature="sig-A")
                content = types.SimpleNamespace(parts=[part_call, part_thought])
                return types.SimpleNamespace(
                    text=None,
                    candidates=[types.SimpleNamespace(content=content)],
                    usage_metadata=types.SimpleNamespace(
                        prompt_token_count=10,
                        candidates_token_count=5,
                        total_token_count=15,
                        thoughts_token_count=2,
                    ),
                )

            content = types.SimpleNamespace(parts=[_Part(text='{"ok":true}')])
            return types.SimpleNamespace(
                text='{"ok":true}',
                candidates=[types.SimpleNamespace(content=content)],
            )

    class _FakeFiles:
        @staticmethod
        def upload(*, file: str) -> dict[str, str]:
            return {"kind": "video", "path": file}

    class _FakeClient:
        def __init__(self, *, api_key: str):
            self.api_key = api_key
            self.models = _FakeModels()
            self.files = _FakeFiles()

    class _FakeThinkingConfig:
        def __init__(self, **kwargs: Any):
            self.kwargs = kwargs

    class _FakeGenerateContentConfig:
        def __init__(self, **kwargs: Any):
            self.kwargs = kwargs

    fake_types = types.SimpleNamespace(
        Part=_Part,
        ThinkingConfig=_FakeThinkingConfig,
        GenerateContentConfig=_FakeGenerateContentConfig,
        Content=lambda **kwargs: dict(kwargs),
    )
    fake_genai = types.ModuleType("google.genai")
    fake_genai.Client = _FakeClient  # type: ignore[attr-defined]
    fake_genai.types = fake_types  # type: ignore[attr-defined]

    fake_google = types.ModuleType("google")
    fake_google.genai = fake_genai  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)

    settings = Settings(gemini_api_key="key", pipeline_max_frames=4)
    text, media_input, meta = runner._gemini_generate(
        settings,
        "prompt",
        frame_paths=[str(frame_path)],
        llm_input_mode="frames_text",
        include_thoughts=True,
        max_function_call_rounds=2,
        media_resolution={"frame": "high"},
    )

    assert text == '{"ok":true}'
    assert media_input == "frames_text"
    assert len(calls) == 2
    first_contents = calls[0]["contents"]
    assert isinstance(first_contents, list)
    assert any(
        isinstance(item, dict) and item.get("mime_type", "").startswith("image/") and item.get("media_resolution") == "high"
        for item in first_contents
    )
    function_meta = meta["function_calling"]
    assert function_meta["rounds_used"] == 2
    assert function_meta["calls"][0]["name"] == "select_supporting_frames"
    thinking_meta = meta["thinking"]
    assert thinking_meta["include_thoughts"] is True
    assert thinking_meta["thought_count"] == 1
    assert thinking_meta["thought_signatures"] == ["sig-A"]


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
