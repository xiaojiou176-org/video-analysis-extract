from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..security import sanitize_exception_detail
from ..services import IngestService

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


class IngestPollRequest(BaseModel):
    subscription_id: uuid.UUID | None = None
    platform: str | None = None
    max_new_videos: int = Field(default=50, ge=1, le=500)


class IngestCandidate(BaseModel):
    video_id: uuid.UUID
    platform: str
    video_uid: str
    source_url: str
    title: str | None
    published_at: datetime | None
    job_id: uuid.UUID


class IngestPollResponse(BaseModel):
    enqueued: int
    candidates: list[IngestCandidate]


@router.post("/poll", response_model=IngestPollResponse, status_code=status.HTTP_202_ACCEPTED)
async def poll_ingest(payload: IngestPollRequest, db: Session = Depends(get_db)):
    service = IngestService(db)
    try:
        enqueued, candidates = await service.poll(
            subscription_id=payload.subscription_id,
            platform=payload.platform,
            max_new_videos=payload.max_new_videos,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=sanitize_exception_detail(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=sanitize_exception_detail(exc)) from exc

    return IngestPollResponse(
        enqueued=enqueued,
        candidates=[
            IngestCandidate(
                video_id=item["video_id"],
                platform=item["platform"],
                video_uid=item["video_uid"],
                source_url=item["source_url"],
                title=item["title"],
                published_at=item["published_at"],
                job_id=item["job_id"],
            )
            for item in candidates
        ],
    )
