from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Any

from worker.config import Settings
from worker.pipeline.policies import normalize_llm_input_mode
from worker.pipeline.types import LLMInputMode
from worker.pipeline.steps.llm_prompts import build_evidence_citations, select_supporting_frames

_CACHE_NAME_BY_KEY: dict[str, str] = {}


def _cache_key(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8", errors="ignore"))
        digest.update(b"\0")
    return digest.hexdigest()


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
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    chunks.append(part_text.strip())
            if chunks:
                return "\n".join(chunks)
    return None


def _build_frame_parts(genai_types: Any, frame_paths: list[str], *, limit: int) -> list[Any]:
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
        parts.append(genai_types.Part.from_bytes(data=data, mime_type=mime_type))
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
) -> tuple[str | None, str]:
    if not settings.gemini_api_key:
        return None, "none"

    try:
        from google import genai  # type: ignore
        from google.genai import types as genai_types  # type: ignore
    except Exception:
        return None, "none"

    model_name = str(model or settings.gemini_model).strip() or settings.gemini_model
    normalized_mode = normalize_llm_input_mode(llm_input_mode)
    normalized_media_path = str(media_path or "").strip()
    normalized_frame_paths = list(frame_paths or [])

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
    except Exception:
        return None, "none"

    effective_thinking_level = str(thinking_level or settings.gemini_thinking_level or "high")
    effective_include_thoughts = (
        settings.gemini_include_thoughts if include_thoughts is None else bool(include_thoughts)
    )
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

    should_try_video = normalized_mode in {"auto", "video_text"} and bool(normalized_media_path)
    if should_try_video:
        try:
            uploaded = client.files.upload(file=normalized_media_path)
            response = _generate([uploaded, prompt])
            text = _extract_response_text(response)
            if text:
                return text, "video_text"
        except Exception:
            pass

    should_try_frames = normalized_mode in {"auto", "video_text", "frames_text"} and bool(normalized_frame_paths)
    if should_try_frames:
        try:
            frame_parts = _build_frame_parts(
                genai_types,
                normalized_frame_paths,
                limit=max(1, settings.pipeline_max_frames),
            )
            if frame_parts:
                response = _generate([prompt, *frame_parts])
                text = _extract_response_text(response)
                if text:
                    return text, "frames_text"
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
                response = _generate(
                    "Use the cached context and return a strict JSON response.",
                    cached_content=cached_content_name,
                )
            else:
                response = _generate(prompt)
            text = _extract_response_text(response)
            if text:
                return text, "text"
        except Exception:
            pass

    return None, "none"
