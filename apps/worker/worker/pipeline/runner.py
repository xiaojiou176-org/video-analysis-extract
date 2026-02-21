from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Callable, Literal
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from worker.comments import (
    BilibiliCommentCollector,
    YouTubeCommentCollector,
    empty_comments_payload,
)
from worker.config import Settings
from worker.state.postgres_store import PostgresBusinessStore
from worker.state.sqlite_store import SQLiteStateStore

StepStatus = Literal["succeeded", "failed", "skipped"]
PipelineStatus = Literal["succeeded", "partial", "failed"]
RetryCategory = Literal["transient", "rate_limit", "auth", "fatal"]
PipelineMode = Literal["full", "text_only", "refresh_comments", "refresh_llm"]
LLMInputMode = Literal["auto", "text", "video_text", "frames_text"]

PIPELINE_STEPS: list[str] = [
    "fetch_metadata",
    "download_media",
    "collect_subtitles",
    "collect_comments",
    "extract_frames",
    "llm_outline",
    "llm_digest",
    "write_artifacts",
]

STEP_VERSIONS: dict[str, str] = {step: "v1" for step in PIPELINE_STEPS}
STEP_VERSIONS["collect_comments"] = "v3"
STEP_VERSIONS["llm_outline"] = "v2"
STEP_VERSIONS["llm_digest"] = "v2"
NON_DEGRADING_SKIP_REASONS = {
    "cache_hit",
    "legacy_cache_hit",
    "checkpoint_recovered",
    "mode_matrix_skip",
}

PIPELINE_MODE_SKIP_STEPS: dict[PipelineMode, set[str]] = {
    "full": set(),
    "text_only": {"download_media", "collect_subtitles", "extract_frames"},
    "refresh_comments": set(),
    "refresh_llm": set(),
}
PIPELINE_MODE_FORCE_STEPS: dict[PipelineMode, set[str]] = {
    "full": set(),
    "text_only": set(),
    "refresh_comments": {"collect_comments", "llm_outline", "llm_digest", "write_artifacts"},
    "refresh_llm": {"llm_outline", "llm_digest", "write_artifacts"},
}
PIPELINE_MODE_SKIP_UPDATES: dict[str, dict[str, Any]] = {
    "download_media": {"media_path": None, "download_mode": "text_only"},
    "collect_subtitles": {"transcript": "", "subtitle_files": []},
    "extract_frames": {"frames": []},
}

STEP_INPUT_KEYS: dict[str, tuple[str, ...]] = {
    "fetch_metadata": ("source_url", "title", "platform", "video_uid", "published_at"),
    "download_media": ("source_url",),
    "collect_subtitles": ("media_path", "download_mode"),
    "collect_comments": ("source_url", "platform", "video_uid"),
    "extract_frames": ("media_path",),
    "llm_outline": (
        "title",
        "metadata",
        "transcript",
        "comments",
        "frames",
        "source_url",
        "llm_input_mode",
        "llm_media_input",
    ),
    "llm_digest": (
        "title",
        "metadata",
        "outline",
        "transcript",
        "comments",
        "frames",
        "source_url",
        "llm_input_mode",
        "llm_media_input",
    ),
    "write_artifacts": (
        "source_url",
        "platform",
        "video_uid",
        "metadata",
        "digest",
        "outline",
        "comments",
        "transcript",
        "degradations",
        "frames",
    ),
}

STEP_SETTING_KEYS: dict[str, tuple[str, ...]] = {
    "fetch_metadata": ("pipeline_subprocess_timeout_seconds",),
    "download_media": ("pipeline_subprocess_timeout_seconds",),
    "collect_comments": (
        "comments_top_n",
        "comments_replies_per_comment",
        "comments_request_timeout_seconds",
        "request_retry_attempts",
        "request_retry_backoff_seconds",
    ),
    "extract_frames": (
        "pipeline_subprocess_timeout_seconds",
        "pipeline_frame_interval_seconds",
        "pipeline_max_frames",
    ),
    "llm_outline": ("gemini_model", "pipeline_max_frames", "pipeline_llm_input_mode"),
    "llm_digest": ("gemini_model", "pipeline_max_frames", "pipeline_llm_input_mode"),
    "write_artifacts": ("digest_template_path",),
}

@dataclass
class CommandResult:
    ok: bool
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    reason: str | None = None

@dataclass
class StepExecution:
    status: StepStatus
    output: dict[str, Any] = field(default_factory=dict)
    state_updates: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
    error: str | None = None
    error_kind: RetryCategory | None = None
    retry_meta: dict[str, Any] = field(default_factory=dict)
    cache_meta: dict[str, Any] = field(default_factory=dict)
    degraded: bool = False

    def to_record(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "output": self.output,
            "state_updates": self.state_updates,
            "reason": self.reason,
            "error": self.error,
            "error_kind": self.error_kind,
            "retry_meta": self.retry_meta,
            "cache_meta": self.cache_meta,
            "degraded": self.degraded,
        }

    @classmethod
    def from_record(cls, payload: dict[str, Any]) -> "StepExecution":
        return cls(
            status=str(payload.get("status", "failed")),  # type: ignore[arg-type]
            output=dict(payload.get("output") or {}),
            state_updates=dict(payload.get("state_updates") or {}),
            reason=payload.get("reason"),
            error=payload.get("error"),
            error_kind=payload.get("error_kind"),
            retry_meta=dict(payload.get("retry_meta") or {}),
            cache_meta=dict(payload.get("cache_meta") or {}),
            degraded=bool(payload.get("degraded", False)),
        )

@dataclass
class PipelineContext:
    settings: Settings
    sqlite_store: SQLiteStateStore
    pg_store: PostgresBusinessStore
    job_id: str
    attempt: int
    job_record: dict[str, Any]
    work_dir: Path
    cache_dir: Path
    download_dir: Path
    frames_dir: Path
    artifacts_dir: Path

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value

def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def _write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.write_text(
        json.dumps(_jsonable(payload), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

def _legacy_step_cache_path(ctx: PipelineContext, step_name: str) -> Path:
    return ctx.cache_dir / f"{step_name}.json"


def _truncate_text(value: str, *, keep: int = 240) -> str:
    if len(value) <= keep:
        return value
    digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"<<sha256:{digest}|len:{len(value)}>>"


def _normalize_for_signature(value: Any) -> Any:
    if isinstance(value, str):
        return _truncate_text(value)
    if isinstance(value, Path):
        return str(value.resolve())
    if isinstance(value, dict):
        return {str(k): _normalize_for_signature(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_for_signature(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_for_signature(item) for item in value]
    return _jsonable(value)


def _settings_subset(settings: Settings, keys: tuple[str, ...]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in keys:
        payload[key] = getattr(settings, key, None)
    return payload


def _step_input_payload(ctx: PipelineContext, state: dict[str, Any], step_name: str) -> dict[str, Any]:
    state_keys = STEP_INPUT_KEYS.get(step_name, ())
    settings_keys = STEP_SETTING_KEYS.get(step_name, ())
    state_payload = {key: state.get(key) for key in state_keys}
    return {
        "state": _normalize_for_signature(state_payload),
        "settings": _normalize_for_signature(_settings_subset(ctx.settings, settings_keys)),
    }


def _build_step_cache_info(
    ctx: PipelineContext, state: dict[str, Any], step_name: str
) -> dict[str, Any]:
    version = STEP_VERSIONS.get(step_name, "v1")
    payload = {
        "step": step_name,
        "version": version,
        "inputs": _step_input_payload(ctx, state, step_name),
    }
    signature = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()[:24]
    cache_key = f"{step_name}:{version}:{signature}"
    cache_path = _ensure_dir(ctx.cache_dir / step_name) / f"{version}_{signature}.json"
    return {
        "step": step_name,
        "version": version,
        "signature": signature,
        "cache_key": cache_key,
        "cache_path": cache_path,
        "legacy_path": _legacy_step_cache_path(ctx, step_name),
    }


def _load_cache_execution(cache_path: Path) -> StepExecution | None:
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(_read_text_file(cache_path))
        execution = StepExecution.from_record(dict(payload))
    except Exception:
        return None
    if execution.status != "succeeded":
        return None
    return execution


def _load_step_execution_from_cache(cache_info: dict[str, Any]) -> tuple[StepExecution | None, str | None]:
    cache_path = cache_info["cache_path"]
    execution = _load_cache_execution(cache_path)
    if execution is not None:
        return execution, "cache_hit"

    legacy_path = cache_info["legacy_path"]
    legacy_execution = _load_cache_execution(legacy_path)
    if legacy_execution is not None:
        return legacy_execution, "legacy_cache_hit"
    return None, None


def _write_step_cache(cache_info: dict[str, Any], execution: StepExecution) -> None:
    payload = execution.to_record()
    payload["cache_meta"] = {
        **payload.get("cache_meta", {}),
        "cache_key": cache_info["cache_key"],
        "signature": cache_info["signature"],
        "version": cache_info["version"],
        "cached_at": _utc_now_iso(),
    }
    cache_path = cache_info["cache_path"]
    cache_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    legacy_path = cache_info["legacy_path"]
    legacy_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _safe_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _safe_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _build_retry_policy(settings: Settings) -> dict[RetryCategory, dict[str, float | int]]:
    base_retries = max(0, int(getattr(settings, "pipeline_retry_attempts", 2)))
    base_backoff = max(0.0, float(getattr(settings, "pipeline_retry_backoff_seconds", 1.0)))
    return {
        "transient": {
            "retries": max(0, _safe_int_env("PIPELINE_RETRY_TRANSIENT_ATTEMPTS", base_retries)),
            "backoff": max(
                0.0, _safe_float_env("PIPELINE_RETRY_TRANSIENT_BACKOFF_SECONDS", base_backoff)
            ),
            "max_backoff": max(
                0.0,
                _safe_float_env("PIPELINE_RETRY_TRANSIENT_MAX_BACKOFF_SECONDS", base_backoff * 8),
            ),
        },
        "rate_limit": {
            "retries": max(
                0, _safe_int_env("PIPELINE_RETRY_RATE_LIMIT_ATTEMPTS", max(base_retries, 3))
            ),
            "backoff": max(
                0.0, _safe_float_env("PIPELINE_RETRY_RATE_LIMIT_BACKOFF_SECONDS", base_backoff * 2)
            ),
            "max_backoff": max(
                0.0,
                _safe_float_env(
                    "PIPELINE_RETRY_RATE_LIMIT_MAX_BACKOFF_SECONDS", max(base_backoff * 16, 1.0)
                ),
            ),
        },
        "auth": {
            "retries": max(0, _safe_int_env("PIPELINE_RETRY_AUTH_ATTEMPTS", 0)),
            "backoff": max(0.0, _safe_float_env("PIPELINE_RETRY_AUTH_BACKOFF_SECONDS", base_backoff)),
            "max_backoff": max(
                0.0, _safe_float_env("PIPELINE_RETRY_AUTH_MAX_BACKOFF_SECONDS", base_backoff * 2)
            ),
        },
        "fatal": {
            "retries": max(0, _safe_int_env("PIPELINE_RETRY_FATAL_ATTEMPTS", 0)),
            "backoff": 0.0,
            "max_backoff": 0.0,
        },
    }


def _retry_delay_seconds(policy: dict[str, float | int], retries_used: int) -> float:
    backoff = float(policy.get("backoff", 0.0))
    if backoff <= 0:
        return 0.0
    max_backoff = max(0.0, float(policy.get("max_backoff", backoff)))
    delay = backoff * (2**max(0, retries_used))
    return min(delay, max_backoff)


def _classify_error(reason: str | None, error: str | None) -> RetryCategory:
    combined = f"{reason or ''} {error or ''}".lower()
    if any(token in combined for token in ("429", "rate limit", "too many request")):
        return "rate_limit"
    if any(
        token in combined
        for token in (
            "401",
            "403",
            "unauthorized",
            "forbidden",
            "invalid api key",
            "authentication",
            "permission denied",
        )
    ):
        return "auth"
    if any(
        token in combined
        for token in (
            "timeout",
            "timed out",
            "econn",
            "connection reset",
            "network",
            "temporary",
            "service unavailable",
            "non_zero_exit",
        )
    ):
        return "transient"
    return "fatal"

def _run_command_once(cmd: list[str], timeout_seconds: int) -> CommandResult:
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return CommandResult(ok=False, reason="binary_not_found")
    except subprocess.TimeoutExpired:
        return CommandResult(ok=False, reason="timeout")

    return CommandResult(
        ok=completed.returncode == 0,
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        reason=None if completed.returncode == 0 else "non_zero_exit",
    )

async def _run_command(
    ctx: PipelineContext,
    cmd: list[str],
) -> CommandResult:
    timeout = max(1, int(ctx.settings.pipeline_subprocess_timeout_seconds))
    return await asyncio.to_thread(_run_command_once, cmd, timeout)

def _extract_media_file(download_dir: Path, command_stdout: str) -> str | None:
    for line in reversed(command_stdout.splitlines()):
        candidate = line.strip()
        if not candidate:
            continue
        if Path(candidate).exists():
            return str(Path(candidate).resolve())

    files = sorted(
        [
            p
            for p in download_dir.glob("media.*")
            if p.is_file() and p.suffix.lower() not in {".part", ".tmp"}
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if files:
        return str(files[0].resolve())
    return None

def _subtitle_to_text(raw_content: str) -> str:
    lines: list[str] = []
    for line in raw_content.splitlines():
        content = line.strip()
        if not content:
            continue
        if content == "WEBVTT" or content.isdigit():
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}", content):
            continue
        if "-->" in content:
            continue
        content = re.sub(r"<[^>]+>", "", content)
        lines.append(content)
    return "\n".join(lines).strip()

def _collect_key_points_from_text(text: str, limit: int = 5) -> list[str]:
    if not text:
        return []
    parts = re.split(r"(?<=[。！？.!?])\s+", text)
    cleaned = [part.strip() for part in parts if part.strip()]
    if not cleaned:
        return []
    return cleaned[:limit]

def _coerce_bool(value: Any, default: bool = False) -> bool:
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

def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_pipeline_mode(value: Any) -> PipelineMode:
    text = str(value or "full").strip().lower()
    if text in {"full", "text_only", "refresh_comments", "refresh_llm"}:
        return text  # type: ignore[return-value]
    return "full"


def _normalize_llm_input_mode(value: Any) -> LLMInputMode:
    text = str(value or "auto").strip().lower()
    if text in {"auto", "text", "video_text", "frames_text"}:
        return text  # type: ignore[return-value]
    return "auto"


def _frame_paths_from_frames(frames: list[dict[str, Any]], *, limit: int = 8) -> list[str]:
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


def _llm_media_input_dimension(state: dict[str, Any]) -> dict[str, Any]:
    media_path = str(state.get("media_path") or "").strip()
    frames = list(state.get("frames") or [])
    frame_paths = _frame_paths_from_frames(frames, limit=200)
    return {
        "video_available": bool(media_path),
        "frame_count": len(frame_paths),
    }


def _refresh_llm_media_input_dimension(state: dict[str, Any]) -> None:
    state["llm_media_input"] = _llm_media_input_dimension(state)


def _coerce_str_list(values: Any, *, limit: int = 12) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for item in values:
        text = str(item).strip()
        if text:
            normalized.append(text)
        if len(normalized) >= limit:
            break
    return normalized

def _dedupe_keep_order(values: list[str], *, limit: int = 12) -> list[str]:
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

def _extract_json_object(text: str) -> str:
    content = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", content, re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        return content[start : end + 1]
    return content

def _parse_duration_seconds(value: Any) -> int:
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if not isinstance(value, str):
        return 0
    text = value.strip()
    if not text:
        return 0
    if text.isdigit():
        return max(0, int(text))
    parts = text.split(":")
    if len(parts) not in {2, 3}:
        return 0
    try:
        nums = [int(part) for part in parts]
    except ValueError:
        return 0
    if len(nums) == 2:
        mm, ss = nums
        return max(0, mm * 60 + ss)
    hh, mm, ss = nums
    return max(0, hh * 3600 + mm * 60 + ss)

def _estimate_duration_seconds(
    metadata: dict[str, Any], frames: list[dict[str, Any]], fallback_points: int
) -> int:
    for key in ("duration_s", "duration", "duration_seconds"):
        parsed = _parse_duration_seconds(metadata.get(key))
        if parsed > 0:
            return parsed
    frame_max = max((_coerce_int(frame.get("timestamp_s"), 0) for frame in frames), default=0)
    if frame_max > 0:
        return max(frame_max + 15, 60)
    return max(fallback_points * 90, 180)

def _timestamp_link(source_url: str, timestamp_s: int) -> str:
    if not source_url:
        return ""
    if timestamp_s < 0:
        timestamp_s = 0
    try:
        parsed = urlparse(source_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        host = (parsed.netloc or "").lower()
        if "youtube.com" in host or "youtu.be" in host:
            query["t"] = f"{timestamp_s}s"
        else:
            query["t"] = str(timestamp_s)
        return urlunparse(parsed._replace(query=urlencode(query)))
    except Exception:
        return source_url

def _build_comments_prompt_context(comments: dict[str, Any], *, top_n: int = 4) -> str:
    top_comments = comments.get("top_comments") if isinstance(comments, dict) else None
    if not isinstance(top_comments, list) or not top_comments:
        return "No comment data."
    lines: list[str] = []
    for idx, item in enumerate(top_comments[:top_n], start=1):
        if not isinstance(item, dict):
            continue
        author = str(item.get("author") or "unknown")
        content = str(item.get("content") or "").strip() or "empty"
        likes = _coerce_int(item.get("like_count"), 0)
        lines.append(f"{idx}. {author} (likes={likes}): {content}")
        replies = item.get("replies")
        if isinstance(replies, list):
            for reply in replies[:2]:
                if not isinstance(reply, dict):
                    continue
                reply_author = str(reply.get("author") or "unknown")
                reply_text = str(reply.get("content") or "").strip() or "empty"
                reply_likes = _coerce_int(reply.get("like_count"), 0)
                lines.append(
                    f"   - reply by {reply_author} (likes={reply_likes}): {reply_text}"
                )
    return "\n".join(lines) if lines else "No comment data."

def _should_include_frame_prompt(settings: Settings) -> bool:
    env_value = os.getenv("PIPELINE_LLM_INCLUDE_FRAMES")
    if env_value is not None:
        return _coerce_bool(env_value, default=False)
    if hasattr(settings, "pipeline_llm_include_frames"):
        return _coerce_bool(getattr(settings, "pipeline_llm_include_frames"), default=False)
    return False

def _build_frames_prompt_context(frames: list[dict[str, Any]], source_url: str, *, limit: int = 8) -> str:
    if not frames:
        return "No frame data."
    lines: list[str] = []
    for idx, frame in enumerate(frames[:limit], start=1):
        ts = _coerce_int(frame.get("timestamp_s"), 0)
        reason = str(frame.get("reason") or "key frame").strip()
        note = str(frame.get("note") or "").strip()
        path = str(frame.get("path") or "").strip()
        lines.append(
            f"{idx}. [{_format_seconds(ts)}] {_timestamp_link(source_url, ts) or 'n/a'} | {reason} | {note or 'n/a'} | {path or 'n/a'}"
        )
    return "\n".join(lines) if lines else "No frame data."

def _extract_code_snippets(transcript: str, *, limit: int = 4) -> list[dict[str, Any]]:
    if not transcript.strip():
        return []
    pattern = re.compile(r"```(?P<lang>[A-Za-z0-9_+-]*)\n(?P<body>[\s\S]*?)```")
    snippets: list[dict[str, Any]] = []
    for idx, match in enumerate(pattern.finditer(transcript), start=1):
        snippet = match.group("body").strip()
        if not snippet:
            continue
        snippets.append(
            {
                "title": f"Snippet {idx}",
                "language": (match.group("lang") or "text").strip() or "text",
                "snippet": snippet[:1000],
                "range_start_s": 0,
                "range_end_s": 0,
            }
        )
        if len(snippets) >= limit:
            break
    return snippets

def _load_digest_template(settings: Settings) -> str:
    template_path = Path(settings.digest_template_path)
    if template_path.exists():
        return _read_text_file(template_path)
    return (
        "# {{title}}\n\n"
        "- Source: {{source_url}}\n"
        "- Platform: {{platform}}\n"
        "- Video UID: {{video_uid}}\n"
        "- Generated At: {{generated_at}}\n\n"
        "## TL;DR\n\n"
        "{{tldr_markdown}}\n\n"
        "## Summary\n\n"
        "{{summary}}\n\n"
        "## Highlights\n\n"
        "{{highlights_markdown}}\n\n"
        "## Chapters\n\n"
        "{{chapters_toc_markdown}}\n\n"
        "{{chapters_markdown}}\n\n"
        "## Code Blocks\n\n"
        "{{code_blocks_markdown}}\n\n"
        "## Comment Highlights\n\n"
        "{{comments_markdown}}\n\n"
        "## Screenshot Index\n\n"
        "{{frames_index_markdown}}\n\n"
        "## Timestamp References\n\n"
        "{{timestamp_refs_markdown}}\n\n"
        "## Fallback Notes\n\n"
        "{{fallback_notes_markdown}}\n\n"
        "## Degradation Notes\n\n"
        "{{degradations_markdown}}\n"
    )

def _render_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = re.sub(
            r"{{\s*" + re.escape(key) + r"\s*}}",
            lambda _: value,
            rendered,
        )
    return rendered

def _format_seconds(seconds: int) -> str:
    value = max(0, int(seconds))
    h = value // 3600
    m = (value % 3600) // 60
    s = value % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def _build_chapters_toc_markdown(outline: dict[str, Any], source_url: str) -> str:
    chapters = outline.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        return "- （暂无章节）"
    lines: list[str] = []
    for idx, chapter in enumerate(chapters, start=1):
        if not isinstance(chapter, dict):
            continue
        title = str(chapter.get("title") or chapter.get("heading") or f"Chapter {idx}")
        chapter_no = _coerce_int(chapter.get("chapter_no"), idx)
        anchor = str(chapter.get("anchor") or f"chapter-{chapter_no:02d}")
        start_s = _coerce_int(chapter.get("start_s"), 0)
        end_s = _coerce_int(chapter.get("end_s"), start_s)
        start_link = _timestamp_link(source_url, start_s)
        end_link = _timestamp_link(source_url, end_s)
        lines.append(
            f"- [{chapter_no}. {title}](#{anchor})（[{_format_seconds(start_s)}]({start_link}) - [{_format_seconds(end_s)}]({end_link})）"
        )
    return "\n".join(lines).strip() or "- （暂无章节）"

def _build_chapters_markdown(outline: dict[str, Any], source_url: str) -> str:
    chapters = outline.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        return "（暂无章节）"

    lines: list[str] = []
    for idx, chapter in enumerate(chapters, start=1):
        if not isinstance(chapter, dict):
            continue
        title = str(chapter.get("title") or chapter.get("heading") or f"Chapter {idx}")
        chapter_no = _coerce_int(chapter.get("chapter_no"), idx)
        anchor = str(chapter.get("anchor") or f"chapter-{chapter_no:02d}")
        start_s = _coerce_int(chapter.get("start_s"), 0)
        end_s = _coerce_int(chapter.get("end_s"), start_s)
        summary = str(chapter.get("summary") or "").strip() or "（无小结）"
        start_link = _timestamp_link(source_url, start_s)
        end_link = _timestamp_link(source_url, end_s)

        lines.append(f"<a id=\"{anchor}\"></a>")
        lines.append(f"### {chapter_no}. {title}")
        lines.append(
            f"- 时间范围：[{_format_seconds(start_s)}]({start_link}) - [{_format_seconds(end_s)}]({end_link})"
        )
        lines.append(f"- 小结：{summary}")
        lines.append("")
        lines.append("要点：")

        bullets = _coerce_str_list(chapter.get("bullets"), limit=8)
        if bullets:
            for bullet in bullets:
                lines.append(f"- {bullet}")
        else:
            lines.append("- （无要点）")

        key_terms = _coerce_str_list(chapter.get("key_terms"), limit=8)
        lines.append("")
        lines.append("关键术语：")
        if key_terms:
            for term in key_terms:
                lines.append(f"- `{term}`")
        else:
            lines.append("- （无术语）")
        lines.append("")
    return "\n".join(lines).strip() or "（暂无章节）"

def _build_comments_markdown(comments: dict[str, Any]) -> str:
    top_comments = comments.get("top_comments") if isinstance(comments, dict) else None
    if not isinstance(top_comments, list) or not top_comments:
        return "（未采集到评论，或当前未启用评论采集）"

    lines: list[str] = []
    for idx, item in enumerate(top_comments, start=1):
        if not isinstance(item, dict):
            continue
        author = str(item.get("author") or "unknown")
        content = str(item.get("content") or "").strip()
        likes = item.get("like_count")
        lines.append(f"{idx}. **{author}**（👍 {likes if likes is not None else 0}）")
        lines.append(f"   - {content or '（空）'}")
        replies = item.get("replies")
        if isinstance(replies, list) and replies:
            for reply in replies:
                if not isinstance(reply, dict):
                    continue
                reply_author = str(reply.get("author") or "unknown")
                reply_content = str(reply.get("content") or "").strip() or "（空）"
                reply_likes = reply.get("like_count")
                lines.append(
                    f"   - ↳ **{reply_author}**（👍 {reply_likes if reply_likes is not None else 0}）：{reply_content}"
                )
    return "\n".join(lines) if lines else "（评论数据为空）"

def _collect_code_blocks(
    outline: dict[str, Any],
    digest: dict[str, Any],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    raw_blocks = digest.get("code_blocks")
    if isinstance(raw_blocks, list):
        for block in raw_blocks:
            if isinstance(block, dict):
                merged.append(dict(block))
    chapters = outline.get("chapters")
    if isinstance(chapters, list):
        for chapter in chapters:
            if not isinstance(chapter, dict):
                continue
            chapter_blocks = chapter.get("code_snippets")
            if not isinstance(chapter_blocks, list):
                continue
            for block in chapter_blocks:
                if isinstance(block, dict):
                    merged.append(dict(block))
    return merged

def _build_code_blocks_markdown(
    outline: dict[str, Any],
    digest: dict[str, Any],
    source_url: str,
) -> str:
    blocks = _collect_code_blocks(outline, digest)
    if not blocks:
        return "（无代码片段）"
    lines: list[str] = []
    for idx, block in enumerate(blocks, start=1):
        title = str(block.get("title") or f"Snippet {idx}")
        language = str(block.get("language") or "text").strip() or "text"
        snippet = str(block.get("snippet") or "").strip()
        if not snippet:
            continue
        start_s = _coerce_int(block.get("range_start_s"), 0)
        end_s = _coerce_int(block.get("range_end_s"), start_s)
        start_link = _timestamp_link(source_url, start_s)
        end_link = _timestamp_link(source_url, end_s)
        lines.append(
            f"#### {idx}. {title}（[{_format_seconds(start_s)}]({start_link}) - [{_format_seconds(end_s)}]({end_link})）"
        )
        lines.append(f"```{language}")
        lines.append(snippet)
        lines.append("```")
        lines.append("")
    return "\n".join(lines).strip() or "（无代码片段）"

def _build_timestamp_refs_markdown(
    outline: dict[str, Any],
    digest: dict[str, Any],
    source_url: str,
) -> str:
    refs_raw = digest.get("timestamp_references")
    references: list[dict[str, Any]] = []
    if isinstance(refs_raw, list):
        for item in refs_raw:
            if isinstance(item, dict):
                references.append(item)
    if not references:
        refs_outline = outline.get("timestamp_references")
        if isinstance(refs_outline, list):
            for item in refs_outline:
                if isinstance(item, dict):
                    references.append(item)
    if not references:
        return "- （无时间戳引用）"

    lines: list[str] = []
    for idx, item in enumerate(references, start=1):
        ts = _coerce_int(item.get("ts_s"), 0)
        label = str(item.get("label") or f"Reference {idx}")
        reason = str(item.get("reason") or "").strip()
        link = _timestamp_link(source_url, ts)
        suffix = f" - {reason}" if reason else ""
        lines.append(f"- [{_format_seconds(ts)}]({link}) {label}{suffix}")
    return "\n".join(lines).strip() or "- （无时间戳引用）"

def _build_frames_markdown(frames: list[dict[str, Any]], source_url: str) -> str:
    if not frames:
        return "（无截图）"
    lines = [
        "| # | 时间戳 | 跳转 | 原因 | 说明 | 文件 |",
        "|---:|:---:|:---:|---|---|---|",
    ]
    for idx, frame in enumerate(frames, start=1):
        ts_s = _coerce_int(frame.get("timestamp_s"), 0)
        ts = _format_seconds(ts_s)
        link = _timestamp_link(source_url, ts_s)
        path = str(frame.get("path") or "")
        reason = str(frame.get("reason") or "key_frame").strip() or "key_frame"
        note = str(frame.get("note") or "").strip() or "-"
        lines.append(f"| {idx} | {ts} | [link]({link}) | {reason} | {note} | `{path}` |")
    return "\n".join(lines)

def _build_fallback_notes_markdown(digest: dict[str, Any], degradations: list[dict[str, Any]]) -> str:
    notes = _coerce_str_list(digest.get("fallback_notes"), limit=8)
    if notes:
        return "\n".join(f"- {note}" for note in notes)
    degraded_steps = []
    for item in degradations:
        if not isinstance(item, dict):
            continue
        step = str(item.get("step") or "").strip()
        reason = str(item.get("reason") or "n/a").strip()
        status = str(item.get("status") or "unknown").strip()
        if step:
            degraded_steps.append(f"- {step}: {status} ({reason})")
    return "\n".join(degraded_steps) if degraded_steps else "- none"

def _build_context(
    settings: Settings,
    sqlite_store: SQLiteStateStore,
    pg_store: PostgresBusinessStore,
    job_id: str,
    attempt: int,
) -> PipelineContext:
    job_record = pg_store.get_job_with_video(job_id=job_id)

    root = _ensure_dir(Path(settings.pipeline_workspace_dir).expanduser())
    work_dir = _ensure_dir(root / job_id)
    cache_dir = _ensure_dir(work_dir / "cache")
    download_dir = _ensure_dir(work_dir / "downloads")
    frames_dir = _ensure_dir(work_dir / "frames")
    artifact_root = _ensure_dir(Path(settings.pipeline_artifact_root).expanduser())
    platform = str(job_record.get("platform") or "unknown")
    video_uid = str(job_record.get("video_uid") or "unknown")
    artifacts_dir = _ensure_dir(artifact_root / platform / video_uid / job_id)

    return PipelineContext(
        settings=settings,
        sqlite_store=sqlite_store,
        pg_store=pg_store,
        job_id=job_id,
        attempt=attempt,
        job_record=job_record,
        work_dir=work_dir,
        cache_dir=cache_dir,
        download_dir=download_dir,
        frames_dir=frames_dir,
        artifacts_dir=artifacts_dir,
    )

def _append_degradation(
    state: dict[str, Any],
    step_name: str,
    *,
    status: str,
    reason: str | None = None,
    error: str | None = None,
    error_kind: RetryCategory | None = None,
    retry_meta: dict[str, Any] | None = None,
    cache_meta: dict[str, Any] | None = None,
) -> None:
    state.setdefault("degradations", []).append(
        {
            "step": step_name,
            "status": status,
            "reason": reason,
            "error": error,
            "error_kind": error_kind,
            "retry_meta": retry_meta or {},
            "cache_meta": cache_meta or {},
            "at": _utc_now_iso(),
        }
    )

def _apply_state_updates(state: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        state[key] = value


def _build_mode_skip_step(step_name: str, mode: PipelineMode) -> Callable[[PipelineContext, dict[str, Any]], Any]:
    async def _skip(_: PipelineContext, __: dict[str, Any]) -> StepExecution:
        return StepExecution(
            status="skipped",
            output={"skipped_by_mode": mode, "step": step_name},
            state_updates=dict(PIPELINE_MODE_SKIP_UPDATES.get(step_name) or {}),
            reason="mode_matrix_skip",
            degraded=False,
        )

    return _skip


async def _execute_step(
    ctx: PipelineContext,
    state: dict[str, Any],
    *,
    step_name: str,
    step_func: Callable[[PipelineContext, dict[str, Any]], asyncio.Future | Any],
    critical: bool = False,
    resume_hint: bool = False,
    force_run: bool = False,
) -> dict[str, Any]:
    sqlite_store = ctx.sqlite_store
    cache_info = _build_step_cache_info(ctx, state, step_name)
    retry_policy = _build_retry_policy(ctx.settings)

    sqlite_store.mark_step_running(
        job_id=ctx.job_id,
        step_name=step_name,
        attempt=ctx.attempt,
        cache_key=str(cache_info["cache_key"]),
    )

    execution: StepExecution | None = None
    if not force_run:
        execution, cache_reason = _load_step_execution_from_cache(cache_info)
        if execution is not None:
            execution.status = "skipped"
            execution.reason = "checkpoint_recovered" if resume_hint else (cache_reason or "cache_hit")
            execution.cache_meta = {
                **execution.cache_meta,
                "source": cache_reason or "cache_hit",
                "cache_key": cache_info["cache_key"],
                "signature": cache_info["signature"],
                "version": cache_info["version"],
            }
            execution.retry_meta = {
                "attempts": 0,
                "retries_used": 0,
                "retries_configured": 0,
                "classification": None,
                "strategy": "cache",
                "resume_hint": resume_hint,
            }
        elif resume_hint:
            prior = sqlite_store.get_latest_step_run(
                job_id=ctx.job_id,
                step_name=step_name,
                status="succeeded",
                cache_key=str(cache_info["cache_key"]),
            )
            result_json = prior.get("result_json") if prior else None
            if isinstance(result_json, str) and result_json.strip():
                try:
                    payload = json.loads(result_json)
                    execution = StepExecution.from_record(dict(payload))
                    if execution.status == "succeeded":
                        execution.status = "skipped"
                        execution.reason = "checkpoint_recovered"
                        execution.cache_meta = {
                            **execution.cache_meta,
                            "source": "checkpoint",
                            "cache_key": cache_info["cache_key"],
                            "signature": cache_info["signature"],
                            "version": cache_info["version"],
                        }
                        execution.retry_meta = {
                            "attempts": 0,
                            "retries_used": 0,
                            "retries_configured": 0,
                            "classification": None,
                            "strategy": "checkpoint",
                            "resume_hint": True,
                        }
                    else:
                        execution = None
                except Exception:
                    execution = None

    if execution is None:
        execution = StepExecution(status="failed", error="step_not_executed", degraded=True)
        retry_delays: list[float] = []
        retry_categories: list[RetryCategory] = []
        attempts = 0
        configured_retries = 0

        while True:
            attempts += 1
            try:
                maybe_coro = step_func(ctx, state)
                current = await maybe_coro if asyncio.iscoroutine(maybe_coro) else maybe_coro
                if not isinstance(current, StepExecution):
                    current = StepExecution(
                        status="failed",
                        error=f"invalid_step_result:{step_name}",
                        degraded=True,
                    )
            except Exception as exc:  # pragma: no cover - defensive
                current = StepExecution(
                    status="failed",
                    reason="unhandled_exception",
                    error=f"unhandled_exception:{exc}",
                    degraded=True,
                )

            if current.status != "failed":
                execution = current
                break

            category = _classify_error(current.reason, current.error)
            current.error_kind = category
            retry_categories.append(category)
            policy = retry_policy.get(category, retry_policy["fatal"])
            configured_retries = max(configured_retries, int(policy.get("retries", 0)))
            retries_used = attempts - 1
            if retries_used >= int(policy.get("retries", 0)):
                execution = current
                break

            delay = _retry_delay_seconds(policy, retries_used)
            retry_delays.append(delay)
            if delay > 0:
                await asyncio.sleep(delay)

        if execution.status == "failed" and execution.error_kind is None:
            execution.error_kind = _classify_error(execution.reason, execution.error)
        execution.retry_meta = {
            "attempts": attempts,
            "retries_used": max(0, attempts - 1),
            "retries_configured": configured_retries,
            "classification": execution.error_kind,
            "history": retry_categories,
            "delays_seconds": retry_delays,
            "strategy": "retry_wrapper",
            "resume_hint": resume_hint,
        }
    elif not execution.retry_meta:
        execution.retry_meta = {
            "attempts": 0,
            "retries_used": 0,
            "retries_configured": 0,
            "classification": execution.error_kind,
            "history": [],
            "delays_seconds": [],
            "strategy": "none",
            "resume_hint": resume_hint,
        }

    _apply_state_updates(state, execution.state_updates)
    _refresh_llm_media_input_dimension(state)

    error_payload = None
    if execution.status == "failed":
        error_payload = {
            "reason": execution.reason or "step_failed",
            "error": execution.error or "unknown",
            "error_kind": execution.error_kind,
            "retry_meta": execution.retry_meta,
        }
    elif execution.status == "skipped":
        error_payload = {
            "reason": execution.reason or "skipped",
            "error_kind": execution.error_kind,
            "retry_meta": execution.retry_meta,
        }

    sqlite_store.mark_step_finished(
        job_id=ctx.job_id,
        step_name=step_name,
        attempt=ctx.attempt,
        status=execution.status,
        error_payload=error_payload,
        error_kind=execution.error_kind,
        retry_meta=execution.retry_meta,
        result_payload=execution.to_record(),
        cache_key=str(cache_info["cache_key"]),
    )
    if execution.status in {"succeeded", "skipped"}:
        sqlite_store.update_checkpoint(
            job_id=ctx.job_id,
            last_completed_step=step_name,
            payload={
                "cache_key": cache_info["cache_key"],
                "status": execution.status,
                "reason": execution.reason,
                "error_kind": execution.error_kind,
            },
        )

    skip_is_degrade = execution.status == "skipped" and execution.reason not in NON_DEGRADING_SKIP_REASONS
    if execution.status == "failed" or execution.degraded or skip_is_degrade:
        _append_degradation(
            state,
            step_name,
            status=execution.status,
            reason=execution.reason,
            error=execution.error,
            error_kind=execution.error_kind,
            retry_meta=execution.retry_meta,
            cache_meta=execution.cache_meta,
        )

    if execution.status == "failed" and critical:
        state["fatal_error"] = f"{step_name}:{execution.error or execution.reason or 'failed'}"

    if execution.status == "succeeded":
        execution.cache_meta = {
            **execution.cache_meta,
            "cache_key": cache_info["cache_key"],
            "signature": cache_info["signature"],
            "version": cache_info["version"],
        }
        _write_step_cache(cache_info, execution)

    step_record = execution.to_record()
    state.setdefault("steps", {})[step_name] = step_record
    return step_record

async def _step_fetch_metadata(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    source_url = str(state.get("source_url") or "")
    base_metadata = {
        "title": state.get("title"),
        "platform": state.get("platform"),
        "video_uid": state.get("video_uid"),
        "source_url": source_url or None,
        "published_at": state.get("published_at"),
    }
    if not source_url:
        return StepExecution(
            status="failed",
            state_updates={"metadata": base_metadata},
            reason="source_url_missing",
            error="source_url_missing",
            degraded=True,
        )

    cmd = [
        "yt-dlp",
        "--dump-single-json",
        "--skip-download",
        "--no-warnings",
        source_url,
    ]
    result = await _run_command(ctx, cmd)
    if result.ok:
        try:
            payload = json.loads(result.stdout)
            metadata = {
                **base_metadata,
                "extractor": payload.get("extractor"),
                "extractor_key": payload.get("extractor_key"),
                "uploader": payload.get("uploader"),
                "duration": payload.get("duration"),
                "description": payload.get("description"),
                "tags": payload.get("tags") or [],
                "thumbnail": payload.get("thumbnail"),
                "webpage_url": payload.get("webpage_url") or source_url,
                "fetched_at": _utc_now_iso(),
            }
            return StepExecution(
                status="succeeded",
                output={"provider": "yt-dlp"},
                state_updates={"metadata": metadata},
            )
        except json.JSONDecodeError:
            pass

    fallback_metadata = {
        **base_metadata,
        "provider": "fallback",
        "fetched_at": _utc_now_iso(),
    }
    reason = result.reason or "yt_dlp_failed"
    return StepExecution(
        status="succeeded",
        output={"provider": "fallback", "reason": reason},
        state_updates={"metadata": fallback_metadata},
        reason=reason,
        degraded=True,
    )

async def _step_download_media(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    source_url = str(state.get("source_url") or "")
    if not source_url:
        return StepExecution(
            status="skipped",
            state_updates={"media_path": None, "download_mode": "text_only"},
            reason="source_url_missing",
            degraded=True,
        )

    output_tmpl = str((ctx.download_dir / "media.%(ext)s").resolve())
    cmd = [
        "yt-dlp",
        "--no-progress",
        "--no-warnings",
        "--write-auto-sub",
        "--write-sub",
        "--sub-format",
        "vtt",
        "-o",
        output_tmpl,
        "--print",
        "after_move:filepath",
        source_url,
    ]
    result = await _run_command(ctx, cmd)
    if not result.ok:
        status: StepStatus = "skipped" if result.reason == "binary_not_found" else "failed"
        return StepExecution(
            status=status,
            state_updates={"media_path": None, "download_mode": "text_only"},
            reason=result.reason or "yt_dlp_failed",
            error=(result.stderr or "").strip()[-500:] or result.reason,
            degraded=True,
        )

    media_path = _extract_media_file(ctx.download_dir, result.stdout)
    if not media_path:
        return StepExecution(
            status="failed",
            state_updates={"media_path": None, "download_mode": "text_only"},
            reason="media_not_found_after_download",
            error="media_not_found_after_download",
            degraded=True,
        )

    return StepExecution(
        status="succeeded",
        output={"mode": "media"},
        state_updates={"media_path": media_path, "download_mode": "media"},
    )

async def _step_collect_subtitles(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    subtitle_candidates = sorted(
        [p for p in ctx.download_dir.glob("*.vtt") if p.is_file()]
        + [p for p in ctx.download_dir.glob("*.srt") if p.is_file()]
    )
    if not subtitle_candidates:
        return StepExecution(
            status="skipped",
            state_updates={"transcript": "", "subtitle_files": []},
            reason="subtitle_file_not_found",
            degraded=True,
        )

    transcript_chunks: list[str] = []
    subtitle_files: list[str] = []
    for path in subtitle_candidates[:6]:
        text = _subtitle_to_text(_read_text_file(path))
        if text:
            transcript_chunks.append(text)
        subtitle_files.append(str(path.resolve()))
    transcript = "\n".join(chunk for chunk in transcript_chunks if chunk).strip()
    return StepExecution(
        status="succeeded",
        output={"subtitle_files": len(subtitle_files)},
        state_updates={"transcript": transcript, "subtitle_files": subtitle_files},
    )

async def _step_collect_comments(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    platform = str(state.get("platform") or "").lower()
    source_url = str(state.get("source_url") or "")
    video_uid = str(state.get("video_uid") or "")
    if platform == "bilibili":
        collector = BilibiliCommentCollector(
            top_n=ctx.settings.comments_top_n,
            replies_per_comment=ctx.settings.comments_replies_per_comment,
            request_timeout_seconds=ctx.settings.comments_request_timeout_seconds,
            retry_attempts=ctx.settings.request_retry_attempts,
            retry_backoff_seconds=ctx.settings.request_retry_backoff_seconds,
        )
        try:
            comments_payload = await collector.collect(source_url=source_url, video_uid=video_uid)
        except Exception as exc:
            return StepExecution(
                status="succeeded",
                output={"count": 0, "provider": "bilibili"},
                state_updates={"comments": empty_comments_payload()},
                reason="comments_collection_failed_degraded",
                error=str(exc)[:500],
                error_kind=_classify_error("comments_collection_failed_degraded", str(exc)),
                degraded=True,
            )
    elif platform == "youtube":
        if not str(ctx.settings.youtube_api_key or "").strip():
            return StepExecution(
                status="succeeded",
                output={"count": 0, "provider": "youtube_data_api"},
                state_updates={"comments": empty_comments_payload(sort="hot")},
                reason="youtube_api_key_missing",
                error="youtube_api_key_missing",
                error_kind="auth",
                degraded=True,
            )
        collector = YouTubeCommentCollector(
            api_key=str(ctx.settings.youtube_api_key or ""),
            top_n=ctx.settings.comments_top_n,
            replies_per_comment=ctx.settings.comments_replies_per_comment,
            request_timeout_seconds=ctx.settings.comments_request_timeout_seconds,
            retry_attempts=ctx.settings.request_retry_attempts,
            retry_backoff_seconds=ctx.settings.request_retry_backoff_seconds,
        )
        try:
            comments_payload = await collector.collect(source_url=source_url, video_uid=video_uid)
        except Exception as exc:
            return StepExecution(
                status="succeeded",
                output={"count": 0, "provider": "youtube_data_api"},
                state_updates={"comments": empty_comments_payload(sort="hot")},
                reason="youtube_comments_collection_failed_degraded",
                error=str(exc)[:500],
                error_kind=_classify_error("youtube_comments_collection_failed_degraded", str(exc)),
                degraded=True,
            )
    else:
        return StepExecution(
            status="skipped",
            output={"count": 0},
            state_updates={"comments": empty_comments_payload()},
            reason="comments_collection_skipped_platform_unsupported",
            degraded=True,
        )

    try:
        top_comments = comments_payload.get("top_comments")
        count = len(top_comments) if isinstance(top_comments, list) else 0
    except Exception:
        count = 0

    return StepExecution(
        status="succeeded",
        output={"count": count},
        state_updates={"comments": comments_payload},
    )

async def _step_extract_frames(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    media_path = state.get("media_path")
    if not media_path:
        return StepExecution(
            status="skipped",
            state_updates={"frames": []},
            reason="media_path_missing",
            degraded=True,
        )

    frame_interval = max(1, int(ctx.settings.pipeline_frame_interval_seconds))
    max_frames = max(1, int(ctx.settings.pipeline_max_frames))
    output_pattern = str((ctx.frames_dir / "frame_%03d.jpg").resolve())
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(media_path),
        "-vf",
        f"fps=1/{frame_interval}",
        "-frames:v",
        str(max_frames),
        output_pattern,
    ]
    result = await _run_command(ctx, cmd)
    if not result.ok:
        status: StepStatus = "skipped" if result.reason == "binary_not_found" else "failed"
        return StepExecution(
            status=status,
            state_updates={"frames": []},
            reason=result.reason or "ffmpeg_failed",
            error=(result.stderr or "").strip()[-500:] or result.reason,
            degraded=True,
        )

    frame_files = sorted(path.resolve() for path in ctx.frames_dir.glob("frame_*.jpg"))
    if not frame_files:
        return StepExecution(
            status="failed",
            state_updates={"frames": []},
            reason="frame_not_generated",
            error="frame_not_generated",
            degraded=True,
        )
    frames_meta = [
        {
            "path": str(path),
            "timestamp_s": frame_interval * idx,
        }
        for idx, path in enumerate(frame_files)
    ]
    return StepExecution(
        status="succeeded",
        output={"frames": len(frames_meta)},
        state_updates={"frames": frames_meta},
    )

def _build_local_outline(state: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(state.get("metadata") or {})
    title = str(metadata.get("title") or state.get("title") or "Untitled Video")
    transcript = str(state.get("transcript") or "")
    comments = dict(state.get("comments") or {})
    frames = list(state.get("frames") or [])
    source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")

    key_points = _collect_key_points_from_text(transcript, limit=10)
    comment_points: list[str] = []
    top_comments = comments.get("top_comments")
    if isinstance(top_comments, list):
        for item in top_comments[:3]:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "").strip()
            if content:
                comment_points.append(f"评论观点：{content}")
    merged_points = _dedupe_keep_order(key_points + comment_points, limit=12)
    if not merged_points:
        merged_points = [
            f"Focus topic: {title}",
            "Transcript unavailable; outline synthesized from metadata and comments.",
        ]

    chapter_count = min(4, max(2, (len(merged_points) + 2) // 3))
    duration_s = _estimate_duration_seconds(metadata, frames, len(merged_points))
    chapter_span = max(1, duration_s // chapter_count)

    snippets = _extract_code_snippets(transcript, limit=4)
    chapters: list[dict[str, Any]] = []
    for idx in range(chapter_count):
        chapter_no = idx + 1
        start_s = idx * chapter_span
        end_s = duration_s if chapter_no == chapter_count else max(start_s, (idx + 1) * chapter_span - 1)
        bullet_start = idx * 3
        bullet_end = bullet_start + 3
        bullets = merged_points[bullet_start:bullet_end]
        if not bullets:
            bullets = [f"Chapter {chapter_no} follows the main topic progression."]
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
                "start_link": _timestamp_link(source_url, start_s),
                "end_link": _timestamp_link(source_url, end_s),
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
                "ts_s": _coerce_int(chapter.get("start_s"), 0),
                "label": str(chapter.get("title") or "Chapter"),
                "reason": "chapter_start",
            }
        )
    for frame in frames[:5]:
        if not isinstance(frame, dict):
            continue
        timestamp_references.append(
            {
                "ts_s": _coerce_int(frame.get("timestamp_s"), 0),
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
        "generated_at": _utc_now_iso(),
    }

def _normalize_outline_payload(payload: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(state.get("metadata") or {})
    frames = list(state.get("frames") or [])
    source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")
    fallback = _build_local_outline(state)

    title = str(payload.get("title") or fallback.get("title") or "Untitled Video")
    tldr = _coerce_str_list(payload.get("tldr") or fallback.get("tldr"), limit=8)
    highlights = _coerce_str_list(payload.get("highlights") or fallback.get("highlights"), limit=12)
    actions = _coerce_str_list(
        payload.get("recommended_actions") or payload.get("action_items") or fallback.get("recommended_actions"),
        limit=12,
    )
    pitfalls = _coerce_str_list(payload.get("risk_or_pitfalls") or fallback.get("risk_or_pitfalls"), limit=12)

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

    duration_s = _estimate_duration_seconds(metadata, frames, max(1, len(raw_chapters)))
    chapter_span = max(1, duration_s // max(1, len(raw_chapters)))
    chapters: list[dict[str, Any]] = []
    for idx, chapter in enumerate(raw_chapters, start=1):
        if not isinstance(chapter, dict):
            continue
        chapter_no = _coerce_int(chapter.get("chapter_no"), idx)
        chapter_title = str(chapter.get("title") or chapter.get("heading") or f"Chapter {chapter_no}")
        start_s = _coerce_int(chapter.get("start_s"), (idx - 1) * chapter_span)
        end_s = _coerce_int(
            chapter.get("end_s"),
            duration_s if idx == len(raw_chapters) else max(start_s, idx * chapter_span - 1),
        )
        if end_s < start_s:
            end_s = start_s
        bullets = _coerce_str_list(chapter.get("bullets"), limit=8)
        summary = str(chapter.get("summary") or "").strip() or (bullets[0] if bullets else "（无小结）")
        key_terms = _coerce_str_list(chapter.get("key_terms"), limit=8)
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
                        "range_start_s": _coerce_int(snippet.get("range_start_s"), start_s),
                        "range_end_s": _coerce_int(snippet.get("range_end_s"), end_s),
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
                "start_link": _timestamp_link(source_url, start_s),
                "end_link": _timestamp_link(source_url, end_s),
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
                    "ts_s": _coerce_int(ref.get("ts_s"), 0),
                    "label": str(ref.get("label") or f"Reference {idx}"),
                    "reason": str(ref.get("reason") or ""),
                }
            )
    if not timestamp_references:
        timestamp_references = list(fallback.get("timestamp_references") or [])

    if not tldr:
        tldr = highlights[:4] or _coerce_str_list(fallback.get("tldr"), limit=4)
    if not highlights:
        highlights = _coerce_str_list(fallback.get("highlights"), limit=8)
    if not actions:
        actions = _coerce_str_list(fallback.get("recommended_actions"), limit=8)

    return {
        "title": title,
        "tldr": tldr,
        "highlights": highlights,
        "recommended_actions": actions,
        "risk_or_pitfalls": pitfalls,
        "chapters": chapters,
        "timestamp_references": timestamp_references,
        "generated_by": str(payload.get("generated_by") or fallback.get("generated_by") or "local_rule"),
        "generated_at": str(payload.get("generated_at") or fallback.get("generated_at") or _utc_now_iso()),
    }

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


def _gemini_generate(
    settings: Settings,
    prompt: str,
    *,
    media_path: str | None = None,
    frame_paths: list[str] | None = None,
    llm_input_mode: LLMInputMode = "auto",
) -> tuple[str | None, str]:
    if not settings.gemini_api_key:
        return None, "none"
    try:
        import google.generativeai as genai  # type: ignore
    except Exception:
        return None, "none"

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)
    except Exception:
        return None, "none"

    normalized_mode = _normalize_llm_input_mode(llm_input_mode)
    normalized_media_path = str(media_path or "").strip()
    normalized_frame_paths = list(frame_paths or [])

    should_try_video = normalized_mode in {"auto", "video_text"} and bool(normalized_media_path)
    if should_try_video:
        try:
            upload_fn = getattr(genai, "upload_file", None)
            if callable(upload_fn):
                video_part = upload_fn(path=normalized_media_path)
                response = model.generate_content([video_part, prompt])
                text = _extract_gemini_text(response)
                if text:
                    return text, "video_text"
        except Exception:
            pass

    should_try_frames = normalized_mode in {"auto", "video_text", "frames_text"} and bool(
        normalized_frame_paths
    )
    if should_try_frames:
        try:
            frame_parts = _build_frame_parts(normalized_frame_paths, limit=max(1, settings.pipeline_max_frames))
            if frame_parts:
                response = model.generate_content([prompt, *frame_parts])
                text = _extract_gemini_text(response)
                if text:
                    return text, "frames_text"
        except Exception:
            pass

    if normalized_mode in {"auto", "text"}:
        try:
            response = model.generate_content(prompt)
            text = _extract_gemini_text(response)
            if text:
                return text, "text"
        except Exception:
            pass
    return None, "none"

async def _step_llm_outline(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    metadata = dict(state.get("metadata") or {})
    transcript = str(state.get("transcript") or "")
    comments = dict(state.get("comments") or {})
    frames = list(state.get("frames") or [])
    media_path = str(state.get("media_path") or "")
    frame_paths = _frame_paths_from_frames(frames, limit=max(1, ctx.settings.pipeline_max_frames))
    llm_input_mode = _normalize_llm_input_mode(
        state.get("llm_input_mode") or getattr(ctx.settings, "pipeline_llm_input_mode", "auto")
    )
    title = str(metadata.get("title") or state.get("title") or "")
    source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")
    include_frame_context = bool(frames) and _should_include_frame_prompt(ctx.settings)

    prompt_parts = [
        "Generate a strict JSON outline for a video digest.",
        "Return JSON only, no markdown, no code fence.",
        "Required top-level keys:",
        "title, tldr(array), highlights(array), recommended_actions(array), risk_or_pitfalls(array), chapters(array), timestamp_references(array).",
        "Each chapter object must contain:",
        "chapter_no, title, anchor, start_s, end_s, summary, bullets(array), key_terms(array), code_snippets(array).",
        "Each code_snippets item must contain: title, language, snippet, range_start_s, range_end_s.",
        f"Title: {title}",
        f"Metadata: {json.dumps(_jsonable(metadata), ensure_ascii=False)}",
        f"Transcript (truncated):\n{transcript[:9000]}",
        f"Comment Highlights:\n{_build_comments_prompt_context(comments)}",
    ]
    if include_frame_context:
        prompt_parts.append(
            f"Frame Summaries (for richer grounding):\n{_build_frames_prompt_context(frames, source_url)}"
        )
    prompt = "\n\n".join(prompt_parts)

    generated, media_input = await asyncio.to_thread(
        _gemini_generate,
        ctx.settings,
        prompt,
        media_path=media_path,
        frame_paths=frame_paths,
        llm_input_mode=llm_input_mode,
    )
    if generated:
        try:
            payload = json.loads(_extract_json_object(generated))
            if isinstance(payload, dict):
                outline = _normalize_outline_payload(payload, state)
                outline["generated_by"] = "gemini"
                outline["generated_at"] = _utc_now_iso()
                return StepExecution(
                    status="succeeded",
                    output={
                        "provider": "gemini",
                        "frame_context_used": include_frame_context,
                        "media_input": media_input,
                        "llm_input_mode": llm_input_mode,
                    },
                    state_updates={"outline": outline},
                )
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    outline = _build_local_outline(state)
    return StepExecution(
        status="succeeded",
        output={
            "provider": "local_rule",
            "frame_context_used": include_frame_context,
            "media_input": media_input,
            "llm_input_mode": llm_input_mode,
        },
        state_updates={"outline": outline},
        reason="gemini_unavailable_or_invalid",
        degraded=True,
    )

def _local_digest(state: dict[str, Any]) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    title = str(metadata.get("title") or state.get("title") or "Untitled Video")
    transcript = str(state.get("transcript") or "")
    outline = _normalize_outline_payload(dict(state.get("outline") or {}), state)
    highlights = _coerce_str_list(outline.get("highlights"), limit=8)
    tldr = _coerce_str_list(outline.get("tldr"), limit=6)
    actions = _coerce_str_list(outline.get("recommended_actions"), limit=8)
    if not highlights:
        highlights = _collect_key_points_from_text(transcript, limit=6)
    if not highlights:
        highlights = ["Transcript unavailable, use metadata and comments for understanding."]
    if not tldr:
        tldr = highlights[:4]
    if not actions:
        actions = [f"复盘 {item}" for item in tldr[:3]]
    summary = transcript.strip()[:320] if transcript.strip() else f"Digest generated from metadata: {title}"

    code_blocks = _collect_code_blocks(outline, {})
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
        "fallback_notes": [
            "LLM digest unavailable; this digest is generated from local deterministic rules."
        ],
        "generated_by": "local_rule",
        "generated_at": _utc_now_iso(),
    }

def _normalize_digest_payload(payload: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    fallback = _local_digest(state)
    title = str(payload.get("title") or fallback.get("title") or "Untitled Video")
    summary = str(payload.get("summary") or fallback.get("summary") or "").strip()
    tldr = _coerce_str_list(payload.get("tldr") or fallback.get("tldr"), limit=8)
    highlights = _coerce_str_list(payload.get("highlights") or fallback.get("highlights"), limit=12)
    action_items = _coerce_str_list(
        payload.get("action_items") or payload.get("recommended_actions") or fallback.get("action_items"),
        limit=12,
    )
    fallback_notes = _coerce_str_list(payload.get("fallback_notes") or fallback.get("fallback_notes"), limit=8)

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
                    "range_start_s": _coerce_int(item.get("range_start_s"), 0),
                    "range_end_s": _coerce_int(item.get("range_end_s"), _coerce_int(item.get("range_start_s"), 0)),
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
                    "ts_s": _coerce_int(ref.get("ts_s"), 0),
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
        tldr = highlights[:4] or _coerce_str_list(fallback.get("tldr"), limit=4)
    if not highlights:
        highlights = _coerce_str_list(fallback.get("highlights"), limit=8)
    if not action_items:
        action_items = _coerce_str_list(fallback.get("action_items"), limit=8)

    return {
        "title": title,
        "summary": summary or "No summary generated.",
        "tldr": tldr,
        "highlights": highlights,
        "action_items": action_items,
        "code_blocks": code_blocks,
        "timestamp_references": timestamp_references,
        "fallback_notes": fallback_notes,
        "generated_by": str(payload.get("generated_by") or fallback.get("generated_by") or "local_rule"),
        "generated_at": str(payload.get("generated_at") or fallback.get("generated_at") or _utc_now_iso()),
    }

async def _step_llm_digest(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    metadata = dict(state.get("metadata") or {})
    comments = dict(state.get("comments") or {})
    frames = list(state.get("frames") or [])
    media_path = str(state.get("media_path") or "")
    frame_paths = _frame_paths_from_frames(frames, limit=max(1, ctx.settings.pipeline_max_frames))
    llm_input_mode = _normalize_llm_input_mode(
        state.get("llm_input_mode") or getattr(ctx.settings, "pipeline_llm_input_mode", "auto")
    )
    source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")
    include_frame_context = bool(frames) and _should_include_frame_prompt(ctx.settings)

    outline = _normalize_outline_payload(dict(state.get("outline") or {}), state)
    prompt_parts = [
        "Generate digest JSON based on the provided outline.",
        "Return JSON only, no markdown, no code fence.",
        "Required keys: title, summary, tldr(array), highlights(array), action_items(array), code_blocks(array), timestamp_references(array), fallback_notes(array).",
        "Code block item schema: {title, language, snippet, range_start_s, range_end_s}.",
        "Timestamp reference schema: {ts_s, label, reason}.",
        f"Metadata:\n{json.dumps(_jsonable(metadata), ensure_ascii=False)}",
        f"Outline:\n{json.dumps(_jsonable(outline), ensure_ascii=False)}",
        f"Transcript (truncated):\n{str(state.get('transcript') or '')[:9000]}",
        f"Comment Highlights:\n{_build_comments_prompt_context(comments)}",
    ]
    if include_frame_context:
        prompt_parts.append(
            f"Frame Summaries (optional grounding):\n{_build_frames_prompt_context(frames, source_url)}"
        )
    prompt = "\n\n".join(prompt_parts)

    generated, media_input = await asyncio.to_thread(
        _gemini_generate,
        ctx.settings,
        prompt,
        media_path=media_path,
        frame_paths=frame_paths,
        llm_input_mode=llm_input_mode,
    )
    if generated:
        try:
            payload = json.loads(_extract_json_object(generated))
            if isinstance(payload, dict):
                digest = _normalize_digest_payload(payload, state)
                digest["generated_by"] = "gemini"
                digest["generated_at"] = _utc_now_iso()
                return StepExecution(
                    status="succeeded",
                    output={
                        "provider": "gemini",
                        "frame_context_used": include_frame_context,
                        "media_input": media_input,
                        "llm_input_mode": llm_input_mode,
                    },
                    state_updates={"digest": digest},
                )
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    digest = _normalize_digest_payload(_local_digest(state), state)
    return StepExecution(
        status="succeeded",
        output={
            "provider": "local_rule",
            "frame_context_used": include_frame_context,
            "media_input": media_input,
            "llm_input_mode": llm_input_mode,
        },
        state_updates={"digest": digest},
        reason="gemini_unavailable_or_invalid",
        degraded=True,
    )

async def _step_write_artifacts(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    try:
        template = _load_digest_template(ctx.settings)
        metadata = dict(state.get("metadata") or {})
        source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")
        outline = _normalize_outline_payload(dict(state.get("outline") or {}), state)
        digest_state = dict(state)
        digest_state["outline"] = outline
        digest = _normalize_digest_payload(dict(state.get("digest") or {}), digest_state)
        comments = dict(state.get("comments") or empty_comments_payload())
        transcript = str(state.get("transcript") or "")
        degradations = list(state.get("degradations") or [])
        frames = list(state.get("frames") or [])

        tldr = [str(item) for item in (digest.get("tldr") or []) if str(item).strip()]
        highlights = [str(item) for item in (digest.get("highlights") or []) if str(item).strip()]
        action_items = [str(item) for item in (digest.get("action_items") or []) if str(item).strip()]
        if not highlights:
            highlights = ["No highlight extracted."]
        if not tldr:
            tldr = highlights[:4]
        if not action_items:
            action_items = [f"复盘：{item}" for item in highlights[:3]]

        degradation_lines = [
            f"- {item.get('step')}: {item.get('status')} ({item.get('reason') or 'n/a'})"
            for item in degradations
            if isinstance(item, dict)
        ]
        if not degradation_lines:
            degradation_lines = ["- none"]

        rendered_digest = _render_template(
            template,
            {
                "title": str(
                    digest.get("title") or metadata.get("title") or state.get("title") or "Untitled Video"
                ),
                "source_url": source_url,
                "platform": str(state.get("platform") or ""),
                "video_uid": str(state.get("video_uid") or ""),
                "generated_at": _utc_now_iso(),
                "summary": str(digest.get("summary") or "No summary generated."),
                "tldr_markdown": "\n".join(f"- {item}" for item in tldr),
                "highlights_markdown": "\n".join(f"- {item}" for item in highlights),
                "action_items_markdown": "\n".join(f"- [ ] {item}" for item in action_items),
                "chapters_toc_markdown": _build_chapters_toc_markdown(outline, source_url),
                "chapters_markdown": _build_chapters_markdown(outline, source_url),
                "code_blocks_markdown": _build_code_blocks_markdown(outline, digest, source_url),
                "comments_markdown": _build_comments_markdown(comments),
                "frames_index_markdown": _build_frames_markdown(frames, source_url),
                "timestamp_refs_markdown": _build_timestamp_refs_markdown(outline, digest, source_url),
                "fallback_notes_markdown": _build_fallback_notes_markdown(digest, degradations),
                "degradations_markdown": "\n".join(degradation_lines),
            },
        )

        meta_payload = {
            "job": ctx.job_record,
            "metadata": metadata,
            "download_mode": state.get("download_mode"),
            "media_path": state.get("media_path"),
            "subtitle_files": state.get("subtitle_files") or [],
            "frame_files": [item.get("path") for item in frames if isinstance(item, dict)],
            "degradations": degradations,
            "generated_at": _utc_now_iso(),
        }

        meta_path = ctx.artifacts_dir / "meta.json"
        comments_path = ctx.artifacts_dir / "comments.json"
        transcript_path = ctx.artifacts_dir / "transcript.txt"
        outline_path = ctx.artifacts_dir / "outline.json"
        digest_path = ctx.artifacts_dir / "digest.md"

        _write_json(meta_path, meta_payload)
        _write_json(comments_path, comments)
        transcript_path.write_text(transcript, encoding="utf-8")
        _write_json(outline_path, outline)
        digest_path.write_text(rendered_digest, encoding="utf-8")

        return StepExecution(
            status="succeeded",
            output={
                "artifact_dir": str(ctx.artifacts_dir.resolve()),
                "files": {
                    "meta": str(meta_path.resolve()),
                    "comments": str(comments_path.resolve()),
                    "transcript": str(transcript_path.resolve()),
                    "outline": str(outline_path.resolve()),
                    "digest": str(digest_path.resolve()),
                },
            },
            state_updates={
                "artifact_dir": str(ctx.artifacts_dir.resolve()),
                "artifacts": {
                    "meta": str(meta_path.resolve()),
                    "comments": str(comments_path.resolve()),
                    "transcript": str(transcript_path.resolve()),
                    "outline": str(outline_path.resolve()),
                    "digest": str(digest_path.resolve()),
                },
            },
        )
    except Exception as exc:
        return StepExecution(
            status="failed",
            reason="write_artifacts_failed",
            error=str(exc),
            degraded=True,
        )

def _resolve_pipeline_status(step_records: dict[str, dict[str, Any]]) -> PipelineStatus:
    write_step = step_records.get("write_artifacts") or {}
    if write_step.get("status") == "failed":
        return "failed"

    statuses = [record.get("status") for record in step_records.values()]
    if all(status == "succeeded" for status in statuses):
        return "succeeded"
    if any(status in {"failed", "skipped"} for status in statuses):
        return "partial"
    return "failed"

async def run_pipeline(
    settings: Settings,
    sqlite_store: SQLiteStateStore,
    pg_store: PostgresBusinessStore,
    *,
    job_id: str,
    attempt: int,
    mode: str = "full",
) -> dict[str, Any]:
    pipeline_mode = _normalize_pipeline_mode(mode)
    llm_input_mode = _normalize_llm_input_mode(getattr(settings, "pipeline_llm_input_mode", "auto"))
    ctx = _build_context(settings, sqlite_store, pg_store, job_id=job_id, attempt=attempt)
    checkpoint = sqlite_store.get_checkpoint(job_id)
    checkpoint_step = str((checkpoint or {}).get("last_completed_step") or "")
    checkpoint_payload = dict((checkpoint or {}).get("payload") or {})
    resume_upto_idx = PIPELINE_STEPS.index(checkpoint_step) if checkpoint_step in PIPELINE_STEPS else -1

    state: dict[str, Any] = {
        "job_id": job_id,
        "attempt": attempt,
        "mode": pipeline_mode,
        "source_url": ctx.job_record.get("source_url"),
        "title": ctx.job_record.get("title"),
        "platform": ctx.job_record.get("platform"),
        "video_uid": ctx.job_record.get("video_uid"),
        "published_at": ctx.job_record.get("published_at"),
        "metadata": {},
        "media_path": None,
        "download_mode": "text_only",
        "subtitle_files": [],
        "transcript": "",
        "comments": empty_comments_payload(),
        "frames": [],
        "llm_input_mode": llm_input_mode,
        "llm_media_input": {"video_available": False, "frame_count": 0},
        "outline": {},
        "digest": {},
        "artifacts": {},
        "degradations": [],
        "steps": {},
        "resume": {
            "checkpoint_step": checkpoint_step or None,
            "checkpoint_payload": checkpoint_payload,
            "resume_upto_idx": resume_upto_idx,
        },
    }
    _refresh_llm_media_input_dimension(state)

    step_handlers: list[tuple[str, Callable[[PipelineContext, dict[str, Any]], Any], bool]] = [
        ("fetch_metadata", _step_fetch_metadata, False),
        ("download_media", _step_download_media, False),
        ("collect_subtitles", _step_collect_subtitles, False),
        ("collect_comments", _step_collect_comments, False),
        ("extract_frames", _step_extract_frames, False),
        ("llm_outline", _step_llm_outline, False),
        ("llm_digest", _step_llm_digest, False),
        ("write_artifacts", _step_write_artifacts, True),
    ]

    mode_skip_steps = PIPELINE_MODE_SKIP_STEPS.get(pipeline_mode, set())
    mode_force_steps = PIPELINE_MODE_FORCE_STEPS.get(pipeline_mode, set())
    for step_idx, (step_name, handler, critical) in enumerate(step_handlers):
        is_mode_skipped = step_name in mode_skip_steps
        force_run = step_name in mode_force_steps or is_mode_skipped
        await _execute_step(
            ctx,
            state,
            step_name=step_name,
            step_func=_build_mode_skip_step(step_name, pipeline_mode) if is_mode_skipped else handler,
            critical=critical,
            resume_hint=(step_idx <= resume_upto_idx) and not force_run,
            force_run=force_run,
        )

    final_status = _resolve_pipeline_status(state["steps"])
    return {
        "job_id": job_id,
        "attempt": attempt,
        "mode": pipeline_mode,
        "final_status": final_status,
        "steps": state["steps"],
        "artifact_dir": state.get("artifact_dir"),
        "artifacts": state.get("artifacts", {}),
        "degradations": state.get("degradations", []),
        "llm_input_mode": state.get("llm_input_mode"),
        "llm_media_input": state.get("llm_media_input"),
        "resume": state.get("resume", {}),
        "fatal_error": state.get("fatal_error"),
        "completed_at": _utc_now_iso(),
    }
