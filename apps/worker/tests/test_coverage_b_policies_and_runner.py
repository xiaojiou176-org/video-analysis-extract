from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from worker.config import Settings
from worker.pipeline import policies, runner


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        pipeline_workspace_dir=str((tmp_path / "workspace").resolve()),
        pipeline_artifact_root=str((tmp_path / "artifacts").resolve()),
    )


def test_policies_override_and_classification_branches(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)

    assert policies.pipeline_llm_hard_required(settings, {"hard_required": "0"}) is False
    assert policies.pipeline_llm_fail_on_provider_error(settings, {"fail_on_provider_error": "false"}) is False
    assert policies.retry_delay_seconds({"backoff": 0, "max_backoff": 8}, retries_used=4) == 0.0
    assert policies.classify_error("429", "too many request") == "rate_limit"
    assert policies.classify_error(None, "invalid api key") == "auth"
    assert policies.classify_error("unknown", "no known tokens") == "fatal"


def test_runner_policy_wrappers_delegate_to_policy_impls(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)

    retry_policy = runner._build_retry_policy(settings, step_name="llm_outline")
    assert isinstance(retry_policy, dict)
    assert set(retry_policy.keys()) == {"transient", "rate_limit", "auth", "fatal"}
    assert runner._retry_delay_seconds({"backoff": 0.5, "max_backoff": 1.0}, retries_used=2) == 1.0
    assert runner._classify_error("429", None) == "rate_limit"


def test_runner_step_wrappers_delegate_to_impls(monkeypatch: Any, tmp_path: Path) -> None:
    ctx = SimpleNamespace()
    state: dict[str, Any] = {"k": "v"}
    fetch_capture: dict[str, Any] = {}
    embedding_capture: dict[str, Any] = {}

    async def _fake_fetch_impl(
        current_ctx: Any,
        current_state: dict[str, Any],
        *,
        run_command: Any,
    ) -> runner.StepExecution:
        fetch_capture["ctx"] = current_ctx
        fetch_capture["state"] = current_state
        fetch_capture["run_command"] = run_command
        return runner.StepExecution(status="succeeded", output={"wrapped": "fetch"})

    async def _fake_embedding_impl(current_ctx: Any, current_state: dict[str, Any]) -> runner.StepExecution:
        embedding_capture["ctx"] = current_ctx
        embedding_capture["state"] = current_state
        return runner.StepExecution(status="succeeded", output={"wrapped": "embedding"})

    monkeypatch.setattr(runner, "_step_fetch_metadata_impl", _fake_fetch_impl)
    monkeypatch.setattr(runner, "_step_build_embeddings_impl", _fake_embedding_impl)

    fetch_execution = asyncio.run(runner._step_fetch_metadata(ctx, state))
    embedding_execution = asyncio.run(runner._step_build_embeddings(ctx, state))

    assert fetch_execution.output == {"wrapped": "fetch"}
    assert fetch_capture["ctx"] is ctx
    assert fetch_capture["state"] is state
    assert fetch_capture["run_command"] is runner._run_command
    assert embedding_execution.output == {"wrapped": "embedding"}
    assert embedding_capture["ctx"] is ctx
    assert embedding_capture["state"] is state
