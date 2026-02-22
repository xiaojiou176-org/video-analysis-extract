from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Any, Callable

from worker.config import Settings
from worker.pipeline.policies import normalize_llm_input_mode
from worker.pipeline.types import LLMInputMode
from worker.pipeline.steps.llm_prompts import build_evidence_citations, select_supporting_frames

_CACHE_NAME_BY_KEY: dict[str, str] = {}
_ALLOWED_MEDIA_RESOLUTION = {"low", "medium", "high"}


def _cache_key(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8", errors="ignore"))
        digest.update(b"\0")
    return digest.hexdigest()


def _part_is_thought(part: Any) -> bool:
    thought_flag = getattr(part, "thought", None)
    if isinstance(thought_flag, bool):
        return thought_flag
    if isinstance(part, dict):
        raw = part.get("thought")
        if isinstance(raw, bool):
            return raw
    return False


def _extract_response_text(response: Any) -> str | None:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    candidates = getattr(response, "candidates", None)
    if isinstance(candidates, list):
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None)
            if not isinstance(parts, list):
                continue
            chunks: list[str] = []
            for part in parts:
                if _part_is_thought(part):
                    continue
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    chunks.append(part_text.strip())
            if chunks:
                return "\n".join(chunks)
    return None


def _normalize_media_resolution(value: Any, *, default: str = "medium") -> str:
    text = str(value or "").strip().lower()
    if text in _ALLOWED_MEDIA_RESOLUTION:
        return text
    return default


def _normalize_media_resolution_policy(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        base = _normalize_media_resolution(value.get("default"), default="medium")
        return {
            "default": base,
            "frame": _normalize_media_resolution(value.get("frame"), default=base),
            "image": _normalize_media_resolution(value.get("image"), default=base),
            "pdf": _normalize_media_resolution(value.get("pdf"), default=base),
        }
    base = _normalize_media_resolution(value, default="medium")
    return {"default": base, "frame": base, "image": base, "pdf": base}


def _part_media_resolution(policy: dict[str, str], *, mime_type: str, kind: str | None = None) -> str:
    if kind and kind in policy:
        return policy[kind]
    mime = (mime_type or "").strip().lower()
    if mime.startswith("image/"):
        return policy.get("image", policy["default"])
    if mime == "application/pdf":
        return policy.get("pdf", policy["default"])
    return policy["default"]


def _part_from_bytes(genai_types: Any, *, data: bytes, mime_type: str, media_resolution: str) -> Any:
    part_cls = getattr(genai_types, "Part", None)
    if part_cls is None:
        return {"mime_type": mime_type, "data": data, "media_resolution": media_resolution}

    for kwargs in (
        {"data": data, "mime_type": mime_type, "media_resolution": media_resolution},
        {
            "data": data,
            "mime_type": mime_type,
            "config": {"media_resolution": media_resolution.upper()},
        },
        {"data": data, "mime_type": mime_type},
    ):
        try:
            return part_cls.from_bytes(**kwargs)
        except Exception:
            continue
    return {"mime_type": mime_type, "data": data, "media_resolution": media_resolution}


def _build_frame_parts(
    genai_types: Any,
    frame_paths: list[str],
    *,
    limit: int,
    media_resolution_policy: dict[str, str],
) -> list[Any]:
    parts: list[Any] = []
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
        media_resolution = _part_media_resolution(
            media_resolution_policy,
            mime_type=mime_type,
            kind="frame",
        )
        parts.append(
            _part_from_bytes(
                genai_types,
                data=data,
                mime_type=mime_type,
                media_resolution=media_resolution,
            )
        )
    return parts


def _thinking_config(genai_types: Any, *, thinking_level: str, include_thoughts: bool) -> Any:
    level = (thinking_level or "high").strip().lower()
    if level not in {"minimal", "low", "medium", "high"}:
        level = "high"
    return genai_types.ThinkingConfig(
        thinking_level=level.upper(),
        include_thoughts=include_thoughts,
    )


def _create_cached_content(
    client: Any,
    genai_types: Any,
    *,
    model: str,
    prompt: str,
    cache_key: str,
    ttl_seconds: int,
) -> str | None:
    cached_name = _CACHE_NAME_BY_KEY.get(cache_key)
    if cached_name:
        return cached_name

    ttl_seconds = max(300, int(ttl_seconds))
    cached = client.caches.create(
        model=model,
        config=genai_types.CreateCachedContentConfig(
            contents=[prompt],
            ttl=f"{ttl_seconds}s",
            system_instruction=(
                "Use cached context as the single source of truth and return strict JSON only."
            ),
        ),
    )
    name = getattr(cached, "name", None)
    if isinstance(name, str) and name.strip():
        _CACHE_NAME_BY_KEY[cache_key] = name
        return name
    return None


def _extract_function_calls(response: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    candidates = getattr(response, "candidates", None)
    if not isinstance(candidates, list):
        return calls
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None)
        if not isinstance(parts, list):
            continue
        for part in parts:
            function_call = getattr(part, "function_call", None)
            if function_call is None and isinstance(part, dict):
                function_call = part.get("function_call")
            if function_call is None:
                continue

            if isinstance(function_call, dict):
                name = str(function_call.get("name") or "").strip()
                args = function_call.get("args")
            else:
                name = str(getattr(function_call, "name", "") or "").strip()
                args = getattr(function_call, "args", None)
            if not name:
                continue

            if not isinstance(args, dict):
                args = {}
            calls.append({"name": name, "args": dict(args)})
    return calls


def _execute_function_call(
    allowed_tools: dict[str, Callable[..., dict[str, Any]]],
    *,
    tool_name: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    tool = allowed_tools.get(tool_name)
    if tool is None:
        return {
            "name": tool_name,
            "status": "blocked",
            "response": {"error": f"tool_not_allowed:{tool_name}"},
        }
    try:
        response = tool(**args)
    except Exception as exc:
        return {
            "name": tool_name,
            "status": "failed",
            "response": {"error": f"tool_execution_failed:{tool_name}", "detail": str(exc)},
        }
    if not isinstance(response, dict):
        response = {"result": response}
    return {"name": tool_name, "status": "ok", "response": response}


def _extract_primary_candidate_content(response: Any) -> Any | None:
    candidates = getattr(response, "candidates", None)
    if isinstance(candidates, list) and candidates:
        return getattr(candidates[0], "content", None)
    return None


def _build_function_response_part(genai_types: Any, *, name: str, payload: dict[str, Any]) -> Any:
    part_cls = getattr(genai_types, "Part", None)
    if part_cls is not None:
        try:
            return part_cls.from_function_response(
                name=name,
                response=payload,
            )
        except Exception:
            pass
    return {"function_response": {"name": name, "response": payload}}


def _build_function_response_content(genai_types: Any, responses: list[dict[str, Any]]) -> Any:
    parts = [
        _build_function_response_part(genai_types, name=item["name"], payload=item["response"])
        for item in responses
    ]

    content_cls = getattr(genai_types, "Content", None)
    if content_cls is not None:
        for role in ("tool", "user"):
            try:
                return content_cls(role=role, parts=parts)
            except Exception:
                continue
    return {"role": "tool", "parts": parts}


def _collect_thought_metadata(response: Any) -> dict[str, Any]:
    thought_count = 0
    thought_signatures: list[str] = []

    candidates = getattr(response, "candidates", None)
    if isinstance(candidates, list):
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None)
            if not isinstance(parts, list):
                continue
            for part in parts:
                if not _part_is_thought(part):
                    continue
                thought_count += 1
                signature = getattr(part, "signature", None)
                if signature is None:
                    signature = getattr(part, "thought_signature", None)
                if isinstance(signature, bytes):
                    thought_signatures.append(signature.hex())
                elif isinstance(signature, str) and signature.strip():
                    thought_signatures.append(signature.strip())
                else:
                    text = getattr(part, "text", None)
                    if isinstance(text, str) and text.strip():
                        thought_signatures.append(
                            hashlib.sha256(text.strip().encode("utf-8", errors="ignore")).hexdigest()
                        )

    usage = getattr(response, "usage_metadata", None)
    usage_payload: dict[str, Any] = {}
    if usage is not None:
        for key in (
            "prompt_token_count",
            "candidates_token_count",
            "total_token_count",
            "thoughts_token_count",
        ):
            value = getattr(usage, key, None)
            if isinstance(value, int):
                usage_payload[key] = value

    deduped_signatures = list(dict.fromkeys(thought_signatures))
    signature_digest = ""
    if deduped_signatures:
        signature_digest = hashlib.sha256(
            "|".join(deduped_signatures).encode("utf-8", errors="ignore")
        ).hexdigest()

    return {
        "thought_count": thought_count,
        "thought_signatures": deduped_signatures,
        "thought_signature_digest": signature_digest or None,
        "usage": usage_payload,
    }


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
    response_schema: dict[str, Any] | None = None,
    response_mime_type: str | None = "application/json",
    thinking_level: str | None = None,
    include_thoughts: bool | None = None,
    use_context_cache: bool = True,
    enable_function_calling: bool = True,
    media_resolution: dict[str, Any] | str | None = None,
    max_function_call_rounds: int = 2,
) -> tuple[str | None, str, dict[str, Any]]:
    if not settings.gemini_api_key:
        return None, "none", {}

    try:
        from google import genai  # type: ignore
        from google.genai import types as genai_types  # type: ignore
    except Exception:
        return None, "none", {}

    model_name = str(model or settings.gemini_model).strip() or settings.gemini_model
    normalized_mode = normalize_llm_input_mode(llm_input_mode)
    normalized_media_path = str(media_path or "").strip()
    normalized_frame_paths = list(frame_paths or [])

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
    except Exception:
        return None, "none", {}

    effective_thinking_level = str(thinking_level or settings.gemini_thinking_level or "high")
    effective_include_thoughts = (
        settings.gemini_include_thoughts if include_thoughts is None else bool(include_thoughts)
    )
    effective_media_resolution = _normalize_media_resolution_policy(media_resolution)
    max_function_call_rounds = max(0, int(max_function_call_rounds))
    allowed_tools: dict[str, Callable[..., dict[str, Any]]] = {
        "select_supporting_frames": select_supporting_frames,
        "build_evidence_citations": build_evidence_citations,
    }
    config_kwargs: dict[str, Any] = {
        "thinking_config": _thinking_config(
            genai_types,
            thinking_level=effective_thinking_level,
            include_thoughts=effective_include_thoughts,
        ),
    }
    if temperature is not None:
        config_kwargs["temperature"] = temperature
    if max_output_tokens is not None:
        config_kwargs["max_output_tokens"] = max_output_tokens
    if response_mime_type:
        config_kwargs["response_mime_type"] = response_mime_type
    if response_schema:
        config_kwargs["response_schema"] = response_schema
    if enable_function_calling:
        config_kwargs["tools"] = [select_supporting_frames, build_evidence_citations]

    def _generate(contents: Any, *, cached_content: str | None = None) -> Any:
        kwargs = dict(config_kwargs)
        if cached_content:
            kwargs["cached_content"] = cached_content
        config = genai_types.GenerateContentConfig(**kwargs)
        return client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )

    def _generate_with_function_loop(
        contents: Any,
        *,
        cached_content: str | None = None,
    ) -> tuple[str | None, dict[str, Any]]:
        thought_count = 0
        thought_signatures: list[str] = []
        usage_rollup: dict[str, int] = {}
        call_trace: list[dict[str, Any]] = []
        rounds = 0
        termination_reason = "no_response"
        conversation = list(contents) if isinstance(contents, list) else [contents]

        while True:
            rounds += 1
            response = _generate(conversation, cached_content=cached_content)
            thought_meta = _collect_thought_metadata(response)
            thought_count += int(thought_meta.get("thought_count") or 0)
            thought_signatures.extend(list(thought_meta.get("thought_signatures") or []))
            for key, value in dict(thought_meta.get("usage") or {}).items():
                if isinstance(value, int):
                    usage_rollup[key] = usage_rollup.get(key, 0) + value

            text = _extract_response_text(response)
            if text:
                termination_reason = "text"
                break

            if not enable_function_calling:
                termination_reason = "function_calling_disabled"
                break

            function_calls = _extract_function_calls(response)
            if not function_calls:
                termination_reason = "no_function_call"
                break
            if rounds > max_function_call_rounds:
                termination_reason = "max_function_call_rounds_reached"
                break

            tool_responses: list[dict[str, Any]] = []
            for call in function_calls:
                tool_name = str(call.get("name") or "").strip()
                args = call.get("args")
                if not isinstance(args, dict):
                    args = {}
                result = _execute_function_call(
                    allowed_tools,
                    tool_name=tool_name,
                    args=args,
                )
                call_trace.append(
                    {
                        "round": rounds,
                        "name": result["name"],
                        "status": result["status"],
                        "args": args,
                    }
                )
                tool_responses.append(result)

            candidate_content = _extract_primary_candidate_content(response)
            if candidate_content is not None:
                conversation.append(candidate_content)
            conversation.append(_build_function_response_content(genai_types, tool_responses))

        deduped_signatures = list(dict.fromkeys(thought_signatures))
        signature_digest = None
        if deduped_signatures:
            signature_digest = hashlib.sha256(
                "|".join(deduped_signatures).encode("utf-8", errors="ignore")
            ).hexdigest()

        return text if termination_reason == "text" else None, {
            "thinking": {
                "enabled": True,
                "level": str(effective_thinking_level).strip().lower(),
                "include_thoughts": effective_include_thoughts,
                "thought_count": thought_count,
                "thought_signatures": deduped_signatures,
                "thought_signature_digest": signature_digest,
                "usage": usage_rollup,
            },
            "function_calling": {
                "enabled": bool(enable_function_calling),
                "max_rounds": max_function_call_rounds,
                "rounds_used": rounds,
                "calls": call_trace,
                "termination_reason": termination_reason,
            },
            "media_resolution": effective_media_resolution,
        }

    should_try_video = normalized_mode in {"auto", "video_text"} and bool(normalized_media_path)
    if should_try_video:
        try:
            uploaded = client.files.upload(file=normalized_media_path)
            text, metadata = _generate_with_function_loop([uploaded, prompt])
            if text:
                return text, "video_text", metadata
        except Exception:
            pass

    should_try_frames = normalized_mode in {"auto", "video_text", "frames_text"} and bool(normalized_frame_paths)
    if should_try_frames:
        try:
            frame_parts = _build_frame_parts(
                genai_types,
                normalized_frame_paths,
                limit=max(1, settings.pipeline_max_frames),
                media_resolution_policy=effective_media_resolution,
            )
            if frame_parts:
                text, metadata = _generate_with_function_loop([prompt, *frame_parts])
                if text:
                    return text, "frames_text", metadata
        except Exception:
            pass

    if normalized_mode in {"auto", "text"}:
        cached_content_name: str | None = None
        cache_enabled = bool(use_context_cache) and bool(settings.gemini_context_cache_enabled)
        if cache_enabled and len(prompt) >= max(0, settings.gemini_context_cache_min_chars):
            try:
                cache_name = _create_cached_content(
                    client,
                    genai_types,
                    model=model_name,
                    prompt=prompt,
                    cache_key=_cache_key(model_name, prompt, normalized_mode),
                    ttl_seconds=settings.gemini_context_cache_ttl_seconds,
                )
                if cache_name:
                    cached_content_name = cache_name
            except Exception:
                cached_content_name = None

        try:
            if cached_content_name:
                text, metadata = _generate_with_function_loop(
                    "Use the cached context and return a strict JSON response.",
                    cached_content=cached_content_name,
                )
            else:
                text, metadata = _generate_with_function_loop(prompt)
            if text:
                return text, "text", metadata
        except Exception:
            pass

    return None, "none", {}
