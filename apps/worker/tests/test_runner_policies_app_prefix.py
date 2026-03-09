from __future__ import annotations

from worker.config import Settings

from apps.worker.worker.pipeline import runner_policies


def _settings() -> Settings:
    return Settings(
        pipeline_workspace_dir="/tmp/workspace",
        pipeline_artifact_root="/tmp/artifacts",
        comments_top_n=8,
        comments_replies_per_comment=3,
        pipeline_max_frames=5,
        gemini_include_thoughts=False,
        gemini_computer_use_enabled=True,
        gemini_computer_use_require_confirmation=True,
        gemini_computer_use_max_steps=4,
        gemini_computer_use_timeout_seconds=12.0,
        gemini_model="gemini-pro",
        gemini_fast_model="gemini-flash",
        gemini_outline_model="gemini-outline",
        gemini_digest_model="gemini-digest",
    )


def test_coercion_helpers_cover_bool_numeric_and_defaults() -> None:
    assert runner_policies.coerce_bool(True) is True
    assert runner_policies.coerce_bool(None, default=True) is True
    assert runner_policies.coerce_bool("1") is True
    assert runner_policies.coerce_bool("yes") is True
    assert runner_policies.coerce_bool("on") is True
    assert runner_policies.coerce_bool("off", default=True) is False
    assert runner_policies.coerce_bool("unknown", default=True) is True
    assert runner_policies.coerce_bool("unknown") is False

    assert runner_policies.coerce_int("4", default=9) == 4
    assert runner_policies.coerce_int("bad", default=9) == 9
    assert runner_policies.coerce_int("bad") == 0
    assert runner_policies.coerce_float("1.5", default=None) == 1.5
    assert runner_policies.coerce_float("bad", default=2.5) == 2.5


def test_media_resolution_normalization_and_override_helpers() -> None:
    assert runner_policies._normalize_media_resolution("Ultra High") == "ultra_high"
    assert runner_policies._normalize_media_resolution("weird") == "medium"
    assert runner_policies._normalize_media_resolution("weird", default="low") == "low"
    assert runner_policies._normalize_media_resolution_policy("high") == {
        "default": "high",
        "frame": "high",
        "image": "high",
        "pdf": "high",
    }
    assert runner_policies._normalize_media_resolution_policy({}) == {
        "default": "medium",
        "frame": "medium",
        "image": "medium",
        "pdf": "medium",
    }
    assert runner_policies._normalize_media_resolution_policy(
        {"default": "medium", "frame": "high", "image": "low", "pdf": "bad"},
        default="low",
    ) == {
        "default": "medium",
        "frame": "high",
        "image": "low",
        "pdf": "medium",
    }
    assert runner_policies.normalize_overrides_payload(["bad"]) == {}
    assert runner_policies.override_section({"comments": {"top_n": 4}}, "comments") == {"top_n": 4}
    assert runner_policies.override_section({"comments": "bad"}, "comments") == {}


def test_comments_and_frame_policies_normalize_inputs() -> None:
    settings = _settings()
    comments = runner_policies.build_comments_policy(
        settings,
        {"comments": {"top_n": 0, "replies_per_comment": -3, "sort": "bad"}},
        platform="youtube",
    )
    comments_defaults = runner_policies.build_comments_policy(
        settings,
        {"comments": {}},
        platform="bilibili",
    )
    frames = runner_policies.build_frame_policy(
        settings,
        {"frames": {"method": "bad", "max_frames": 0}},
    )
    frames_scene = runner_policies.build_frame_policy(
        settings,
        {"frames": {"method": " Scene ", "max_frames": "3"}},
    )

    assert comments == {"top_n": 1, "replies_per_comment": 0, "sort": "hot"}
    assert comments_defaults == {"top_n": 8, "replies_per_comment": 3, "sort": "like"}
    assert frames == {"method": "fps", "max_frames": 1}
    assert frames_scene == {"method": "scene", "max_frames": 3}
    assert runner_policies.default_comment_sort_for_platform("youtube") == "hot"
    assert runner_policies.default_comment_sort_for_platform("bilibili") == "like"


def test_llm_policy_section_and_build_llm_policy_cover_overrides() -> None:
    settings = _settings()
    section = runner_policies.build_llm_policy_section(
        "default-model",
        {
            "model": " section-model ",
            "temperature": 9,
            "max_output_tokens": "256",
            "max_function_call_rounds": "-1",
            "include_thoughts": "true",
            "enable_computer_use": "true",
            "computer_use_require_confirmation": "false",
            "computer_use_max_steps": "-2",
            "computer_use_timeout_seconds": "0",
            "media_resolution": {"default": "high", "frame": "low"},
        },
        allow_computer_use=True,
    )
    section_no_computer_use = runner_policies.build_llm_policy_section(
        "default-model",
        {
            "temperature": "-3",
            "max_output_tokens": "0",
            "enable_computer_use": "true",
        },
        allow_computer_use=False,
    )
    policy = runner_policies.build_llm_policy(
        settings,
        {
            "llm": {
                "speed_priority": True,
                "thinking_level": "bad",
                "include_thoughts": "true",
                "media_resolution": {"default": "high"},
                "enable_computer_use": "true",
            },
            "llm_outline": {"model": "outline-override"},
            "llm_digest": {"model": "digest-override"},
        },
    )
    policy_without_speed_priority = runner_policies.build_llm_policy(
        settings,
        {"llm": {"thinking_level": "bad"}},
    )

    assert section["model"] == "section-model"
    assert section["temperature"] == 2.0
    assert section["max_output_tokens"] == 256
    assert section["max_function_call_rounds"] == 0
    assert section["include_thoughts"] is True
    assert section["enable_computer_use"] is True
    assert section["computer_use_require_confirmation"] is False
    assert section["computer_use_max_steps"] == 0
    assert section["computer_use_timeout_seconds"] == 30.0
    assert section["media_resolution"]["frame"] == "low"
    assert section_no_computer_use["temperature"] == 0.0
    assert section_no_computer_use["max_output_tokens"] is None
    assert section_no_computer_use["enable_computer_use"] is False

    assert policy["model"] == "gemini-flash"
    assert policy["thinking_level"] == "low"
    assert policy["outline"]["model"] == "outline-override"
    assert policy["digest"]["model"] == "digest-override"
    assert policy["enable_computer_use"] is True
    assert policy_without_speed_priority["speed_priority"] is False
    assert policy_without_speed_priority["thinking_level"] == "high"
    assert policy_without_speed_priority["model"] == "gemini-pro"


def test_llm_policy_turns_off_computer_use_when_globally_disabled() -> None:
    settings = Settings(
        pipeline_workspace_dir="/tmp/workspace",
        pipeline_artifact_root="/tmp/artifacts",
        gemini_include_thoughts=False,
        gemini_computer_use_enabled=False,
        gemini_computer_use_require_confirmation=True,
        gemini_computer_use_max_steps=4,
        gemini_computer_use_timeout_seconds=12.0,
        gemini_model="gemini-pro",
        gemini_fast_model="gemini-flash",
        gemini_outline_model="gemini-outline",
        gemini_digest_model="gemini-digest",
    )

    policy = runner_policies.build_llm_policy(
        settings,
        {
            "llm": {
                "speed_priority": True,
                "enable_computer_use": True,
                "computer_use_require_confirmation": False,
            },
            "llm_outline": {"enable_computer_use": True},
            "llm_digest": {"enable_computer_use": True},
        },
    )

    assert policy["model"] == "gemini-flash"
    assert policy["enable_computer_use"] is False
    assert policy["outline"]["enable_computer_use"] is False
    assert policy["digest"]["enable_computer_use"] is False


def test_apply_comments_policy_and_mode_helpers_cover_sorting_and_lists() -> None:
    payload = runner_policies.apply_comments_policy(
        {
            "sort": "",
            "top_comments": [
                {
                    "comment_id": "older",
                    "like_count": 9,
                    "published_at": "2024-01-01T00:00:00Z",
                    "replies": [{"reply_id": "1"}, {"reply_id": "2"}],
                },
                {
                    "comment_id": "newer",
                    "like_count": 1,
                    "published_at": "2024-01-02T00:00:00Z",
                    "replies": [{"reply_id": "3"}],
                },
                "bad",
            ],
        },
        policy={"sort": "new", "top_n": 1, "replies_per_comment": 1},
        platform="youtube",
    )
    fallback_sort_payload = runner_policies.apply_comments_policy(
        {
            "sort": "",
            "top_n": 2,
            "replies_per_comment": 1,
            "top_comments": [
                {"comment_id": "c1", "like_count": 1, "replies": [{"reply_id": "r1"}]},
                {"comment_id": "c2", "like_count": 9, "replies": [{"reply_id": "r2"}]},
            ],
        },
        policy={"sort": "bad"},
        platform="bilibili",
    )

    assert payload["sort"] == "new"
    assert payload["top_comments"][0]["comment_id"] == "newer"
    assert payload["replies"] == {"newer": [{"reply_id": "3"}]}
    assert fallback_sort_payload["sort"] == "like"
    assert fallback_sort_payload["top_n"] == 2
    assert fallback_sort_payload["replies_per_comment"] == 1
    assert fallback_sort_payload["top_comments"][0]["comment_id"] == "c2"
    assert runner_policies.normalize_pipeline_mode("refresh_llm") == "refresh_llm"
    assert runner_policies.normalize_pipeline_mode("weird") == "full"
    assert runner_policies.normalize_llm_input_mode("frames_text") == "frames_text"
    assert runner_policies.normalize_llm_input_mode("odd") == "auto"
    assert runner_policies.frame_paths_from_frames(
        [{"path": "a"}, {"path": "a"}, {"path": "b"}, {}],
        limit=2,
    ) == ["a", "b"]
    state = {"media_path": "/tmp/video.mp4", "frames": [{"path": "a"}, {"path": "b"}]}
    assert runner_policies.llm_media_input_dimension(state) == {
        "video_available": True,
        "frame_count": 2,
    }
    runner_policies.refresh_llm_media_input_dimension(state)
    assert state["llm_media_input"]["frame_count"] == 2


def test_apply_comments_policy_falls_back_to_payload_sort_before_platform_default() -> None:
    payload = runner_policies.apply_comments_policy(
        {
            "sort": "hot",
            "top_comments": [
                {"comment_id": "a", "like_count": 1, "published_at": "2024-01-01T00:00:00Z"},
                {"comment_id": "b", "like_count": 5, "published_at": "2024-01-02T00:00:00Z"},
            ],
        },
        policy={"sort": "invalid", "top_n": 2, "replies_per_comment": 1},
        platform="bilibili",
    )

    assert payload["sort"] == "hot"
    assert [item["comment_id"] for item in payload["top_comments"]] == ["b", "a"]
    assert payload["top_n"] == 2
    assert payload["replies_per_comment"] == 1


def test_string_and_language_helpers_cover_json_and_cjk_detection() -> None:
    values = runner_policies.coerce_str_list(
        [" a ", {"text": "b"}, {"summary": "c"}, 7, None],
        limit=4,
    )
    deduped = runner_policies.dedupe_keep_order(["a", "a", "b", "", "c"], limit=2)
    json_text = runner_policies.extract_json_object('```json\n{"ok": true}\n```')
    fallback_json = runner_policies.extract_json_object('prefix {"x":1} suffix')
    outline_payload = {"title": "你好", "chapters": [{"title": "章节", "summary": "摘要"}]}
    digest_payload = {"title": "总结", "summary": "内容", "tldr": ["重点"]}

    assert values == ["a", "b", "c", "7"]
    assert deduped == ["a", "b"]
    assert json_text == '{"ok": true}'
    assert fallback_json == '{"x":1}'
    assert runner_policies.contains_cjk("hello你好") is True
    assert runner_policies.contains_cjk("plain english") is False
    assert runner_policies.outline_is_chinese(outline_payload) is True
    assert runner_policies.digest_is_chinese(digest_payload) is True


def test_language_helpers_cover_negative_and_nested_cjk_paths() -> None:
    assert runner_policies.contains_cjk("12345 !!!") is False
    assert runner_policies.outline_is_chinese({"title": "hello", "chapters": []}) is False
    assert (
        runner_policies.outline_is_chinese(
            {"title": "", "chapters": [{"title": "", "summary": "包含中文摘要"}]}
        )
        is True
    )
    assert runner_policies.digest_is_chinese({"title": "report", "summary": "english only"}) is False
    assert runner_policies.digest_is_chinese({"title": "", "summary": "", "highlights": ["关键点"]}) is True
