#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import load_governance_json


def main() -> int:
    evidence = load_governance_json("evidence-contract.json")
    runtime = load_governance_json("runtime-outputs.json")
    errors: list[str] = []

    required_top = {
        "runtime_root",
        "manifest_root",
        "public_entrypoints_source",
        "buckets",
        "required_metadata_fields",
        "required_manifest_fields",
        "evidence_index",
    }
    missing_top = sorted(required_top - set(evidence))
    if missing_top:
        errors.append("missing top-level keys: " + ", ".join(missing_top))

    if evidence.get("runtime_root") != runtime.get("runtime_root"):
        errors.append(
            f"runtime_root drift: evidence-contract={evidence.get('runtime_root')} runtime-outputs={runtime.get('runtime_root')}"
        )

    buckets = evidence.get("buckets", {})
    if not isinstance(buckets, dict) or not buckets:
        errors.append("buckets must be a non-empty object")
    else:
        for name in ("logs", "reports", "evidence"):
            bucket = buckets.get(name)
            if not isinstance(bucket, dict):
                errors.append(f"missing bucket config: {name}")
                continue
            if not str(bucket.get("path") or "").strip():
                errors.append(f"bucket `{name}` missing path")
            if "freshness_required" not in bucket:
                errors.append(f"bucket `{name}` missing freshness_required")

    required_meta = evidence.get("required_metadata_fields", [])
    if not isinstance(required_meta, list) or not required_meta:
        errors.append("required_metadata_fields must be a non-empty list")

    index_cfg = evidence.get("evidence_index", {})
    if not isinstance(index_cfg, dict):
        errors.append("evidence_index must be an object")
    else:
        for field in ("root", "filename_template", "required_fields"):
            value = index_cfg.get(field)
            if value in (None, "", []):
                errors.append(f"evidence_index missing field `{field}`")

    if errors:
        print("[evidence-contract] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[evidence-contract] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
