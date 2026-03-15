#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import artifact_age_hours, load_governance_json, read_runtime_metadata, write_json_artifact


def main() -> int:
    config = load_governance_json("runtime-outputs.json")
    runtime_root = ROOT / str(config["runtime_root"])
    errors: list[str] = []

    for name, subconfig in config.get("subdirectories", {}).items():
        if not bool(subconfig.get("freshness_required")):
            continue
        base = runtime_root / name
        if not base.exists():
            continue
        for artifact in sorted(item for item in base.rglob("*") if item.is_file() and not item.name.endswith(".meta.json")):
            metadata = read_runtime_metadata(artifact)
            if metadata is None:
                errors.append(f"{artifact}: missing runtime metadata for freshness-required artifact")
                continue
            freshness_window_hours = metadata.get("freshness_window_hours")
            if not isinstance(freshness_window_hours, int):
                errors.append(f"{artifact}: freshness-required artifact must declare integer freshness_window_hours")
                continue
            age_hours = artifact_age_hours(artifact, metadata)
            if age_hours > freshness_window_hours:
                errors.append(
                    f"{artifact}: stale artifact age={age_hours:.2f}h exceeds freshness_window_hours={freshness_window_hours}"
                )

    report_path = ROOT / ".runtime-cache" / "reports" / "governance" / "runtime-cache-freshness.json"
    write_json_artifact(
        report_path,
        {"version": 1, "status": "fail" if errors else "pass", "errors": errors},
        source_entrypoint="scripts/governance/check_runtime_cache_freshness.py",
        verification_scope="runtime-cache-freshness",
        source_run_id="governance-runtime-cache-freshness",
        freshness_window_hours=24,
        extra={"report_kind": "runtime-cache-freshness"},
    )

    if errors:
        print("[runtime-cache-freshness] FAIL")
        for item in errors[:20]:
            print(f"  - {item}")
        return 1

    print("[runtime-cache-freshness] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
