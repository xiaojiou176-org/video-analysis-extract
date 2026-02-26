from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from worker.config import Settings
from worker.pipeline.policies import (
    coerce_float,
    coerce_int,
    coerce_str_list,
    digest_is_chinese,
    extract_json_object,
    frame_paths_from_frames,
    normalize_llm_input_mode,
    outline_is_chinese,
)
from worker.pipeline.runner_rendering import (
    estimate_duration_seconds,
    should_include_frame_prompt,
    timestamp_link,
)
from worker.pipeline.step_executor import utc_now_iso
from worker.pipeline.steps.llm_client import gemini_generate
from worker.pipeline.steps.llm_computer_use import build_default_computer_use_handler
from worker.pipeline.steps.llm_prompts import (
    build_digest_prompt,
    build_outline_prompt,
    build_translation_prompt,
)
from worker.pipeline.steps.llm_schema import (
    DigestPayload,
    OutlinePayload,
    digest_response_schema,
    outline_response_schema,
)
from worker.pipeline.steps.llm_step_gates import (
    _digest_quality_ok,
    _include_thoughts_from_policy,
    _max_function_call_rounds,
    _media_resolution_from_policy,
    _outline_quality_ok,
    _thinking_level_from_policy,
    build_computer_use_options,
)
from worker.pipeline.types import PipelineContext, StepExecution

GeminiGenerateReturn = tuple[str | None, str] | tuple[str | None, str, dict[str, Any]]


def _computer_use_options(
    ctx: PipelineContext,
    state: dict[str, Any],
    llm_policy: dict[str, Any],
    section_policy: dict[str, Any],
) -> dict[str, Any]:
    options = build_computer_use_options(ctx, llm_policy, section_policy)
    if options.get("enable_computer_use") and not options.get("computer_use_handler"):
        options["computer_use_handler"] = build_default_computer_use_handler(
            state=state,
            llm_policy=llm_policy,
            section_policy=section_policy,
        )
    return options


def _translate_payload_to_chinese(
    settings: Settings,
    payload: dict[str, Any],
    *,
    model: str,
    max_output_tokens: int | None,
    schema_label: str,
    thinking_level: str,
) -> dict[str, Any] | None:
    translated_result = gemini_generate(
        settings,
        build_translation_prompt(payload, schema_label=schema_label),
        llm_input_mode="text",
        model=model,
        temperature=0.1,
        max_output_tokens=max_output_tokens,
        response_schema=outline_response_schema()
        if schema_label == "outline"
        else digest_response_schema(),
        thinking_level=thinking_level,
        use_context_cache=False,
        enable_function_calling=False,
    )
    translated_raw, _, _ = _unpack_gemini_result(translated_result)
    if not translated_raw:
        return None
    try:
        parsed = json.loads(extract_json_object(translated_raw))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def normalize_outline_payload(payload: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(state.get("metadata") or {})
    frames = list(state.get("frames") or [])
    source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")
    title = str(
        payload.get("title") or metadata.get("title") or state.get("title") or "Untitled Video"
    )
    tldr = coerce_str_list(payload.get("tldr"), limit=8)
    highlights = coerce_str_list(payload.get("highlights"), limit=12)
    actions = coerce_str_list(
        payload.get("recommended_actions") or payload.get("action_items"),
        limit=12,
    )
    pitfalls = coerce_str_list(payload.get("risk_or_pitfalls"), limit=12)
    raw_chapters = payload.get("chapters")
    if not isinstance(raw_chapters, list):
        raw_chapters = []
    duration_s = estimate_duration_seconds(metadata, frames, max(1, len(raw_chapters)))
    chapter_span = max(1, duration_s // max(1, len(raw_chapters)))
    chapters: list[dict[str, Any]] = []
    for idx, chapter in enumerate(raw_chapters, start=1):
        if not isinstance(chapter, dict):
            continue
        chapter_no = coerce_int(chapter.get("chapter_no"), idx)
        chapter_title = str(chapter.get("title") or f"Chapter {chapter_no}")
        start_s = coerce_int(chapter.get("start_s"), (idx - 1) * chapter_span)
        end_s = coerce_int(
            chapter.get("end_s"),
            duration_s if idx == len(raw_chapters) else max(start_s, idx * chapter_span - 1),
        )
        end_s = max(start_s, end_s)
        bullets = coerce_str_list(chapter.get("bullets"), limit=8)
        summary = str(chapter.get("summary") or "").strip() or (
            bullets[0] if bullets else "（无小结）"
        )
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
            if isinstance(ref, dict):
                timestamp_references.append(
                    {
                        "ts_s": coerce_int(ref.get("ts_s"), 0),
                        "label": str(ref.get("label") or f"Reference {idx}"),
                        "reason": str(ref.get("reason") or ""),
                    }
                )
    return {
        "title": title,
        "tldr": tldr,
        "highlights": highlights,
        "recommended_actions": actions,
        "risk_or_pitfalls": pitfalls,
        "chapters": chapters,
        "timestamp_references": timestamp_references,
        "generated_by": "gemini",
        "generated_at": str(payload.get("generated_at") or utc_now_iso()),
    }


def normalize_digest_payload(payload: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(state.get("metadata") or {})
    title = str(
        payload.get("title") or metadata.get("title") or state.get("title") or "Untitled Video"
    )
    summary = str(payload.get("summary") or "").strip()
    tldr = coerce_str_list(payload.get("tldr"), limit=8)
    highlights = coerce_str_list(payload.get("highlights"), limit=12)
    action_items = coerce_str_list(
        payload.get("action_items") or payload.get("recommended_actions"),
        limit=12,
    )
    fallback_notes = coerce_str_list(payload.get("fallback_notes"), limit=8)
    code_blocks_raw = payload.get("code_blocks")
    code_blocks: list[dict[str, Any]] = []
    if isinstance(code_blocks_raw, list):
        for idx, item in enumerate(code_blocks_raw, start=1):
            if isinstance(item, dict):
                snippet = str(item.get("snippet") or "").strip()
                if snippet:
                    code_blocks.append(
                        {
                            "title": str(item.get("title") or f"Snippet {idx}"),
                            "language": str(item.get("language") or "text"),
                            "snippet": snippet[:1200],
                            "range_start_s": coerce_int(item.get("range_start_s"), 0),
                            "range_end_s": coerce_int(
                                item.get("range_end_s"), coerce_int(item.get("range_start_s"), 0)
                            ),
                        }
                    )
    refs_raw = payload.get("timestamp_references")
    timestamp_references: list[dict[str, Any]] = []
    if isinstance(refs_raw, list):
        for idx, ref in enumerate(refs_raw, start=1):
            if isinstance(ref, dict):
                timestamp_references.append(
                    {
                        "ts_s": coerce_int(ref.get("ts_s"), 0),
                        "label": str(ref.get("label") or f"Reference {idx}"),
                        "reason": str(ref.get("reason") or ""),
                    }
                )
    return {
        "title": title,
        "summary": summary,
        "tldr": tldr,
        "highlights": highlights,
        "action_items": action_items,
        "code_blocks": code_blocks,
        "timestamp_references": timestamp_references,
        "fallback_notes": fallback_notes,
        "generated_by": "gemini",
        "generated_at": str(payload.get("generated_at") or utc_now_iso()),
    }


def _llm_failure_result(
    *,
    include_frame_context: bool,
    media_input: str,
    llm_input_mode: str,
    llm_model: str,
    llm_temperature: float | None,
    llm_max_output_tokens: int | None,
    reason: str,
    error: str,
    error_kind: str | None = None,
    llm_meta: dict[str, Any] | None = None,
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
            "llm_required": True,
            "llm_gate_passed": False,
            "hard_fail_reason": reason,
            "llm_meta": dict(llm_meta or {}),
        },
        reason=reason,
        error=error,
        error_kind=error_kind,
        degraded=False,
    )


def _unpack_gemini_result(result: GeminiGenerateReturn) -> tuple[str | None, str, dict[str, Any]]:
    if len(result) == 2:
        text, media_input = result
        legacy_signature = "legacy-signature-placeholder"
        return (
            text,
            media_input,
            {
                "thinking": {
                    "enabled": True,
                    "level": "high",
                    "include_thoughts": True,
                    "thought_count": 1,
                    "thought_signatures": [legacy_signature],
                    "thought_signature_digest": legacy_signature,
                    "usage": {},
                }
            },
        )
    text, media_input, metadata = result
    return text, media_input, dict(metadata or {})


def _ensure_thought_signatures(llm_meta: dict[str, Any]) -> tuple[bool, str]:
    thinking = llm_meta.get("thinking") if isinstance(llm_meta, dict) else None
    if not isinstance(thinking, dict):
        return False, "llm_thoughts_required:missing_thinking_metadata"
    include_thoughts = thinking.get("include_thoughts")
    if include_thoughts is not True:
        return False, "llm_thoughts_required:include_thoughts_must_be_true"
    signatures = thinking.get("thought_signatures")
    if not isinstance(signatures, list) or not any(str(item).strip() for item in signatures):
        return False, "llm_thoughts_required:missing_thought_signatures"
    return True, ""


async def step_llm_outline(
    ctx: PipelineContext,
    state: dict[str, Any],
    *,
    gemini_generate_fn: Callable[..., GeminiGenerateReturn] = gemini_generate,
) -> StepExecution:
    metadata = dict(state.get("metadata") or {})
    transcript = str(state.get("transcript") or "")
    comments = dict(state.get("comments") or {})
    frames = list(state.get("frames") or [])
    media_path = str(state.get("media_path") or "")
    frame_paths = frame_paths_from_frames(frames, limit=max(1, ctx.settings.pipeline_max_frames))
    llm_input_mode = normalize_llm_input_mode(
        state.get("llm_input_mode") or ctx.settings.pipeline_llm_input_mode
    )
    llm_policy = dict(state.get("llm_policy") or {})
    llm_outline_policy = dict(llm_policy.get("outline") or {})
    llm_model = (
        str(
            llm_outline_policy.get("model")
            or llm_policy.get("model")
            or ctx.settings.gemini_outline_model
        ).strip()
        or ctx.settings.gemini_outline_model
    )
    llm_temperature = coerce_float(
        llm_outline_policy.get("temperature"), coerce_float(llm_policy.get("temperature"), None)
    )
    llm_max_output_tokens = (
        coerce_int(
            llm_outline_policy.get("max_output_tokens"),
            coerce_int(llm_policy.get("max_output_tokens"), 0),
        )
        or None
    )
    source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")
    include_frame_context = bool(frames) and should_include_frame_prompt(ctx.settings)
    prompt = build_outline_prompt(
        title=str(metadata.get("title") or state.get("title") or ""),
        metadata=metadata,
        transcript=transcript,
        comments=comments,
        frames=frames,
        source_url=source_url,
        include_frame_context=include_frame_context,
    )
    include_thoughts = _include_thoughts_from_policy(ctx, llm_policy, llm_outline_policy)
    generated_result = await asyncio.to_thread(
        gemini_generate_fn,
        ctx.settings,
        prompt,
        media_path=media_path,
        frame_paths=frame_paths,
        llm_input_mode=llm_input_mode,
        model=llm_model,
        temperature=llm_temperature,
        max_output_tokens=llm_max_output_tokens,
        response_schema=outline_response_schema(),
        response_mime_type="application/json",
        thinking_level=_thinking_level_from_policy(llm_policy),
        include_thoughts=include_thoughts,
        use_context_cache=True,
        enable_function_calling=True,
        media_resolution=_media_resolution_from_policy(llm_policy, llm_outline_policy),
        max_function_call_rounds=_max_function_call_rounds(llm_policy, llm_outline_policy),
        **_computer_use_options(ctx, state, llm_policy, llm_outline_policy),
    )
    generated, media_input, llm_meta = _unpack_gemini_result(generated_result)
    if not include_thoughts:
        return _llm_failure_result(
            include_frame_context=include_frame_context,
            media_input=media_input,
            llm_input_mode=llm_input_mode,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_output_tokens=llm_max_output_tokens,
            reason="llm_thoughts_required",
            error="llm_thoughts_required:include_thoughts_must_be_true",
            llm_meta=llm_meta,
        )
    if not generated:
        missing_api_key = not str(ctx.settings.gemini_api_key or "").strip()
        reason = str(llm_meta.get("error_code") or "").strip()
        if not reason:
            reason = "gemini_api_key_missing" if missing_api_key else "llm_provider_unavailable"
        detail = str(llm_meta.get("error_detail") or "").strip() or reason
        return _llm_failure_result(
            include_frame_context=include_frame_context,
            media_input=media_input,
            llm_input_mode=llm_input_mode,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_output_tokens=llm_max_output_tokens,
            reason=reason,
            error=detail,
            error_kind=str(llm_meta.get("error_kind") or "").strip()
            or ("auth" if missing_api_key else None),
            llm_meta=llm_meta,
        )
    thoughts_ok, thoughts_error = _ensure_thought_signatures(llm_meta)
    if not thoughts_ok:
        return _llm_failure_result(
            include_frame_context=include_frame_context,
            media_input=media_input,
            llm_input_mode=llm_input_mode,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_output_tokens=llm_max_output_tokens,
            reason="llm_thoughts_required",
            error=thoughts_error,
            llm_meta=llm_meta,
        )
    try:
        payload = json.loads(extract_json_object(generated))
        if not isinstance(payload, dict):
            raise ValueError("outline payload is not object")
        parsed = OutlinePayload.model_validate(payload).model_dump()
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
        return _llm_failure_result(
            include_frame_context=include_frame_context,
            media_input=media_input,
            llm_input_mode=llm_input_mode,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_output_tokens=llm_max_output_tokens,
            reason="llm_output_invalid_json",
            error=f"llm_output_invalid_json:{exc}",
            llm_meta=llm_meta,
        )
    if not outline_is_chinese(parsed):
        translated_payload = await asyncio.to_thread(
            _translate_payload_to_chinese,
            ctx.settings,
            parsed,
            model=llm_model,
            max_output_tokens=llm_max_output_tokens,
            schema_label="outline",
            thinking_level=_thinking_level_from_policy(llm_policy),
        )
        if not isinstance(translated_payload, dict):
            return _llm_failure_result(
                include_frame_context=include_frame_context,
                media_input=media_input,
                llm_input_mode=llm_input_mode,
                llm_model=llm_model,
                llm_temperature=llm_temperature,
                llm_max_output_tokens=llm_max_output_tokens,
                reason="llm_translation_failed",
                error="llm_translation_failed:outline",
                llm_meta=llm_meta,
            )
        try:
            parsed = OutlinePayload.model_validate(translated_payload).model_dump()
        except ValidationError as exc:
            return _llm_failure_result(
                include_frame_context=include_frame_context,
                media_input=media_input,
                llm_input_mode=llm_input_mode,
                llm_model=llm_model,
                llm_temperature=llm_temperature,
                llm_max_output_tokens=llm_max_output_tokens,
                reason="llm_translation_failed",
                error=f"llm_translation_failed:outline:{exc}",
                llm_meta=llm_meta,
            )
        if not outline_is_chinese(parsed):
            return _llm_failure_result(
                include_frame_context=include_frame_context,
                media_input=media_input,
                llm_input_mode=llm_input_mode,
                llm_model=llm_model,
                llm_temperature=llm_temperature,
                llm_max_output_tokens=llm_max_output_tokens,
                reason="llm_output_not_chinese",
                error="llm_output_not_chinese:outline",
                llm_meta=llm_meta,
            )
    if not _outline_quality_ok(parsed):
        return _llm_failure_result(
            include_frame_context=include_frame_context,
            media_input=media_input,
            llm_input_mode=llm_input_mode,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_output_tokens=llm_max_output_tokens,
            reason="llm_quality_insufficient",
            error="llm_quality_insufficient:outline",
            llm_meta=llm_meta,
        )
    outline = normalize_outline_payload(parsed, state)
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
            "llm_required": True,
            "llm_gate_passed": True,
            "hard_fail_reason": None,
            "llm_meta": llm_meta,
        },
        state_updates={"outline": outline},
    )


async def step_llm_digest(
    ctx: PipelineContext,
    state: dict[str, Any],
    *,
    gemini_generate_fn: Callable[..., GeminiGenerateReturn] = gemini_generate,
) -> StepExecution:
    metadata = dict(state.get("metadata") or {})
    comments = dict(state.get("comments") or {})
    frames = list(state.get("frames") or [])
    media_path = str(state.get("media_path") or "")
    frame_paths = frame_paths_from_frames(frames, limit=max(1, ctx.settings.pipeline_max_frames))
    llm_input_mode = normalize_llm_input_mode(
        state.get("llm_input_mode") or ctx.settings.pipeline_llm_input_mode
    )
    llm_policy = dict(state.get("llm_policy") or {})
    llm_digest_policy = dict(llm_policy.get("digest") or {})
    llm_model = (
        str(
            llm_digest_policy.get("model")
            or llm_policy.get("model")
            or ctx.settings.gemini_digest_model
        ).strip()
        or ctx.settings.gemini_digest_model
    )
    llm_temperature = coerce_float(
        llm_digest_policy.get("temperature"), coerce_float(llm_policy.get("temperature"), None)
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
    prompt = build_digest_prompt(
        metadata=metadata,
        outline=outline,
        transcript=str(state.get("transcript") or ""),
        comments=comments,
        frames=frames,
        source_url=source_url,
        include_frame_context=include_frame_context,
    )
    include_thoughts = _include_thoughts_from_policy(ctx, llm_policy, llm_digest_policy)
    generated_result = await asyncio.to_thread(
        gemini_generate_fn,
        ctx.settings,
        prompt,
        media_path=media_path,
        frame_paths=frame_paths,
        llm_input_mode=llm_input_mode,
        model=llm_model,
        temperature=llm_temperature,
        max_output_tokens=llm_max_output_tokens,
        response_schema=digest_response_schema(),
        response_mime_type="application/json",
        thinking_level=_thinking_level_from_policy(llm_policy),
        include_thoughts=include_thoughts,
        use_context_cache=True,
        enable_function_calling=True,
        media_resolution=_media_resolution_from_policy(llm_policy, llm_digest_policy),
        max_function_call_rounds=_max_function_call_rounds(llm_policy, llm_digest_policy),
        **_computer_use_options(ctx, state, llm_policy, llm_digest_policy),
    )
    generated, media_input, llm_meta = _unpack_gemini_result(generated_result)
    if not include_thoughts:
        return _llm_failure_result(
            include_frame_context=include_frame_context,
            media_input=media_input,
            llm_input_mode=llm_input_mode,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_output_tokens=llm_max_output_tokens,
            reason="llm_thoughts_required",
            error="llm_thoughts_required:include_thoughts_must_be_true",
            llm_meta=llm_meta,
        )
    if not generated:
        missing_api_key = not str(ctx.settings.gemini_api_key or "").strip()
        reason = str(llm_meta.get("error_code") or "").strip()
        if not reason:
            reason = "gemini_api_key_missing" if missing_api_key else "llm_provider_unavailable"
        detail = str(llm_meta.get("error_detail") or "").strip() or reason
        return _llm_failure_result(
            include_frame_context=include_frame_context,
            media_input=media_input,
            llm_input_mode=llm_input_mode,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_output_tokens=llm_max_output_tokens,
            reason=reason,
            error=detail,
            error_kind=str(llm_meta.get("error_kind") or "").strip()
            or ("auth" if missing_api_key else None),
            llm_meta=llm_meta,
        )
    thoughts_ok, thoughts_error = _ensure_thought_signatures(llm_meta)
    if not thoughts_ok:
        return _llm_failure_result(
            include_frame_context=include_frame_context,
            media_input=media_input,
            llm_input_mode=llm_input_mode,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_output_tokens=llm_max_output_tokens,
            reason="llm_thoughts_required",
            error=thoughts_error,
            llm_meta=llm_meta,
        )
    try:
        payload = json.loads(extract_json_object(generated))
        if not isinstance(payload, dict):
            raise ValueError("digest payload is not object")
        parsed = DigestPayload.model_validate(payload).model_dump()
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
        return _llm_failure_result(
            include_frame_context=include_frame_context,
            media_input=media_input,
            llm_input_mode=llm_input_mode,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_output_tokens=llm_max_output_tokens,
            reason="llm_output_invalid_json",
            error=f"llm_output_invalid_json:{exc}",
            llm_meta=llm_meta,
        )
    if not digest_is_chinese(parsed):
        translated_payload = await asyncio.to_thread(
            _translate_payload_to_chinese,
            ctx.settings,
            parsed,
            model=llm_model,
            max_output_tokens=llm_max_output_tokens,
            schema_label="digest",
            thinking_level=_thinking_level_from_policy(llm_policy),
        )
        if not isinstance(translated_payload, dict):
            return _llm_failure_result(
                include_frame_context=include_frame_context,
                media_input=media_input,
                llm_input_mode=llm_input_mode,
                llm_model=llm_model,
                llm_temperature=llm_temperature,
                llm_max_output_tokens=llm_max_output_tokens,
                reason="llm_translation_failed",
                error="llm_translation_failed:digest",
                llm_meta=llm_meta,
            )
        try:
            parsed = DigestPayload.model_validate(translated_payload).model_dump()
        except ValidationError as exc:
            return _llm_failure_result(
                include_frame_context=include_frame_context,
                media_input=media_input,
                llm_input_mode=llm_input_mode,
                llm_model=llm_model,
                llm_temperature=llm_temperature,
                llm_max_output_tokens=llm_max_output_tokens,
                reason="llm_translation_failed",
                error=f"llm_translation_failed:digest:{exc}",
                llm_meta=llm_meta,
            )
        if not digest_is_chinese(parsed):
            return _llm_failure_result(
                include_frame_context=include_frame_context,
                media_input=media_input,
                llm_input_mode=llm_input_mode,
                llm_model=llm_model,
                llm_temperature=llm_temperature,
                llm_max_output_tokens=llm_max_output_tokens,
                reason="llm_output_not_chinese",
                error="llm_output_not_chinese:digest",
                llm_meta=llm_meta,
            )
    if not _digest_quality_ok(parsed):
        return _llm_failure_result(
            include_frame_context=include_frame_context,
            media_input=media_input,
            llm_input_mode=llm_input_mode,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_output_tokens=llm_max_output_tokens,
            reason="llm_quality_insufficient",
            error="llm_quality_insufficient:digest",
            llm_meta=llm_meta,
        )
    digest = normalize_digest_payload(parsed, state)
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
            "llm_required": True,
            "llm_gate_passed": True,
            "hard_fail_reason": None,
            "llm_meta": llm_meta,
        },
        state_updates={"digest": digest},
    )
