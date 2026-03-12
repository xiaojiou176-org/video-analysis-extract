from __future__ import annotations

import asyncio
import sys
import types
import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from apps.api.app.errors import ApiTimeoutError
from apps.api.app.services import ingest as ingest_module
from apps.api.app.services.ingest import IngestService


class _ScalarDB:
    def __init__(self, *, exists: bool = True) -> None:
        self.exists = exists
        self.scalar_calls = 0
        self.last_scalar_stmt: Any | None = None

    def scalar(self, stmt: Any) -> Any:
        self.scalar_calls += 1
        self.last_scalar_stmt = stmt
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
        self.scalar_calls = 0
        self.execute_calls = 0
        self.last_scalar_stmt: Any | None = None

    def scalar(self, stmt: Any) -> Any:
        self.scalar_calls += 1
        self.last_scalar_stmt = stmt
        return uuid.uuid4() if self.exists else None

    def execute(self, _stmt: Any) -> _RowsResult:
        self.execute_calls += 1
        return _RowsResult(self.rows)


class _FakeHandle:
    def __init__(self, payload: dict[str, Any], *, workflow_id: str) -> None:
        self.payload = payload
        self.id = workflow_id

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
        return _FakeHandle(self.result_payload, workflow_id=id)


def _install_temporal_client(
    monkeypatch: pytest.MonkeyPatch,
    client: _FakeTemporalClient,
    *,
    connect_calls: list[tuple[str, str]] | None = None,
) -> None:
    temporalio_mod = types.ModuleType("temporalio")
    temporal_client_mod = types.ModuleType("temporalio.client")

    class _Client:
        @staticmethod
        async def connect(target_host: str, *, namespace: str) -> _FakeTemporalClient:
            assert namespace
            if connect_calls is not None:
                connect_calls.append((target_host, namespace))
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
            raise TimeoutError
        return await awaitable


class _WaitForRecorder:
    def __init__(self, steps: list[str]) -> None:
        self._steps = iter(steps)
        self.timeouts: list[float | None] = []

    async def __call__(self, awaitable: Any, timeout: float | None) -> Any:
        self.timeouts.append(timeout)
        step = next(self._steps, "await")
        if step == "timeout":
            close = getattr(awaitable, "close", None)
            if callable(close):
                close()
            raise TimeoutError
        return await awaitable


async def _run_poll(
    service: IngestService,
    *,
    subscription_id: uuid.UUID | None = None,
    platform: str | None = "youtube",
    max_new_videos: int = 10,
    trace_id: str | None = None,
    user: str | None = None,
) -> tuple[int, list[dict[str, object]]]:
    return await service.poll(
        subscription_id=subscription_id,
        platform=platform,
        max_new_videos=max_new_videos,
        trace_id=trace_id,
        user=user,
    )


def test_poll_raises_when_subscription_not_found() -> None:
    db = _ScalarDB(exists=False)
    service = IngestService(db)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match=r"^subscription does not exist$"):
        asyncio.run(_run_poll(service, subscription_id=uuid.uuid4()))

    assert db.scalar_calls == 1
    assert db.last_scalar_stmt is not None
    sql = str(db.last_scalar_stmt)
    assert "SELECT subscriptions.id" in sql
    assert "subscriptions.id =" in sql
    assert "!=" not in sql
    assert "<>" not in sql
    assert "WHERE" in sql
    assert "=" in sql


def test_poll_connects_to_temporal_with_expected_host_and_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": []})
    connect_calls: list[tuple[str, str]] = []
    _install_temporal_client(monkeypatch, client, connect_calls=connect_calls)
    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    total, candidates = asyncio.run(_run_poll(service))

    assert total == 0
    assert candidates == []
    assert connect_calls == [
        (
            ingest_module.settings.temporal_target_host,
            ingest_module.settings.temporal_namespace,
        )
    ]


def test_poll_returns_empty_when_temporal_creates_no_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": []})
    _install_temporal_client(monkeypatch, client)
    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    total, candidates = asyncio.run(
        _run_poll(service, subscription_id=uuid.uuid4(), platform="youtube", max_new_videos=5)
    )

    assert total == 0
    assert candidates == []
    assert len(client.calls) == 1
    assert client.calls[0]["workflow"] == "PollFeedsWorkflow"
    assert client.calls[0]["filters"]["platform"] == "youtube"
    assert client.calls[0]["filters"]["max_new_videos"] == 5


def test_poll_skips_subscription_lookup_when_subscription_id_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": []})
    _install_temporal_client(monkeypatch, client)
    db = _PollDB(exists=True)
    service = IngestService(db)  # type: ignore[arg-type]

    total, candidates = asyncio.run(_run_poll(service, subscription_id=None, platform=None))

    assert total == 0
    assert candidates == []
    assert db.scalar_calls == 0
    assert db.execute_calls == 0
    assert client.calls[0]["filters"] == {
        "subscription_id": None,
        "platform": None,
        "max_new_videos": 10,
    }


def test_poll_workflow_call_includes_expected_id_and_task_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription_id = uuid.uuid4()
    client = _FakeTemporalClient(result_payload={"created_job_ids": []})
    _install_temporal_client(monkeypatch, client)
    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    total, candidates = asyncio.run(
        _run_poll(service, subscription_id=subscription_id, platform="youtube", max_new_videos=7)
    )

    assert total == 0
    assert candidates == []
    assert client.calls[0]["id"].startswith("api-poll-feeds-")
    assert client.calls[0]["task_queue"] == ingest_module.settings.temporal_task_queue
    assert client.calls[0]["filters"] == {
        "subscription_id": str(subscription_id),
        "platform": "youtube",
        "max_new_videos": 7,
    }


def test_poll_returns_immediately_after_workflow_start(monkeypatch: pytest.MonkeyPatch) -> None:
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

    total, candidates = asyncio.run(
        _run_poll(service, subscription_id=uuid.uuid4(), platform="youtube", max_new_videos=20)
    )

    assert total == 0
    assert candidates == []


def test_poll_maps_connect_timeout_to_api_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": []})
    _install_temporal_client(monkeypatch, client)
    monkeypatch.setattr(
        "apps.api.app.services.ingest.asyncio.wait_for", _WaitForSequence(["timeout"])
    )

    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    with pytest.raises(ApiTimeoutError) as exc_info:
        asyncio.run(_run_poll(service))

    assert exc_info.value.error_code == "TEMPORAL_CONNECT_TIMEOUT"
    assert "temporal connect timed out after" in exc_info.value.detail


def test_poll_logs_connect_timeout_with_context(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": []})
    _install_temporal_client(monkeypatch, client)
    monkeypatch.setattr(
        "apps.api.app.services.ingest.asyncio.wait_for", _WaitForSequence(["timeout"])
    )

    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    caplog.set_level("ERROR", logger="apps.api.app.services.ingest")
    with pytest.raises(ApiTimeoutError):
        asyncio.run(_run_poll(service, trace_id="trace-connect", user="operator"))

    timeout_logs = [r for r in caplog.records if r.message == "ingest_temporal_connect_timeout"]
    assert timeout_logs
    timeout_log = timeout_logs[-1]
    assert timeout_log.trace_id == "trace-connect"
    assert timeout_log.user == "operator"
    assert timeout_log.timeout_seconds == ingest_module.settings.api_temporal_connect_timeout_seconds
    assert timeout_log.error == ""


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
    assert "temporal workflow start timed out after" in exc_info.value.detail


def test_poll_passes_temporal_wait_for_timeouts_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": []})
    _install_temporal_client(monkeypatch, client)
    wait_for = _WaitForRecorder(["await", "await"])
    monkeypatch.setattr("apps.api.app.services.ingest.asyncio.wait_for", wait_for)
    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    total, candidates = asyncio.run(_run_poll(service))

    assert total == 0
    assert candidates == []
    assert wait_for.timeouts == [
        ingest_module.settings.api_temporal_connect_timeout_seconds,
        ingest_module.settings.api_temporal_start_timeout_seconds,
    ]


def test_poll_logs_default_trace_actor_and_workflow_id(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": []})
    _install_temporal_client(monkeypatch, client)
    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    caplog.set_level("INFO", logger="apps.api.app.services.ingest")
    total, candidates = asyncio.run(_run_poll(service, trace_id=None, user=None))

    assert total == 0
    assert candidates == []
    start_logs = [r for r in caplog.records if r.message == "ingest_poll_started"]
    assert start_logs
    assert start_logs[-1].trace_id == "missing_trace"
    assert start_logs[-1].user == "system"
    complete_logs = [r for r in caplog.records if r.message == "ingest_poll_completed"]
    assert complete_logs
    complete_log = complete_logs[-1]
    assert complete_log.trace_id == "missing_trace"
    assert complete_log.user == "system"
    assert complete_log.workflow_id == client.calls[0]["id"]
    assert complete_log.enqueued == 0
    assert complete_log.candidates == 0


def test_poll_logs_started_fields_with_explicit_payload(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": []})
    _install_temporal_client(monkeypatch, client)
    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]
    subscription_id = uuid.uuid4()

    caplog.set_level("INFO", logger="apps.api.app.services.ingest")
    total, candidates = asyncio.run(
        _run_poll(
            service,
            subscription_id=subscription_id,
            platform="bilibili",
            max_new_videos=17,
            trace_id="trace-start",
            user="reviewer",
        )
    )

    assert total == 0
    assert candidates == []
    start_logs = [r for r in caplog.records if r.message == "ingest_poll_started"]
    assert start_logs
    start_log = start_logs[-1]
    assert start_log.trace_id == "trace-start"
    assert start_log.user == "reviewer"
    assert start_log.subscription_id == str(subscription_id)
    assert start_log.platform == "bilibili"
    assert start_log.max_new_videos == 17


def test_poll_logs_start_timeout_with_context(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": []})
    _install_temporal_client(monkeypatch, client)
    monkeypatch.setattr(
        "apps.api.app.services.ingest.asyncio.wait_for",
        _WaitForSequence(["await", "timeout"]),
    )
    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    caplog.set_level("ERROR", logger="apps.api.app.services.ingest")
    with pytest.raises(ApiTimeoutError):
        asyncio.run(_run_poll(service, trace_id="trace-1", user="alice"))

    timeout_logs = [r for r in caplog.records if r.message == "ingest_temporal_start_timeout"]
    assert timeout_logs
    timeout_log = timeout_logs[-1]
    assert timeout_log.trace_id == "trace-1"
    assert timeout_log.user == "alice"
    assert timeout_log.timeout_seconds == ingest_module.settings.api_temporal_start_timeout_seconds
    assert timeout_log.error == ""


def test_poll_returns_degraded_empty_result_when_workflow_result_times_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeTemporalClient(result_payload={"created_job_ids": [str(uuid.uuid4())]})
    _install_temporal_client(monkeypatch, client)
    monkeypatch.setattr(
        "apps.api.app.services.ingest.asyncio.wait_for",
        _WaitForSequence(["await", "await", "timeout"]),
    )

    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    total, candidates = asyncio.run(_run_poll(service))

    assert total == 0
    assert candidates == []


def test_poll_raises_runtime_error_when_temporal_client_import_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    temporalio_mod = types.ModuleType("temporalio")
    temporal_client_mod = types.ModuleType("temporalio.client")
    monkeypatch.setitem(sys.modules, "temporalio", temporalio_mod)
    monkeypatch.setitem(sys.modules, "temporalio.client", temporal_client_mod)

    service = IngestService(_PollDB(exists=True))  # type: ignore[arg-type]

    caplog.set_level("ERROR", logger="apps.api.app.services.ingest")
    with pytest.raises(RuntimeError, match="temporal client not available") as exc_info:
        asyncio.run(_run_poll(service))

    error_logs = [r for r in caplog.records if r.message == "ingest_temporal_client_import_failed"]
    assert error_logs
    error_log = error_logs[-1]
    cause = exc_info.value.__cause__
    assert cause is not None
    assert error_log.trace_id == "missing_trace"
    assert error_log.user == "system"
    assert error_log.error == str(cause)
