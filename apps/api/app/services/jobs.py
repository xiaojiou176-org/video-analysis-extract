from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..config import settings
from ..repositories import JobsRepository


class JobsService:
    def __init__(self, db: Session) -> None:
        self.repo = JobsRepository(db)

    def get_job(self, job_id: uuid.UUID):
        return self.repo.get(job_id)

    def get_pipeline_final_status(self, job_id: uuid.UUID, *, fallback_status: str) -> str | None:
        status = self.repo.get_pipeline_final_status(job_id=job_id)
        if status in {"succeeded", "partial", "failed"}:
            return status
        if fallback_status in {"succeeded", "partial", "failed"}:
            return fallback_status
        return None

    def get_steps(self, job_id: uuid.UUID) -> list[dict[str, object]]:
        try:
            conn = sqlite3.connect(settings.sqlite_state_path)
            conn.row_factory = sqlite3.Row
        except sqlite3.Error:
            return []

        try:
            rows = conn.execute(
                """
                SELECT
                    step_name,
                    status,
                    attempt,
                    started_at,
                    finished_at,
                    error_json,
                    error_kind,
                    retry_meta_json,
                    result_json,
                    cache_key
                FROM step_runs
                WHERE job_id = ?
                ORDER BY attempt ASC, started_at ASC, step_name ASC
                """,
                (str(job_id),),
            ).fetchall()
        except sqlite3.Error:
            return []
        finally:
            conn.close()

        result: list[dict[str, object]] = []
        for row in rows:
            error_value = self._json_loads(row["error_json"])
            retry_meta = self._json_loads(row["retry_meta_json"])
            result_payload = self._json_loads(row["result_json"])

            result.append(
                {
                    "name": row["step_name"],
                    "status": row["status"],
                    "attempt": row["attempt"],
                    "started_at": row["started_at"],
                    "finished_at": row["finished_at"],
                    "error": error_value,
                    "error_kind": row["error_kind"],
                    "retry_meta": retry_meta if isinstance(retry_meta, dict) else None,
                    "result": result_payload if isinstance(result_payload, dict) else None,
                    "cache_key": row["cache_key"],
                }
            )

        return result

    def get_step_summary(self, job_id: uuid.UUID) -> list[dict[str, object]]:
        return [
            {
                "name": item["name"],
                "status": item["status"],
                "attempt": item["attempt"],
                "started_at": item["started_at"],
                "finished_at": item["finished_at"],
                "error": item["error"],
            }
            for item in self.get_steps(job_id)
        ]

    def get_degradations(
        self,
        *,
        artifact_root: str | None,
        artifact_digest_md: str | None,
        steps: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        meta = self._read_artifact_meta(artifact_root=artifact_root, digest_path=artifact_digest_md)
        degradations = meta.get("degradations")
        if isinstance(degradations, list):
            return [item for item in degradations if isinstance(item, dict)]

        fallback: list[dict[str, object]] = []
        for step in steps:
            step_name = step.get("name")
            step_status = step.get("status")
            step_error = step.get("error")
            step_result = step.get("result")
            should_collect = step_status in {"failed", "skipped"} or (
                isinstance(step_result, dict) and bool(step_result.get("degraded"))
            )
            if not should_collect:
                continue

            record: dict[str, object] = {
                "step": str(step_name) if step_name else None,
                "status": str(step_status) if step_status else None,
            }
            if isinstance(step_error, dict):
                if "reason" in step_error:
                    record["reason"] = step_error.get("reason")
                if "error" in step_error:
                    record["error"] = step_error.get("error")
                if "error_kind" in step_error:
                    record["error_kind"] = step_error.get("error_kind")
                if "retry_meta" in step_error:
                    record["retry_meta"] = step_error.get("retry_meta")
            elif step_error is not None:
                record["error"] = step_error

            if isinstance(step_result, dict):
                if "reason" in step_result and "reason" not in record:
                    record["reason"] = step_result.get("reason")
                if "error" in step_result and "error" not in record:
                    record["error"] = step_result.get("error")
                if "error_kind" in step_result and "error_kind" not in record:
                    record["error_kind"] = step_result.get("error_kind")
                if "retry_meta" in step_result and "retry_meta" not in record:
                    record["retry_meta"] = step_result.get("retry_meta")
                if "cache_meta" in step_result:
                    record["cache_meta"] = step_result.get("cache_meta")
            fallback.append(record)

        return fallback

    def get_artifacts_index(
        self,
        *,
        artifact_root: str | None,
        artifact_digest_md: str | None,
        steps: list[dict[str, object]],
    ) -> dict[str, str]:
        from_steps = self._artifacts_from_steps(steps)
        if from_steps:
            return from_steps

        index: dict[str, str] = {}
        if artifact_root:
            root = Path(artifact_root).expanduser()
            known_files = {
                "meta": "meta.json",
                "comments": "comments.json",
                "transcript": "transcript.txt",
                "outline": "outline.json",
                "digest": "digest.md",
            }
            for key, name in known_files.items():
                path = root / name
                if path.exists() and path.is_file():
                    index[key] = str(path.resolve())

        if artifact_digest_md:
            digest_path = Path(artifact_digest_md).expanduser()
            if digest_path.exists() and digest_path.is_file():
                index["digest"] = str(digest_path.resolve())

        return index

    def get_artifact_payload(
        self, *, job_id: uuid.UUID | None, video_url: str | None
    ) -> dict[str, Any] | None:
        digest_path: str | None
        if job_id is not None:
            digest_path = self.repo.get_artifact_digest_md(job_id=job_id)
        elif video_url:
            digest_path = self.repo.get_artifact_digest_md_by_video_url(video_url=video_url)
        else:
            return None

        if not digest_path:
            return None

        path = Path(digest_path)
        if not path.exists() or not path.is_file():
            return None
        try:
            markdown = path.read_text(encoding="utf-8")
        except OSError:
            return None
        return {
            "markdown": markdown,
            "meta": self._read_artifact_meta(artifact_root=None, digest_path=str(path)),
        }

    def get_artifact_digest_md(self, *, job_id: uuid.UUID | None, video_url: str | None) -> str | None:
        payload = self.get_artifact_payload(job_id=job_id, video_url=video_url)
        if payload is None:
            return None
        markdown = payload.get("markdown")
        return str(markdown) if isinstance(markdown, str) else None

    def _read_artifact_meta(self, *, artifact_root: str | None, digest_path: str | None) -> dict[str, Any]:
        candidates: list[Path] = []
        if artifact_root:
            candidates.append(Path(artifact_root).expanduser() / "meta.json")
        if digest_path:
            candidates.append(Path(digest_path).expanduser().parent / "meta.json")

        for candidate in candidates:
            if not candidate.exists() or not candidate.is_file():
                continue
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                return payload
        return {}

    def _artifacts_from_steps(self, steps: list[dict[str, object]]) -> dict[str, str]:
        for step in reversed(steps):
            if step.get("name") != "write_artifacts":
                continue
            result = step.get("result")
            if not isinstance(result, dict):
                continue

            files = None
            output = result.get("output")
            if isinstance(output, dict):
                files = output.get("files")
            if not isinstance(files, dict):
                state_updates = result.get("state_updates")
                if isinstance(state_updates, dict):
                    files = state_updates.get("artifacts")
            if not isinstance(files, dict):
                continue

            index = {
                str(key): str(value)
                for key, value in files.items()
                if isinstance(key, str) and isinstance(value, str) and value
            }
            if index:
                return index
        return {}

    def _json_loads(self, payload: str | None) -> Any:
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {"raw": payload}
