from __future__ import annotations

import json
from typing import Any

from worker.pipeline.runner_rendering import build_comments_prompt_context, build_frames_prompt_context
from worker.pipeline.step_executor import jsonable


def build_translation_prompt(payload: dict[str, Any], *, schema_label: str) -> str:
    return "\n\n".join(
        [
            "将下面 JSON 中所有面向读者的自然语言翻译为简体中文。",
            "保持 JSON 的 key、结构、数字、时间戳、URL、ID 不变。",
            "如果包含代码片段（如 code_snippets.snippet / code_blocks.snippet），代码内容不要翻译。",
            "只返回 JSON，不要解释。",
            f"Schema: {schema_label}",
            json.dumps(jsonable(payload), ensure_ascii=False),
        ]
    )


def build_outline_prompt(
    *,
    title: str,
    metadata: dict[str, Any],
    transcript: str,
    comments: dict[str, Any],
    frames: list[dict[str, Any]],
    source_url: str,
    include_frame_context: bool,
) -> str:
    prompt_parts = [
        "你是资深技术视频分析师，请基于多模态输入生成严格 JSON 大纲。",
        "输出约束：只返回 JSON，不要 Markdown，不要代码块围栏。",
        "语言约束：所有面向读者字段必须是简体中文（专有名词、产品名、代码标识可保留英文）。",
        "结构约束：顶层字段必须包含 title,tldr,highlights,recommended_actions,risk_or_pitfalls,chapters,timestamp_references。",
        "章节约束：chapter 必须包含 chapter_no,title,anchor,start_s,end_s,summary,bullets,key_terms,code_snippets。",
        "证据约束：尽量给出时间戳与评论证据，避免编造。",
        f"Title: {title}",
        f"Metadata: {json.dumps(jsonable(metadata), ensure_ascii=False)}",
        f"Transcript (truncated):\n{transcript[:12000]}",
        f"Comment Highlights:\n{build_comments_prompt_context(comments)}",
    ]
    if include_frame_context:
        prompt_parts.append(
            f"Frame Summaries (for richer grounding):\n{build_frames_prompt_context(frames, source_url)}"
        )
    return "\n\n".join(prompt_parts)


def build_digest_prompt(
    *,
    metadata: dict[str, Any],
    outline: dict[str, Any],
    transcript: str,
    comments: dict[str, Any],
    frames: list[dict[str, Any]],
    source_url: str,
    include_frame_context: bool,
) -> str:
    prompt_parts = [
        "你是资深技术内容编辑，请输出结构化摘要 JSON。",
        "输出约束：只返回 JSON，不要 Markdown，不要代码块围栏。",
        "语言约束：所有面向读者字段必须是简体中文（专有名词、产品名、代码标识可保留英文）。",
        "字段约束：必须包含 title,summary,tldr,highlights,action_items,code_blocks,timestamp_references,fallback_notes。",
        "质量约束：summary 120~220字；条目去重、可执行、证据导向。",
        f"Metadata:\n{json.dumps(jsonable(metadata), ensure_ascii=False)}",
        f"Outline:\n{json.dumps(jsonable(outline), ensure_ascii=False)}",
        f"Transcript (truncated):\n{transcript[:12000]}",
        f"Comment Highlights:\n{build_comments_prompt_context(comments)}",
    ]
    if include_frame_context:
        prompt_parts.append(
            f"Frame Summaries (optional grounding):\n{build_frames_prompt_context(frames, source_url)}"
        )
    return "\n\n".join(prompt_parts)


def select_supporting_frames(
    frame_summaries: list[dict[str, Any]] | None = None,
    max_items: int = 5,
) -> dict[str, Any]:
    entries = frame_summaries if isinstance(frame_summaries, list) else []
    limit = max(1, min(20, int(max_items)))
    selected = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        selected.append(
            {
                "timestamp_s": int(item.get("timestamp_s") or 0),
                "reason": str(item.get("reason") or "supporting_frame"),
                "path": str(item.get("path") or ""),
            }
        )
        if len(selected) >= limit:
            break
    return {"frames": selected}


def build_evidence_citations(
    chapters: list[dict[str, Any]] | None = None,
    comments: list[dict[str, Any]] | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    chapter_entries = chapters if isinstance(chapters, list) else []
    comment_entries = comments if isinstance(comments, list) else []
    max_items = max(1, min(30, int(limit)))

    citations: list[str] = []
    for chapter in chapter_entries:
        if not isinstance(chapter, dict):
            continue
        start_s = int(chapter.get("start_s") or 0)
        title = str(chapter.get("title") or "章节").strip() or "章节"
        citations.append(f"[{start_s}s] {title}")
        if len(citations) >= max_items:
            break

    if len(citations) < max_items:
        for comment in comment_entries:
            if not isinstance(comment, dict):
                continue
            content = str(comment.get("content") or "").strip()
            if not content:
                continue
            citations.append(f"[comment] {content[:60]}")
            if len(citations) >= max_items:
                break

    return {"citations": citations}
