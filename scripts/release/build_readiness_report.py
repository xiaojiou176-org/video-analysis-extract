#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import write_json_artifact, write_text_artifact

STATUS_WEIGHT = {
    "pass": 1.0,
    "warn": 0.5,
    "fail": 0.0,
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def _calc_status(value: float, green: float, yellow: float) -> str:
    if value >= green:
        return "pass"
    if value >= yellow:
        return "warn"
    return "fail"


def _build_kpi_checks(
    kpi: dict[str, Any],
    pass_rate_green: float,
    pass_rate_yellow: float,
    coverage_green: float,
    coverage_yellow: float,
    mutation_green: float,
    mutation_yellow: float,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    j = kpi.get("junit", {})
    cp = kpi.get("coverage_python", {})
    cw = kpi.get("coverage_web", {})
    m = kpi.get("mutation", {})

    pass_rate = _to_float(j.get("pass_rate_pct"))
    failed_total = int(_to_float(j.get("failed_total")))
    py_cov = _to_float(cp.get("lines_pct"))
    web_cov = _to_float(cw.get("lines_pct"))
    mutation_score = _to_float(m.get("score_pct"))

    checks.append(
        {
            "name": "junit_pass_rate",
            "value": pass_rate,
            "unit": "%",
            "status": _calc_status(pass_rate, pass_rate_green, pass_rate_yellow),
            "required": True,
            "weight": 2.0,
            "evidence": f"pass_rate_pct={pass_rate:.2f} failed_total={failed_total}",
        }
    )
    checks.append(
        {
            "name": "junit_failed_total",
            "value": failed_total,
            "unit": "count",
            "status": "pass" if failed_total == 0 else ("warn" if failed_total <= 2 else "fail"),
            "required": True,
            "weight": 2.0,
            "evidence": f"failed_total={failed_total}",
        }
    )
    checks.append(
        {
            "name": "python_coverage_lines",
            "value": py_cov,
            "unit": "%",
            "status": _calc_status(py_cov, coverage_green, coverage_yellow),
            "required": True,
            "weight": 1.5,
            "evidence": f"coverage_python.lines_pct={py_cov:.2f}",
        }
    )
    checks.append(
        {
            "name": "web_coverage_lines",
            "value": web_cov,
            "unit": "%",
            "status": _calc_status(web_cov, coverage_green, coverage_yellow),
            "required": True,
            "weight": 1.5,
            "evidence": f"coverage_web.lines_pct={web_cov:.2f}",
        }
    )
    checks.append(
        {
            "name": "mutation_score",
            "value": mutation_score,
            "unit": "%",
            "status": _calc_status(mutation_score, mutation_green, mutation_yellow),
            "required": True,
            "weight": 1.0,
            "evidence": f"mutation.score_pct={mutation_score:.2f}",
        }
    )
    return checks


def _load_external_checks(paths: list[Path]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for path in paths:
        payload = _load_json(path)
        if "checks" in payload and isinstance(payload["checks"], list):
            raw_checks = payload["checks"]
        else:
            raw_checks = [payload]
        for item in raw_checks:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status", "")).strip().lower()
            if status not in STATUS_WEIGHT:
                continue
            name = str(item.get("name", path.stem))
            checks.append(
                {
                    "name": name,
                    "status": status,
                    "required": bool(item.get("required", True)),
                    "weight": float(item.get("weight", 1.0)),
                    "value": item.get("value"),
                    "unit": item.get("unit", ""),
                    "evidence": str(item.get("evidence", f"source={path}")),
                    "source_file": str(path),
                }
            )
    return checks


def _aggregate(
    checks: list[dict[str, Any]], green_threshold: float, yellow_threshold: float
) -> dict[str, Any]:
    total_weight = 0.0
    earned = 0.0
    required_fail = False
    warn_count = 0
    fail_count = 0

    for check in checks:
        status = check["status"]
        weight = max(float(check.get("weight", 1.0)), 0.0)
        total_weight += weight
        earned += weight * STATUS_WEIGHT[status]
        if status == "warn":
            warn_count += 1
        elif status == "fail":
            fail_count += 1
            if bool(check.get("required", True)):
                required_fail = True

    score = 0.0 if total_weight <= 0 else round((earned / total_weight) * 100.0, 2)
    if required_fail or score < yellow_threshold:
        readiness = "red"
    elif warn_count > 0 or score < green_threshold:
        readiness = "yellow"
    else:
        readiness = "green"

    return {
        "readiness": readiness,
        "score_pct": score,
        "checks_total": len(checks),
        "warn_count": warn_count,
        "fail_count": fail_count,
        "required_fail": required_fail,
        "green_threshold": green_threshold,
        "yellow_threshold": yellow_threshold,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines: list[str] = []
    lines.append("# Release Readiness Report")
    lines.append("")
    lines.append(f"- generated_at: `{payload['generated_at']}`")
    lines.append(f"- readiness: `{summary['readiness']}`")
    lines.append(f"- score_pct: `{summary['score_pct']:.2f}`")
    lines.append(
        f"- thresholds: green>={summary['green_threshold']:.2f}, yellow>={summary['yellow_threshold']:.2f}, else red"
    )
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Name | Status | Weight | Required | Value | Evidence |")
    lines.append("|---|---|---:|:---:|---:|---|")
    for item in payload["checks"]:
        value = item.get("value")
        unit = item.get("unit", "")
        value_label = "-" if value is None else f"{value}{unit}"
        lines.append(
            f"| {item['name']} | {item['status']} | {float(item.get('weight', 1.0)):.2f} | "
            f"{'Y' if bool(item.get('required', True)) else 'N'} | {value_label} | {item.get('evidence', '-')} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build release readiness report from KPI summary and optional external check results."
    )
    parser.add_argument(
        "--kpi-json",
        default=".runtime-cache/reports/release-readiness/ci-kpi-summary.json",
        help="KPI json from collect_ci_kpi.py",
    )
    parser.add_argument(
        "--check-json",
        action="append",
        default=[],
        help="Additional check json path. Can be repeated.",
    )
    parser.add_argument(
        "--green-threshold",
        type=float,
        default=85.0,
        help="Readiness score threshold for green.",
    )
    parser.add_argument(
        "--yellow-threshold",
        type=float,
        default=65.0,
        help="Readiness score threshold for yellow.",
    )
    parser.add_argument("--pass-rate-green", type=float, default=100.0)
    parser.add_argument("--pass-rate-yellow", type=float, default=98.0)
    parser.add_argument("--coverage-green", type=float, default=80.0)
    parser.add_argument("--coverage-yellow", type=float, default=75.0)
    parser.add_argument("--mutation-green", type=float, default=85.0)
    parser.add_argument("--mutation-yellow", type=float, default=60.0)
    parser.add_argument(
        "--json-out",
        default=".runtime-cache/reports/release-readiness/release-readiness.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--md-out",
        default=".runtime-cache/reports/release-readiness/release-readiness.md",
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--fail-on-red",
        action="store_true",
        help="Exit 1 when readiness is red.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    kpi_path = Path(args.kpi_json)
    kpi_payload = _load_json(kpi_path)
    kpi = kpi_payload.get("kpi", {})
    if not isinstance(kpi, dict):
        raise SystemExit(f"invalid KPI payload, missing object kpi: {kpi_path}")

    checks = _build_kpi_checks(
        kpi=kpi,
        pass_rate_green=args.pass_rate_green,
        pass_rate_yellow=args.pass_rate_yellow,
        coverage_green=args.coverage_green,
        coverage_yellow=args.coverage_yellow,
        mutation_green=args.mutation_green,
        mutation_yellow=args.mutation_yellow,
    )
    checks.extend(_load_external_checks([Path(p) for p in args.check_json]))

    summary = _aggregate(
        checks=checks,
        green_threshold=float(args.green_threshold),
        yellow_threshold=float(args.yellow_threshold),
    )
    payload = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "inputs": {
            "kpi_json": str(kpi_path),
            "check_json": args.check_json,
        },
        "summary": summary,
        "checks": checks,
    }

    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    write_json_artifact(
        json_out,
        payload,
        source_entrypoint="scripts/release/build_readiness_report.py",
        verification_scope="release-readiness-report",
        source_run_id="release-build-readiness-report",
        freshness_window_hours=24,
        extra={"report_kind": "release-readiness-json"},
    )
    write_text_artifact(
        md_out,
        _render_markdown(payload),
        source_entrypoint="scripts/release/build_readiness_report.py",
        verification_scope="release-readiness-report",
        source_run_id="release-build-readiness-report",
        freshness_window_hours=24,
        extra={"report_kind": "release-readiness-markdown"},
    )

    print(f"[release-readiness] json={json_out}")
    print(f"[release-readiness] markdown={md_out}")
    print(
        "[release-readiness] summary:"
        f" readiness={summary['readiness']},"
        f" score={summary['score_pct']:.2f},"
        f" warn={summary['warn_count']},"
        f" fail={summary['fail_count']}"
    )

    if args.fail_on_red and summary["readiness"] == "red":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
