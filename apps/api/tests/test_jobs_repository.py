from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import DBAPIError, IntegrityError

from apps.api.app.repositories.jobs import JobsRepository


@dataclass
class _JobStub:
    status: str


class _DBStub:
    def __init__(self) -> None:
        self.rollback_calls = 0

    def rollback(self) -> None:
        self.rollback_calls += 1


class _ResultStub:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row

    def first(self) -> tuple[Any, ...] | None:
        return self._row


class _ExecuteDBStub(_DBStub):
    def __init__(self, *, row: tuple[Any, ...] | None = None, exc: Exception | None = None) -> None:
        super().__init__()
        self._row = row
        self._exc = exc

    def execute(self, _stmt: Any, _params: dict[str, Any]) -> _ResultStub:
        if self._exc is not None:
            raise self._exc
        return _ResultStub(self._row)


def _dbapi_error(message: str) -> DBAPIError:
    return DBAPIError.instance(statement="SELECT 1", params={}, orig=Exception(message), dbapi_base_err=Exception)


class _CreateOrReuseRepo(JobsRepository):
    def __init__(self, db: _DBStub) -> None:
        super().__init__(db)  # type: ignore[arg-type]
        self.created: _JobStub | None = None
        self.active: _JobStub | None = None
        self.retryable: _JobStub | None = None
        self.by_idempotency: _JobStub | None = None
        self.raise_integrity = False

    def create(self, **_: Any) -> _JobStub:  # type: ignore[override]
        if self.raise_integrity:
            raise IntegrityError("insert", {}, Exception("duplicate"))
        assert self.created is not None
        return self.created

    def get_active_by_idempotency_key(self, idempotency_key: str) -> _JobStub | None:  # type: ignore[override]
        del idempotency_key
        return self.active

    def requeue_retryable_dispatch_failure(self, *, idempotency_key: str) -> _JobStub | None:  # type: ignore[override]
        del idempotency_key
        return self.retryable

    def get_by_idempotency_key(self, idempotency_key: str) -> _JobStub | None:  # type: ignore[override]
        del idempotency_key
        return self.by_idempotency


def test_create_or_reuse_returns_active_job_without_create() -> None:
    repo = _CreateOrReuseRepo(_DBStub())
    repo.active = _JobStub(status="running")

    job, created = repo.create_or_reuse(
        video_id=uuid.uuid4(),
        kind="video_digest_v1",
        mode="full",
        overrides_json={},
        idempotency_key="idem-1",
        force=False,
    )

    assert job.status == "running"
    assert created is False


def test_create_or_reuse_requeues_retryable_failure() -> None:
    repo = _CreateOrReuseRepo(_DBStub())
    repo.retryable = _JobStub(status="queued")

    job, created = repo.create_or_reuse(
        video_id=uuid.uuid4(),
        kind="video_digest_v1",
        mode="full",
        overrides_json={},
        idempotency_key="idem-2",
        force=False,
    )

    assert job.status == "queued"
    assert created is True


def test_create_or_reuse_on_integrity_error_rolls_back_and_returns_existing() -> None:
    db = _DBStub()
    repo = _CreateOrReuseRepo(db)
    repo.raise_integrity = True
    repo.by_idempotency = _JobStub(status="queued")

    job, created = repo.create_or_reuse(
        video_id=uuid.uuid4(),
        kind="video_digest_v1",
        mode="full",
        overrides_json={},
        idempotency_key="idem-3",
        force=False,
    )

    assert db.rollback_calls == 1
    assert job.status == "queued"
    assert created is False


def test_get_pipeline_final_status_returns_none_when_column_missing() -> None:
    db = _ExecuteDBStub(exc=_dbapi_error('column "pipeline_final_status" does not exist'))
    repo = JobsRepository(db)  # type: ignore[arg-type]

    result = repo.get_pipeline_final_status(job_id=uuid.uuid4())

    assert result is None
    assert db.rollback_calls == 1


def test_get_artifact_digest_md_returns_none_when_column_missing() -> None:
    db = _ExecuteDBStub(exc=_dbapi_error('column "artifact_digest_md" does not exist'))
    repo = JobsRepository(db)  # type: ignore[arg-type]

    result = repo.get_artifact_digest_md(job_id=uuid.uuid4())

    assert result is None
    assert db.rollback_calls == 1


def test_get_artifact_digest_md_by_video_url_returns_string_value() -> None:
    db = _ExecuteDBStub(row=("# digest",))
    repo = JobsRepository(db)  # type: ignore[arg-type]

    result = repo.get_artifact_digest_md_by_video_url(video_url="https://www.youtube.com/watch?v=abc")

    assert result == "# digest"
