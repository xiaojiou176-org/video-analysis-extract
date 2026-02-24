from __future__ import annotations

from pydantic import BaseModel


class DigestFeedItem(BaseModel):
    feed_id: str
    job_id: str
    video_url: str
    title: str
    source: str
    source_name: str
    category: str
    published_at: str
    summary_md: str
    artifact_type: str


class DigestFeedResponse(BaseModel):
    items: list[DigestFeedItem]
    has_more: bool
    next_cursor: str | None
