from __future__ import annotations

import asyncio
from pathlib import Path
import re
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qsl, urlparse

from worker.pipeline.policies import coerce_bool
from worker.pipeline.types import CommandResult, PipelineContext, StepExecution


def subtitle_candidates(download_dir: Path) -> list[Path]:
    return sorted(
        [p for p in download_dir.glob("*.vtt") if p.is_file()]
        + [p for p in download_dir.glob("*.srt") if p.is_file()]
        + [p for p in download_dir.glob("*.ass") if p.is_file()]
    )


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def subtitle_to_text(raw_content: str) -> str:
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


def collect_subtitle_text_from_files(
    subtitle_files: list[Path],
    *,
    limit: int = 6,
) -> tuple[str, list[str]]:
    transcript_chunks: list[str] = []
    used_files: list[str] = []
    for path in subtitle_files[:limit]:
        text = subtitle_to_text(read_text_file(path))
        if text:
            transcript_chunks.append(text)
        used_files.append(str(path.resolve()))
    transcript = "\n".join(chunk for chunk in transcript_chunks if chunk).strip()
    return transcript, used_files


def extract_youtube_video_id(source_url: str | None, video_uid: str | None) -> str:
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


def fetch_youtube_transcript_text(video_id: str) -> str:
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
    iterable = entries if isinstance(entries, list) else list(entries or [])
    for item in iterable:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
        else:
            text = str(getattr(item, "text", "") or "").strip()
        if text:
            lines.append(text)
    return "\n".join(lines).strip()


def collect_asr_output_text(download_dir: Path, media_path: str) -> str:
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
        text = read_text_file(path).strip()
        if text:
            return text
    return ""


async def step_collect_subtitles(
    ctx: PipelineContext,
    state: dict[str, Any],
    *,
    run_command: Callable[[PipelineContext, list[str]], Awaitable[CommandResult]],
    fetch_youtube_transcript_text_fn: Callable[[str], str],
) -> StepExecution:
    subtitle_files = subtitle_candidates(ctx.download_dir)
    transcript, used_subtitle_files = collect_subtitle_text_from_files(subtitle_files)
    if transcript:
        return StepExecution(
            status="succeeded",
            output={
                "subtitle_files": len(used_subtitle_files),
                "transcript_provider": "downloaded_subtitles",
                "fallback_used": False,
            },
            state_updates={"transcript": transcript, "subtitle_files": used_subtitle_files},
        )

    failure_reasons: list[str] = []
    if used_subtitle_files:
        failure_reasons.append("subtitle_text_empty_after_parse")
    else:
        failure_reasons.append("subtitle_file_not_found")

    source_url = str(state.get("source_url") or "").strip()
    video_uid = str(state.get("video_uid") or "").strip()
    platform = str(state.get("platform") or "").strip().lower()

    if platform == "youtube" and coerce_bool(
        getattr(ctx.settings, "youtube_transcript_fallback_enabled", True),
        default=True,
    ):
        video_id = extract_youtube_video_id(source_url, video_uid)
        if video_id:
            try:
                yt_transcript = await asyncio.to_thread(fetch_youtube_transcript_text_fn, video_id)
                if yt_transcript.strip():
                    return StepExecution(
                        status="succeeded",
                        output={
                            "subtitle_files": len(used_subtitle_files),
                            "transcript_provider": "youtube_transcript_fallback",
                            "fallback_used": True,
                        },
                        state_updates={
                            "transcript": yt_transcript.strip(),
                            "subtitle_files": used_subtitle_files,
                        },
                    )
                failure_reasons.append("youtube_transcript_empty")
            except Exception as exc:  # pragma: no cover
                failure_reasons.append(f"youtube_transcript_failed:{exc.__class__.__name__}")
        else:
            failure_reasons.append("youtube_video_id_not_resolved")
    else:
        failure_reasons.append("youtube_transcript_fallback_disabled_or_not_youtube")

    if coerce_bool(getattr(ctx.settings, "asr_fallback_enabled", False), default=False):
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
                result = await run_command(ctx, cmd)
                if result.ok:
                    asr_text = collect_asr_output_text(ctx.download_dir, media_path)
                    if asr_text:
                        return StepExecution(
                            status="succeeded",
                            output={
                                "subtitle_files": len(used_subtitle_files),
                                "transcript_provider": "asr_fallback",
                                "asr_model_size": asr_model_size,
                                "fallback_used": True,
                            },
                            state_updates={
                                "transcript": asr_text,
                                "subtitle_files": used_subtitle_files,
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
            "subtitle_files": len(used_subtitle_files),
            "transcript_provider": "none",
            "fallback_chain": failure_reasons,
        },
        state_updates={"transcript": "", "subtitle_files": used_subtitle_files},
        reason=failure_reasons[-1] if failure_reasons else "subtitle_unavailable",
        degraded=True,
    )
