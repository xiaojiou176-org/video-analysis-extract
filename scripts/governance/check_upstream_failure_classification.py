#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import repo_root

ALLOWED_FAILURE_CLASSES = {
    "repo_bug",
    "upstream_api_break",
    "upstream_binary_missing",
    "upstream_image_drift",
    "compat_matrix_gap",
    "local_cache_pollution",
    "environment_contract_violation",
}


def main() -> int:
    root = repo_root()
    logs_root = root / ".runtime-cache" / "logs"
    errors: list[str] = []
    observed = 0

    if logs_root.exists():
        for path in logs_root.rglob("*.jsonl"):
            lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            for line in lines:
                payload = json.loads(line)
                failure_class = payload.get("failure_class")
                if failure_class is None:
                    continue
                observed += 1
                if str(failure_class) not in ALLOWED_FAILURE_CLASSES:
                    errors.append(f"{path.relative_to(root).as_posix()}: unsupported failure_class `{failure_class}`")

    if errors:
        print("[upstream-failure-classification] FAIL")
        for item in errors[:20]:
            print(f"  - {item}")
        return 1

    print(f"[upstream-failure-classification] PASS (observed={observed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
