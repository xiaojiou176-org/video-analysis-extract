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


def test_resolve_runtime_route_value_precedence(tmp_path: Path) -> None:
    root = _repo_root()
    (tmp_path / ".runtime-cache" / "full-stack").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".env").write_text("export API_PORT='3009'\n", encoding="utf-8")
    (tmp_path / ".runtime-cache" / "full-stack" / "resolved.env").write_text(
        "export API_PORT='18000'\n",
        encoding="utf-8",
    )

    probe = f"""
source "{root}/scripts/lib/load_env.sh"
printf '%s\\n' "$(resolve_runtime_route_value "{tmp_path}" "API_PORT" "" "9000")"
printf '%s\\n' "$(resolve_runtime_route_value "{tmp_path}" "API_PORT" "19000" "9000")"
printf '%s\\n' "$(resolve_runtime_route_value "{tmp_path}" "MISSING_KEY" "" "3000")"
"""
    proc = _run_bash(probe)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == ["18000", "19000", "3000"]


def test_bootstrap_runtime_values_do_not_persist_into_repo_env() -> None:
    script = (_repo_root() / "scripts" / "bootstrap_full_stack.sh").read_text(encoding="utf-8")

    assert "write_runtime_resolved_env" in script
    assert 'cat >> "$ROOT_DIR/.env"' not in script
    assert 'upsert_export_env "$ROOT_DIR/.env"' not in script
    assert 'perl -0pi -e "s|export DATABASE_URL=' not in script
    assert "sed -i.bak" not in script


def test_full_stack_status_handles_stale_pid_metadata(tmp_path: Path) -> None:
    root = _repo_root()
    target_script_dir = tmp_path / "scripts"
    target_lib_dir = target_script_dir / "lib"
    target_lib_dir.mkdir(parents=True, exist_ok=True)

    full_stack_target = target_script_dir / "full_stack.sh"
    load_env_target = target_lib_dir / "load_env.sh"
    temporal_ready_target = target_lib_dir / "temporal_ready.sh"
    full_stack_target.write_text(
        (root / "scripts" / "full_stack.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    load_env_target.write_text(
        (root / "scripts" / "lib" / "load_env.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    temporal_ready_target.write_text(
        (root / "scripts" / "lib" / "temporal_ready.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    full_stack_target.chmod(0o755)

    pid_file = tmp_path / ".runtime-cache" / "full-stack" / "api.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(
        (
            "pid=999999\n"
            "pgid=999999\n"
            "service=api\n"
            "signature=api_dev_server\n"
            "started_at=2026-03-08T00:00:00Z\n"
        ),
        encoding="utf-8",
    )

    proc = _run_bash(f'"{full_stack_target}" status', cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "api: stopped" in proc.stdout
    assert not pid_file.exists()


def test_api_base_resolution_is_unified_across_scripts() -> None:
    root = _repo_root()
    http_api = (root / "scripts" / "lib" / "http_api.sh").read_text(encoding="utf-8")
    daily_digest = (root / "scripts" / "run_daily_digest.sh").read_text(encoding="utf-8")
    failure_alerts = (root / "scripts" / "run_failure_alerts.sh").read_text(encoding="utf-8")
    ai_feed_sync = (root / "scripts" / "run_ai_feed_sync.sh").read_text(encoding="utf-8")
    smoke_full_stack = (root / "scripts" / "smoke_full_stack.sh").read_text(encoding="utf-8")

    assert "resolve_http_api_base_url" in http_api
    assert "apply_http_api_base_url" in http_api

    assert 'apply_http_api_base_url "$API_BASE_URL_OVERRIDE" "$ROOT_DIR"' in daily_digest
    assert 'apply_http_api_base_url "$API_BASE_URL_OVERRIDE" "$ROOT_DIR"' in failure_alerts

    assert "resolve_route_value_local" in ai_feed_sync
    assert '"VD_API_BASE_URL"' in ai_feed_sync
    assert "resolve_runtime_route_value" in ai_feed_sync

    assert "resolve_route_value_local" in smoke_full_stack
    assert '"VD_API_BASE_URL"' in smoke_full_stack
    assert "resolve_runtime_route_value" in smoke_full_stack
    assert '--api-base-url "$API_BASE"' in smoke_full_stack


def test_smoke_full_stack_defaults_are_strict_for_local_validation() -> None:
    root = _repo_root()
    smoke_full_stack = (root / "scripts" / "smoke_full_stack.sh").read_text(encoding="utf-8")

    assert 'OFFLINE_FALLBACK="0"' in smoke_full_stack
    assert 'LIVE_SMOKE_REQUIRE_SECRETS="1"' in smoke_full_stack
    assert "Allow offline fallback marker skip (default: 0)" in smoke_full_stack
    assert "e2e live smoke require secrets (default: 1)" in smoke_full_stack
    assert '--require-secrets "$LIVE_SMOKE_REQUIRE_SECRETS"' in smoke_full_stack


def test_e2e_live_smoke_defaults_require_secrets_and_keep_opt_out_explicit() -> None:
    root = _repo_root()
    e2e_live_smoke = (root / "scripts" / "e2e_live_smoke.sh").read_text(encoding="utf-8")

    assert 'LIVE_SMOKE_REQUIRE_SECRETS="1"' in e2e_live_smoke
    assert "Require secrets gate (default: 1)" in e2e_live_smoke
    assert 'if is_truthy "$LIVE_SMOKE_REQUIRE_SECRETS"; then' in e2e_live_smoke
    assert 'fail "missing required secrets: ${missing[*]}"' in e2e_live_smoke
    assert 'log "SKIP: missing secrets: ${missing[*]}"' in e2e_live_smoke
    assert "Scenario: cleanup workflow API closure" in e2e_live_smoke
    assert 'api_post "/api/v1/workflows/run"' in e2e_live_smoke
    assert '"workflow": "cleanup"' in e2e_live_smoke
    assert 'payload["workflow_name"] == "CleanupWorkspaceWorkflow"' in e2e_live_smoke
    assert 'record_scenario "cleanup_workflow_api" "passed" "status=completed"' in e2e_live_smoke
