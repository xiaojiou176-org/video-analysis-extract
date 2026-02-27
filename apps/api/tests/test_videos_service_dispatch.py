from __future__ import annotations

import asyncio
import re
import sys
import types
import uuid
from dataclasses import dataclass
from typing import Any

import pytest

from apps.api.app.services.videos import (
    VideosService,
    _build_process_idempotency_key,
    _extract_video_uid,
    _url_hash,
    _validate_video_source_url,
)


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
        self.job.idempotency_key = str(kwargs["idempotency_key"])
        self.job.mode = str(kwargs["mode"])
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
        self.upsert_calls: list[dict[str, Any]] = []

    def upsert_for_processing(self, **kwargs: Any) -> _VideoRow:
        self.upsert_calls.append(dict(kwargs))
        return self.video


class _FakeClient:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls: list[dict[str, Any]] = []

    async def start_workflow(
        self, workflow: str, job_id: str, *, id: str, task_queue: str, **kwargs: Any
    ) -> None:
        self.calls.append(
            {
                "workflow": workflow,
                "job_id": job_id,
                "id": id,
                "task_queue": task_queue,
                "kwargs": kwargs,
            }
        )
        if self.should_fail:
            raise RuntimeError("temporal start failed")


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
        overrides={},
        force=False,
    )


def test_process_video_marks_dispatch_failed_when_temporal_start_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _RepoStub(should_dispatch=True)
    service = VideosService(db=object())
    service.video_repo = _VideoRepoStub()  # type: ignore[assignment]
    service.jobs_repo = repo  # type: ignore[assignment]

    fake_client = _FakeClient(should_fail=True)
    _install_temporal_modules(monkeypatch, client=fake_client)

    with pytest.raises(RuntimeError, match="failed to start ProcessJobWorkflow"):
        asyncio.run(_run_process(service))

    assert len(repo.mark_failed_calls) == 1
    assert repo.mark_failed_calls[0]["job_id"] == repo.job.id
    assert "temporal start failed" in repo.mark_failed_calls[0]["error_message"]


def test_process_video_uses_deterministic_workflow_id_and_conflict_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _RepoStub(should_dispatch=True)
    service = VideosService(db=object())
    service.video_repo = _VideoRepoStub()  # type: ignore[assignment]
    service.jobs_repo = repo  # type: ignore[assignment]

    fake_client = _FakeClient(should_fail=False)
    _install_temporal_modules(monkeypatch, client=fake_client)

    result = asyncio.run(_run_process(service))

    assert result["workflow_id"] == f"process-job-{repo.job.id}"
    assert result["reused"] is False

    call = fake_client.calls[0]
    assert call["id"] == f"process-job-{repo.job.id}"
    assert call["kwargs"]["id_reuse_policy"] == "reject_duplicate"
    assert call["kwargs"]["id_conflict_policy"] == "use_existing"


def test_process_video_reuses_existing_job_without_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _RepoStub(should_dispatch=False)
    service = VideosService(db=object())
    service.video_repo = _VideoRepoStub()  # type: ignore[assignment]
    service.jobs_repo = repo  # type: ignore[assignment]

    fake_client = _FakeClient(should_fail=False)
    _install_temporal_modules(monkeypatch, client=fake_client)

    result = asyncio.run(_run_process(service))

    assert result["workflow_id"] is None
    assert result["reused"] is True
    assert fake_client.calls == []


@pytest.mark.parametrize(
    ("platform", "url", "expected"),
    [
        ("youtube", "https://www.youtube.com/watch?v=abc123", "abc123"),
        ("youtube", "https://youtu.be/short123/extra", "short123"),
        ("youtube", "https://www.youtube.com/watch?list=abc", _url_hash("https://www.youtube.com/watch?list=abc")),
        ("bilibili", "https://www.bilibili.com/video/BV1xx411c7mD", "BV1xx411c7mD"),
        ("bilibili", "https://www.bilibili.com/video/av123456", _url_hash("https://www.bilibili.com/video/av123456")),
        ("other", "https://example.com/watch?v=abc", _url_hash("https://example.com/watch?v=abc")),
    ],
)
def test_extract_video_uid_branch_coverage(platform: str, url: str, expected: str) -> None:
    assert _extract_video_uid(platform=platform, url=url) == expected


def test_process_video_passes_expected_repo_params_with_explicit_video_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _RepoStub(should_dispatch=False)
    video_repo = _VideoRepoStub()
    service = VideosService(db=object())
    service.video_repo = video_repo  # type: ignore[assignment]
    service.jobs_repo = repo  # type: ignore[assignment]

    _install_temporal_modules(monkeypatch, client=_FakeClient())
    result = asyncio.run(
        service.process_video(
            platform="youtube",
            url=" https://www.youtube.com/watch?v=from-url ",
            video_id=" manual-video-id ",
            mode="text-only",
            overrides={"lang": "en", "limit": 5},
            force=False,
        )
    )

    assert result["video_uid"] == "manual-video-id"
    assert result["mode"] == "text_only"
    assert len(video_repo.upsert_calls) == 1
    assert video_repo.upsert_calls[0] == {
        "platform": "youtube",
        "video_uid": "manual-video-id",
        "source_url": "https://www.youtube.com/watch?v=from-url",
    }

    assert len(repo.created_calls) == 1
    created = repo.created_calls[0]
    expected_idempotency = _build_process_idempotency_key(
        platform="youtube",
        video_uid="manual-video-id",
        mode="text_only",
        overrides={"lang": "en", "limit": 5},
    )
    assert created["video_id"] == video_repo.video.id
    assert created["kind"] == "video_digest_v1"
    assert created["mode"] == "text_only"
    assert created["overrides_json"] == {"lang": "en", "limit": 5}
    assert created["idempotency_key"] == expected_idempotency
    assert created["force"] is False


def test_process_video_builds_force_idempotency_key_with_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _RepoStub(should_dispatch=False)
    service = VideosService(db=object())
    service.video_repo = _VideoRepoStub()  # type: ignore[assignment]
    service.jobs_repo = repo  # type: ignore[assignment]

    _install_temporal_modules(monkeypatch, client=_FakeClient())

    result = asyncio.run(
        service.process_video(
            platform="youtube",
            url="https://youtu.be/force-video",
            video_id=None,
            mode="full",
            overrides={"x": 1},
            force=True,
        )
    )

    expected_base_key = _build_process_idempotency_key(
        platform="youtube",
        video_uid="force-video",
        mode="full",
        overrides={"x": 1},
    )
    created = repo.created_calls[0]
    assert created["idempotency_key"].startswith(f"{expected_base_key}:force:")
    assert re.fullmatch(
        rf"{re.escape(expected_base_key)}:force:[0-9a-f]{{32}}",
        created["idempotency_key"],
    )
    assert created["force"] is True
    assert result["idempotency_key"] == created["idempotency_key"]


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=abc123", "https://www.youtube.com/watch?v=abc123"),
        ("http://m.youtube.com/watch?v=abc123", "http://m.youtube.com/watch?v=abc123"),
        ("https://youtu.be/abc123", "https://youtu.be/abc123"),
        ("https://music.youtube.com/watch?v=abc123", "https://music.youtube.com/watch?v=abc123"),
        (
            "https://www.bilibili.com/video/BV1xx411c7mD",
            "https://www.bilibili.com/video/BV1xx411c7mD",
        ),
        ("https://m.bilibili.com/video/BV1xx411c7mD", "https://m.bilibili.com/video/BV1xx411c7mD"),
        ("https://b23.tv/abc123", "https://b23.tv/abc123"),
        (" https://www.youtube.com/watch?v=trimmed ", "https://www.youtube.com/watch?v=trimmed"),
    ],
)
def test_validate_video_source_url_accepts_whitelisted_hosts(url: str, expected: str) -> None:
    assert _validate_video_source_url(url) == expected


@pytest.mark.parametrize(
    ("url", "error_code"),
    [
        ("", "video_url_empty"),
        ("ftp://www.youtube.com/watch?v=abc123", "video_url_invalid_scheme"),
        ("https:///watch?v=abc123", "video_url_host_required"),
        ("https://localhost/watch?v=abc123", "video_url_blocked_internal_host"),
        ("https://api.internal/watch?v=abc123", "video_url_blocked_internal_host"),
        ("https://127.0.0.1/watch?v=abc123", "video_url_ip_literal_blocked"),
        ("https://[::1]/watch?v=abc123", "video_url_ip_literal_blocked"),
        ("https://10.0.0.8/watch?v=abc123", "video_url_ip_literal_blocked"),
        ("https://example.com/watch?v=abc123", "video_url_domain_not_allowed"),
        ("https://youtube.com.evil.com/watch?v=abc123", "video_url_domain_not_allowed"),
    ],
)
def test_validate_video_source_url_rejects_disallowed_hosts(url: str, error_code: str) -> None:
    with pytest.raises(ValueError, match=error_code):
        _validate_video_source_url(url)
