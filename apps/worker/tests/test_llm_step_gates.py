from __future__ import annotations

from types import SimpleNamespace

from apps.worker.worker.pipeline.steps import llm_step_gates as gates


def _ctx(*, include_thoughts: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        settings=SimpleNamespace(
            gemini_include_thoughts=include_thoughts,
            gemini_computer_use_enabled=False,
            gemini_computer_use_require_confirmation=True,
            gemini_computer_use_max_steps=3,
            gemini_computer_use_timeout_seconds=1.5,
        )
    )


def test_semantic_len_and_outline_quality_gate() -> None:
    assert gates._semantic_len(" 你好, A-1 ! ") == 4

    assert gates._outline_quality_ok({"highlights": ["short"], "chapters": [{"summary": "valid summary"}]}) is False
    assert gates._outline_quality_ok({"highlights": ["meaningful highlight"], "chapters": []}) is False
    assert (
        gates._outline_quality_ok(
            {
                "highlights": ["meaningful highlight"],
                "chapters": [{"summary": "tiny", "bullets": ["mini"]}],
            }
        )
        is False
    )
    assert (
        gates._outline_quality_ok(
            {
                "highlights": ["非常有信息量的重点内容"],
                "chapters": ["invalid", {"summary": "", "bullets": ["long enough bullet"]}],
            }
        )
        is True
    )


def test_digest_quality_gate_requires_summary_and_highlights() -> None:
    assert gates._digest_quality_ok({"summary": "too short", "highlights": ["long enough highlight"]}) is False
    assert gates._digest_quality_ok({"summary": "this summary has enough semantic length", "highlights": ["short"]}) is False
    assert (
        gates._digest_quality_ok(
            {
                "summary": "this summary has enough semantic length",
                "highlights": ["this highlight is long enough"],
            }
        )
        is True
    )


def test_thinking_level_bool_and_include_thoughts_policy() -> None:
    assert gates._thinking_level_from_policy({"thinking_level": "minimal"}) == "low"
    assert gates._thinking_level_from_policy({"speed_priority": True}) == "low"
    assert gates._thinking_level_from_policy({"thinking_level": "unknown"}) == "high"

    assert gates._coerce_bool("yes", default=False) is True
    assert gates._coerce_bool("off", default=True) is False
    assert gates._coerce_bool("maybe", default=True) is True

    ctx = _ctx(include_thoughts=True)
    assert gates._include_thoughts_from_policy(ctx, {}, {"include_thoughts": "0"}) is False
    assert gates._include_thoughts_from_policy(ctx, {"include_thoughts": "1"}, {}) is True
    assert gates._include_thoughts_from_policy(_ctx(include_thoughts=False), {}, {}) is False


def test_media_resolution_rounds_and_computer_use_options() -> None:
    raw_resolution = {"default": "high", "frames": "ultra"}
    normalized = gates._media_resolution_from_policy({}, {"media_resolution": raw_resolution})
    assert normalized == raw_resolution
    assert normalized is not raw_resolution
    assert gates._media_resolution_from_policy({"media_resolution": " HIGH "}, {}) == {"default": "high"}
    assert gates._media_resolution_from_policy({}, {}) == {}

    assert gates._max_function_call_rounds({"max_function_call_rounds": -2}, {}) == 0
    assert gates._max_function_call_rounds({}, {"max_function_call_rounds": "3"}) == 3

    options = gates.build_computer_use_options(
        _ctx(),
        {
            "enable_computer_use": "1",
            "computer_use_require_confirmation": "0",
            "computer_use_max_steps": "-4",
            "computer_use_timeout_seconds": "0",
        },
        {},
    )
    assert options == {
        "enable_computer_use": True,
        "computer_use_require_confirmation": False,
        "computer_use_max_steps": 0,
        "computer_use_timeout_seconds": 1.5,
    }

    clamped = gates.build_computer_use_options(
        _ctx(),
        {"computer_use_timeout_seconds": "-1"},
        {},
    )
    assert clamped["computer_use_timeout_seconds"] == 0.1
