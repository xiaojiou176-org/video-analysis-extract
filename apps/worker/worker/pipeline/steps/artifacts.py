from __future__ import annotations

from typing import Any

from worker.comments import empty_comments_payload
from worker.pipeline.runner_rendering import (
    build_chapters_markdown,
    build_chapters_toc_markdown,
    build_code_blocks_markdown,
    build_comments_markdown,
    build_fallback_notes_markdown,
    build_frames_embedded_markdown,
    build_frames_markdown,
    build_timestamp_refs_markdown,
    load_digest_template,
    materialize_frames_for_artifacts,
    render_template,
)
from worker.pipeline.step_executor import utc_now_iso, write_json
from worker.pipeline.steps.llm import normalize_digest_payload, normalize_outline_payload
from worker.pipeline.types import PipelineContext, StepExecution


def _has_transcript_evidence(transcript: str) -> bool:
    return len(transcript.strip()) >= 80


def _has_comments_evidence(comments: dict[str, Any]) -> bool:
    top_comments = comments.get("top_comments") if isinstance(comments, dict) else None
    return isinstance(top_comments, list) and bool(top_comments)


def _is_low_evidence_mode(
    *,
    transcript: str,
    comments: dict[str, Any],
    frames: list[dict[str, Any]],
) -> bool:
    return (
        not _has_transcript_evidence(transcript)
        and not _has_comments_evidence(comments)
        and not bool(frames)
    )


def _apply_low_evidence_guard(
    digest: dict[str, Any],
    outline: dict[str, Any],
    *,
    transcript: str,
    comments: dict[str, Any],
) -> None:
    digest["summary"] = (
        "当前缺少可验证证据（字幕/评论/截图均不可用），无法生成高置信度内容摘要。"
        "以下仅保留流程性提示，不提供具体章节与时间戳结论。"
    )
    digest["tldr"] = [
        "未获取到可用字幕，无法基于语义内容做摘要。",
        "未采集到评论，缺少外部观点信号。",
        "未提取到关键截图，缺少画面证据。",
    ]
    digest["highlights"] = [
        "证据不足：本次结果不能作为视频内容事实依据。",
        "已禁用章节精读与时间戳定位，避免误导。",
        "建议补齐字幕、评论或关键帧后重新生成。",
    ]
    digest["action_items"] = [
        "检查字幕抓取链路（平台字幕/ASR）后重跑。",
        "启用评论采集或确认评论接口可用。",
        "启用关键帧提取后再次生成摘要。",
    ]
    digest["timestamp_references"] = []
    digest["code_blocks"] = []

    fallback_notes = [str(item) for item in (digest.get("fallback_notes") or []) if str(item).strip()]
    if not _has_transcript_evidence(transcript):
        fallback_notes.append("transcript_missing_or_too_short")
    if not _has_comments_evidence(comments):
        fallback_notes.append("comments_missing")
    fallback_notes.append("frames_missing")
    fallback_notes.append("quality_gate:low_evidence_mode")
    digest["fallback_notes"] = fallback_notes

    outline["chapters"] = []
    outline["timestamp_references"] = []


async def step_write_artifacts(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    try:
        template = load_digest_template(ctx.settings)
        metadata = dict(state.get("metadata") or {})
        source_url = str(state.get("source_url") or metadata.get("webpage_url") or "")
        outline = normalize_outline_payload(dict(state.get("outline") or {}), state)
        digest_state = dict(state)
        digest_state["outline"] = outline
        digest = normalize_digest_payload(dict(state.get("digest") or {}), digest_state)
        comments = dict(state.get("comments") or empty_comments_payload())
        transcript = str(state.get("transcript") or "")
        degradations = list(state.get("degradations") or [])
        raw_frames = list(state.get("frames") or [])
        frames, frame_files = materialize_frames_for_artifacts(raw_frames, ctx.artifacts_dir)
        if _is_low_evidence_mode(transcript=transcript, comments=comments, frames=frames):
            _apply_low_evidence_guard(digest, outline, transcript=transcript, comments=comments)

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

        rendered_digest = render_template(
            template,
            {
                "title": str(digest.get("title") or metadata.get("title") or state.get("title") or "Untitled Video"),
                "source_url": source_url,
                "platform": str(state.get("platform") or ""),
                "video_uid": str(state.get("video_uid") or ""),
                "generated_at": utc_now_iso(),
                "summary": str(digest.get("summary") or "未生成摘要。"),
                "tldr_markdown": "\n".join(f"- {item}" for item in tldr),
                "highlights_markdown": "\n".join(f"- {item}" for item in highlights),
                "action_items_markdown": "\n".join(f"- [ ] {item}" for item in action_items),
                "chapters_toc_markdown": build_chapters_toc_markdown(outline, source_url),
                "chapters_markdown": build_chapters_markdown(outline, source_url),
                "code_blocks_markdown": build_code_blocks_markdown(outline, digest, source_url),
                "comments_markdown": build_comments_markdown(comments),
                "frames_embedded_markdown": build_frames_embedded_markdown(frames, ctx.job_id),
                "frames_index_markdown": build_frames_markdown(frames, source_url),
                "timestamp_refs_markdown": build_timestamp_refs_markdown(outline, digest, source_url),
                "fallback_notes_markdown": build_fallback_notes_markdown(digest, degradations),
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
            "generated_at": utc_now_iso(),
        }

        meta_path = ctx.artifacts_dir / "meta.json"
        comments_path = ctx.artifacts_dir / "comments.json"
        transcript_path = ctx.artifacts_dir / "transcript.txt"
        outline_path = ctx.artifacts_dir / "outline.json"
        digest_path = ctx.artifacts_dir / "digest.md"

        write_json(meta_path, meta_payload)
        write_json(comments_path, comments)
        transcript_path.write_text(transcript, encoding="utf-8")
        write_json(outline_path, outline)
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
    except Exception as exc:  # pragma: no cover
        return StepExecution(
            status="failed",
            reason="write_artifacts_failed",
            error=str(exc),
            degraded=True,
        )
