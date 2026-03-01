#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"\b\d+\b")
HEX_RE = re.compile(r"\b[0-9a-f]{7,}\b", re.IGNORECASE)

LOG_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("pytest-assertion", re.compile(r"AssertionError[:\s].+")),
    ("python-traceback", re.compile(r"Traceback \(most recent call last\):")),
    ("python-exception", re.compile(r"[A-Za-z_][A-Za-z0-9_]*Error: .+")),
    ("typescript", re.compile(r"TS\d{4}: .+")),
    ("npm-error", re.compile(r"npm ERR! .+")),
    ("eslint", re.compile(r"(?:ESLint|eslint).*(?:error|Error).+")),
]


def _normalize_signal(value: str) -> str:
    compact = " ".join(value.strip().split())
    compact = TOKEN_RE.sub("#", compact)
    compact = HEX_RE.sub("<hash>", compact)
    return compact[:240]


def _fingerprint_id(parts: list[str]) -> str:
    raw = "||".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _suggestion_for_signal(kind: str, signal: str) -> dict[str, str]:
    lower = signal.lower()
    if kind == "junit" and ("assert" in lower or "expected" in lower):
        return {
            "category": "test_assertion",
            "action": "复现失败用例并修正断言或业务逻辑；补充边界输入样例。",
            "validation": "仅重跑失败测试，再跑全量测试。",
        }
    if "timeout" in lower or "timed out" in lower:
        return {
            "category": "timeout",
            "action": "排查慢调用/死循环，必要时缩小测试数据或提升稳定等待条件。",
            "validation": "串行重跑失败用例 3 次。",
        }
    if "module not found" in lower or "cannot import" in lower:
        return {
            "category": "dependency_or_import",
            "action": "检查依赖安装与导入路径；必要时锁定缺失依赖版本。",
            "validation": "重新安装依赖后跑构建与相关测试。",
        }
    if "ts" in lower:
        return {
            "category": "typescript_compile",
            "action": "修复类型签名不匹配并校准 tsconfig/类型依赖。",
            "validation": "运行 `npx tsc --noEmit` 后重跑测试。",
        }
    if "eslint" in lower:
        return {
            "category": "lint",
            "action": "修复 lint 违规，避免 suppress；必要时先执行自动格式化。",
            "validation": "运行 lint 与格式检查。",
        }
    return {
        "category": "generic_failure",
        "action": "基于失败指纹定位首个错误，最小改动修复并补充回归测试。",
        "validation": "重跑失败步骤并确认无新增失败。",
    }


def _parse_junit_file(path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    root = ET.parse(path).getroot()
    testcases = root.findall(".//testcase")
    for case in testcases:
        failure = case.find("failure") or case.find("error")
        if failure is None:
            continue
        message = failure.get("message") or failure.text or "unknown junit failure"
        signal = _normalize_signal(message)
        testsuite = case.get("classname") or "unknown_suite"
        testname = case.get("name") or "unknown_test"
        finding = {
            "source_type": "junit",
            "source_file": str(path),
            "signal": signal,
            "examples": [f"{testsuite}::{testname}", signal],
            "fingerprint_id": _fingerprint_id(["junit", testsuite, testname, signal]),
        }
        finding.update(_suggestion_for_signal("junit", signal))
        findings.append(finding)
    return findings


def _parse_log_file(path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for line in lines:
        for label, pattern in LOG_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            signal = _normalize_signal(match.group(0))
            finding = {
                "source_type": "log",
                "source_file": str(path),
                "signal": signal,
                "examples": [line.strip()[:300]],
                "fingerprint_id": _fingerprint_id(["log", label, signal]),
            }
            finding.update(_suggestion_for_signal("log", signal))
            findings.append(finding)
            break
    return findings


def _expand_inputs(paths: list[str], globs: list[str]) -> list[Path]:
    result: list[Path] = []
    for item in paths:
        path = Path(item)
        if path.is_file():
            result.append(path)
    for pattern in globs:
        result.extend(path for path in Path().glob(pattern) if path.is_file())
    unique: dict[str, Path] = {str(path): path for path in result}
    return [unique[key] for key in sorted(unique)]


def _aggregate(findings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in findings:
        fid = item["fingerprint_id"]
        if fid not in grouped:
            grouped[fid] = {
                "fingerprint_id": fid,
                "source_types": {item["source_type"]},
                "source_files": {item["source_file"]},
                "signal": item["signal"],
                "occurrences": 1,
                "examples": item["examples"][:],
                "category": item["category"],
                "action": item["action"],
                "validation": item["validation"],
            }
            continue
        current = grouped[fid]
        current["source_types"].add(item["source_type"])
        current["source_files"].add(item["source_file"])
        current["occurrences"] += 1
        current["examples"] = (current["examples"] + item["examples"])[:4]

    fingerprints: list[dict[str, Any]] = []
    plan_scores: dict[str, int] = defaultdict(int)
    plan_payload: dict[str, dict[str, str]] = {}

    for payload in grouped.values():
        plan_key = f"{payload['category']}|{payload['action']}|{payload['validation']}"
        plan_scores[plan_key] += payload["occurrences"]
        plan_payload[plan_key] = {
            "category": payload["category"],
            "action": payload["action"],
            "validation": payload["validation"],
        }
        fingerprints.append(
            {
                "fingerprint_id": payload["fingerprint_id"],
                "signal": payload["signal"],
                "occurrences": payload["occurrences"],
                "source_types": sorted(payload["source_types"]),
                "source_files": sorted(payload["source_files"]),
                "examples": payload["examples"],
                "suggestion": plan_payload[plan_key],
            }
        )

    fingerprints.sort(key=lambda item: (-item["occurrences"], item["fingerprint_id"]))
    fix_plan: list[dict[str, Any]] = []
    for plan_key, score in sorted(plan_scores.items(), key=lambda item: (-item[1], item[0])):
        data = plan_payload[plan_key]
        fix_plan.append(
            {
                "priority_score": score,
                "category": data["category"],
                "action": data["action"],
                "validation": data["validation"],
                "mode": "dry-run",
            }
        )
    return fingerprints, fix_plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate dry-run autofix report from CI junit/log artifacts."
    )
    parser.add_argument("--junit", action="append", default=[], help="Path to a junit xml file.")
    parser.add_argument(
        "--junit-glob", action="append", default=[], help="Glob for junit xml files."
    )
    parser.add_argument("--log", action="append", default=[], help="Path to a log file.")
    parser.add_argument("--log-glob", action="append", default=[], help="Glob for log files.")
    parser.add_argument(
        "--output",
        default=".runtime-cache/autofix-report.json",
        help="Output report path.",
    )
    args = parser.parse_args()

    junit_files = _expand_inputs(args.junit, args.junit_glob)
    log_files = _expand_inputs(args.log, args.log_glob)

    findings: list[dict[str, Any]] = []
    for path in junit_files:
        try:
            findings.extend(_parse_junit_file(path))
        except Exception as exc:
            findings.append(
                {
                    "source_type": "junit",
                    "source_file": str(path),
                    "signal": f"failed to parse junit: {exc}",
                    "examples": [str(path)],
                    "fingerprint_id": _fingerprint_id(["junit-parse-error", str(path), str(exc)]),
                    **_suggestion_for_signal("log", "junit parse error"),
                }
            )
    for path in log_files:
        findings.extend(_parse_log_file(path))

    fingerprints, fix_plan = _aggregate(findings)
    report = {
        "mode": "dry-run",
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "inputs": {
            "junit_files": [str(path) for path in junit_files],
            "log_files": [str(path) for path in log_files],
        },
        "summary": {
            "findings": len(findings),
            "unique_fingerprints": len(fingerprints),
            "has_failures": bool(fingerprints),
        },
        "failure_fingerprints": fingerprints,
        "suggested_fix_plan": fix_plan,
        "guardrails": {
            "autofix_applied": False,
            "note": "Dry-run only. No source code modifications are performed by this script.",
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ci-autofix] dry-run report written: {output_path}")
    print(
        "[ci-autofix] summary:"
        f" findings={report['summary']['findings']},"
        f" unique_fingerprints={report['summary']['unique_fingerprints']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
