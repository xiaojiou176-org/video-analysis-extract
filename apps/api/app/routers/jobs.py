from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import JobsService

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


class JobStepSummary(BaseModel):
    name: str
    status: str
    attempt: int
    started_at: str | None
    finished_at: str | None
    error: Any | None = None


class JobStepDetail(JobStepSummary):
    error_kind: str | None = None
    retry_meta: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    cache_key: str | None = None


class JobDegradation(BaseModel):
    step: str | None = None
    status: str | None = None
    reason: str | None = None
    error: Any | None = None
    error_kind: str | None = None
    retry_meta: dict[str, Any] | None = None
    cache_meta: dict[str, Any] | None = None


class JobResponse(BaseModel):
    id: uuid.UUID
    video_id: uuid.UUID
    kind: Literal["phase2_ingest_stub"]
    status: Literal["queued", "running", "succeeded", "failed", "partial"]
    mode: str | None = None
    idempotency_key: str
    error_message: str | None
    artifact_digest_md: str | None
    artifact_root: str | None
    created_at: datetime
    updated_at: datetime
    step_summary: list[JobStepSummary]
    steps: list[JobStepDetail]
    degradations: list[JobDegradation]
    pipeline_final_status: Literal["succeeded", "partial", "failed"] | None = None
    artifacts_index: dict[str, str]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    service = JobsService(db)
    row = service.get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="job not found")
    steps = service.get_steps(job_id)
    step_summary = [
        JobStepSummary(
            name=item["name"],
            status=item["status"],
            attempt=item["attempt"],
            started_at=item["started_at"],
            finished_at=item["finished_at"],
            error=item.get("error"),
        )
        for item in steps
    ]
    degradations = service.get_degradations(
        artifact_root=row.artifact_root,
        artifact_digest_md=row.artifact_digest_md,
        steps=steps,
    )
    artifacts_index = service.get_artifacts_index(
        artifact_root=row.artifact_root,
        artifact_digest_md=row.artifact_digest_md,
        steps=steps,
    )

    return JobResponse(
        id=row.id,
        video_id=row.video_id,
        kind=row.kind,
        status=row.status,
        mode=row.mode,
        idempotency_key=row.idempotency_key,
        error_message=row.error_message,
        artifact_digest_md=row.artifact_digest_md,
        artifact_root=row.artifact_root,
        created_at=row.created_at,
        updated_at=row.updated_at,
        step_summary=step_summary,
        steps=[JobStepDetail(**item) for item in steps],
        degradations=[JobDegradation(**item) for item in degradations],
        pipeline_final_status=service.get_pipeline_final_status(job_id, fallback_status=row.status),
        artifacts_index=artifacts_index,
    )
