from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..services.retrieval import RetrievalService

router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])


class RetrievalSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)
    mode: Literal["keyword", "semantic", "hybrid"] = "keyword"
    filters: dict[str, Any] = Field(default_factory=dict)


class RetrievalHit(BaseModel):
    job_id: str
    video_id: str
    platform: Literal["bilibili", "youtube"]
    video_uid: str
    source_url: str
    title: str | None = None
    kind: str
    mode: str | None = None
    source: Literal["digest", "transcript", "outline", "comments", "meta"]
    snippet: str
    score: float


class RetrievalSearchResponse(BaseModel):
    query: str
    top_k: int
    filters: dict[str, Any]
    items: list[RetrievalHit]


@router.post("/search", response_model=RetrievalSearchResponse)
def retrieval_search(
    payload: RetrievalSearchRequest,
    db: Session = Depends(get_db),
) -> RetrievalSearchResponse:
    service = RetrievalService(db)
    result = service.search(query=payload.query, top_k=payload.top_k, mode=payload.mode, filters=payload.filters)
    return RetrievalSearchResponse(**result)
