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


def test_load_repo_env_empty_parent_value_does_not_override_repo_env_file(
    tmp_path: Path,
) -> None:
    root = _repo_root()
    key = "TEST_LOAD_ENV_PRIORITY_KEY"
    (tmp_path / ".env").write_text(f"export {key}='from_repo_env'\n", encoding="utf-8")

    probe = f"""
source "{root}/scripts/lib/load_env.sh"
load_repo_env "{tmp_path}" "env_precedence_regression" "local"
printf '%s\n' "${{{key}:-}}"
"""

    proc = _run_bash(probe, env={key: ""})
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "from_repo_env"


def test_load_repo_env_non_empty_parent_value_still_has_highest_precedence(
    tmp_path: Path,
) -> None:
    root = _repo_root()
    key = "TEST_LOAD_ENV_PRIORITY_KEY"
    (tmp_path / ".env").write_text(f"export {key}='from_repo_env'\n", encoding="utf-8")

    probe = f"""
source "{root}/scripts/lib/load_env.sh"
load_repo_env "{tmp_path}" "env_precedence_regression" "local"
printf '%s\n' "${{{key}:-}}"
"""

    proc = _run_bash(probe, env={key: "from_parent"})
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "from_parent"
