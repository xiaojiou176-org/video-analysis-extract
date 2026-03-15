#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: check_mutation_stats.py <stats_path> <min_score> <min_effective_ratio> <max_no_tests_ratio>"
        )

    stats_path = Path(sys.argv[1])
    min_score = float(sys.argv[2])
    min_effective_ratio = float(sys.argv[3])
    max_no_tests_ratio = float(sys.argv[4])

    if not stats_path.exists():
        raise SystemExit(
            f"[quality-gate] mutation gate failed: stats file missing at {stats_path.as_posix()}."
        )

    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    killed = int(stats.get("killed", 0))
    survived = int(stats.get("survived", 0))
    total = int(stats.get("total", killed + survived))
    no_tests = int(stats.get("no_tests", stats.get("skipped", 0)))
    effective = killed + survived

    if effective <= 0:
        raise SystemExit(
            f"[quality-gate] mutation gate failed: killed+survived=0 (total={total}), no effective mutants."
        )

    score = killed / effective
    effective_ratio = effective / total if total > 0 else 0.0
    no_tests_ratio = no_tests / total if total > 0 else 1.0

    print(
        f"[quality-gate] mutation stats: killed={killed}, survived={survived}, "
        f"effective={effective}, total={total}, no_tests={no_tests}, "
        f"score={score:.4f}, threshold={min_score:.4f}, "
        f"effective_ratio={effective_ratio:.4f}, min_effective_ratio={min_effective_ratio:.4f}, "
        f"no_tests_ratio={no_tests_ratio:.4f}, max_no_tests_ratio={max_no_tests_ratio:.4f}"
    )

    if score < min_score:
        raise SystemExit(
            f"[quality-gate] mutation gate failed: score {score:.4f} < threshold {min_score:.4f}."
        )
    if effective_ratio < min_effective_ratio:
        raise SystemExit(
            "[quality-gate] mutation gate failed: "
            f"effective_ratio {effective_ratio:.4f} < min_effective_ratio {min_effective_ratio:.4f}."
        )
    if no_tests_ratio > max_no_tests_ratio:
        raise SystemExit(
            "[quality-gate] mutation gate failed: "
            f"no_tests_ratio {no_tests_ratio:.4f} > max_no_tests_ratio {max_no_tests_ratio:.4f}."
        )

    print("[quality-gate] mutation gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
