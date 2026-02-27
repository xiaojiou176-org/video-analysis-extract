#!/usr/bin/env python3
from __future__ import annotations

import tomllib
from pathlib import Path

PYPROJECT_PATH = Path("pyproject.toml")

REQUIRED_TEST_SELECTION = {
    "apps/worker/tests/test_llm_step_gates.py",
    "apps/worker/tests/test_coverage_b_policies_and_runner.py",
    "apps/worker/tests/test_runner_modes.py",
    "apps/worker/tests/test_runner_llm_and_status.py",
    "apps/worker/tests/test_runner_overrides.py",
    "apps/worker/tests/test_runner_multimodal.py",
    "apps/worker/tests/test_worker_step_branches.py",
    "apps/worker/tests/test_step_executor_cancellation.py",
    "apps/worker/tests/test_runner_fallbacks.py",
    "apps/worker/tests/test_sqlite_state_locking.py",
    "apps/api/tests/test_ingest_service.py",
    "apps/api/tests/test_jobs_service.py",
    "apps/api/tests/test_subscriptions_service_coverage.py",
    "apps/api/tests/test_videos_service_dispatch.py",
    "apps/api/tests/test_api_routes.py",
    "apps/api/tests/test_videos_and_subscriptions_router_coverage.py",
}

MIN_TEST_SELECTION_COUNT = 16


def main() -> int:
    if not PYPROJECT_PATH.is_file():
        print(f"mutation test selection guard failed: missing {PYPROJECT_PATH}")
        return 1

    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    test_selection = (
        data.get("tool", {}).get("mutmut", {}).get("pytest_add_cli_args_test_selection", [])
    )

    if not isinstance(test_selection, list) or not all(
        isinstance(item, str) for item in test_selection
    ):
        print(
            "mutation test selection guard failed: "
            "[tool.mutmut].pytest_add_cli_args_test_selection must be a string list"
        )
        return 1

    normalized = {item.strip() for item in test_selection if item.strip()}
    missing = sorted(REQUIRED_TEST_SELECTION - normalized)
    if missing:
        print("mutation test selection guard failed: missing required mutation test entries:")
        for item in missing:
            print(f"- {item}")
        return 1

    if len(normalized) < MIN_TEST_SELECTION_COUNT:
        print(
            "mutation test selection guard failed: insufficient selection breadth "
            f"(count={len(normalized)} < required={MIN_TEST_SELECTION_COUNT})"
        )
        return 1

    print(
        "mutation test selection guard passed: "
        f"tests={len(normalized)}, required={len(REQUIRED_TEST_SELECTION)}, min={MIN_TEST_SELECTION_COUNT}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
