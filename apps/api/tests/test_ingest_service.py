from __future__ import annotations

import asyncio
import sys
import types
import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from apps.api.app.errors import ApiTimeoutError
from apps.api.app.services.ingest import IngestService


class _ScalarDB:
    def __init__(self, *, exists: bool = True) -> None:
        self.exists = exists

    def scalar(self, _stmt: Any) -> Any:
        return uuid.uuid4() if self.exists else None


class _RowsResult:
    def __init__(self, rows: list[tuple[Any, Any]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[Any, Any]]:
        return self._rows


class _PollDB:
    def __init__(self, *, exists: bool = True, rows: list[tuple[Any, Any]] | None = None) -> None:
        self.exists = exists
        self.rows = rows or []

    def scalar(self, _stmt: Any) -> Any:
        return uuid.uuid4() if self.exists else None

    def execute(self, _stmt: Any) -> _RowsResult:
        return _RowsResult(self.rows)


class _FakeHandle:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    async def result(self) -> dict[str, Any]:
        return self.payload


class _FakeTemporalClient:
    def __init__(self, *, result_payload: dict[str, Any]) -> None:
        self.calls: list[dict[str, Any]] = []
        self.result_payload = result_payload

    async def start_workflow(
        self,
        workflow: str,
        filters: dict[str, Any],
        *,
        id: str,
        task_queue: str,
    ) -> _FakeHandle:
        self.calls.append(
            {
                "workflow": workflow,
                "filters": filters,
                "id": id,
                "task_queue": task_queue,
            }
        )
        return _FakeHandle(self.result_payload)


def _install_temporal_client(monkeypatch: pytest.MonkeyPatch, client: _FakeTemporalClient) -> None:
    temporalio_mod = types.ModuleType("temporalio")
    temporal_client_mod = types.ModuleType("temporalio.client")

    class _Client:
        @staticmethod
        async def connect(_target_host: str, *, namespace: str) -> _FakeTemporalClient:
            assert namespace
            return client

    temporal_client_mod.Client = _Client
    monkeypatch.setitem(sys.modules, "temporalio", temporalio_mod)
    monkeypatch.setitem(sys.modules, "temporalio.client", temporal_client_mod)


class _WaitForSequence:
    def __init__(self, steps: list[str]) -> None:
        self._steps = iter(steps)

    async def __call__(self, awaitable: Any, timeout: float) -> Any:
        del timeout
        step = next(self._steps)
        if step == "timeout":
            close = getattr(awaitable, "close", None)
            if callable(close):
                close()
            raise TimeoutError()
        return await awaitable


async def _run_poll(
    service: IngestService,
    *,
    subscription_id: uuid.UUID | None = None,
    platform: str | None = "youtube",
    max_new_videos: int = 10,
) -> tuple[int, list[dict[str, object]]]:
    return await service.poll(
        subscription_id=subscription_id,
        platform=platform,
        max_new_videos=max_new_videos,
    )


def test_poll_raises_when_subscription_not_found() -> None:
    service = IngestService(_ScalarDB(exists=False))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="subscription does not exist"):
        asyncio.run(_run_poll(service, subscription_id=uuid.uuid4()))


def test_poll_returns_empty_when_temporal_creates_no_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": []})
    _install_temporal_client(monkeypatch, client)
    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    total, candidates = asyncio.run(_run_poll(service, subscription_id=uuid.uuid4(), platform="youtube", max_new_videos=5))

    assert total == 0
    assert candidates == []
    assert len(client.calls) == 1
    assert client.calls[0]["workflow"] == "PollFeedsWorkflow"
    assert client.calls[0]["filters"]["platform"] == "youtube"
    assert client.calls[0]["filters"]["max_new_videos"] == 5


def test_poll_returns_candidates_from_created_job_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = uuid.uuid4()
    video_id = uuid.uuid4()
    client = _FakeTemporalClient(result_payload={"created_job_ids": [str(job_id)]})
    _install_temporal_client(monkeypatch, client)

    job = SimpleNamespace(id=job_id)
    video = SimpleNamespace(
        id=video_id,
        platform="youtube",
        video_uid="abc123",
        source_url="https://www.youtube.com/watch?v=abc123",
        title="demo",
        published_at=None,
    )
    service = IngestService(_PollDB(exists=True, rows=[(job, video)]))  # type: ignore[arg-type]

    total, candidates = asyncio.run(_run_poll(service, subscription_id=uuid.uuid4(), platform="youtube", max_new_videos=20))

    assert total == 1
    assert len(candidates) == 1
    assert candidates[0]["job_id"] == job_id
    assert candidates[0]["video_id"] == video_id
    assert candidates[0]["video_uid"] == "abc123"
    assert candidates[0]["source_url"] == "https://www.youtube.com/watch?v=abc123"


def test_poll_maps_connect_timeout_to_api_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": []})
    _install_temporal_client(monkeypatch, client)
    monkeypatch.setattr("apps.api.app.services.ingest.asyncio.wait_for", _WaitForSequence(["timeout"]))

    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    with pytest.raises(ApiTimeoutError) as exc_info:
        asyncio.run(_run_poll(service))

    assert exc_info.value.error_code == "TEMPORAL_CONNECT_TIMEOUT"


def test_poll_maps_workflow_start_timeout_to_api_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": []})
    _install_temporal_client(monkeypatch, client)
    monkeypatch.setattr(
        "apps.api.app.services.ingest.asyncio.wait_for",
        _WaitForSequence(["await", "timeout"]),
    )

    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    with pytest.raises(ApiTimeoutError) as exc_info:
        asyncio.run(_run_poll(service))

    assert exc_info.value.error_code == "TEMPORAL_WORKFLOW_START_TIMEOUT"


def test_poll_maps_workflow_result_timeout_to_api_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": [str(uuid.uuid4())]})
    _install_temporal_client(monkeypatch, client)
    monkeypatch.setattr(
        "apps.api.app.services.ingest.asyncio.wait_for",
        _WaitForSequence(["await", "await", "timeout"]),
    )

    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    with pytest.raises(ApiTimeoutError) as exc_info:
        asyncio.run(_run_poll(service))

    assert exc_info.value.error_code == "TEMPORAL_WORKFLOW_RESULT_TIMEOUT"
