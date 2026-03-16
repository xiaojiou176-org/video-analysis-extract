#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import artifact_age_hours, read_runtime_metadata


def main() -> int:
    baseline = json.loads((ROOT / "evals" / "baseline.json").read_text(encoding="utf-8"))
    reports_root = ROOT / ".runtime-cache" / "reports" / "evals"
    if not reports_root.exists():
        print("[eval-regression-check] FAIL")
        print("  - no eval regression reports found under .runtime-cache/reports/evals")
        return 1

    candidates = sorted(
        (item for item in reports_root.glob("*.json") if item.is_file() and not item.name.endswith(".meta.json")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        print("[eval-regression-check] FAIL")
        print("  - no eval regression reports found under .runtime-cache/reports/evals")
        return 1

    report_path = candidates[0]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    metadata = read_runtime_metadata(report_path)
    errors: list[str] = []

    if report.get("status") != "passed":
        errors.append(f"latest eval regression status is {report.get('status')}, expected passed")
    pass_rate = float(report.get("pass_rate", 0.0))
    minimum_pass_rate = float(baseline["minimum_pass_rate"])
    if pass_rate < minimum_pass_rate:
        errors.append(f"pass_rate {pass_rate:.4f} below minimum_pass_rate {minimum_pass_rate:.4f}")
    for key, floor in baseline["dimensions"].items():
        actual = float(report.get("dimensions", {}).get(key, 0.0))
        if actual < float(floor):
            errors.append(f"dimension {key}={actual:.4f} below floor {float(floor):.4f}")
    if metadata is None:
        errors.append("latest eval regression report is missing runtime metadata")
    else:
        max_age = int(metadata.get("freshness_window_hours") or 168)
        age = artifact_age_hours(report_path, metadata)
        if age > max_age:
            errors.append(f"latest eval regression report age {age:.2f}h exceeds freshness window {max_age}h")

    if errors:
        print("[eval-regression-check] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"[eval-regression-check] PASS ({report_path.relative_to(ROOT).as_posix()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
