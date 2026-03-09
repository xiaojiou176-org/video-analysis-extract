from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_api_real_smoke_script_enforces_real_postgres_and_strict_mode() -> None:
    script = (_repo_root() / "scripts" / "api_real_smoke_local.sh").read_text(encoding="utf-8")

    assert 'driver_name" != "postgresql+psycopg"' in script
    assert "creating isolated smoke database" in script
    assert "CREATE DATABASE" in script
    assert "DROP DATABASE IF EXISTS" in script
    assert 'API_INTEGRATION_SMOKE_STRICT="1"' in script
    assert "uv run pytest apps/api/tests/test_api_integration_smoke.py -q -rA" in script
    assert "workflow-closure-timeout-seconds" in script
    assert "/api/v1/workflows/run" in script
    assert '"workflow": "cleanup"' in script
    assert '"wait_for_result": True' in script
    assert '"workflow_name"] == "CleanupWorkspaceWorkflow"' in script
    assert "api -> temporal -> worker cleanup workflow closure probe passed" in script
    assert 'API_PORT_EXPLICIT="0"' in script
    assert "choose_available_api_port" in script
    assert "using fallback port" in script
    assert "starting temporary worker for cleanup workflow probe" in script
    assert "./scripts/dev_worker.sh --no-show-hints" in script
    assert "temporary worker exited before cleanup workflow probe" in script
    assert "describe_task_queue" in script
    assert "TASK_QUEUE_TYPE_WORKFLOW" in script
    assert "TASK_QUEUE_TYPE_ACTIVITY" in script
    assert "detected existing temporal worker pollers on task queue" in script
    assert "timed out waiting for worker pollers on task queue" in script
    assert "preflight_loopback_ipv4_connectivity" in script
    assert "host_loopback_ipv4_exhausted" in script
    assert "EADDRNOTAVAIL (Errno 49)" in script
