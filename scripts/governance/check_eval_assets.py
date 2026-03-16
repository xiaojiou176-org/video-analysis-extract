#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_PATHS = (
    ROOT / "evals" / "README.md",
    ROOT / "evals" / "rubric.md",
    ROOT / "evals" / "golden-set.sample.jsonl",
    ROOT / "evals" / "baseline.json",
)


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object: {path}")
    return payload


def main() -> int:
    failures: list[str] = []
    for path in REQUIRED_PATHS:
        if not path.is_file():
            failures.append(f"missing eval asset: {path.relative_to(ROOT).as_posix()}")

    if failures:
        print("[eval-assets] FAIL")
        for item in failures:
            print(f"  - {item}")
        return 1

    baseline = _load_json(ROOT / "evals" / "baseline.json")
    required_baseline_fields = {
        "version",
        "scope",
        "rubric_version",
        "minimum_pass_rate",
        "dimensions",
        "regression_policy",
    }
    missing = sorted(required_baseline_fields - set(baseline))
    if missing:
        failures.append("baseline.json missing fields: " + ", ".join(missing))

    dimensions = baseline.get("dimensions", {})
    if not isinstance(dimensions, dict) or not dimensions:
        failures.append("baseline.json dimensions must be a non-empty object")
    else:
        for key in ("factuality", "coverage", "citation_hygiene", "failure_honesty"):
            if key not in dimensions:
                failures.append(f"baseline.json missing dimension: {key}")

    policy = baseline.get("regression_policy", {})
    if not isinstance(policy, dict):
        failures.append("baseline.json regression_policy must be an object")
    else:
        for key in ("block_on_dimension_drop", "block_on_pass_rate_drop", "notes"):
            if key not in policy:
                failures.append(f"baseline.json regression_policy missing field: {key}")

    sample_lines = [
        line
        for line in (ROOT / "evals" / "golden-set.sample.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not sample_lines:
        failures.append("golden-set.sample.jsonl must contain at least one sample")
    else:
        for index, line in enumerate(sample_lines, 1):
            payload = json.loads(line)
            for field in ("case_id", "prompt", "expected_signals", "fixture_response"):
                if field not in payload:
                    failures.append(f"golden-set.sample.jsonl line {index} missing field: {field}")

    readme = (ROOT / "evals" / "README.md").read_text(encoding="utf-8")
    rubric = (ROOT / "evals" / "rubric.md").read_text(encoding="utf-8")
    if "baseline.json" not in readme:
        failures.append("evals/README.md must reference baseline.json")
    if "Regression Gate" not in rubric:
        failures.append("evals/rubric.md must describe the regression gate")

    if failures:
        print("[eval-assets] FAIL")
        for item in failures:
            print(f"  - {item}")
        return 1

    print(f"[eval-assets] PASS (cases={len(sample_lines)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
