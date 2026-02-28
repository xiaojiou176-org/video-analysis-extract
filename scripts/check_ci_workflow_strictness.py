#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

WORKFLOW_PATH = Path(".github/workflows/ci.yml")


def _job_blocks(text: str) -> list[tuple[str, str]]:
    jobs: list[tuple[str, int]] = []
    for match in re.finditer(r"^  ([A-Za-z0-9_-]+):\n", text, flags=re.MULTILINE):
        jobs.append((match.group(1), match.start()))
    blocks: list[tuple[str, str]] = []
    for i, (name, start) in enumerate(jobs):
        end = jobs[i + 1][1] if i + 1 < len(jobs) else len(text)
        blocks.append((name, text[start:end]))
    return blocks


def main() -> int:
    if not WORKFLOW_PATH.is_file():
        raise SystemExit(f"missing workflow file: {WORKFLOW_PATH}")

    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    blocks = dict(_job_blocks(text))
    failures: list[str] = []

    # 1) Any runnable job must declare timeout-minutes.
    for job, block in blocks.items():
        if "runs-on:" in block and "timeout-minutes:" not in block:
            failures.append(f"{job}: missing timeout-minutes")

    # 2) quality-gate-pre-push must run broadly (not main/schedule-only gated).
    qg_block = blocks.get("quality-gate-pre-push", "")
    if not qg_block:
        failures.append("quality-gate-pre-push: missing job")
    else:
        if re.search(r"^\s{4}if:\s", qg_block, flags=re.MULTILINE):
            failures.append("quality-gate-pre-push: should not narrow execution with job-level if")
        if "--mode pre-push" not in qg_block:
            failures.append("quality-gate-pre-push: missing pre-push quality gate command")
        if "--ci-dedupe 1" not in qg_block:
            failures.append(
                "quality-gate-pre-push: must set --ci-dedupe 1 to avoid duplicate heavy checks already enforced by standalone CI jobs"
            )
        if "--mutation-min-score 0.62" not in qg_block:
            failures.append("quality-gate-pre-push: mutation threshold must be at least 0.62")
        if "--mutation-min-effective-ratio 0.25" not in qg_block:
            failures.append("quality-gate-pre-push: missing mutation effective ratio floor")
        if "--mutation-max-no-tests-ratio 0.75" not in qg_block:
            failures.append("quality-gate-pre-push: missing mutation no-tests ratio ceiling")

    # 3) Real smoke jobs must not bypass write auth.
    for job_name in ("api-real-smoke", "pr-llm-real-smoke"):
        block = blocks.get(job_name, "")
        if not block:
            failures.append(f"{job_name}: missing job")
            continue
        if "VD_ALLOW_UNAUTH_WRITE" in block:
            failures.append(f"{job_name}: forbidden VD_ALLOW_UNAUTH_WRITE bypass detected")

    # 4) Aggregate gate must require critical jobs.
    aggregate = blocks.get("aggregate-gate", "")
    for required_job in ("quality-gate-pre-push", "api-real-smoke", "web-e2e", "python-tests"):
        if f"- {required_job}" not in aggregate:
            failures.append(f"aggregate-gate: missing needs dependency `{required_job}`")

    # 5) Preflight must include focused-test guard steps.
    required_preflight_markers = {
        "Test focus/todo marker guard": "test focus/todo marker guard step",
        "E2E strictness guard": "e2e strictness guard step",
        "Mutation scope guard": "mutation scope guard step",
        "Mutation test selection guard": "mutation test selection guard step",
    }
    preflight_fast = blocks.get("preflight-fast", "")
    missing_in_preflight = [
        description for marker, description in required_preflight_markers.items() if marker not in preflight_fast
    ]
    if missing_in_preflight:
        # Fallback-aware structure: `preflight-fast` can be a resolver while hosted/fallback
        # execute the actual checks. In that case, both execution paths must contain markers.
        for job_name in ("preflight-fast-hosted", "preflight-fast-fallback"):
            block = blocks.get(job_name, "")
            for marker, description in required_preflight_markers.items():
                if marker not in block:
                    failures.append(f"{job_name}: missing {description}")

    if failures:
        print("ci workflow strictness gate failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("ci workflow strictness gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
