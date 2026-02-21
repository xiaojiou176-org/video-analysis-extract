from __future__ import annotations

import re
from typing import Any, Literal

from worker.config import Settings

PipelineMode = Literal["full", "text_only", "refresh_comments", "refresh_llm"]
LLMInputMode = Literal["auto", "text", "video_text", "frames_text"]


def coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "y"}:
        return True
    if text in {"0", "false", "no", "off", "n"}:
        return False
    return default


def coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def coerce_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_overrides_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return dict(value)


def override_section(overrides: dict[str, Any], section: str) -> dict[str, Any]:
    value = overrides.get(section)
    if not isinstance(value, dict):
        return {}
    return dict(value)


def default_comment_sort_for_platform(platform: str) -> str:
    if platform == "youtube":
        return "hot"
    return "like"


def build_comments_policy(
    settings: Settings, overrides: dict[str, Any], *, platform: str
) -> dict[str, Any]:
    section = override_section(overrides, "comments")
    top_n = max(1, coerce_int(section.get("top_n"), settings.comments_top_n))
    replies_per_comment = max(
        0,
        coerce_int(section.get("replies_per_comment"), settings.comments_replies_per_comment),
    )
    sort_text = str(section.get("sort") or "").strip().lower()
    if sort_text not in {"hot", "new"}:
        sort_text = default_comment_sort_for_platform(platform)
    return {
        "top_n": top_n,
        "replies_per_comment": replies_per_comment,
        "sort": sort_text,
    }


def build_frame_policy(settings: Settings, overrides: dict[str, Any]) -> dict[str, Any]:
    section = override_section(overrides, "frames")
    method = str(section.get("method") or "fps").strip().lower()
    if method not in {"fps", "scene"}:
        method = "fps"
    max_frames = max(1, coerce_int(section.get("max_frames"), settings.pipeline_max_frames))
    return {"method": method, "max_frames": max_frames}


def build_llm_policy_section(default_model: str, section: dict[str, Any]) -> dict[str, Any]:
    model = str(section.get("model") or default_model).strip() or default_model
    temperature = coerce_float(section.get("temperature"), None)
    if temperature is not None:
        temperature = min(2.0, max(0.0, temperature))
    max_output_tokens_raw = section.get("max_output_tokens")
    max_output_tokens: int | None = None
    if max_output_tokens_raw is not None:
        parsed = coerce_int(max_output_tokens_raw, 0)
        if parsed > 0:
            max_output_tokens = parsed
    return {
        "model": model,
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }


def build_llm_policy(settings: Settings, overrides: dict[str, Any]) -> dict[str, Any]:
    section = override_section(overrides, "llm")
    outline_section = {**section, **override_section(overrides, "llm_outline")}
    digest_section = {**section, **override_section(overrides, "llm_digest")}
    outline = build_llm_policy_section(settings.gemini_outline_model, outline_section)
    digest = build_llm_policy_section(settings.gemini_digest_model, digest_section)
    model = str(section.get("model") or settings.gemini_model).strip() or settings.gemini_model
    temperature = coerce_float(section.get("temperature"), None)
    if temperature is not None:
        temperature = min(2.0, max(0.0, temperature))
    max_output_tokens_raw = section.get("max_output_tokens")
    max_output_tokens: int | None = None
    if max_output_tokens_raw is not None:
        parsed = coerce_int(max_output_tokens_raw, 0)
        if parsed > 0:
            max_output_tokens = parsed
    return {
        "model": model,
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "outline": outline,
        "digest": digest,
    }


def apply_comments_policy(
    comments_payload: dict[str, Any],
    *,
    policy: dict[str, Any],
    platform: str,
) -> dict[str, Any]:
    top_n = max(1, coerce_int(policy.get("top_n"), coerce_int(comments_payload.get("top_n"), 10)))
    replies_per_comment = max(
        0,
        coerce_int(
            policy.get("replies_per_comment"),
            coerce_int(comments_payload.get("replies_per_comment"), 10),
        ),
    )
    requested_sort = str(policy.get("sort") or "").strip().lower()
    if requested_sort not in {"hot", "new"}:
        requested_sort = str(comments_payload.get("sort") or "").strip().lower()
    if not requested_sort:
        requested_sort = default_comment_sort_for_platform(platform)

    top_comments: list[dict[str, Any]] = []
    raw_top_comments = comments_payload.get("top_comments")
    if isinstance(raw_top_comments, list):
        for item in raw_top_comments:
            if isinstance(item, dict):
                top_comments.append(dict(item))

    if requested_sort == "new":
        top_comments.sort(key=lambda item: str(item.get("published_at") or ""), reverse=True)
    else:
        top_comments.sort(key=lambda item: coerce_int(item.get("like_count"), 0), reverse=True)

    normalized_comments: list[dict[str, Any]] = []
    replies_index: dict[str, list[dict[str, Any]]] = {}
    for item in top_comments[:top_n]:
        replies: list[dict[str, Any]] = []
        raw_replies = item.get("replies")
        if isinstance(raw_replies, list):
            for reply in raw_replies[:replies_per_comment]:
                if isinstance(reply, dict):
                    replies.append(dict(reply))
        normalized_item = {**item, "replies": replies}
        normalized_comments.append(normalized_item)
        comment_id = str(normalized_item.get("comment_id") or "").strip()
        if comment_id:
            replies_index[comment_id] = replies

    return {
        **comments_payload,
        "sort": requested_sort,
        "top_n": top_n,
        "replies_per_comment": replies_per_comment,
        "top_comments": normalized_comments,
        "replies": replies_index,
    }


def normalize_pipeline_mode(value: Any) -> PipelineMode:
    text = str(value or "full").strip().lower()
    if text in {"full", "text_only", "refresh_comments", "refresh_llm"}:
        return text  # type: ignore[return-value]
    return "full"


def normalize_llm_input_mode(value: Any) -> LLMInputMode:
    text = str(value or "auto").strip().lower()
    if text in {"auto", "text", "video_text", "frames_text"}:
        return text  # type: ignore[return-value]
    return "auto"


def frame_paths_from_frames(frames: list[dict[str, Any]], *, limit: int = 8) -> list[str]:
    paths: list[str] = []
    for item in frames:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        if not path:
            continue
        if path in paths:
            continue
        paths.append(path)
        if len(paths) >= limit:
            break
    return paths


def llm_media_input_dimension(state: dict[str, Any]) -> dict[str, Any]:
    media_path = str(state.get("media_path") or "").strip()
    frames = list(state.get("frames") or [])
    frame_paths = frame_paths_from_frames(frames, limit=200)
    return {
        "video_available": bool(media_path),
        "frame_count": len(frame_paths),
    }


def refresh_llm_media_input_dimension(state: dict[str, Any]) -> None:
    state["llm_media_input"] = llm_media_input_dimension(state)


def coerce_str_list(values: Any, *, limit: int = 12) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for item in values:
        text = ""
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            for key in ("text", "summary", "title", "content", "label", "value"):
                candidate = item.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    text = candidate.strip()
                    break
        elif isinstance(item, (int, float)):
            text = str(item).strip()
        if text:
            normalized.append(text)
        if len(normalized) >= limit:
            break
    return normalized


def dedupe_keep_order(values: list[str], *, limit: int = 12) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
        if len(result) >= limit:
            break
    return result


def extract_json_object(text: str) -> str:
    content = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", content, re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        return content[start : end + 1]
    return content


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def outline_is_chinese(payload: dict[str, Any]) -> bool:
    candidates: list[str] = [str(payload.get("title") or "")]
    chapters = payload.get("chapters")
    if isinstance(chapters, list):
        for chapter in chapters[:4]:
            if not isinstance(chapter, dict):
                continue
            candidates.append(str(chapter.get("title") or ""))
            candidates.append(str(chapter.get("summary") or ""))
    text = " ".join(item for item in candidates if item).strip()
    return contains_cjk(text)


def digest_is_chinese(payload: dict[str, Any]) -> bool:
    candidates: list[str] = [str(payload.get("title") or ""), str(payload.get("summary") or "")]
    for key in ("tldr", "highlights", "action_items"):
        values = payload.get(key)
        if isinstance(values, list):
            candidates.extend(str(item) for item in values[:4])
    text = " ".join(item for item in candidates if item).strip()
    return contains_cjk(text)
