#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import load_governance_json


def main() -> int:
    config = load_governance_json("logging-contract.json")
    minimum_fields = [str(field) for field in config.get("minimum_common_fields", [])]
    per_channel = {
        str(channel): [str(field) for field in fields]
        for channel, fields in config.get("channel_required_fields", {}).items()
    }
    errors: list[str] = []

    for channel, rel_path in config.get("sample_targets", {}).items():
        path = ROOT / str(rel_path)
        if not path.is_file():
            errors.append(f"{rel_path}: missing sample target")
            continue
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            errors.append(f"{rel_path}: empty sample target")
            continue
        payload = json.loads(lines[-1])
        for field in minimum_fields:
            if payload.get(field) in (None, ""):
                errors.append(f"{rel_path}: missing minimum correlation field `{field}`")
        if str(channel) == "app" and payload.get("trace_id") == "missing_trace":
            errors.append(f"{rel_path}: app logs must carry a real trace_id")
        for field in per_channel.get(str(channel), []):
            if payload.get(field) in (None, ""):
                errors.append(f"{rel_path}: channel `{channel}` missing required field `{field}`")

    if errors:
        print("[log-correlation-completeness] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[log-correlation-completeness] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
