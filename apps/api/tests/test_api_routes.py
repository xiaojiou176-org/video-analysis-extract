from __future__ import annotations

import base64
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
            status="succeeded",
            mode="refresh_llm",
            idempotency_key="idem-1",
            error_message=None,
            artifact_digest_md=None,
            artifact_root=None,
            llm_required=True,
            llm_gate_passed=False,
            hard_fail_reason="llm_provider_unavailable",
            created_at=now,
            updated_at=now,
        )

    monkeypatch.setattr("apps.api.app.services.jobs.JobsService.get_job", fake_get_job)
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_steps",
        lambda self, _job_id: [
            {
                "name": "write_artifacts",
                "status": "failed",
                "attempt": 1,
                "started_at": now.isoformat(),
                "finished_at": now.isoformat(),
                "error": {"reason": "llm_provider_unavailable"},
                "error_kind": None,
                "retry_meta": None,
                "result": None,
                "thought_metadata": {"provider": "gemini", "thought_tokens": 42},
                "cache_key": None,
            }
        ],
    )
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_degradations",
        lambda self, **kwargs: [{"step": "write_artifacts", "status": "failed"}],
    )
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_artifacts_index",
        lambda self, **kwargs: {"digest": "/tmp/digest.md"},
    )
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_pipeline_final_status",
        lambda self, _job_id, fallback_status: "degraded",
    )
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_notification_retry",
        lambda self, _job_id: {
            "delivery_id": str(uuid.uuid4()),
            "status": "failed",
            "attempt_count": 2,
            "next_retry_at": now,
            "last_error_kind": "transient",
        },
    )

    response = api_client.get(f"/api/v1/jobs/{job_id}")
    payload = response.json()

    assert response.status_code == 200
    assert payload["kind"] == "phase2_ingest_stub"
    assert payload["mode"] == "refresh_llm"
    assert payload["llm_required"] is True
    assert payload["llm_gate_passed"] is False
    assert payload["hard_fail_reason"] == "llm_provider_unavailable"
    assert payload["steps"][0]["name"] == "write_artifacts"
    assert payload["steps"][0]["thought_metadata"] == {"provider": "gemini", "thought_tokens": 42}
    assert payload["degradations"][0]["step"] == "write_artifacts"
    assert payload["pipeline_final_status"] == "degraded"
    assert payload["notification_retry"]["status"] == "failed"
    assert payload["notification_retry"]["attempt_count"] == 2


def test_retrieval_search_returns_items(api_client: TestClient, monkeypatch) -> None:
    def fake_search(self, *, query, top_k, filters):
        assert query == "timeout"
        assert top_k == 2
        assert filters == {"platform": "youtube"}
        return {
            "query": query,
            "top_k": top_k,
            "filters": filters,
            "items": [
                {
                    "job_id": "00000000-0000-0000-0000-000000000001",
                    "video_id": "00000000-0000-0000-0000-000000000010",
                    "platform": "youtube",
                    "video_uid": "abc123",
                    "source_url": "https://www.youtube.com/watch?v=abc123",
                    "title": "Demo",
                    "kind": "video_digest_v1",
                    "mode": "full",
                    "source": "digest",
                    "snippet": "timeout happened in provider step",
                    "score": 2.5,
                }
            ],
        }

    monkeypatch.setattr("apps.api.app.services.retrieval.RetrievalService.search", fake_search)

    response = api_client.post(
        "/api/v1/retrieval/search",
        json={"query": "timeout", "top_k": 2, "filters": {"platform": "youtube"}},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["query"] == "timeout"
    assert payload["top_k"] == 2
    assert payload["filters"] == {"platform": "youtube"}
    assert payload["items"][0]["source"] == "digest"
    assert payload["items"][0]["score"] == 2.5


def test_computer_use_run_returns_required_fields(api_client: TestClient, monkeypatch) -> None:
    screenshot_b64 = base64.b64encode(b"fake-image-bytes").decode("ascii")
    monkeypatch.setattr(
        "apps.api.app.services.computer_use.ComputerUseService.run",
        lambda self, **kwargs: {
            "actions": [
                {
                    "step": 1,
                    "action": "click",
                    "target": "submit button",
                    "input_text": None,
                    "reasoning": "click submit",
                }
            ],
            "require_confirmation": True,
            "blocked_actions": ["submit"],
            "final_text": "confirmation required",
            "thought_metadata": {"provider": "gemini", "planner": "gemini_computer_use"},
        },
    )

    response = api_client.post(
        "/api/v1/computer-use/run",
        json={
            "instruction": "Open settings; click submit button",
            "screenshot_base64": screenshot_b64,
            "safety": {
                "confirm_before_execute": False,
                "blocked_actions": ["submit"],
                "max_actions": 5,
            },
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert isinstance(payload["actions"], list)
    assert payload["actions"][0]["step"] == 1
    assert payload["require_confirmation"] is True
    assert payload["blocked_actions"] == ["submit"]
    assert isinstance(payload["final_text"], str)
    assert isinstance(payload["thought_metadata"], dict)


def test_computer_use_run_rejects_invalid_screenshot_base64(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/computer-use/run",
        json={
            "instruction": "Open settings",
            "screenshot_base64": "%%%not-base64%%%",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "screenshot must be valid base64"


def test_job_get_infers_llm_gate_fields_from_steps_when_legacy_fields_are_null(
    api_client: TestClient,
    monkeypatch,
) -> None:
    job_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_job",
        lambda self, query_job_id: SimpleNamespace(
            id=query_job_id,
            video_id=uuid.uuid4(),
            kind="video_digest_v1",
            status="failed",
            mode="refresh_llm",
            idempotency_key="idem-legacy",
            error_message="failed",
            artifact_digest_md=None,
            artifact_root=None,
            llm_required=None,
            llm_gate_passed=None,
            hard_fail_reason=None,
            created_at=now,
            updated_at=now,
        ),
    )
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_steps",
        lambda self, _job_id: [
            {
                "name": "llm_outline",
                "status": "succeeded",
                "attempt": 1,
                "started_at": now.isoformat(),
                "finished_at": now.isoformat(),
                "error": None,
                "error_kind": None,
                "retry_meta": None,
                "result": None,
                "cache_key": None,
            },
            {
                "name": "llm_digest",
                "status": "failed",
                "attempt": 1,
                "started_at": now.isoformat(),
                "finished_at": now.isoformat(),
                "error": {"reason": "provider_unavailable"},
                "error_kind": "upstream_error",
                "retry_meta": {"max_attempts": 2},
                "result": None,
                "cache_key": None,
            },
        ],
    )
    monkeypatch.setattr("apps.api.app.services.jobs.JobsService.get_degradations", lambda self, **kwargs: [])
    monkeypatch.setattr("apps.api.app.services.jobs.JobsService.get_artifacts_index", lambda self, **kwargs: {})
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_pipeline_final_status",
        lambda self, _job_id, fallback_status: "failed",
    )
    monkeypatch.setattr("apps.api.app.services.jobs.JobsService.get_notification_retry", lambda self, _job_id: None)

    response = api_client.get(f"/api/v1/jobs/{job_id}")
    payload = response.json()

    assert response.status_code == 200
    assert payload["llm_required"] is True
    assert payload["llm_gate_passed"] is False
    assert payload["hard_fail_reason"] == "provider_unavailable"


def test_job_get_infers_llm_gate_passed_true_when_llm_steps_succeed(
    api_client: TestClient,
    monkeypatch,
) -> None:
    job_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_job",
        lambda self, query_job_id: SimpleNamespace(
            id=query_job_id,
            video_id=uuid.uuid4(),
            kind="video_digest_v1",
            status="succeeded",
            mode="full",
            idempotency_key="idem-legacy-ok",
            error_message=None,
            artifact_digest_md=None,
            artifact_root=None,
            llm_required=None,
            llm_gate_passed=None,
            hard_fail_reason="legacy_reason_should_clear",
            created_at=now,
            updated_at=now,
        ),
    )
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_steps",
        lambda self, _job_id: [
            {
                "name": "llm_outline",
                "status": "succeeded",
                "attempt": 1,
                "started_at": now.isoformat(),
                "finished_at": now.isoformat(),
                "error": None,
                "error_kind": None,
                "retry_meta": None,
                "result": None,
                "cache_key": None,
            },
            {
                "name": "llm_digest",
                "status": "skipped",
                "attempt": 1,
                "started_at": now.isoformat(),
                "finished_at": now.isoformat(),
                "error": None,
                "error_kind": None,
                "retry_meta": None,
                "result": {"degraded": False},
                "cache_key": None,
            },
        ],
    )
    monkeypatch.setattr("apps.api.app.services.jobs.JobsService.get_degradations", lambda self, **kwargs: [])
    monkeypatch.setattr("apps.api.app.services.jobs.JobsService.get_artifacts_index", lambda self, **kwargs: {})
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_pipeline_final_status",
        lambda self, _job_id, fallback_status: "succeeded",
    )
    monkeypatch.setattr("apps.api.app.services.jobs.JobsService.get_notification_retry", lambda self, _job_id: None)

    response = api_client.get(f"/api/v1/jobs/{job_id}")
    payload = response.json()

    assert response.status_code == 200
    assert payload["llm_required"] is True
    assert payload["llm_gate_passed"] is True
    assert payload["hard_fail_reason"] is None


def test_health_providers_returns_rollup(api_client: TestClient, monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        "apps.api.app.services.health.HealthService.get_provider_health",
        lambda self, window_hours=24: {
            "window_hours": window_hours,
            "providers": [
                {
                    "provider": "rsshub",
                    "ok": 3,
                    "warn": 1,
                    "fail": 0,
                    "last_status": "ok",
                    "last_checked_at": now,
                    "last_error_kind": None,
                    "last_message": "ok",
                }
            ],
        },
    )

    response = api_client.get("/api/v1/health/providers?window_hours=24")

    assert response.status_code == 200
    payload = response.json()
    assert payload["window_hours"] == 24
    assert payload["providers"][0]["provider"] == "rsshub"
    assert payload["providers"][0]["ok"] == 3


def _mock_artifact_job(
    monkeypatch,
    *,
    artifact_root: str | None,
    artifact_digest_md: str | None = None,
) -> None:
    monkeypatch.setattr(
        "apps.api.app.services.jobs.JobsService.get_job",
        lambda self, query_job_id: SimpleNamespace(
            id=query_job_id,
            artifact_root=artifact_root,
            artifact_digest_md=artifact_digest_md,
        ),
    )


def test_artifact_assets_allows_whitelisted_meta(api_client: TestClient, monkeypatch, tmp_path) -> None:
    job_id = uuid.uuid4()
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "meta.json").write_text('{"ok": true}', encoding="utf-8")
    _mock_artifact_job(monkeypatch, artifact_root=str(artifact_root))

    response = api_client.get(
        "/api/v1/artifacts/assets",
        params={"job_id": str(job_id), "path": "meta"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_artifact_assets_blocks_path_traversal(api_client: TestClient, monkeypatch, tmp_path) -> None:
    job_id = uuid.uuid4()
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    _mock_artifact_job(monkeypatch, artifact_root=str(artifact_root))

    response = api_client.get(
        "/api/v1/artifacts/assets",
        params={"job_id": str(job_id), "path": "../secret.txt"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "artifact asset not found"


def test_artifact_assets_blocks_non_whitelisted_file(api_client: TestClient, monkeypatch, tmp_path) -> None:
    job_id = uuid.uuid4()
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "notes.txt").write_text("private", encoding="utf-8")
    _mock_artifact_job(monkeypatch, artifact_root=str(artifact_root))

    response = api_client.get(
        "/api/v1/artifacts/assets",
        params={"job_id": str(job_id), "path": "notes.txt"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "artifact asset not found"


def test_artifact_assets_allows_frame_image(api_client: TestClient, monkeypatch, tmp_path) -> None:
    job_id = uuid.uuid4()
    artifact_root = tmp_path / "artifacts"
    frame_dir = artifact_root / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    frame_path = frame_dir / "frame_001.jpg"
    frame_path.write_bytes(b"\xff\xd8\xff\xd9")
    _mock_artifact_job(monkeypatch, artifact_root=str(artifact_root))

    response = api_client.get(
        "/api/v1/artifacts/assets",
        params={"job_id": str(job_id), "path": "frames/frame_001.jpg"},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"\xff\xd8")
    assert response.headers["content-type"].startswith("image/jpeg")


def test_workflows_run_returns_503_when_temporal_unavailable(api_client: TestClient, monkeypatch) -> None:
    async def fake_connect(*args, **kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr("temporalio.client.Client.connect", fake_connect)

    response = api_client.post(
        "/api/v1/workflows/run",
        json={
            "workflow": "provider_canary",
            "run_once": True,
            "wait_for_result": False,
            "payload": {},
        },
    )

    assert response.status_code == 503
    assert "failed to connect temporal" in response.json()["detail"]


def test_notification_html_renderer_supports_markdown() -> None:
    from apps.api.app.services.notifications import _to_html

    html = _to_html("# 标题\n\n- 一\n- 二\n\n[链接](https://example.com)")
    assert "<h1>标题</h1>" in html
    assert "<li>一</li>" in html
    assert "<a href=\"https://example.com\">链接</a>" in html
