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
import shutil
import subprocess
from typing import Any, Callable, Literal
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

from worker.comments import (
    BilibiliCommentCollector,
    YouTubeCommentCollector,
    empty_comments_payload,
)
from worker.config import Settings
from worker.pipeline.runner_policies import (
    apply_comments_policy as _apply_comments_policy,
    build_comments_policy as _build_comments_policy,
    build_frame_policy as _build_frame_policy,
    build_llm_policy as _build_llm_policy,
    build_llm_policy_section as _build_llm_policy_section,
    coerce_bool as _coerce_bool,
    coerce_float as _coerce_float,
    coerce_int as _coerce_int,
    coerce_str_list as _coerce_str_list,
    dedupe_keep_order as _dedupe_keep_order,
    default_comment_sort_for_platform as _default_comment_sort_for_platform,
    digest_is_chinese as _digest_is_chinese,
    extract_json_object as _extract_json_object,
    frame_paths_from_frames as _frame_paths_from_frames,
    llm_media_input_dimension as _llm_media_input_dimension,
    normalize_llm_input_mode as _normalize_llm_input_mode,
    normalize_overrides_payload as _normalize_overrides_payload,
    normalize_pipeline_mode as _normalize_pipeline_mode,
    outline_is_chinese as _outline_is_chinese,
    override_section as _override_section,
    refresh_llm_media_input_dimension as _refresh_llm_media_input_dimension,
)
from worker.pipeline.runner_rendering import (
    build_artifact_asset_url as _build_artifact_asset_url,
    build_chapters_markdown as _build_chapters_markdown,
    build_chapters_toc_markdown as _build_chapters_toc_markdown,
    build_code_blocks_markdown as _build_code_blocks_markdown,
    build_comments_markdown as _build_comments_markdown,
    build_comments_prompt_context as _build_comments_prompt_context,
    build_fallback_notes_markdown as _build_fallback_notes_markdown,
    build_frames_embedded_markdown as _build_frames_embedded_markdown,
    build_frames_markdown as _build_frames_markdown,
    build_frames_prompt_context as _build_frames_prompt_context,
    build_timestamp_refs_markdown as _build_timestamp_refs_markdown,
    collect_code_blocks as _collect_code_blocks,
    estimate_duration_seconds as _estimate_duration_seconds,
    extract_code_snippets as _extract_code_snippets,
    format_seconds as _format_seconds,
    load_digest_template as _load_digest_template,
    materialize_frames_for_artifacts as _materialize_frames_for_artifacts,
    parse_duration_seconds as _parse_duration_seconds,
    render_template as _render_template,
    should_include_frame_prompt as _should_include_frame_prompt,
    timestamp_link as _timestamp_link,
)
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
STEP_VERSIONS["download_media"] = "v2"
STEP_VERSIONS["collect_subtitles"] = "v2"
STEP_VERSIONS["collect_comments"] = "v4"
STEP_VERSIONS["llm_outline"] = "v3"
STEP_VERSIONS["llm_digest"] = "v4"
STEP_VERSIONS["write_artifacts"] = "v2"
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
    "collect_subtitles": ("media_path", "download_mode", "source_url", "platform", "video_uid"),
    "collect_comments": ("source_url", "platform", "video_uid", "comments_policy"),
    "extract_frames": ("media_path", "frame_policy"),
    "llm_outline": (
        "title",
        "metadata",
        "transcript",
        "comments",
        "frames",
        "source_url",
        "llm_input_mode",
        "llm_media_input",
        "llm_policy",
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
        "llm_policy",
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
    "download_media": ("pipeline_subprocess_timeout_seconds", "bilibili_downloader"),
    "collect_subtitles": (
        "pipeline_subprocess_timeout_seconds",
        "youtube_transcript_fallback_enabled",
        "asr_fallback_enabled",
        "asr_model_size",
    ),
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
    "llm_outline": (
        "gemini_model",
        "gemini_outline_model",
        "pipeline_max_frames",
        "pipeline_llm_input_mode",
    ),
    "llm_digest": (
        "gemini_model",
        "gemini_digest_model",
        "pipeline_max_frames",
        "pipeline_llm_input_mode",
    ),
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

    if str(cache_info.get("version") or "v1") != "v1":
        return None, None

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


def _normalize_bilibili_downloader(value: Any) -> str:
    text = str(value or "auto").strip().lower()
    if text in {"auto", "yt-dlp", "bbdown"}:
        return text
    return "auto"


def _build_download_provider_chain(platform: str, settings: Settings) -> list[str]:
    if platform != "bilibili":
        return ["yt-dlp"]
    selected = _normalize_bilibili_downloader(getattr(settings, "bilibili_downloader", "auto"))
    if selected == "auto":
        return ["yt-dlp", "bbdown"]
    return [selected]


def _yt_dlp_download_command(source_url: str, output_tmpl: str) -> list[str]:
    return [
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


def _bbdown_commands(source_url: str, download_dir: Path) -> list[list[str]]:
    target_dir = str(download_dir.resolve())
    return [
        ["BBDown", source_url, "--work-dir", target_dir, "--save-subtitle"],
        ["bbdown", source_url, "--work-dir", target_dir, "--save-subtitle"],
    ]


def _extract_media_file(download_dir: Path, command_stdout: str) -> str | None:
    for line in reversed(command_stdout.splitlines()):
        candidate = line.strip()
        if not candidate:
            continue
        if Path(candidate).exists():
            return str(Path(candidate).resolve())

    suffixes = {".mp4", ".mkv", ".webm", ".flv", ".mov", ".m4v", ".ts"}
    files = sorted(
        [
            p
            for p in download_dir.glob("*")
            if p.is_file()
            and p.suffix.lower() not in {".part", ".tmp"}
            and (p.name.startswith("media.") or p.suffix.lower() in suffixes)
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if files:
        return str(files[0].resolve())
    return None


def _subtitle_candidates(download_dir: Path) -> list[Path]:
    return sorted(
        [p for p in download_dir.glob("*.vtt") if p.is_file()]
        + [p for p in download_dir.glob("*.srt") if p.is_file()]
        + [p for p in download_dir.glob("*.ass") if p.is_file()]
    )


def _collect_subtitle_text_from_files(
    subtitle_candidates: list[Path], *, limit: int = 6
) -> tuple[str, list[str]]:
    transcript_chunks: list[str] = []
    subtitle_files: list[str] = []
    for path in subtitle_candidates[:limit]:
        text = _subtitle_to_text(_read_text_file(path))
        if text:
            transcript_chunks.append(text)
        subtitle_files.append(str(path.resolve()))
    transcript = "\n".join(chunk for chunk in transcript_chunks if chunk).strip()
    return transcript, subtitle_files


def _extract_youtube_video_id(source_url: str | None, video_uid: str | None) -> str:
    uid = str(video_uid or "").strip()
    if uid:
        return uid

    raw = str(source_url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    if host == "youtu.be":
        return parsed.path.strip("/").split("/")[0]
    if "youtube.com" not in host:
        return ""
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    candidate = str(query.get("v") or "").strip()
    if candidate:
        return candidate
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "shorts":
        return parts[1]
    return ""


def _fetch_youtube_transcript_text(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore[import-not-found]

    languages = ["zh-Hans", "zh-Hant", "zh", "en", "en-US"]
    entries: Any = None

    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        entries = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
    else:
        api = YouTubeTranscriptApi()  # type: ignore[operator]
        if hasattr(api, "get_transcript"):
            entries = api.get_transcript(video_id, languages=languages)  # type: ignore[call-arg]
        elif hasattr(api, "fetch"):
            try:
                entries = api.fetch(video_id, languages=languages)  # type: ignore[call-arg]
            except TypeError:
                entries = api.fetch(video_id)  # type: ignore[call-arg]

    lines: list[str] = []
    if isinstance(entries, list):
        iterable = entries
    else:
        iterable = list(entries or [])
    for item in iterable:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
        else:
            text = str(getattr(item, "text", "") or "").strip()
        if text:
            lines.append(text)
    return "\n".join(lines).strip()


def _collect_asr_output_text(download_dir: Path, media_path: str) -> str:
    media_stem = Path(media_path).stem
    preferred = download_dir / f"{media_stem}.txt"
    candidates: list[Path] = []
    if preferred.exists() and preferred.is_file():
        candidates.append(preferred)
    candidates.extend(
        sorted(
            [
                p
                for p in download_dir.glob("*.txt")
                if p.is_file() and p.name not in {preferred.name}
            ],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    )
    for path in candidates:
        text = _read_text_file(path).strip()
        if text:
            return text
    return ""


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
            json.dumps(_jsonable(payload), ensure_ascii=False),
        ]
    )
    translated_raw, _ = _gemini_generate(
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
        parsed = json.loads(_extract_json_object(translated_raw))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if isinstance(parsed, dict):
        return parsed
    return None

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
    platform = str(state.get("platform") or "").strip().lower()
    if not source_url:
        return StepExecution(
            status="skipped",
            state_updates={"media_path": None, "download_mode": "text_only"},
            reason="source_url_missing",
            degraded=True,
        )

    providers = _build_download_provider_chain(platform, ctx.settings)
    output_tmpl = str((ctx.download_dir / "media.%(ext)s").resolve())
    attempts: list[dict[str, Any]] = []
    for provider in providers:
        provider_result: CommandResult | None = None
        if provider == "yt-dlp":
            provider_result = await _run_command(
                ctx,
                _yt_dlp_download_command(source_url, output_tmpl),
            )
        elif provider == "bbdown":
            for cmd in _bbdown_commands(source_url, ctx.download_dir):
                provider_result = await _run_command(ctx, cmd)
                if provider_result.ok:
                    break
                if provider_result.reason != "binary_not_found":
                    break
            if provider_result is None:
                provider_result = CommandResult(ok=False, reason="binary_not_found")
        else:
            provider_result = CommandResult(ok=False, reason="provider_unsupported")

        media_path = _extract_media_file(ctx.download_dir, provider_result.stdout)
        if provider_result.ok and media_path:
            return StepExecution(
                status="succeeded",
                output={"mode": "media", "provider": provider, "providers_tried": providers},
                state_updates={"media_path": media_path, "download_mode": "media"},
            )

        reason = provider_result.reason or "provider_failed"
        if provider_result.ok and not media_path:
            reason = "media_not_found_after_download"
        attempts.append(
            {
                "provider": provider,
                "reason": reason,
                "error": (provider_result.stderr or "").strip()[-500:] or reason,
                "returncode": provider_result.returncode,
            }
        )

    only_binary_missing = bool(attempts) and all(
        str(item.get("reason")) == "binary_not_found" for item in attempts
    )
    status: StepStatus = "skipped" if only_binary_missing else "failed"
    last_attempt = attempts[-1] if attempts else {}
    return StepExecution(
        status=status,
        output={"mode": "text_only", "providers_tried": providers, "attempts": attempts},
        state_updates={"media_path": None, "download_mode": "text_only"},
        reason=str(last_attempt.get("reason") or "download_provider_chain_failed"),
        error=str(last_attempt.get("error") or "download_provider_chain_failed"),
        degraded=True,
    )

async def _step_collect_subtitles(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    subtitle_candidates = _subtitle_candidates(ctx.download_dir)
    transcript, subtitle_files = _collect_subtitle_text_from_files(subtitle_candidates)
    if transcript:
        return StepExecution(
            status="succeeded",
            output={
                "subtitle_files": len(subtitle_files),
                "transcript_provider": "downloaded_subtitles",
                "fallback_used": False,
            },
            state_updates={"transcript": transcript, "subtitle_files": subtitle_files},
        )

    failure_reasons: list[str] = []
    if subtitle_files:
        failure_reasons.append("subtitle_text_empty_after_parse")
    else:
        failure_reasons.append("subtitle_file_not_found")

    source_url = str(state.get("source_url") or "").strip()
    video_uid = str(state.get("video_uid") or "").strip()
    platform = str(state.get("platform") or "").strip().lower()
    if (
        platform == "youtube"
        and _coerce_bool(getattr(ctx.settings, "youtube_transcript_fallback_enabled", True), default=True)
    ):
        video_id = _extract_youtube_video_id(source_url, video_uid)
        if video_id:
            try:
                yt_transcript = await asyncio.to_thread(_fetch_youtube_transcript_text, video_id)
                if yt_transcript.strip():
                    return StepExecution(
                        status="succeeded",
                        output={
                            "subtitle_files": len(subtitle_files),
                            "transcript_provider": "youtube_transcript_fallback",
                            "fallback_used": True,
                        },
                        state_updates={
                            "transcript": yt_transcript.strip(),
                            "subtitle_files": subtitle_files,
                        },
                    )
                failure_reasons.append("youtube_transcript_empty")
            except Exception as exc:
                failure_reasons.append(f"youtube_transcript_failed:{exc.__class__.__name__}")
        else:
            failure_reasons.append("youtube_video_id_not_resolved")
    else:
        failure_reasons.append("youtube_transcript_fallback_disabled_or_not_youtube")

    if _coerce_bool(getattr(ctx.settings, "asr_fallback_enabled", False), default=False):
        media_path = str(state.get("media_path") or "").strip()
        if media_path:
            asr_model_size = str(getattr(ctx.settings, "asr_model_size", "small") or "small").strip()
            asr_failure_reasons: list[str] = []
            asr_commands = [
                [
                    "whisper",
                    media_path,
                    "--model",
                    asr_model_size,
                    "--task",
                    "transcribe",
                    "--output_format",
                    "txt",
                    "--output_dir",
                    str(ctx.download_dir.resolve()),
                ],
                [
                    "faster-whisper",
                    media_path,
                    "--model",
                    asr_model_size,
                    "--output_dir",
                    str(ctx.download_dir.resolve()),
                    "--output_format",
                    "txt",
                ],
            ]
            for cmd in asr_commands:
                result = await _run_command(ctx, cmd)
                if result.ok:
                    asr_text = _collect_asr_output_text(ctx.download_dir, media_path)
                    if asr_text:
                        return StepExecution(
                            status="succeeded",
                            output={
                                "subtitle_files": len(subtitle_files),
                                "transcript_provider": "asr_fallback",
                                "asr_model_size": asr_model_size,
                                "fallback_used": True,
                            },
                            state_updates={
                                "transcript": asr_text,
                                "subtitle_files": subtitle_files,
                            },
                        )
                    asr_failure_reasons.append("asr_transcript_empty")
                    continue
                asr_failure_reasons.append(result.reason or "asr_command_failed")
                if result.reason != "binary_not_found":
                    break
            if asr_failure_reasons:
                failure_reasons.append(f"asr_failed:{'|'.join(asr_failure_reasons)}")
        else:
            failure_reasons.append("asr_media_path_missing")
    else:
        failure_reasons.append("asr_fallback_disabled")

    return StepExecution(
        status="succeeded",
        output={
            "subtitle_files": len(subtitle_files),
            "transcript_provider": "none",
            "fallback_chain": failure_reasons,
        },
        state_updates={"transcript": "", "subtitle_files": subtitle_files},
        reason=failure_reasons[-1] if failure_reasons else "subtitle_unavailable",
        degraded=True,
    )

async def _step_collect_comments(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    platform = str(state.get("platform") or "").lower()
    source_url = str(state.get("source_url") or "")
    video_uid = str(state.get("video_uid") or "")
    comments_policy = dict(state.get("comments_policy") or {})
    top_n = max(1, _coerce_int(comments_policy.get("top_n"), ctx.settings.comments_top_n))
    replies_per_comment = max(
        0,
        _coerce_int(
            comments_policy.get("replies_per_comment"),
            ctx.settings.comments_replies_per_comment,
        ),
    )
    requested_sort = str(comments_policy.get("sort") or _default_comment_sort_for_platform(platform))
    if platform == "bilibili":
        collector = BilibiliCommentCollector(
            top_n=top_n,
            replies_per_comment=replies_per_comment,
            request_timeout_seconds=ctx.settings.comments_request_timeout_seconds,
            retry_attempts=ctx.settings.request_retry_attempts,
            retry_backoff_seconds=ctx.settings.request_retry_backoff_seconds,
            cookie=getattr(ctx.settings, "bilibili_cookie", None),
        )
        try:
            comments_payload = await collector.collect(source_url=source_url, video_uid=video_uid)
        except Exception as exc:
            return StepExecution(
                status="succeeded",
                output={"count": 0, "provider": "bilibili"},
                state_updates={
                    "comments": _apply_comments_policy(
                        empty_comments_payload(sort=requested_sort),
                        policy=comments_policy,
                        platform=platform,
                    )
                },
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
                state_updates={
                    "comments": _apply_comments_policy(
                        empty_comments_payload(sort=requested_sort),
                        policy=comments_policy,
                        platform=platform,
                    )
                },
                reason="youtube_api_key_missing",
                error="youtube_api_key_missing",
                error_kind="auth",
                degraded=True,
            )
        collector = YouTubeCommentCollector(
            api_key=str(ctx.settings.youtube_api_key or ""),
            top_n=top_n,
            replies_per_comment=replies_per_comment,
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
                state_updates={
                    "comments": _apply_comments_policy(
                        empty_comments_payload(sort=requested_sort),
                        policy=comments_policy,
                        platform=platform,
                    )
                },
                reason="youtube_comments_collection_failed_degraded",
                error=str(exc)[:500],
                error_kind=_classify_error("youtube_comments_collection_failed_degraded", str(exc)),
                degraded=True,
            )
    else:
        return StepExecution(
            status="skipped",
            output={"count": 0},
            state_updates={
                "comments": _apply_comments_policy(
                    empty_comments_payload(sort=requested_sort),
                    policy=comments_policy,
                    platform=platform,
                )
            },
            reason="comments_collection_skipped_platform_unsupported",
            degraded=True,
        )

    comments_payload = _apply_comments_policy(
        dict(comments_payload or {}),
        policy=comments_policy,
        platform=platform,
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

    frame_policy = dict(state.get("frame_policy") or {})
    frame_interval = max(1, int(ctx.settings.pipeline_frame_interval_seconds))
    frame_method = str(frame_policy.get("method") or "fps").strip().lower()
    if frame_method not in {"fps", "scene"}:
        frame_method = "fps"
    max_frames = max(1, _coerce_int(frame_policy.get("max_frames"), int(ctx.settings.pipeline_max_frames)))
    output_pattern = str((ctx.frames_dir / "frame_%03d.jpg").resolve())
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(media_path),
    ]
    if frame_method == "scene":
        cmd += [
            "-vf",
            "select='gt(scene,0.3)'",
            "-vsync",
            "vfr",
        ]
    else:
        cmd += [
            "-vf",
            f"fps=1/{frame_interval}",
        ]
    cmd += [
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
        output={"frames": len(frames_meta), "method": frame_method, "max_frames": max_frames},
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
            f"本期核心主题：{title}",
            "字幕缺失，以下导读基于元信息与评论区自动生成。",
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
        model = genai.GenerativeModel(model_name)
    except Exception:
        return None, "none"

    normalized_mode = _normalize_llm_input_mode(llm_input_mode)
    normalized_media_path = str(media_path or "").strip()
    normalized_frame_paths = list(frame_paths or [])
    generation_config: dict[str, Any] = {}
    if temperature is not None:
        generation_config["temperature"] = temperature
    if max_output_tokens is not None:
        generation_config["max_output_tokens"] = max_output_tokens

    def _generate_content(content: Any) -> Any:
        if generation_config:
            return model.generate_content(content, generation_config=generation_config)
        return model.generate_content(content)

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

    should_try_frames = normalized_mode in {"auto", "video_text", "frames_text"} and bool(
        normalized_frame_paths
    )
    if should_try_frames:
        try:
            frame_parts = _build_frame_parts(normalized_frame_paths, limit=max(1, settings.pipeline_max_frames))
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
    llm_temperature = _coerce_float(
        llm_outline_policy.get("temperature"),
        _coerce_float(llm_policy.get("temperature"), None),
    )
    llm_max_output_tokens = (
        _coerce_int(
            llm_outline_policy.get("max_output_tokens"),
            _coerce_int(llm_policy.get("max_output_tokens"), 0),
        )
        or None
    )
    title = str(metadata.get("title") or state.get("title") or "")
    source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")
    include_frame_context = bool(frames) and _should_include_frame_prompt(ctx.settings)

    prompt_parts = [
        "为视频摘要生成严格 JSON 大纲。",
        "只返回 JSON，不要 Markdown，不要代码块围栏。",
        "所有面向读者的字段必须使用简体中文（专有名词、产品名、代码标识可保留英文）。",
        "顶层必填字段：title, tldr(array), highlights(array), recommended_actions(array), risk_or_pitfalls(array), chapters(array), timestamp_references(array)。",
        "chapter 对象必填：chapter_no, title, anchor, start_s, end_s, summary, bullets(array), key_terms(array), code_snippets(array)。",
        "code_snippets 项必填：title, language, snippet, range_start_s, range_end_s。",
        "内容风格：人类可读，避免空话，不要重复，不要编造无法从输入中确认的事实。",
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
        model=llm_model,
        temperature=llm_temperature,
        max_output_tokens=llm_max_output_tokens,
    )
    if generated:
        try:
            payload = json.loads(_extract_json_object(generated))
            if isinstance(payload, dict):
                translated_to_zh = False
                if not _outline_is_chinese(payload):
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
                        "model": llm_model,
                        "temperature": llm_temperature,
                        "max_output_tokens": llm_max_output_tokens,
                        "translated_to_zh": translated_to_zh,
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
            "model": llm_model,
            "temperature": llm_temperature,
            "max_output_tokens": llm_max_output_tokens,
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
        highlights = ["未获取到有效字幕，以下内容基于标题、简介与评论区生成。"]
    if not tldr:
        tldr = highlights[:4]
    if not actions:
        actions = [f"复盘 {item}" for item in tldr[:3]]
    summary = transcript.strip()[:320] if transcript.strip() else f"该摘要基于视频元信息自动生成：{title}"

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
            "LLM 摘要不可用，当前内容由本地规则降级生成。"
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
        "summary": summary or "未生成摘要。",
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
    llm_temperature = _coerce_float(
        llm_digest_policy.get("temperature"),
        _coerce_float(llm_policy.get("temperature"), None),
    )
    llm_max_output_tokens = (
        _coerce_int(
            llm_digest_policy.get("max_output_tokens"),
            _coerce_int(llm_policy.get("max_output_tokens"), 0),
        )
        or None
    )
    source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")
    include_frame_context = bool(frames) and _should_include_frame_prompt(ctx.settings)

    outline = _normalize_outline_payload(dict(state.get("outline") or {}), state)
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
        model=llm_model,
        temperature=llm_temperature,
        max_output_tokens=llm_max_output_tokens,
    )
    if generated:
        try:
            payload = json.loads(_extract_json_object(generated))
            if isinstance(payload, dict):
                translated_to_zh = False
                if not _digest_is_chinese(payload):
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
                        "model": llm_model,
                        "temperature": llm_temperature,
                        "max_output_tokens": llm_max_output_tokens,
                        "translated_to_zh": translated_to_zh,
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
            "model": llm_model,
            "temperature": llm_temperature,
            "max_output_tokens": llm_max_output_tokens,
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
        raw_frames = list(state.get("frames") or [])
        frames, frame_files = _materialize_frames_for_artifacts(raw_frames, ctx.artifacts_dir)

        tldr = [str(item) for item in (digest.get("tldr") or []) if str(item).strip()]
        highlights = [str(item) for item in (digest.get("highlights") or []) if str(item).strip()]
        action_items = [str(item) for item in (digest.get("action_items") or []) if str(item).strip()]
        if not highlights:
            highlights = ["未提取到高置信度要点。"]
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
            degradation_lines = ["- 无明显降级。"]

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
                "summary": str(digest.get("summary") or "未生成摘要。"),
                "tldr_markdown": "\n".join(f"- {item}" for item in tldr),
                "highlights_markdown": "\n".join(f"- {item}" for item in highlights),
                "action_items_markdown": "\n".join(f"- [ ] {item}" for item in action_items),
                "chapters_toc_markdown": _build_chapters_toc_markdown(outline, source_url),
                "chapters_markdown": _build_chapters_markdown(outline, source_url),
                "code_blocks_markdown": _build_code_blocks_markdown(outline, digest, source_url),
                "comments_markdown": _build_comments_markdown(comments),
                "frames_embedded_markdown": _build_frames_embedded_markdown(frames, ctx.job_id),
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
            "frame_files": frame_files,
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
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pipeline_mode = _normalize_pipeline_mode(mode)
    llm_input_mode = _normalize_llm_input_mode(getattr(settings, "pipeline_llm_input_mode", "auto"))
    ctx = _build_context(settings, sqlite_store, pg_store, job_id=job_id, attempt=attempt)
    resolved_overrides = _normalize_overrides_payload(overrides)
    if not resolved_overrides:
        resolved_overrides = _normalize_overrides_payload(ctx.job_record.get("overrides_json"))
    platform = str(ctx.job_record.get("platform") or "").strip().lower()
    comments_policy = _build_comments_policy(settings, resolved_overrides, platform=platform)
    frame_policy = _build_frame_policy(settings, resolved_overrides)
    llm_policy = _build_llm_policy(settings, resolved_overrides)
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
        "overrides": resolved_overrides,
        "comments_policy": comments_policy,
        "frame_policy": frame_policy,
        "llm_policy": llm_policy,
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
