from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from worker.config import Settings
from worker.pipeline import orchestrator
from worker.pipeline.types import PIPELINE_STEPS


class _FakeSQLiteStore:
    def get_checkpoint(self, _: str) -> dict[str, Any] | None:
        return None


class _FakePGStore:
    def get_job_with_video(self, *, job_id: str) -> dict[str, Any]:
        return {
            "job_id": job_id,
            "job_status": "running",
            "job_kind": "phase2_ingest_stub",
            "idempotency_key": "idem",
            "video_id": "video-id",
            "platform": "youtube",
            "video_uid": "video-uid",
            "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "title": "Demo",
            "published_at": None,
        }


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
        pipeline_artifact_root=str((tmp_path / "artifact-root").resolve()),
    )


def test_orchestrator_default_handlers_match_pipeline_steps(monkeypatch: Any, tmp_path: Path) -> None:
    seen_steps: list[str] = []

    async def _fake_execute_step(
        _: orchestrator.PipelineContext,
        state: dict[str, Any],
        *,
        step_name: str,
        step_func: Any,
        critical: bool = False,
        resume_hint: bool = False,
        force_run: bool = False,
    ) -> dict[str, Any]:
        del step_func, critical, resume_hint, force_run
        seen_steps.append(step_name)
        state["steps"][step_name] = {"status": "succeeded"}
        return state["steps"][step_name]

    monkeypatch.setattr(orchestrator, "execute_step", _fake_execute_step)

    result = asyncio.run(
        orchestrator.run_pipeline(
            _make_settings(tmp_path),
            _FakeSQLiteStore(),  # type: ignore[arg-type]
            _FakePGStore(),  # type: ignore[arg-type]
            job_id="job-step-contract",
            attempt=1,
            mode="full",
        )
    )

    assert seen_steps == PIPELINE_STEPS
    assert list(result["steps"].keys()) == PIPELINE_STEPS


def test_resolve_llm_gate_hard_required_true_missing_steps_fails() -> None:
    llm_required, gate_passed, hard_fail_reason = orchestrator.resolve_llm_gate(
        {"fetch_metadata": {"status": "succeeded"}},
        pipeline_llm_hard_required=True,
    )

    assert llm_required is True
    assert gate_passed is False
    assert hard_fail_reason == "llm_step_missing"


def test_resolve_llm_gate_hard_required_false_allows_failed_llm_steps() -> None:
    llm_required, gate_passed, hard_fail_reason = orchestrator.resolve_llm_gate(
        {
            "llm_outline": {"status": "failed", "reason": "provider_unavailable"},
            "llm_digest": {"status": "failed", "reason": "provider_unavailable"},
        },
        pipeline_llm_hard_required=False,
    )

    assert llm_required is False
    assert gate_passed is True
    assert hard_fail_reason is None


def test_resolve_pipeline_status_soft_llm_failure_is_degraded() -> None:
    status = orchestrator.resolve_pipeline_status(
        {
            "fetch_metadata": {"status": "succeeded"},
            "llm_outline": {"status": "failed"},
            "llm_digest": {"status": "succeeded"},
            "write_artifacts": {"status": "succeeded"},
        },
        degradations=[],
        pipeline_llm_hard_required=False,
    )

    assert status == "degraded"


def test_orchestrator_with_empty_step_handlers_is_not_succeeded(tmp_path: Path) -> None:
    result = asyncio.run(
        orchestrator.run_pipeline(
            _make_settings(tmp_path),
            _FakeSQLiteStore(),  # type: ignore[arg-type]
            _FakePGStore(),  # type: ignore[arg-type]
            job_id="job-empty-steps",
            attempt=1,
            mode="full",
            step_handlers=[],
        )
    )

    assert result["steps"] == {}
    assert result["final_status"] == "failed"


def test_worker_common_schema_step_names_include_pipeline_steps() -> None:
    schema_path = Path(__file__).resolve().parents[1] / "worker" / "contracts" / "common.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    step_name_def = schema.get("$defs", {}).get("StepName", {})
    step_enums = set(step_name_def.get("enum", []))

    for step in PIPELINE_STEPS:
        assert step in step_enums
