#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE_PATH = REPO_ROOT / "infra" / "config" / "self_hosted_runner_baseline.json"


def load_baseline(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def docker_compose_available() -> bool:
    docker = shutil.which("docker")
    if docker is not None:
        result = subprocess.run(
            [docker, "compose", "version"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return True
    return shutil.which("docker-compose") is not None


def _existing_path(path: Path) -> Path:
    current = path.expanduser().resolve()
    while not current.exists() and current.parent != current:
        current = current.parent
    return current


def _free_gib(path: Path) -> float:
    usage = shutil.disk_usage(_existing_path(path))
    return usage.free / (1024**3)


def _format_gib(value: float) -> str:
    return f"{value:.2f} GiB"


def validate_profile(profile: str, baseline: dict[str, Any], *, workspace: Path) -> tuple[list[str], list[str]]:
    profiles = baseline.get("profiles", {})
    if profile not in profiles:
        return [f"unknown runner baseline profile: {profile}"], []
    payload = profiles[profile]
    commands = payload.get("commands", [])
    failures = [f"missing command: {command}" for command in commands if not command_exists(command)]
    if payload.get("docker_compose_required", False) and not docker_compose_available():
        failures.append("missing docker compose")

    details: list[str] = []
    disk_budget = payload.get("disk_budget_gb", {})
    if isinstance(disk_budget, dict):
        tmp_path = Path(str(payload.get("tmp_path", "/tmp")))
        workspace_path = Path(str(payload.get("workspace_path", workspace)))
        tmp_free_gib = _free_gib(tmp_path)
        workspace_free_gib = _free_gib(workspace_path)
        details.append(f"tmp free: {_format_gib(tmp_free_gib)} at {_existing_path(tmp_path)}")
        details.append(
            f"workspace free: {_format_gib(workspace_free_gib)} at {_existing_path(workspace_path)}"
        )

        min_free_tmp = float(disk_budget.get("min_free_gb_tmp", 0))
        min_free_workspace = float(disk_budget.get("min_free_gb_workspace", 0))
        if tmp_free_gib < min_free_tmp:
            failures.append(
                f"insufficient free space under {_existing_path(tmp_path)}: "
                f"{_format_gib(tmp_free_gib)} < required {_format_gib(min_free_tmp)}"
            )
        if workspace_free_gib < min_free_workspace:
            failures.append(
                f"insufficient free space under {_existing_path(workspace_path)}: "
                f"{_format_gib(workspace_free_gib)} < required {_format_gib(min_free_workspace)}"
            )

        purge_paths = payload.get("purge_paths", [])
        if isinstance(purge_paths, list) and purge_paths:
            details.append("suggested purge paths: " + ", ".join(str(item) for item in purge_paths))

    return failures, details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE_PATH)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--workspace", type=Path, default=REPO_ROOT)
    args = parser.parse_args()

    baseline = load_baseline(args.baseline)
    failures, details = validate_profile(args.profile, baseline, workspace=args.workspace)
    if failures:
        print("runner baseline check failed:")
        for item in failures:
            print(f"- {item}")
        for detail in details:
            print(f"- {detail}")
        return 1

    for detail in details:
        print(detail)
    print(f"runner baseline check passed ({args.profile})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
