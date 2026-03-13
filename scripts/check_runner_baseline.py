#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
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


def validate_profile(profile: str, baseline: dict[str, Any]) -> list[str]:
    profiles = baseline.get("profiles", {})
    if profile not in profiles:
        return [f"unknown runner baseline profile: {profile}"]
    payload = profiles[profile]
    commands = payload.get("commands", [])
    failures = [f"missing command: {command}" for command in commands if not command_exists(command)]
    if payload.get("docker_compose_required", False) and not docker_compose_available():
        failures.append("missing docker compose")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE_PATH)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()

    baseline = load_baseline(args.baseline)
    failures = validate_profile(args.profile, baseline)
    if failures:
        print("runner baseline check failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    print(f"runner baseline check passed ({args.profile})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
