from __future__ import annotations

import base64
import json
import mimetypes
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

_PLAYWRIGHT_HINTS = {
    "playwright",
    "trace",
    "screenshot",
    "snapshot",
    "axe",
    "a11y",
    "accessibility",
    "lighthouse",
}

_FINDING_SEVERITY_MAP = {
    "critical": "critical",
    "serious": "high",
    "high": "high",
    "moderate": "medium",
    "medium": "medium",
    "minor": "low",
    "low": "low",
    "info": "info",
}

_JSON_SUFFIXES = {".json", ".ndjson"}
_MAX_SCAN_FILES = 400


class UiAuditService:
    _run_store: dict[str, dict[str, Any]] = {}
    _store_lock = threading.Lock()

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def run(
        self,
        *,
        job_id: uuid.UUID | None = None,
        artifact_root: str | None = None,
    ) -> dict[str, Any]:
        resolved_root = self._resolve_artifact_root(job_id=job_id, artifact_root=artifact_root)
        run_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        if resolved_root is None:
            payload = {
                "run_id": run_id,
                "job_id": str(job_id) if job_id is not None else None,
                "artifact_root": None,
                "status": "not_found",
                "created_at": created_at,
                "summary": {
                    "artifact_count": 0,
                    "finding_count": 0,
                    "severity_counts": {},
                },
                "findings": [],
                "artifacts": [],
            }
            self._save_run(payload)
            return payload

        artifacts = self._collect_artifacts(resolved_root)
        findings = self._collect_findings(artifacts)
        severity_counts = self._build_severity_counts(findings)

        payload = {
            "run_id": run_id,
            "job_id": str(job_id) if job_id is not None else None,
            "artifact_root": str(resolved_root),
            "status": "completed",
            "created_at": created_at,
            "summary": {
                "artifact_count": len(artifacts),
                "finding_count": len(findings),
                "severity_counts": severity_counts,
            },
            "findings": findings,
            "artifacts": artifacts,
        }
        self._save_run(payload)
        return payload

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._store_lock:
            payload = self._run_store.get(run_id)
        if payload is None:
            return None
        return {
            "run_id": payload["run_id"],
            "job_id": payload.get("job_id"),
            "artifact_root": payload.get("artifact_root"),
            "status": payload.get("status"),
            "created_at": payload.get("created_at"),
            "summary": payload.get("summary") or {
                "artifact_count": 0,
                "finding_count": 0,
                "severity_counts": {},
            },
        }

    def list_findings(self, *, run_id: str, severity: str | None = None) -> list[dict[str, Any]] | None:
        with self._store_lock:
            payload = self._run_store.get(run_id)
        if payload is None:
            return None

        findings = payload.get("findings") if isinstance(payload, dict) else None
        finding_items = findings if isinstance(findings, list) else []
        if severity is None:
            return [item for item in finding_items if isinstance(item, dict)]

        target = severity.strip().lower()
        return [
            item
            for item in finding_items
            if isinstance(item, dict) and str(item.get("severity") or "").lower() == target
        ]

    def list_artifacts(self, *, run_id: str) -> list[dict[str, Any]] | None:
        with self._store_lock:
            payload = self._run_store.get(run_id)
        if payload is None:
            return None

        artifacts = payload.get("artifacts") if isinstance(payload, dict) else None
        return [item for item in artifacts if isinstance(item, dict)] if isinstance(artifacts, list) else []

    def get_artifact(
        self,
        *,
        run_id: str,
        key: str,
        include_base64: bool = False,
    ) -> dict[str, Any] | None:
        artifacts = self.list_artifacts(run_id=run_id)
        if artifacts is None:
            return None

        selected = next((item for item in artifacts if item.get("key") == key), None)
        if selected is None:
            return None

        path_value = selected.get("path")
        if not isinstance(path_value, str):
            return None

        target = Path(path_value).expanduser()
        if not target.exists() or not target.is_file():
            return None

        payload = dict(selected)
        payload["exists"] = True
        payload["base64"] = None
        if include_base64:
            try:
                payload["base64"] = base64.b64encode(target.read_bytes()).decode("ascii")
            except OSError:
                return None
        return payload

    def autofix(
        self,
        *,
        run_id: str,
        mode: str = "dry-run",
        max_files: int = 3,
        max_changed_lines: int = 120,
    ) -> dict[str, Any] | None:
        with self._store_lock:
            payload = self._run_store.get(run_id)
        if payload is None:
            return None

        findings = payload.get("findings") if isinstance(payload, dict) else None
        finding_items = findings if isinstance(findings, list) else []
        high_or_worse = 0
        for item in finding_items:
            if not isinstance(item, dict):
                continue
            severity = str(item.get("severity") or "info").lower()
            if severity in {"critical", "high"}:
                high_or_worse += 1

        suggested_actions: list[str] = []
        if high_or_worse > 0:
            suggested_actions.append("Fix high-severity UI issues first and rerun focused E2E.")
        if finding_items:
            suggested_actions.append("Apply minimal patches and rerun failed tests before full suite.")
        else:
            suggested_actions.append("No findings detected; no code changes recommended.")

        return {
            "run_id": run_id,
            "mode": "dry-run" if mode != "apply" else "apply",
            "autofix_applied": False if mode != "apply" else False,
            "summary": {
                "finding_count": len([item for item in finding_items if isinstance(item, dict)]),
                "high_or_worse_count": int(high_or_worse),
            },
            "guardrails": {
                "max_files": int(max_files),
                "max_changed_lines": int(max_changed_lines),
                "note": "This endpoint currently returns a dry-run plan only.",
            },
            "suggested_actions": suggested_actions,
        }

    def _resolve_artifact_root(
        self,
        *,
        job_id: uuid.UUID | None,
        artifact_root: str | None,
    ) -> Path | None:
        if artifact_root and artifact_root.strip():
            path = Path(artifact_root.strip()).expanduser()
            if path.exists() and path.is_dir():
                return path
            return None

        if job_id is None or self.db is None:
            return None

        statement = text(
            """
            SELECT artifact_root
            FROM jobs
            WHERE CAST(id AS TEXT) = :job_id
            LIMIT 1
            """
        )
        try:
            row = self.db.execute(statement, {"job_id": str(job_id)}).mappings().first()
        except DBAPIError:
            self.db.rollback()
            return None

        root_value = row.get("artifact_root") if row is not None else None
        if not isinstance(root_value, str) or not root_value.strip():
            return None

        path = Path(root_value).expanduser()
        return path if path.exists() and path.is_dir() else None

    def _collect_artifacts(self, root: Path) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        files = sorted((path for path in root.rglob("*") if path.is_file()), key=lambda p: str(p))

        for path in files[:_MAX_SCAN_FILES]:
            relative = path.relative_to(root).as_posix()
            mime_type, _ = mimetypes.guess_type(path.name)
            category = "playwright" if self._is_playwright_artifact(relative) else "artifact"
            try:
                size_bytes = path.stat().st_size
            except OSError:
                size_bytes = 0
            payload.append(
                {
                    "key": relative,
                    "path": str(path),
                    "mime_type": mime_type or "application/octet-stream",
                    "size_bytes": int(size_bytes),
                    "category": category,
                }
            )
        return payload

    def _collect_findings(self, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []

        for artifact in artifacts:
            path_value = artifact.get("path")
            key = artifact.get("key")
            if not isinstance(path_value, str) or not isinstance(key, str):
                continue

            path = Path(path_value)
            if path.suffix.lower() not in _JSON_SUFFIXES:
                continue

            parsed = self._load_json(path)
            if parsed is None:
                continue

            findings.extend(self._extract_findings_from_json(parsed, artifact_key=key))

        if findings:
            return findings

        if any(item.get("category") == "playwright" for item in artifacts):
            return [
                {
                    "id": "evidence-collected",
                    "severity": "info",
                    "title": "Playwright evidence collected",
                    "message": "No structured findings were parsed, but Playwright artifacts were found.",
                    "rule": None,
                    "artifact_key": None,
                }
            ]

        return []

    def _extract_findings_from_json(self, payload: Any, *, artifact_key: str) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            return []

        findings: list[dict[str, Any]] = []

        violations = payload.get("violations")
        if isinstance(violations, list):
            for index, item in enumerate(violations):
                if not isinstance(item, dict):
                    continue
                impact = str(item.get("impact") or "medium").lower()
                severity = _FINDING_SEVERITY_MAP.get(impact, "medium")
                findings.append(
                    {
                        "id": f"{artifact_key}#violation-{index + 1}",
                        "severity": severity,
                        "title": str(item.get("help") or item.get("id") or "Accessibility violation"),
                        "message": str(item.get("description") or "A UI accessibility issue was detected."),
                        "rule": str(item.get("id") or ""),
                        "artifact_key": artifact_key,
                    }
                )

        generic_items = payload.get("findings")
        if isinstance(generic_items, list):
            for index, item in enumerate(generic_items):
                if not isinstance(item, dict):
                    continue
                severity_raw = str(item.get("severity") or "medium").lower()
                findings.append(
                    {
                        "id": str(item.get("id") or f"{artifact_key}#finding-{index + 1}"),
                        "severity": _FINDING_SEVERITY_MAP.get(severity_raw, "medium"),
                        "title": str(item.get("title") or "UI audit finding"),
                        "message": str(item.get("message") or item.get("description") or ""),
                        "rule": str(item.get("rule") or "") or None,
                        "artifact_key": artifact_key,
                    }
                )

        return findings

    def _load_json(self, path: Path) -> dict[str, Any] | None:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return None

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None

        return payload if isinstance(payload, dict) else None

    def _is_playwright_artifact(self, relative: str) -> bool:
        normalized = relative.lower()
        return any(token in normalized for token in _PLAYWRIGHT_HINTS)

    def _build_severity_counts(self, findings: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in findings:
            severity = str(item.get("severity") or "info").lower()
            counts[severity] = counts.get(severity, 0) + 1
        return counts

    def _save_run(self, payload: dict[str, Any]) -> None:
        run_id = str(payload.get("run_id") or "")
        if not run_id:
            return
        with self._store_lock:
            self._run_store[run_id] = payload
