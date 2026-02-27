#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_SUMMARY_PATH = Path("apps/web/coverage/coverage-summary.json")
DEFAULT_CORE_PATTERNS = [
    "apps/web/lib/*.ts",
    "apps/web/lib/**/*.ts",
    "apps/web/components/*.tsx",
    "apps/web/components/**/*.tsx",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate web coverage thresholds from a Vitest json-summary file. "
            "Hard gates: global >= 85 and core >= 95 by default."
        )
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=DEFAULT_SUMMARY_PATH,
        help="Path to vitest coverage summary JSON. Default: apps/web/coverage/coverage-summary.json",
    )
    parser.add_argument(
        "--global-threshold",
        type=float,
        default=85.0,
        help="Minimum global coverage percentage [0,100]. Default: 85",
    )
    parser.add_argument(
        "--core-threshold",
        type=float,
        default=95.0,
        help="Minimum core coverage percentage [0,100]. Default: 95",
    )
    parser.add_argument(
        "--metric",
        choices=["lines", "statements", "functions", "branches"],
        default="lines",
        help="Coverage metric to evaluate. Default: lines",
    )
    parser.add_argument(
        "--core-pattern",
        action="append",
        default=[],
        help=(
            "Core file glob pattern. Can be passed multiple times. "
            "Default patterns include both direct and nested files under "
            "apps/web/lib and apps/web/components."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved config and exit without reading coverage summary.",
    )
    return parser.parse_args()


def validate_threshold(value: float, name: str) -> None:
    if not 0 <= value <= 100:
        raise SystemExit(f"{name} must be in [0,100], got {value}")


def normalize_path_for_matching(raw_key: str) -> str:
    normalized = raw_key.replace("\\", "/")
    marker = "/apps/web/"
    index = normalized.rfind(marker)
    if index >= 0:
        return normalized[index + 1 :]
    return normalized.lstrip("./")


def load_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        cmd = ["npm", "--prefix", "apps/web", "run", "test", "--", "--coverage"]
        print(
            f"coverage summary not found: {path}. Generating with: {' '.join(cmd)}",
        )
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(
                f"failed to generate coverage summary via {' '.join(cmd)} (exit={exc.returncode})"
            ) from exc
    if not path.is_file():
        raise SystemExit(f"coverage summary not found after generation attempt: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid coverage summary JSON: {path} ({exc})") from exc


def pick_metric_bucket(payload: dict[str, Any], metric: str, scope: str) -> dict[str, Any]:
    bucket = payload.get(metric)
    if not isinstance(bucket, dict):
        raise SystemExit(f"missing metric '{metric}' in {scope} coverage payload")
    return bucket


def read_pct(bucket: dict[str, Any], scope: str, metric: str) -> float:
    pct = bucket.get("pct")
    if not isinstance(pct, (int, float)):
        raise SystemExit(f"missing numeric pct in {scope}.{metric}")
    return float(pct)


def read_count(bucket: dict[str, Any], key: str, scope: str, metric: str) -> int:
    value = bucket.get(key)
    if not isinstance(value, (int, float)):
        raise SystemExit(f"missing numeric {key} in {scope}.{metric}")
    return int(value)


def is_core_file(path_key: str, patterns: list[str]) -> bool:
    normalized = path_key.replace("\\", "/")
    relative = normalize_path_for_matching(path_key)
    return any(
        fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(relative, pattern)
        for pattern in patterns
    )


def evaluate(
    summary: dict[str, Any], metric: str, core_patterns: list[str]
) -> tuple[float, int, int, float, int, int, int]:
    total_payload = summary.get("total")
    if not isinstance(total_payload, dict):
        raise SystemExit("coverage summary missing 'total' section")

    global_bucket = pick_metric_bucket(total_payload, metric, "total")
    global_pct = read_pct(global_bucket, "total", metric)

    core_total = 0
    core_covered = 0
    core_matches = 0

    for file_key, payload in summary.items():
        if file_key == "total":
            continue
        if not isinstance(payload, dict):
            continue
        if not is_core_file(file_key, core_patterns):
            continue

        metric_bucket = pick_metric_bucket(payload, metric, file_key)
        core_total += read_count(metric_bucket, "total", file_key, metric)
        core_covered += read_count(metric_bucket, "covered", file_key, metric)
        core_matches += 1

    core_pct = (100.0 * core_covered / core_total) if core_total else 0.0
    global_total = read_count(global_bucket, "total", "total", metric)
    global_covered = read_count(global_bucket, "covered", "total", metric)
    return (
        global_pct,
        global_total,
        global_covered,
        core_pct,
        core_total,
        core_covered,
        core_matches,
    )


def main() -> int:
    args = parse_args()
    validate_threshold(args.global_threshold, "global-threshold")
    validate_threshold(args.core_threshold, "core-threshold")

    core_patterns = args.core_pattern if args.core_pattern else list(DEFAULT_CORE_PATTERNS)

    if args.dry_run:
        print("[dry-run] web coverage threshold check configuration")
        print(f"[dry-run] summary_path={args.summary_path}")
        print(f"[dry-run] metric={args.metric}")
        print(f"[dry-run] global_threshold={args.global_threshold:.2f}%")
        print(f"[dry-run] core_threshold={args.core_threshold:.2f}%")
        print(f"[dry-run] core_patterns={core_patterns}")
        return 0

    summary = load_summary(args.summary_path)
    (
        global_pct,
        global_total,
        global_covered,
        core_pct,
        core_total,
        core_covered,
        core_matches,
    ) = evaluate(summary, args.metric, core_patterns)

    print(
        "web coverage gate: "
        f"metric={args.metric} "
        f"global={global_pct:.2f}% ({global_covered}/{global_total}) "
        f"core={core_pct:.2f}% ({core_covered}/{core_total}) "
        f"core_matches={core_matches}"
    )

    failures: list[str] = []
    if global_pct < args.global_threshold:
        failures.append(
            f"global coverage {global_pct:.2f}% is below threshold {args.global_threshold:.2f}%"
        )
    if core_matches == 0:
        failures.append(
            "no core files matched --core-pattern; adjust patterns or coverage include settings"
        )
    elif core_pct < args.core_threshold:
        failures.append(
            f"core coverage {core_pct:.2f}% is below threshold {args.core_threshold:.2f}%"
        )

    if failures:
        print("web coverage gate failed:")
        for item in failures:
            print(f"  - {item}")
        print(f"summary_path={args.summary_path}")
        print(f"core_patterns={core_patterns}")
        return 1

    print("web coverage gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
