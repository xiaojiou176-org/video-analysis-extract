from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import JobsService

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


class MarkdownArtifactMetaResponse(BaseModel):
    markdown: str
    meta: dict[str, Any] | None = None


@router.get("/markdown", response_class=PlainTextResponse)
def get_markdown_artifact(
    job_id: uuid.UUID | None = Query(default=None),
    video_url: str | None = Query(default=None, min_length=1),
    include_meta: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    if job_id is None and not video_url:
        raise HTTPException(status_code=400, detail="either job_id or video_url is required")

    service = JobsService(db)
    payload = service.get_artifact_payload(job_id=job_id, video_url=video_url)
    if payload is None:
        raise HTTPException(status_code=404, detail="digest markdown not found")

    markdown = payload.get("markdown")
    if not isinstance(markdown, str):
        raise HTTPException(status_code=404, detail="digest markdown not found")

    if include_meta:
        meta = payload.get("meta")
        body = MarkdownArtifactMetaResponse(
            markdown=markdown,
            meta=meta if isinstance(meta, dict) else None,
        )
        return JSONResponse(body.model_dump())

    return PlainTextResponse(markdown, media_type="text/markdown")
