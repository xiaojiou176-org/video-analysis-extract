#!/usr/bin/env python3
from __future__ import annotations

import tomllib
from pathlib import Path

PYPROJECT_PATH = Path("pyproject.toml")

REQUIRED_TARGETS = {
    "apps/worker/worker/pipeline/orchestrator.py",
    "apps/worker/worker/pipeline/policies.py",
    "apps/worker/worker/pipeline/runner.py",
    "apps/worker/worker/pipeline/types.py",
    "apps/worker/worker/pipeline/step_executor.py",
    "apps/worker/worker/state/sqlite_store.py",
    "apps/api/app/services/ingest.py",
    "apps/api/app/services/jobs.py",
    "apps/api/app/services/subscriptions.py",
    "apps/api/app/services/videos.py",
    "apps/api/app/routers/ingest.py",
    "apps/api/app/routers/jobs.py",
    "apps/api/app/routers/subscriptions.py",
    "apps/api/app/routers/videos.py",
}

MIN_TARGET_COUNT = 16


def main() -> int:
    if not PYPROJECT_PATH.is_file():
        print(f"mutation scope guard failed: missing {PYPROJECT_PATH}")
        return 1

    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    targets = data.get("tool", {}).get("mutmut", {}).get("paths_to_mutate", [])

    if not isinstance(targets, list) or not all(isinstance(item, str) for item in targets):
        print("mutation scope guard failed: [tool.mutmut].paths_to_mutate must be a string list")
        return 1

    normalized = {item.strip() for item in targets if item.strip()}
    missing = sorted(REQUIRED_TARGETS - normalized)
    if missing:
        print("mutation scope guard failed: missing required mutation targets:")
        for item in missing:
            print(f"- {item}")
        return 1

    if len(normalized) < MIN_TARGET_COUNT:
        print(
            "mutation scope guard failed: insufficient mutation target breadth "
            f"(count={len(normalized)} < required={MIN_TARGET_COUNT})"
        )
        return 1

    print(
        "mutation scope guard passed: "
        f"targets={len(normalized)}, required={len(REQUIRED_TARGETS)}, min={MIN_TARGET_COUNT}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
