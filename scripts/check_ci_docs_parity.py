#!/usr/bin/env python3
"""Legacy advisory CI docs parity check.

This script is intentionally lightweight and compatibility-focused. The blocking
docs gate now lives in `scripts/check_docs_governance.py`, which validates the
docs control plane and render freshness. This script only ensures the manual
explanation layer still points readers at the generated governance references.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when legacy parity hints are missing.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    target = repo_root / "docs" / "testing.md"
    generated_ci = repo_root / "docs" / "generated" / "ci-topology.md"
    generated_release = repo_root / "docs" / "generated" / "release-evidence.md"

    if not target.exists():
        print(f"[ERROR] Target file not found: {target}")
        return 2

    content = target.read_text(encoding="utf-8")
    generated_refs = {
        "generated_ci_topology_link": "`docs/generated/ci-topology.md`" in content,
        "generated_release_reference_link": "`docs/generated/release-evidence.md`" in content,
        "trusted_internal_pr_policy": "trusted internal PR" in content or "同仓 trusted internal PR" in content,
        "docs_control_plane_reference": "`config/docs/*.json`" in content or "docs control plane" in content,
    }

    print("Legacy CI Docs Parity Check")
    print(f"Target: {target}")
    print(f"Generated references present: ci={generated_ci.exists()} release={generated_release.exists()}")
    print("Hints:")

    failed = []
    for rule_id, ok in generated_refs.items():
        status = "PASS" if ok else "FAIL"
        print(f"- [{status}] {rule_id}")
        if not ok:
            failed.append(rule_id)

    if failed:
        print("\nResult: WARNING")
        print("Missing legacy explanation hints:")
        for item in failed:
            print(f"- {item}")
        if args.strict:
            return 1
        return 0

    print("\nResult: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
