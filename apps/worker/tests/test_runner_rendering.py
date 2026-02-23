from __future__ import annotations

from worker.config import Settings
from worker.pipeline.runner_rendering import should_include_frame_prompt


def test_should_include_frame_prompt_reads_settings_flag() -> None:
    assert should_include_frame_prompt(Settings(pipeline_llm_include_frames=True)) is True
    assert should_include_frame_prompt(Settings(pipeline_llm_include_frames=False)) is False
