from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _run_bash(
    script: str, *, cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["bash", "-lc", script],
        cwd=str(cwd) if cwd else None,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )


def _prepare_full_stack_script(tmp_path: Path) -> Path:
    root = _repo_root()
    target_script_dir = tmp_path / "scripts"
    target_lib_dir = target_script_dir / "lib"
    target_lib_dir.mkdir(parents=True, exist_ok=True)

    full_stack_target = target_script_dir / "full_stack.sh"
    full_stack_target.write_text(
        (root / "scripts" / "full_stack.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (target_lib_dir / "load_env.sh").write_text(
        (root / "scripts" / "lib" / "load_env.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    full_stack_target.chmod(0o755)
    return full_stack_target


def test_full_stack_up_fails_worker_env_preflight_before_any_service_start(
    tmp_path: Path,
) -> None:
    full_stack_target = _prepare_full_stack_script(tmp_path)
    proc = _run_bash(
        f'"{full_stack_target}" up',
        cwd=tmp_path,
        env={
            "SQLITE_PATH": "",
            "DATABASE_URL": "",
            "TEMPORAL_TARGET_HOST": "",
            "TEMPORAL_NAMESPACE": "",
            "TEMPORAL_TASK_QUEUE": "",
            "PIPELINE_WORKSPACE_DIR": "",
            "PIPELINE_ARTIFACT_ROOT": "",
        },
    )

    assert proc.returncode != 0
    assert "DIAGNOSE stage=worker_preflight_env conclusion=missing_worker_required_env" in proc.stderr

    api_pid = tmp_path / ".runtime-cache" / "full-stack" / "api.pid"
    api_log = tmp_path / "logs" / "full-stack" / "api.log"
    last_failure_reason = tmp_path / ".runtime-cache" / "full-stack" / "last_failure_reason"

    assert not api_pid.exists()
    assert not api_log.exists()
    assert last_failure_reason.exists()
    assert "stage=worker_preflight_env" in last_failure_reason.read_text(encoding="utf-8")


def test_full_stack_up_records_temporal_preflight_failure_before_service_start(
    tmp_path: Path,
) -> None:
    full_stack_target = _prepare_full_stack_script(tmp_path)
    proc = _run_bash(
        f'"{full_stack_target}" up',
        cwd=tmp_path,
        env={
            "SQLITE_PATH": str(tmp_path / "state.sqlite3"),
            "DATABASE_URL": "sqlite+pysqlite:///:memory:",
            "TEMPORAL_TARGET_HOST": "temporal-invalid-target",
            "TEMPORAL_NAMESPACE": "default",
            "TEMPORAL_TASK_QUEUE": "video-analysis",
            "PIPELINE_WORKSPACE_DIR": str(tmp_path / "workspace"),
            "PIPELINE_ARTIFACT_ROOT": str(tmp_path / "artifacts"),
        },
    )

    assert proc.returncode != 0
    assert "DIAGNOSE stage=worker_preflight_temporal conclusion=temporal_not_ready" in proc.stderr

    api_pid = tmp_path / ".runtime-cache" / "full-stack" / "api.pid"
    api_log = tmp_path / "logs" / "full-stack" / "api.log"
    last_failure_reason = tmp_path / ".runtime-cache" / "full-stack" / "last_failure_reason"

    assert not api_pid.exists()
    assert not api_log.exists()
    assert last_failure_reason.exists()
    failure_text = last_failure_reason.read_text(encoding="utf-8")
    assert "stage=worker_preflight_temporal" in failure_text
    assert "conclusion=temporal_not_ready" in failure_text
