#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import write_json_artifact

SIGNAL_DIMENSION_MAP = {
    "outline_is_structured": "coverage",
    "key_topics_present": "coverage",
    "no_invented_sources": "citation_hygiene",
    "summary_is_grounded": "factuality",
    "citation_hygiene_ok": "citation_hygiene",
    "failure_boundary_explicit": "failure_honesty",
}


def _is_structured(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    structured = [line for line in lines if re.match(r"^(\d+\.|- |\* )", line)]
    return len(structured) >= 2


def _has_topics(text: str) -> bool:
    return "主题" in text and len(re.findall(r"^(\d+\.|- |\* )", text, flags=re.MULTILINE)) >= 3


def _no_invented_sources(text: str) -> bool:
    return "http" not in text and "来源:" not in text and "source:" not in text.lower()


def _summary_grounded(text: str) -> bool:
    return any(token in text for token in ("根据", "基于", "证据", "处理结果"))


def _citation_hygiene(text: str) -> bool:
    return any(token in text for token in ("证据", "引用", "可追溯", "[1]"))


def _failure_boundary(text: str) -> bool:
    return any(token in text for token in ("无法确认", "未提供", "如果缺少证据", "边界"))


SIGNAL_CHECKS = {
    "outline_is_structured": _is_structured,
    "key_topics_present": _has_topics,
    "no_invented_sources": _no_invented_sources,
    "summary_is_grounded": _summary_grounded,
    "citation_hygiene_ok": _citation_hygiene,
    "failure_boundary_explicit": _failure_boundary,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic repo-side eval regression against curated fixture responses.")
    parser.add_argument("--golden-set", default="evals/golden-set.sample.jsonl")
    parser.add_argument("--baseline", default="evals/baseline.json")
    parser.add_argument("--rubric", default="evals/rubric.md")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    golden_path = ROOT / args.golden_set
    baseline_path = ROOT / args.baseline
    rubric_path = ROOT / args.rubric
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    _ = rubric_path.read_text(encoding="utf-8")

    run_id = f"eval-regression-{uuid.uuid4().hex}"
    cases_payload: list[dict] = []
    dimension_scores: dict[str, list[float]] = {key: [] for key in baseline["dimensions"]}

    lines = [line for line in golden_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for raw in lines:
        case = json.loads(raw)
        fixture_response = str(case.get("fixture_response") or "").strip()
        signal_results: dict[str, bool] = {}
        for signal in case["expected_signals"]:
            checker = SIGNAL_CHECKS.get(signal)
            signal_results[signal] = bool(checker and checker(fixture_response))
            dimension = SIGNAL_DIMENSION_MAP.get(signal)
            if dimension:
                dimension_scores[dimension].append(1.0 if signal_results[signal] else 0.0)
        case_pass = all(signal_results.values())
        cases_payload.append(
            {
                "case_id": case["case_id"],
                "prompt": case["prompt"],
                "signals": signal_results,
                "pass": case_pass,
                "notes": "deterministic fixture-scored repo-side regression",
            }
        )

    pass_count = sum(1 for item in cases_payload if item["pass"])
    case_count = len(cases_payload)
    pass_rate = pass_count / case_count if case_count else 0.0
    dimensions = {
        key: round(sum(values) / len(values), 4) if values else 0.0
        for key, values in dimension_scores.items()
    }

    status = "passed"
    failures: list[str] = []
    if pass_rate < float(baseline["minimum_pass_rate"]):
        status = "failed"
        failures.append(
            f"pass_rate {pass_rate:.4f} below minimum_pass_rate {float(baseline['minimum_pass_rate']):.4f}"
        )
    for key, floor in baseline["dimensions"].items():
        if float(dimensions.get(key, 0.0)) < float(floor):
            status = "failed"
            failures.append(f"dimension {key}={dimensions.get(key, 0.0):.4f} below floor {float(floor):.4f}")

    report = {
        "version": 1,
        "status": status,
        "run_id": run_id,
        "scope": baseline["scope"],
        "rubric_version": baseline["rubric_version"],
        "baseline_path": args.baseline,
        "golden_set_path": args.golden_set,
        "cases": cases_payload,
        "case_count": case_count,
        "pass_count": pass_count,
        "pass_rate": round(pass_rate, 4),
        "dimensions": dimensions,
        "failures": failures,
    }
    output_path = (
        ROOT / args.output
        if args.output
        else ROOT / ".runtime-cache" / "reports" / "evals" / f"{run_id}.json"
    )
    write_json_artifact(
        output_path,
        report,
        source_entrypoint="scripts/evals/run_regression.py",
        verification_scope="eval-regression",
        source_run_id=run_id,
        freshness_window_hours=168,
        extra={"report_kind": "eval-regression"},
    )

    if status != "passed":
        print("[eval-regression] FAIL")
        for item in failures:
            print(f"  - {item}")
        return 1

    print(f"[eval-regression] PASS (cases={case_count} pass_rate={pass_rate:.4f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
