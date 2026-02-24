from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas.feed import DigestFeedItem, DigestFeedResponse
from ..services.feed import FeedService

router = APIRouter(prefix="/api/v1/feed", tags=["feed"])


@router.get("/digests", response_model=DigestFeedResponse)
def list_digests(
    source: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    service = FeedService(db)
    payload = service.list_digest_feed(
        source=source,
        category=category,
        limit=limit,
        cursor=cursor,
        since=since,
    )
    return DigestFeedResponse(
        items=[DigestFeedItem(**item) for item in payload.get("items", [])],
        has_more=bool(payload.get("has_more", False)),
        next_cursor=payload.get("next_cursor"),
    )
