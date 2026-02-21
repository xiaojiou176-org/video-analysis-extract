from __future__ import annotations

import asyncio
import json
import mimetypes
from pathlib import Path
import re
from typing import Any, Callable

from worker.config import Settings
from worker.pipeline.policies import (
    coerce_float,
    coerce_int,
    coerce_str_list,
    dedupe_keep_order,
    digest_is_chinese,
    extract_json_object,
    frame_paths_from_frames,
    normalize_llm_input_mode,
    outline_is_chinese,
    pipeline_llm_fail_on_provider_error,
    pipeline_llm_hard_required,
)
from worker.pipeline.runner_rendering import (
    build_comments_prompt_context,
    build_frames_prompt_context,
    collect_code_blocks,
    estimate_duration_seconds,
    extract_code_snippets,
    should_include_frame_prompt,
    timestamp_link,
)
from worker.pipeline.step_executor import jsonable, utc_now_iso
from worker.pipeline.types import LLMInputMode, PipelineContext, StepExecution


def collect_key_points_from_text(text: str, limit: int = 5) -> list[str]:
    if not text:
        return []
    parts = re.split(r"(?<=[。！？.!?])\s+", text)
    cleaned = [part.strip() for part in parts if part.strip()]
    if not cleaned:
        return []
    return cleaned[:limit]


def _translate_payload_to_chinese(
    settings: Settings,
    payload: dict[str, Any],
    *,
    model: str,
    max_output_tokens: int | None,
    schema_label: str,
) -> dict[str, Any] | None:
    prompt = "\n\n".join(
        [
            "将下面 JSON 中所有面向读者的自然语言翻译为简体中文。",
            "保持 JSON 的 key、结构、数字、时间戳、URL、ID 不变。",
            "如果包含代码片段（如 code_snippets.snippet / code_blocks.snippet），代码内容不要翻译。",
            "只返回 JSON，不要解释。",
            f"Schema: {schema_label}",
            json.dumps(jsonable(payload), ensure_ascii=False),
        ]
    )
    translated_raw, _ = gemini_generate(
        settings,
        prompt,
        llm_input_mode="text",
        model=model,
        temperature=0.1,
        max_output_tokens=max_output_tokens,
    )
    if not translated_raw:
        return None
    try:
        parsed = json.loads(extract_json_object(translated_raw))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _extract_gemini_text(response: Any) -> str | None:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    return None


def _build_frame_parts(frame_paths: list[str], *, limit: int = 6) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for frame_path in frame_paths[:limit]:
        path = Path(frame_path)
        if not path.exists() or not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if not data:
            continue
        mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        parts.append({"mime_type": mime_type, "data": data})
    return parts


def gemini_generate(
    settings: Settings,
    prompt: str,
    *,
    media_path: str | None = None,
    frame_paths: list[str] | None = None,
    llm_input_mode: LLMInputMode = "auto",
    model: str | None = None,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> tuple[str | None, str]:
    if not settings.gemini_api_key:
        return None, "none"
    try:
        import google.generativeai as genai  # type: ignore
    except Exception:
        return None, "none"

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model_name = str(model or settings.gemini_model).strip() or settings.gemini_model
        llm_model = genai.GenerativeModel(model_name)
    except Exception:
        return None, "none"

    normalized_mode = normalize_llm_input_mode(llm_input_mode)
    normalized_media_path = str(media_path or "").strip()
    normalized_frame_paths = list(frame_paths or [])

    generation_config: dict[str, Any] = {}
    if temperature is not None:
        generation_config["temperature"] = temperature
    if max_output_tokens is not None:
        generation_config["max_output_tokens"] = max_output_tokens

    def _generate_content(content: Any) -> Any:
        if generation_config:
            return llm_model.generate_content(content, generation_config=generation_config)
        return llm_model.generate_content(content)

    should_try_video = normalized_mode in {"auto", "video_text"} and bool(normalized_media_path)
    if should_try_video:
        try:
            upload_fn = getattr(genai, "upload_file", None)
            if callable(upload_fn):
                video_part = upload_fn(path=normalized_media_path)
                response = _generate_content([video_part, prompt])
                text = _extract_gemini_text(response)
                if text:
                    return text, "video_text"
        except Exception:
            pass

    should_try_frames = normalized_mode in {"auto", "video_text", "frames_text"} and bool(normalized_frame_paths)
    if should_try_frames:
        try:
            frame_parts = _build_frame_parts(
                normalized_frame_paths,
                limit=max(1, settings.pipeline_max_frames),
            )
            if frame_parts:
                response = _generate_content([prompt, *frame_parts])
                text = _extract_gemini_text(response)
                if text:
                    return text, "frames_text"
        except Exception:
            pass

    if normalized_mode in {"auto", "text"}:
        try:
            response = _generate_content(prompt)
            text = _extract_gemini_text(response)
            if text:
                return text, "text"
        except Exception:
            pass

    return None, "none"


def _build_local_outline(state: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(state.get("metadata") or {})
    title = str(metadata.get("title") or state.get("title") or "Untitled Video")
    transcript = str(state.get("transcript") or "")
    comments = dict(state.get("comments") or {})
    frames = list(state.get("frames") or [])
    source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")

    key_points = collect_key_points_from_text(transcript, limit=10)
    comment_points: list[str] = []
    top_comments = comments.get("top_comments")
    if isinstance(top_comments, list):
        for item in top_comments[:3]:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "").strip()
            if content:
                comment_points.append(f"评论观点：{content}")

    merged_points = dedupe_keep_order(key_points + comment_points, limit=12)
    if not merged_points:
        merged_points = [
            f"本期核心主题：{title}",
            "字幕缺失，以下导读基于元信息与评论区自动生成。",
        ]

    chapter_count = min(4, max(2, (len(merged_points) + 2) // 3))
    duration_s = estimate_duration_seconds(metadata, frames, len(merged_points))
    chapter_span = max(1, duration_s // chapter_count)

    snippets = extract_code_snippets(transcript, limit=4)
    chapters: list[dict[str, Any]] = []
    for idx in range(chapter_count):
        chapter_no = idx + 1
        start_s = idx * chapter_span
        end_s = duration_s if chapter_no == chapter_count else max(start_s, (idx + 1) * chapter_span - 1)
        bullets = merged_points[idx * 3 : idx * 3 + 3]
        if not bullets:
            bullets = [f"第 {chapter_no} 章承接主线内容展开。"]
        summary = bullets[0]
        title_hint = re.sub(r"[。.!?！？].*$", "", summary).strip()[:48]
        chapter_title = title_hint or f"Chapter {chapter_no}"
        key_terms = re.findall(r"[A-Za-z][A-Za-z0-9_+-]{2,}", " ".join(bullets))[:5]
        chapter_snippets = [snippets[idx]] if idx < len(snippets) else []
        if chapter_snippets:
            chapter_snippets[0]["range_start_s"] = start_s
            chapter_snippets[0]["range_end_s"] = end_s

        chapters.append(
            {
                "chapter_no": chapter_no,
                "title": chapter_title,
                "anchor": f"chapter-{chapter_no:02d}",
                "start_s": start_s,
                "end_s": end_s,
                "start_link": timestamp_link(source_url, start_s),
                "end_link": timestamp_link(source_url, end_s),
                "summary": summary,
                "bullets": bullets,
                "key_terms": key_terms,
                "code_snippets": chapter_snippets,
            }
        )

    timestamp_references: list[dict[str, Any]] = []
    for chapter in chapters:
        timestamp_references.append(
            {
                "ts_s": coerce_int(chapter.get("start_s"), 0),
                "label": str(chapter.get("title") or "Chapter"),
                "reason": "chapter_start",
            }
        )
    for frame in frames[:5]:
        if not isinstance(frame, dict):
            continue
        timestamp_references.append(
            {
                "ts_s": coerce_int(frame.get("timestamp_s"), 0),
                "label": "关键帧",
                "reason": str(frame.get("reason") or "key_frame"),
            }
        )

    highlights = merged_points[:6]
    tldr = highlights[:4]
    recommended_actions = [f"回看章节 {idx + 1} 并整理关键证据。" for idx in range(min(3, len(chapters)))]

    return {
        "title": title,
        "tldr": tldr,
        "highlights": highlights,
        "recommended_actions": recommended_actions,
        "risk_or_pitfalls": ["关注上下文信息缺失导致的误解风险。"] if not transcript.strip() else [],
        "chapters": chapters,
        "timestamp_references": timestamp_references,
        "generated_by": "local_rule",
        "generated_at": utc_now_iso(),
    }


def normalize_outline_payload(payload: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(state.get("metadata") or {})
    frames = list(state.get("frames") or [])
    source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")
    fallback = _build_local_outline(state)

    title = str(payload.get("title") or fallback.get("title") or "Untitled Video")
    tldr = coerce_str_list(payload.get("tldr") or fallback.get("tldr"), limit=8)
    highlights = coerce_str_list(payload.get("highlights") or fallback.get("highlights"), limit=12)
    actions = coerce_str_list(
        payload.get("recommended_actions") or payload.get("action_items") or fallback.get("recommended_actions"),
        limit=12,
    )
    pitfalls = coerce_str_list(payload.get("risk_or_pitfalls") or fallback.get("risk_or_pitfalls"), limit=12)

    raw_chapters: Any = payload.get("chapters")
    if not isinstance(raw_chapters, list):
        sections = payload.get("sections")
        if isinstance(sections, list):
            converted: list[dict[str, Any]] = []
            for idx, section in enumerate(sections, start=1):
                if not isinstance(section, dict):
                    continue
                converted.append(
                    {
                        "chapter_no": idx,
                        "title": section.get("title") or section.get("heading") or f"Chapter {idx}",
                        "bullets": section.get("bullets") or [],
                        "summary": section.get("summary"),
                    }
                )
            raw_chapters = converted

    if not isinstance(raw_chapters, list) or not raw_chapters:
        raw_chapters = fallback.get("chapters") or []

    duration_s = estimate_duration_seconds(metadata, frames, max(1, len(raw_chapters)))
    chapter_span = max(1, duration_s // max(1, len(raw_chapters)))
    chapters: list[dict[str, Any]] = []
    for idx, chapter in enumerate(raw_chapters, start=1):
        if not isinstance(chapter, dict):
            continue
        chapter_no = coerce_int(chapter.get("chapter_no"), idx)
        chapter_title = str(chapter.get("title") or chapter.get("heading") or f"Chapter {chapter_no}")
        start_s = coerce_int(chapter.get("start_s"), (idx - 1) * chapter_span)
        end_s = coerce_int(
            chapter.get("end_s"),
            duration_s if idx == len(raw_chapters) else max(start_s, idx * chapter_span - 1),
        )
        if end_s < start_s:
            end_s = start_s
        bullets = coerce_str_list(chapter.get("bullets"), limit=8)
        summary = str(chapter.get("summary") or "").strip() or (bullets[0] if bullets else "（无小结）")
        key_terms = coerce_str_list(chapter.get("key_terms"), limit=8)

        code_snippets: list[dict[str, Any]] = []
        raw_snippets = chapter.get("code_snippets")
        if isinstance(raw_snippets, list):
            for s_idx, snippet in enumerate(raw_snippets, start=1):
                if not isinstance(snippet, dict):
                    continue
                body = str(snippet.get("snippet") or "").strip()
                if not body:
                    continue
                code_snippets.append(
                    {
                        "title": str(snippet.get("title") or f"Snippet {s_idx}"),
                        "language": str(snippet.get("language") or "text"),
                        "snippet": body[:1200],
                        "range_start_s": coerce_int(snippet.get("range_start_s"), start_s),
                        "range_end_s": coerce_int(snippet.get("range_end_s"), end_s),
                    }
                )

        anchor = str(chapter.get("anchor") or f"chapter-{chapter_no:02d}")
        chapters.append(
            {
                "chapter_no": chapter_no,
                "title": chapter_title,
                "anchor": anchor,
                "start_s": start_s,
                "end_s": end_s,
                "start_link": timestamp_link(source_url, start_s),
                "end_link": timestamp_link(source_url, end_s),
                "summary": summary,
                "bullets": bullets,
                "key_terms": key_terms,
                "code_snippets": code_snippets,
            }
        )

    refs_raw = payload.get("timestamp_references")
    timestamp_references: list[dict[str, Any]] = []
    if isinstance(refs_raw, list):
        for idx, ref in enumerate(refs_raw, start=1):
            if not isinstance(ref, dict):
                continue
            timestamp_references.append(
                {
                    "ts_s": coerce_int(ref.get("ts_s"), 0),
                    "label": str(ref.get("label") or f"Reference {idx}"),
                    "reason": str(ref.get("reason") or ""),
                }
            )
    if not timestamp_references:
        timestamp_references = list(fallback.get("timestamp_references") or [])

    if not tldr:
        tldr = highlights[:4] or coerce_str_list(fallback.get("tldr"), limit=4)
    if not highlights:
        highlights = coerce_str_list(fallback.get("highlights"), limit=8)
    if not actions:
        actions = coerce_str_list(fallback.get("recommended_actions"), limit=8)

    return {
        "title": title,
        "tldr": tldr,
        "highlights": highlights,
        "recommended_actions": actions,
        "risk_or_pitfalls": pitfalls,
        "chapters": chapters,
        "timestamp_references": timestamp_references,
        "generated_by": str(payload.get("generated_by") or fallback.get("generated_by") or "local_rule"),
        "generated_at": str(payload.get("generated_at") or fallback.get("generated_at") or utc_now_iso()),
    }


def _local_digest(state: dict[str, Any]) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    title = str(metadata.get("title") or state.get("title") or "Untitled Video")
    transcript = str(state.get("transcript") or "")
    outline = normalize_outline_payload(dict(state.get("outline") or {}), state)
    highlights = coerce_str_list(outline.get("highlights"), limit=8)
    tldr = coerce_str_list(outline.get("tldr"), limit=6)
    actions = coerce_str_list(outline.get("recommended_actions"), limit=8)

    if not highlights:
        highlights = collect_key_points_from_text(transcript, limit=6)
    if not highlights:
        highlights = ["未获取到有效字幕，以下内容基于标题、简介与评论区生成。"]
    if not tldr:
        tldr = highlights[:4]
    if not actions:
        actions = [f"复盘 {item}" for item in tldr[:3]]

    summary = transcript.strip()[:320] if transcript.strip() else f"该摘要基于视频元信息自动生成：{title}"
    code_blocks = collect_code_blocks(outline, {})
    refs = outline.get("timestamp_references")
    timestamp_refs = refs if isinstance(refs, list) else []

    return {
        "title": title,
        "summary": summary,
        "tldr": tldr,
        "highlights": highlights[:8],
        "action_items": actions,
        "code_blocks": code_blocks,
        "timestamp_references": timestamp_refs,
        "fallback_notes": ["LLM 摘要不可用，当前内容由本地规则降级生成。"],
        "generated_by": "local_rule",
        "generated_at": utc_now_iso(),
    }


def normalize_digest_payload(payload: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    fallback = _local_digest(state)
    title = str(payload.get("title") or fallback.get("title") or "Untitled Video")
    summary = str(payload.get("summary") or fallback.get("summary") or "").strip()
    tldr = coerce_str_list(payload.get("tldr") or fallback.get("tldr"), limit=8)
    highlights = coerce_str_list(payload.get("highlights") or fallback.get("highlights"), limit=12)
    action_items = coerce_str_list(
        payload.get("action_items") or payload.get("recommended_actions") or fallback.get("action_items"),
        limit=12,
    )
    fallback_notes = coerce_str_list(payload.get("fallback_notes") or fallback.get("fallback_notes"), limit=8)

    code_blocks_raw = payload.get("code_blocks")
    code_blocks: list[dict[str, Any]] = []
    if isinstance(code_blocks_raw, list):
        for idx, item in enumerate(code_blocks_raw, start=1):
            if not isinstance(item, dict):
                continue
            snippet = str(item.get("snippet") or "").strip()
            if not snippet:
                continue
            code_blocks.append(
                {
                    "title": str(item.get("title") or f"Snippet {idx}"),
                    "language": str(item.get("language") or "text"),
                    "snippet": snippet[:1200],
                    "range_start_s": coerce_int(item.get("range_start_s"), 0),
                    "range_end_s": coerce_int(item.get("range_end_s"), coerce_int(item.get("range_start_s"), 0)),
                }
            )
    if not code_blocks:
        fallback_blocks = fallback.get("code_blocks")
        if isinstance(fallback_blocks, list):
            for item in fallback_blocks:
                if isinstance(item, dict):
                    code_blocks.append(dict(item))

    refs_raw = payload.get("timestamp_references")
    timestamp_references: list[dict[str, Any]] = []
    if isinstance(refs_raw, list):
        for idx, ref in enumerate(refs_raw, start=1):
            if not isinstance(ref, dict):
                continue
            timestamp_references.append(
                {
                    "ts_s": coerce_int(ref.get("ts_s"), 0),
                    "label": str(ref.get("label") or f"Reference {idx}"),
                    "reason": str(ref.get("reason") or ""),
                }
            )
    if not timestamp_references:
        fallback_refs = fallback.get("timestamp_references")
        if isinstance(fallback_refs, list):
            for item in fallback_refs:
                if isinstance(item, dict):
                    timestamp_references.append(dict(item))

    if not tldr:
        tldr = highlights[:4] or coerce_str_list(fallback.get("tldr"), limit=4)
    if not highlights:
        highlights = coerce_str_list(fallback.get("highlights"), limit=8)
    if not action_items:
        action_items = coerce_str_list(fallback.get("action_items"), limit=8)

    return {
        "title": title,
        "summary": summary or "未生成摘要。",
        "tldr": tldr,
        "highlights": highlights,
        "action_items": action_items,
        "code_blocks": code_blocks,
        "timestamp_references": timestamp_references,
        "fallback_notes": fallback_notes,
        "generated_by": str(payload.get("generated_by") or fallback.get("generated_by") or "local_rule"),
        "generated_at": str(payload.get("generated_at") or fallback.get("generated_at") or utc_now_iso()),
    }


def _llm_failure_result(
    *,
    hard_required: bool,
    fail_on_provider_error: bool,
    include_frame_context: bool,
    media_input: str,
    llm_input_mode: str,
    llm_model: str,
    llm_temperature: float | None,
    llm_max_output_tokens: int | None,
    reason: str,
    error: str,
    error_kind: str | None = None,
) -> StepExecution:
    return StepExecution(
        status="failed",
        output={
            "provider": "gemini",
            "frame_context_used": include_frame_context,
            "media_input": media_input,
            "llm_input_mode": llm_input_mode,
            "model": llm_model,
            "temperature": llm_temperature,
            "max_output_tokens": llm_max_output_tokens,
            "hard_required": hard_required,
            "fail_on_provider_error": fail_on_provider_error,
        },
        reason=reason,
        error=error,
        error_kind=error_kind,
        degraded=True,
    )


async def step_llm_outline(
    ctx: PipelineContext,
    state: dict[str, Any],
    *,
    gemini_generate_fn: Callable[..., tuple[str | None, str]] = gemini_generate,
) -> StepExecution:
    metadata = dict(state.get("metadata") or {})
    transcript = str(state.get("transcript") or "")
    comments = dict(state.get("comments") or {})
    frames = list(state.get("frames") or [])
    media_path = str(state.get("media_path") or "")
    frame_paths = frame_paths_from_frames(frames, limit=max(1, ctx.settings.pipeline_max_frames))
    llm_input_mode = normalize_llm_input_mode(
        state.get("llm_input_mode") or getattr(ctx.settings, "pipeline_llm_input_mode", "auto")
    )
    llm_policy = dict(state.get("llm_policy") or {})
    hard_required = pipeline_llm_hard_required(ctx.settings, llm_policy)
    fail_on_provider_error = pipeline_llm_fail_on_provider_error(ctx.settings, llm_policy)

    llm_outline_policy = dict(llm_policy.get("outline") or {})
    llm_model = (
        str(llm_outline_policy.get("model") or llm_policy.get("model") or ctx.settings.gemini_outline_model).strip()
        or ctx.settings.gemini_outline_model
    )
    llm_temperature = coerce_float(
        llm_outline_policy.get("temperature"),
        coerce_float(llm_policy.get("temperature"), None),
    )
    llm_max_output_tokens = (
        coerce_int(
            llm_outline_policy.get("max_output_tokens"),
            coerce_int(llm_policy.get("max_output_tokens"), 0),
        )
        or None
    )

    title = str(metadata.get("title") or state.get("title") or "")
    source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")
    include_frame_context = bool(frames) and should_include_frame_prompt(ctx.settings)

    prompt_parts = [
        "为视频摘要生成严格 JSON 大纲。",
        "只返回 JSON，不要 Markdown，不要代码块围栏。",
        "所有面向读者的字段必须使用简体中文（专有名词、产品名、代码标识可保留英文）。",
        "顶层必填字段：title, tldr(array), highlights(array), recommended_actions(array), risk_or_pitfalls(array), chapters(array), timestamp_references(array)。",
        "chapter 对象必填：chapter_no, title, anchor, start_s, end_s, summary, bullets(array), key_terms(array), code_snippets(array)。",
        "code_snippets 项必填：title, language, snippet, range_start_s, range_end_s。",
        "内容风格：人类可读，避免空话，不要重复，不要编造无法从输入中确认的事实。",
        f"Title: {title}",
        f"Metadata: {json.dumps(jsonable(metadata), ensure_ascii=False)}",
        f"Transcript (truncated):\n{transcript[:9000]}",
        f"Comment Highlights:\n{build_comments_prompt_context(comments)}",
    ]
    if include_frame_context:
        prompt_parts.append(f"Frame Summaries (for richer grounding):\n{build_frames_prompt_context(frames, source_url)}")
    prompt = "\n\n".join(prompt_parts)

    generated, media_input = await asyncio.to_thread(
        gemini_generate_fn,
        ctx.settings,
        prompt,
        media_path=media_path,
        frame_paths=frame_paths,
        llm_input_mode=llm_input_mode,
        model=llm_model,
        temperature=llm_temperature,
        max_output_tokens=llm_max_output_tokens,
    )

    if generated:
        try:
            payload = json.loads(extract_json_object(generated))
            if isinstance(payload, dict):
                translated_to_zh = False
                if not outline_is_chinese(payload):
                    translated_payload = await asyncio.to_thread(
                        _translate_payload_to_chinese,
                        ctx.settings,
                        payload,
                        model=llm_model,
                        max_output_tokens=llm_max_output_tokens,
                        schema_label="outline",
                    )
                    if isinstance(translated_payload, dict):
                        payload = translated_payload
                        translated_to_zh = True
                outline = normalize_outline_payload(payload, state)
                outline["generated_by"] = "gemini"
                outline["generated_at"] = utc_now_iso()
                return StepExecution(
                    status="succeeded",
                    output={
                        "provider": "gemini",
                        "frame_context_used": include_frame_context,
                        "media_input": media_input,
                        "llm_input_mode": llm_input_mode,
                        "model": llm_model,
                        "temperature": llm_temperature,
                        "max_output_tokens": llm_max_output_tokens,
                        "translated_to_zh": translated_to_zh,
                        "hard_required": hard_required,
                        "fail_on_provider_error": fail_on_provider_error,
                    },
                    state_updates={"outline": outline},
                )
        except (json.JSONDecodeError, TypeError, ValueError):
            if hard_required or fail_on_provider_error:
                return _llm_failure_result(
                    hard_required=hard_required,
                    fail_on_provider_error=fail_on_provider_error,
                    include_frame_context=include_frame_context,
                    media_input=media_input,
                    llm_input_mode=llm_input_mode,
                    llm_model=llm_model,
                    llm_temperature=llm_temperature,
                    llm_max_output_tokens=llm_max_output_tokens,
                    reason="llm_output_invalid_json",
                    error="llm_output_invalid_json",
                )

    missing_api_key = not str(ctx.settings.gemini_api_key or "").strip()
    if hard_required or fail_on_provider_error:
        reason = "gemini_api_key_missing" if missing_api_key else "llm_provider_unavailable"
        return _llm_failure_result(
            hard_required=hard_required,
            fail_on_provider_error=fail_on_provider_error,
            include_frame_context=include_frame_context,
            media_input=media_input,
            llm_input_mode=llm_input_mode,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_output_tokens=llm_max_output_tokens,
            reason=reason,
            error=reason,
            error_kind="auth" if missing_api_key else None,
        )

    outline = _build_local_outline(state)
    return StepExecution(
        status="succeeded",
        output={
            "provider": "local_rule",
            "frame_context_used": include_frame_context,
            "media_input": media_input,
            "llm_input_mode": llm_input_mode,
            "model": llm_model,
            "temperature": llm_temperature,
            "max_output_tokens": llm_max_output_tokens,
            "hard_required": hard_required,
            "fail_on_provider_error": fail_on_provider_error,
        },
        state_updates={"outline": outline},
        reason="gemini_unavailable_or_invalid",
        degraded=True,
    )


async def step_llm_digest(
    ctx: PipelineContext,
    state: dict[str, Any],
    *,
    gemini_generate_fn: Callable[..., tuple[str | None, str]] = gemini_generate,
) -> StepExecution:
    metadata = dict(state.get("metadata") or {})
    comments = dict(state.get("comments") or {})
    frames = list(state.get("frames") or [])
    media_path = str(state.get("media_path") or "")
    frame_paths = frame_paths_from_frames(frames, limit=max(1, ctx.settings.pipeline_max_frames))
    llm_input_mode = normalize_llm_input_mode(
        state.get("llm_input_mode") or getattr(ctx.settings, "pipeline_llm_input_mode", "auto")
    )
    llm_policy = dict(state.get("llm_policy") or {})
    hard_required = pipeline_llm_hard_required(ctx.settings, llm_policy)
    fail_on_provider_error = pipeline_llm_fail_on_provider_error(ctx.settings, llm_policy)

    llm_digest_policy = dict(llm_policy.get("digest") or {})
    llm_model = (
        str(llm_digest_policy.get("model") or llm_policy.get("model") or ctx.settings.gemini_digest_model).strip()
        or ctx.settings.gemini_digest_model
    )
    llm_temperature = coerce_float(
        llm_digest_policy.get("temperature"),
        coerce_float(llm_policy.get("temperature"), None),
    )
    llm_max_output_tokens = (
        coerce_int(
            llm_digest_policy.get("max_output_tokens"),
            coerce_int(llm_policy.get("max_output_tokens"), 0),
        )
        or None
    )
    source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")
    include_frame_context = bool(frames) and should_include_frame_prompt(ctx.settings)

    outline = normalize_outline_payload(dict(state.get("outline") or {}), state)
    prompt_parts = [
        "基于输入内容生成面向人类阅读的摘要 JSON。",
        "只返回 JSON，不要 Markdown，不要代码块围栏。",
        "所有面向读者的字段必须使用简体中文（专有名词、产品名、代码标识可保留英文）。",
        "必填字段：title, summary, tldr(array), highlights(array), action_items(array), code_blocks(array), timestamp_references(array), fallback_notes(array)。",
        "summary 请控制在 120~220 字，直说结论，避免套话。",
        "tldr/highlights/action_items 每项要简短、可执行、去重。",
        "code_blocks 项结构：{title, language, snippet, range_start_s, range_end_s}。",
        "timestamp_references 项结构：{ts_s, label, reason}。",
        "内容风格：中文优先、证据导向、便于快速阅读。",
        f"Metadata:\n{json.dumps(jsonable(metadata), ensure_ascii=False)}",
        f"Outline:\n{json.dumps(jsonable(outline), ensure_ascii=False)}",
        f"Transcript (truncated):\n{str(state.get('transcript') or '')[:9000]}",
        f"Comment Highlights:\n{build_comments_prompt_context(comments)}",
    ]
    if include_frame_context:
        prompt_parts.append(
            f"Frame Summaries (optional grounding):\n{build_frames_prompt_context(frames, source_url)}"
        )
    prompt = "\n\n".join(prompt_parts)

    generated, media_input = await asyncio.to_thread(
        gemini_generate_fn,
        ctx.settings,
        prompt,
        media_path=media_path,
        frame_paths=frame_paths,
        llm_input_mode=llm_input_mode,
        model=llm_model,
        temperature=llm_temperature,
        max_output_tokens=llm_max_output_tokens,
    )

    if generated:
        try:
            payload = json.loads(extract_json_object(generated))
            if isinstance(payload, dict):
                translated_to_zh = False
                if not digest_is_chinese(payload):
                    translated_payload = await asyncio.to_thread(
                        _translate_payload_to_chinese,
                        ctx.settings,
                        payload,
                        model=llm_model,
                        max_output_tokens=llm_max_output_tokens,
                        schema_label="digest",
                    )
                    if isinstance(translated_payload, dict):
                        payload = translated_payload
                        translated_to_zh = True
                digest = normalize_digest_payload(payload, state)
                digest["generated_by"] = "gemini"
                digest["generated_at"] = utc_now_iso()
                return StepExecution(
                    status="succeeded",
                    output={
                        "provider": "gemini",
                        "frame_context_used": include_frame_context,
                        "media_input": media_input,
                        "llm_input_mode": llm_input_mode,
                        "model": llm_model,
                        "temperature": llm_temperature,
                        "max_output_tokens": llm_max_output_tokens,
                        "translated_to_zh": translated_to_zh,
                        "hard_required": hard_required,
                        "fail_on_provider_error": fail_on_provider_error,
                    },
                    state_updates={"digest": digest},
                )
        except (json.JSONDecodeError, TypeError, ValueError):
            if hard_required or fail_on_provider_error:
                return _llm_failure_result(
                    hard_required=hard_required,
                    fail_on_provider_error=fail_on_provider_error,
                    include_frame_context=include_frame_context,
                    media_input=media_input,
                    llm_input_mode=llm_input_mode,
                    llm_model=llm_model,
                    llm_temperature=llm_temperature,
                    llm_max_output_tokens=llm_max_output_tokens,
                    reason="llm_output_invalid_json",
                    error="llm_output_invalid_json",
                )

    missing_api_key = not str(ctx.settings.gemini_api_key or "").strip()
    if hard_required or fail_on_provider_error:
        reason = "gemini_api_key_missing" if missing_api_key else "llm_provider_unavailable"
        return _llm_failure_result(
            hard_required=hard_required,
            fail_on_provider_error=fail_on_provider_error,
            include_frame_context=include_frame_context,
            media_input=media_input,
            llm_input_mode=llm_input_mode,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_output_tokens=llm_max_output_tokens,
            reason=reason,
            error=reason,
            error_kind="auth" if missing_api_key else None,
        )

    digest = normalize_digest_payload(_local_digest(state), state)
    return StepExecution(
        status="succeeded",
        output={
            "provider": "local_rule",
            "frame_context_used": include_frame_context,
            "media_input": media_input,
            "llm_input_mode": llm_input_mode,
            "model": llm_model,
            "temperature": llm_temperature,
            "max_output_tokens": llm_max_output_tokens,
            "hard_required": hard_required,
            "fail_on_provider_error": fail_on_provider_error,
        },
        state_updates={"digest": digest},
        reason="gemini_unavailable_or_invalid",
        degraded=True,
    )
