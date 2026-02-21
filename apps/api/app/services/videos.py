from __future__ import annotations

import hashlib
import json
import re
import uuid
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from sqlalchemy.orm import Session

from ..config import settings
from ..repositories import JobsRepository, VideosRepository

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
BILIBILI_HOSTS = {"bilibili.com", "www.bilibili.com", "m.bilibili.com", "b23.tv"}
SUPPORTED_MODES = {"full", "text_only", "refresh_comments", "refresh_llm"}
MODE_ALIASES = {
    "text-only": "text_only",
    "refresh-comments": "refresh_comments",
    "refresh-llm": "refresh_llm",
}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _url_hash(url: str) -> str:
    return _sha256(url.strip().lower())


def _extract_video_uid(*, platform: str, url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path or ""
    query = parse_qs(parsed.query)

    if platform == "youtube" and host in YOUTUBE_HOSTS:
        if "v" in query and query["v"]:
            return str(query["v"][0]).strip()
        if host == "youtu.be":
            candidate = str(path.strip("/").split("/")[0]).strip()
            if candidate:
                return candidate
        return _url_hash(url)

    if platform == "bilibili" and host in BILIBILI_HOSTS:
        bv_match = re.search(r"(BV[0-9A-Za-z]+)", path)
        if bv_match:
            return bv_match.group(1)
        return _url_hash(url)

    return _url_hash(url)


def _build_process_idempotency_key(
    *,
    platform: str,
    video_uid: str,
    mode: str,
    overrides: dict[str, object] | None,
) -> str:
    try:
        normalized_overrides = json.dumps(overrides or {}, ensure_ascii=False, sort_keys=True)
    except TypeError as exc:
        raise ValueError("overrides must be JSON-serializable") from exc
    return _sha256(f"{platform}:{video_uid}:{mode}:{normalized_overrides}")


def _normalize_mode(raw_mode: str) -> str:
    candidate = raw_mode.strip().lower()
    normalized = MODE_ALIASES.get(candidate, candidate)
    if normalized not in SUPPORTED_MODES:
        raise ValueError(f"unsupported mode: {raw_mode}")
    return normalized


def _normalize_overrides(overrides: dict[str, object] | None) -> dict[str, object]:
    return dict(overrides or {})


class VideosService:
    def __init__(self, db: Session) -> None:
        self.video_repo = VideosRepository(db)
        self.jobs_repo = JobsRepository(db)

    def list_videos(self, *, platform: str | None = None, status: str | None = None, limit: int = 50):
        return self.video_repo.list(platform=platform, status=status, limit=limit)

    async def process_video(
        self,
        *,
        platform: str,
        url: str,
        video_id: str | None,
        mode: str,
        overrides: dict[str, object] | None,
        force: bool,
    ) -> dict[str, object]:
        normalized_mode = _normalize_mode(mode)
        normalized_overrides = _normalize_overrides(overrides)
        resolved_video_uid = (video_id or "").strip() or _extract_video_uid(
            platform=platform,
            url=url,
        )
        base_idempotency_key = _build_process_idempotency_key(
            platform=platform,
            video_uid=resolved_video_uid,
            mode=normalized_mode,
            overrides=normalized_overrides,
        )
        idempotency_key = (
            f"{base_idempotency_key}:force:{uuid4().hex}" if force else base_idempotency_key
        )

        video_row = self.video_repo.upsert_for_processing(
            platform=platform,
            video_uid=resolved_video_uid,
            source_url=url,
        )
        job_row, created = self.jobs_repo.create_or_reuse(
            video_id=video_row.id,
            kind="phase2_ingest_stub",
            mode=normalized_mode,
            overrides_json=normalized_overrides,
            idempotency_key=idempotency_key,
            force=force,
        )

        workflow_id: str | None = None
        if created:
            try:
                from temporalio.client import Client
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(f"temporal client not available: {exc}") from exc

            client = await Client.connect(
                settings.temporal_target_host,
                namespace=settings.temporal_namespace,
            )
            workflow_id = f"api-process-job-{job_row.id}-{uuid4()}"
            await client.start_workflow(
                "ProcessJobWorkflow",
                str(job_row.id),
                id=workflow_id,
                task_queue=settings.temporal_task_queue,
            )

        return {
            "job_id": job_row.id,
            "video_db_id": video_row.id,
            "video_uid": resolved_video_uid,
            "status": job_row.status,
            "idempotency_key": job_row.idempotency_key,
            "mode": job_row.mode or normalized_mode,
            "overrides": normalized_overrides,
            "force": force,
            "reused": not created,
            "workflow_id": workflow_id,
        }
