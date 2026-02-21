from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_healthz_returns_ok_status(api_client: TestClient) -> None:
    response = api_client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingest_poll_returns_candidates(
    api_client: TestClient,
    monkeypatch,
) -> None:
    video_id = uuid.uuid4()
    job_id = uuid.uuid4()

    async def fake_poll(self, *, subscription_id, platform, max_new_videos):
        assert max_new_videos == 10
        return (
            1,
            [
                {
                    "video_id": video_id,
                    "platform": "youtube",
                    "video_uid": "abc123",
                    "source_url": "https://www.youtube.com/watch?v=abc123",
                    "title": "Demo",
                    "published_at": datetime.now(timezone.utc),
                    "job_id": job_id,
                }
            ],
        )

    monkeypatch.setattr("apps.api.app.services.ingest.IngestService.poll", fake_poll)

    response = api_client.post(
        "/api/v1/ingest/poll",
        json={"platform": "youtube", "max_new_videos": 10},
    )

    payload = response.json()
    assert response.status_code == 202
    assert payload["enqueued"] == 1
    assert payload["candidates"][0]["video_uid"] == "abc123"
    assert payload["candidates"][0]["job_id"] == str(job_id)


def test_video_process_maps_value_error_to_400(
    api_client: TestClient,
    monkeypatch,
) -> None:
    async def fake_process_video(self, **kwargs):
        raise ValueError("invalid_url")

    monkeypatch.setattr(
        "apps.api.app.services.videos.VideosService.process_video",
        fake_process_video,
    )

    response = api_client.post(
        "/api/v1/videos/process",
        json={
            "video": {
                "platform": "youtube",
                "url": "invalid-url",
            }
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_url"


def test_video_process_returns_mode_field(
    api_client: TestClient,
    monkeypatch,
) -> None:
    job_id = uuid.uuid4()
    video_db_id = uuid.uuid4()

    async def fake_process_video(self, **kwargs):
        assert kwargs["mode"] == "refresh_comments"
        return {
            "job_id": job_id,
            "video_db_id": video_db_id,
            "video_uid": "abc123",
            "status": "queued",
            "idempotency_key": "idem-key",
            "mode": "refresh_comments",
            "overrides": {"lang": "zh-CN"},
            "force": False,
            "reused": False,
            "workflow_id": "wf-1",
        }

    monkeypatch.setattr(
        "apps.api.app.services.videos.VideosService.process_video",
        fake_process_video,
    )

    response = api_client.post(
        "/api/v1/videos/process",
        json={
            "video": {
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=abc123",
            },
            "mode": "refresh_comments",
            "overrides": {"lang": "zh-CN"},
        },
    )

    payload = response.json()
    assert response.status_code == 202
    assert payload["mode"] == "refresh_comments"
    assert payload["job_id"] == str(job_id)
    assert payload["overrides"] == {"lang": "zh-CN"}


def test_job_get_returns_mode_and_pipeline_fields(
    api_client: TestClient,
    monkeypatch,
) -> None:
    job_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    def fake_get_job(self, query_job_id):
        assert query_job_id == job_id
        return SimpleNamespace(
            id=job_id,
            video_id=uuid.uuid4(),
            kind="phase2_ingest_stub",
            status="partial",
            mode="refresh_llm",
            idempotency_key="idem-1",
            error_message=None,
            artifact_digest_md=None,
            artifact_root=None,
            created_at=now,
            updated_at=now,
        )

    monkeypatch.setattr("apps.api.app.services.jobs.JobsService.get_job", fake_get_job)
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_steps",
        lambda self, _job_id: [
            {
                "name": "write_artifacts",
                "status": "partial",
                "attempt": 1,
                "started_at": now.isoformat(),
                "finished_at": now.isoformat(),
                "error": {"reason": "fallback"},
                "error_kind": None,
                "retry_meta": None,
                "result": None,
                "cache_key": None,
            }
        ],
    )
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_degradations",
        lambda self, **kwargs: [{"step": "write_artifacts", "status": "partial"}],
    )
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_artifacts_index",
        lambda self, **kwargs: {"digest": "/tmp/digest.md"},
    )
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_pipeline_final_status",
        lambda self, _job_id, fallback_status: "partial",
    )

    response = api_client.get(f"/api/v1/jobs/{job_id}")
    payload = response.json()

    assert response.status_code == 200
    assert payload["mode"] == "refresh_llm"
    assert payload["steps"][0]["name"] == "write_artifacts"
    assert payload["degradations"][0]["step"] == "write_artifacts"
    assert payload["pipeline_final_status"] == "partial"
