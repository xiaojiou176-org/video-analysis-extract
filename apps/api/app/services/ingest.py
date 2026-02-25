from __future__ import annotations

import asyncio
import uuid
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..errors import ApiTimeoutError
from ..models import Job, Subscription, Video


class IngestService:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def poll(
        self,
        *,
        subscription_id: uuid.UUID | None,
        platform: str | None,
        max_new_videos: int,
    ) -> tuple[int, list[dict[str, object]]]:
        if subscription_id is not None:
            exists = self.db.scalar(
                select(Subscription.id).where(Subscription.id == subscription_id)
            )
            if exists is None:
                raise ValueError("subscription does not exist")

        try:
            from temporalio.client import Client
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"temporal client not available: {exc}") from exc

        try:
            client = await asyncio.wait_for(
                Client.connect(
                    settings.temporal_target_host,
                    namespace=settings.temporal_namespace,
                ),
                timeout=settings.api_temporal_connect_timeout_seconds,
            )
        except TimeoutError as exc:
            raise ApiTimeoutError(
                detail=(
                    "temporal connect timed out "
                    f"after {settings.api_temporal_connect_timeout_seconds:.1f}s"
                ),
                error_code="TEMPORAL_CONNECT_TIMEOUT",
            ) from exc

        filters = {
            "subscription_id": str(subscription_id) if subscription_id else None,
            "platform": platform,
            "max_new_videos": max_new_videos,
        }

        try:
            handle = await asyncio.wait_for(
                client.start_workflow(
                    "PollFeedsWorkflow",
                    filters,
                    id=f"api-poll-feeds-{uuid4()}",
                    task_queue=settings.temporal_task_queue,
                ),
                timeout=settings.api_temporal_start_timeout_seconds,
            )
        except TimeoutError as exc:
            raise ApiTimeoutError(
                detail=(
                    "temporal workflow start timed out "
                    f"after {settings.api_temporal_start_timeout_seconds:.1f}s"
                ),
                error_code="TEMPORAL_WORKFLOW_START_TIMEOUT",
            ) from exc

        try:
            result = await asyncio.wait_for(
                handle.result(),
                timeout=settings.api_temporal_result_timeout_seconds,
            )
        except TimeoutError as exc:
            raise ApiTimeoutError(
                detail=(
                    "temporal workflow result timed out "
                    f"after {settings.api_temporal_result_timeout_seconds:.1f}s"
                ),
                error_code="TEMPORAL_WORKFLOW_RESULT_TIMEOUT",
            ) from exc

        created_job_ids = [uuid.UUID(str(item)) for item in result.get("created_job_ids", [])]
        if not created_job_ids:
            return 0, []

        stmt = (
            select(Job, Video)
            .join(Video, Video.id == Job.video_id)
            .where(Job.id.in_(created_job_ids))
            .order_by(Job.created_at.desc())
            .limit(max_new_videos)
        )
        rows = self.db.execute(stmt).all()

        candidates = [
            {
                "job_id": job.id,
                "video_id": video.id,
                "platform": video.platform,
                "video_uid": video.video_uid,
                "source_url": video.source_url,
                "title": video.title,
                "published_at": video.published_at,
            }
            for job, video in rows
        ]
        return len(candidates), candidates
