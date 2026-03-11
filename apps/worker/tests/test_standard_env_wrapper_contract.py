from __future__ import annotations

import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _run_standard_env_probe(
    *,
    database_url: str,
    temporal_target_host: str,
    simulated_uname: str | None = None,
) -> subprocess.CompletedProcess[str]:
    root = _repo_root()
    script = """source scripts/lib/standard_env.sh
if [[ -n \"${SIMULATED_UNAME:-}\" ]]; then
  uname() {
    printf '%s\\n' \"$SIMULATED_UNAME\"
  }
fi
route_database_url=\"$(resolve_standard_env_runtime_value DATABASE_URL \"$DATABASE_URL\")\"
route_temporal_target_host=\"$(resolve_standard_env_runtime_value TEMPORAL_TARGET_HOST \"$TEMPORAL_TARGET_HOST\")\"
printf 'DATABASE_URL=%s\\n' \"$route_database_url\"
printf 'TEMPORAL_TARGET_HOST=%s\\n' \"$route_temporal_target_host\"
"""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "DATABASE_URL": database_url,
        "TEMPORAL_TARGET_HOST": temporal_target_host,
        "SIMULATED_UNAME": simulated_uname or "",
    }
    return subprocess.run(
        ["bash", "-lc", script],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_standard_env_detection_probe(
    *,
    github_actions: str,
    marker_exists: bool,
    dockerenv_exists: bool,
) -> subprocess.CompletedProcess[str]:
    root = _repo_root()
    with TemporaryDirectory() as tmp_dir:
        marker_path = Path(tmp_dir) / "strict-env-marker"
        dockerenv_path = Path(tmp_dir) / "dockerenv"
        if marker_exists:
            marker_path.write_text("marker", encoding="utf-8")
        if dockerenv_exists:
            dockerenv_path.write_text("dockerenv", encoding="utf-8")
        script = """source scripts/lib/standard_env.sh
if is_running_inside_standard_env; then
  printf 'INSIDE=1\\n'
else
  printf 'INSIDE=0\\n'
fi
"""
        env = {
            "PATH": os.environ.get("PATH", ""),
            "VD_IN_STANDARD_ENV": "0",
            "GITHUB_ACTIONS": github_actions,
            "VD_STANDARD_ENV_MARKER_PATH": str(marker_path),
            "VD_STANDARD_ENV_DOCKERENV_PATH": str(dockerenv_path),
        }
        return subprocess.run(
            ["bash", "-lc", script],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )


def test_standard_env_wrapper_and_helper_contract_exist() -> None:
    root = _repo_root()
    strict_entry = (root / "scripts" / "strict_ci_entry.sh").read_text(encoding="utf-8")
    runner = (root / "scripts" / "run_in_standard_env.sh").read_text(encoding="utf-8")
    helper = (root / "scripts" / "lib" / "standard_env.sh").read_text(encoding="utf-8")
    bootstrap = (root / "scripts" / "bootstrap_strict_ci_runtime.sh").read_text(encoding="utf-8")

    assert 'source "$ROOT_DIR/scripts/lib/standard_env.sh"' in strict_entry
    assert "if is_running_inside_standard_env; then" in strict_entry
    assert "run_with_strict_bootstrap() {" in strict_entry
    assert "source ./scripts/bootstrap_strict_ci_runtime.sh" in strict_entry

    assert 'source "$ROOT_DIR/scripts/lib/standard_env.sh"' in runner
    assert 'ALLOW_LOCAL_BUILD="${VD_STANDARD_ENV_ALLOW_LOCAL_BUILD:-0}"' in runner
    assert "if is_running_inside_standard_env; then" in runner
    assert 'if [[ "$ALLOW_LOCAL_BUILD" == "1" ]]; then' in runner
    assert 'run_in_standard_env "$@"' in runner

    assert 'eval "$(python3 "$ROOT_DIR/scripts/ci_contract.py" shell-exports)"' in helper
    assert 'STANDARD_ENV_IMAGE="${VD_STANDARD_ENV_IMAGE:-$STRICT_CI_STANDARD_IMAGE_REF}"' in helper
    assert 'STANDARD_ENV_DOCKERFILE="${VD_STANDARD_ENV_DOCKERFILE:-$ROOT_DIR/$STRICT_CI_STANDARD_IMAGE_DOCKERFILE}"' in helper
    assert 'STANDARD_ENV_WORKDIR="${VD_STANDARD_ENV_WORKDIR:-$STRICT_CI_STANDARD_IMAGE_WORKDIR}"' in helper
    assert 'docker pull "$STANDARD_ENV_IMAGE"' in helper
    assert 'STANDARD_ENV_MARKER_PATH="${VD_STANDARD_ENV_MARKER_PATH:-/etc/video-analysis-extract-strict-ci-standard-env}"' in helper
    assert 'STANDARD_ENV_DOCKERENV_PATH="${VD_STANDARD_ENV_DOCKERENV_PATH:-/.dockerenv}"' in helper
    assert "-e VD_IN_STANDARD_ENV=1" in helper
    assert 'STANDARD_ENV_HOST_GATEWAY="${VD_STANDARD_ENV_HOST_GATEWAY:-host.docker.internal}"' in helper
    assert "is_truthy_env() {" in helper
    assert "is_running_inside_standard_env() {" in helper
    assert "resolve_standard_env_runtime_value() {" in helper
    assert 'runtime_database_url="$(resolve_standard_env_runtime_value DATABASE_URL "${DATABASE_URL:-}")"' in helper
    assert 'runtime_temporal_target_host="$(resolve_standard_env_runtime_value TEMPORAL_TARGET_HOST "${TEMPORAL_TARGET_HOST:-}")"' in helper
    assert '-e DATABASE_URL="$runtime_database_url"' in helper
    assert '-e TEMPORAL_TARGET_HOST="$runtime_temporal_target_host"' in helper
    assert '-e PYTHONPATH="${PYTHONPATH:-}"' in helper
    assert '-e TEMPORAL_NAMESPACE="${TEMPORAL_NAMESPACE:-}"' in helper
    assert '-e TEMPORAL_TASK_QUEUE="${TEMPORAL_TASK_QUEUE:-}"' in helper

    assert "uv sync --frozen --extra dev --extra e2e" in bootstrap
    assert "npm --prefix apps/web ci --no-audit --no-fund" in bootstrap
    assert 'DATABASE_URL="${DATABASE_URL:-' not in bootstrap


def test_standard_env_detection_uses_marker_file_short_circuit() -> None:
    result = _run_standard_env_detection_probe(
        github_actions="",
        marker_exists=True,
        dockerenv_exists=False,
    )

    assert result.returncode == 0, result.stderr
    assert "INSIDE=1" in result.stdout


def test_standard_env_detection_uses_github_actions_container_fallback() -> None:
    result = _run_standard_env_detection_probe(
        github_actions="true",
        marker_exists=False,
        dockerenv_exists=True,
    )

    assert result.returncode == 0, result.stderr
    assert "INSIDE=1" in result.stdout


def test_standard_env_detection_ignores_container_file_without_github_actions() -> None:
    result = _run_standard_env_detection_probe(
        github_actions="",
        marker_exists=False,
        dockerenv_exists=True,
    )

    assert result.returncode == 0, result.stderr
    assert "INSIDE=0" in result.stdout


def test_standard_env_wrapper_rewrites_loopback_backend_targets_for_container_runtime() -> None:
    result = _run_standard_env_probe(
        database_url="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/video_analysis_pytests",
        temporal_target_host="localhost:7233",
        simulated_uname="Darwin",
    )

    assert result.returncode == 0, result.stderr
    assert (
        "DATABASE_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/video_analysis_pytests"
        in result.stdout
    )
    assert "TEMPORAL_TARGET_HOST=host.docker.internal:7233" in result.stdout


def test_standard_env_wrapper_preserves_non_loopback_backend_targets() -> None:
    result = _run_standard_env_probe(
        database_url="postgresql+psycopg://postgres:postgres@postgres.internal:5432/video_analysis_pytests",
        temporal_target_host="temporal.internal:7233",
        simulated_uname="Darwin",
    )

    assert result.returncode == 0, result.stderr
    assert (
        "DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres.internal:5432/video_analysis_pytests"
        in result.stdout
    )
    assert "TEMPORAL_TARGET_HOST=temporal.internal:7233" in result.stdout


def test_standard_env_wrapper_preserves_loopback_targets_on_linux() -> None:
    result = _run_standard_env_probe(
        database_url="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/video_analysis_pytests",
        temporal_target_host="127.0.0.1:7233",
        simulated_uname="Linux",
    )

    assert result.returncode == 0, result.stderr
    assert (
        "DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/video_analysis_pytests"
        in result.stdout
    )
    assert "TEMPORAL_TARGET_HOST=127.0.0.1:7233" in result.stdout


def test_devcontainer_dockerfile_mitigates_broken_yarn_apt_source_before_update() -> None:
    dockerfile = (_repo_root() / ".devcontainer" / "Dockerfile").read_text(encoding="utf-8")

    assert "rm -f /etc/apt/sources.list.d/yarn.list" in dockerfile
    assert dockerfile.index("rm -f /etc/apt/sources.list.d/yarn.list") < dockerfile.index("apt-get update")


def test_devcontainer_dockerfile_installs_uv_for_repo_owned_wrapper_scripts() -> None:
    dockerfile = (_repo_root() / ".devcontainer" / "Dockerfile").read_text(encoding="utf-8")

    assert 'python3 -m pip install --no-cache-dir "uv==${STRICT_CI_UV_VERSION}"' in dockerfile
    assert "uv --version" in dockerfile


def test_devcontainer_dockerfile_pins_nodesource_node_22_for_standard_env() -> None:
    dockerfile = (_repo_root() / ".devcontainer" / "Dockerfile").read_text(encoding="utf-8")

    assert "STRICT_CI_NODE_MAJOR=22" in dockerfile
    assert "https://deb.nodesource.com/setup_${STRICT_CI_NODE_MAJOR}.x" in dockerfile
    assert dockerfile.index("https://deb.nodesource.com/setup_${STRICT_CI_NODE_MAJOR}.x") < dockerfile.index("apt-get install -y --no-install-recommends \\\n    nodejs")
    assert "nodejs" in dockerfile
