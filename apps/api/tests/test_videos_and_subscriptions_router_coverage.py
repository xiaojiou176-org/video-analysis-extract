from __future__ import annotations

import asyncio
import sys
import types
import uuid
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.api.app.errors import ApiTimeoutError
from apps.api.app.services.videos import (
    VideosService,
    _build_process_idempotency_key,
    _extract_video_uid,
    _normalize_mode,
    _url_hash,
)

pytestmark = pytest.mark.allow_unauth_write


@dataclass
class _JobRow:
    id: uuid.UUID
    status: str
    idempotency_key: str
    mode: str


@dataclass
class _VideoRow:
    id: uuid.UUID


class _RepoStub:
    def __init__(self, *, should_dispatch: bool = True) -> None:
        self.should_dispatch = should_dispatch
        self.created_calls: list[dict[str, Any]] = []
        self.mark_failed_calls: list[dict[str, Any]] = []
        self.job = _JobRow(
            id=uuid.uuid4(),
            status="queued",
            idempotency_key="idem-1",
            mode="full",
        )

    def create_or_reuse(self, **kwargs: Any) -> tuple[_JobRow, bool]:
        self.created_calls.append(dict(kwargs))
        return self.job, self.should_dispatch

    def mark_dispatch_failed(
        self, *, job_id: uuid.UUID, error_message: str, reason: str = "dispatch_failed"
    ) -> _JobRow:
        self.mark_failed_calls.append(
            {
                "job_id": job_id,
                "error_message": error_message,
                "reason": reason,
            }
        )
        self.job.status = "failed"
        return self.job


class _VideoRepoStub:
    def __init__(self) -> None:
        self.video = _VideoRow(id=uuid.uuid4())

    def upsert_for_processing(self, **_: Any) -> _VideoRow:
        return self.video


class _FakeClient:
    async def start_workflow(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def _install_temporal_modules(monkeypatch: pytest.MonkeyPatch, *, client: _FakeClient) -> None:
    temporalio_mod = types.ModuleType("temporalio")
    temporal_client_mod = types.ModuleType("temporalio.client")
    temporal_common_mod = types.ModuleType("temporalio.common")

    class _WorkflowIDReusePolicy:
        REJECT_DUPLICATE = "reject_duplicate"

    class _WorkflowIDConflictPolicy:
        USE_EXISTING = "use_existing"

    class _Client:
        @staticmethod
        async def connect(_target_host: str, *, namespace: str):
            assert namespace == "default"
            return client

    temporal_client_mod.Client = _Client
    temporal_common_mod.WorkflowIDReusePolicy = _WorkflowIDReusePolicy
    temporal_common_mod.WorkflowIDConflictPolicy = _WorkflowIDConflictPolicy

    monkeypatch.setitem(sys.modules, "temporalio", temporalio_mod)
    monkeypatch.setitem(sys.modules, "temporalio.client", temporal_client_mod)
    monkeypatch.setitem(sys.modules, "temporalio.common", temporal_common_mod)


async def _run_process(service: VideosService) -> dict[str, Any]:
    return await service.process_video(
        platform="youtube",
        url="https://www.youtube.com/watch?v=abc123",
        video_id=None,
        mode="full",
        overrides={"lang": "en"},
        force=False,
    )


def test_videos_helpers_cover_hash_uid_mode_and_serialization_guards() -> None:
    assert len(_url_hash(" https://youtu.be/abc123 ")) == 64

    assert _extract_video_uid(platform="youtube", url="https://youtu.be/") == _url_hash(
        "https://youtu.be/"
    )
    assert _extract_video_uid(
        platform="bilibili", url="https://www.bilibili.com/video/not-bv"
    ) == _url_hash("https://www.bilibili.com/video/not-bv")
    assert _extract_video_uid(platform="other", url="https://example.com/v") == _url_hash(
        "https://example.com/v"
    )

    assert _normalize_mode(" refresh-comments ") == "refresh_comments"
    with pytest.raises(ValueError, match="unsupported mode"):
        _normalize_mode("invalid")

    with pytest.raises(ValueError, match="JSON-serializable"):
        _build_process_idempotency_key(
            platform="youtube",
            video_uid="abc",
            mode="full",
            overrides={"bad": {1, 2}},
        )


def test_process_video_maps_temporal_connect_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _RepoStub(should_dispatch=True)
    service = VideosService(db=object())
    service.video_repo = _VideoRepoStub()  # type: ignore[assignment]
    service.jobs_repo = repo  # type: ignore[assignment]

    _install_temporal_modules(monkeypatch, client=_FakeClient())

    async def _timeout_wait_for(awaitable: Any, *, timeout: float):
        del timeout
        if hasattr(awaitable, "close"):
            awaitable.close()
        raise TimeoutError

    monkeypatch.setattr("apps.api.app.services.videos.asyncio.wait_for", _timeout_wait_for)

    with pytest.raises(ApiTimeoutError, match="temporal connect timed out") as exc_info:
        asyncio.run(_run_process(service))

    assert exc_info.value.error_code == "TEMPORAL_CONNECT_TIMEOUT"


def test_process_video_maps_temporal_start_timeout_and_marks_dispatch_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _RepoStub(should_dispatch=True)
    service = VideosService(db=object())
    service.video_repo = _VideoRepoStub()  # type: ignore[assignment]
    service.jobs_repo = repo  # type: ignore[assignment]

    _install_temporal_modules(monkeypatch, client=_FakeClient())

    state = {"call": 0}

    async def _wait_for(awaitable: Any, *, timeout: float):
        del timeout
        state["call"] += 1
        if state["call"] == 1:
            return await awaitable
        if hasattr(awaitable, "close"):
            awaitable.close()
        raise TimeoutError

    monkeypatch.setattr("apps.api.app.services.videos.asyncio.wait_for", _wait_for)

    with pytest.raises(ApiTimeoutError, match="temporal workflow start timed out") as exc_info:
        asyncio.run(_run_process(service))

    assert exc_info.value.error_code == "TEMPORAL_WORKFLOW_START_TIMEOUT"
    assert len(repo.mark_failed_calls) == 1
    assert repo.mark_failed_calls[0]["reason"] == "dispatch_timeout"


def test_subscriptions_router_maps_service_value_errors_to_400(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "apps.api.app.services.subscriptions.SubscriptionsService.upsert_subscription",
        lambda self, **kwargs: (_ for _ in ()).throw(ValueError("invalid source")),
    )

    response = api_client.post(
        "/api/v1/subscriptions",
        json={
            "platform": "youtube",
            "source_type": "url",
            "source_value": "https://youtube.com/@demo",
            "adapter_type": "rsshub_route",
            "rsshub_route": "/youtube/channel/demo",
            "category": "misc",
            "tags": [],
            "priority": 50,
            "enabled": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid source"

    monkeypatch.setattr(
        "apps.api.app.services.subscriptions.SubscriptionsService.batch_update_category",
        lambda self, **kwargs: (_ for _ in ()).throw(ValueError("bad category")),
    )
    response2 = api_client.post(
        "/api/v1/subscriptions/batch-update-category",
        json={"ids": [str(uuid.uuid4())], "category": "bad"},
    )
    assert response2.status_code == 400
    assert response2.json()["detail"] == "bad category"


def test_subscriptions_router_delete_returns_404_when_missing(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "apps.api.app.services.subscriptions.SubscriptionsService.delete_subscription",
        lambda self, _id: False,
    )

    response = api_client.delete(f"/api/v1/subscriptions/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "subscription not found"
