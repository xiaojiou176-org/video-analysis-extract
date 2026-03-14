#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any


def _expand_globs(patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        pattern_path = Path(pattern)
        if pattern_path.is_absolute():
            root = Path(pattern_path.anchor)
            normalized = str(pattern_path).replace(pattern_path.anchor, "", 1).lstrip("/")
            files.extend(path for path in root.glob(normalized) if path.is_file())
        else:
            files.extend(path for path in Path().glob(pattern) if path.is_file())
    unique = {str(path.resolve()): path.resolve() for path in files}
    return [unique[key] for key in sorted(unique)]


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 4)


def _total_bytes(files: list[Path]) -> int:
    total = 0
    for path in files:
        try:
            total += path.stat().st_size
        except FileNotFoundError:
            continue
    return total


def _parse_junit(files: list[Path]) -> dict[str, Any]:
    tests = 0
    failures = 0
    errors = 0
    skipped = 0
    duration_seconds = 0.0
    parsed_files = 0
    broken_files: list[str] = []

    for path in files:
        try:
            root = ET.parse(path).getroot()
        except Exception:
            broken_files.append(str(path))
            continue

        parsed_files += 1
        suites = [root] if root.tag == "testsuite" else root.findall(".//testsuite")
        if not suites and root.tag == "testsuites":
            suites = list(root)
        if not suites and root.tag == "testcase":
            suites = [root]

        for suite in suites:
            tests += _to_int(suite.attrib.get("tests"))
            failures += _to_int(suite.attrib.get("failures"))
            errors += _to_int(suite.attrib.get("errors"))
            skipped += _to_int(suite.attrib.get("skipped"))
            duration_seconds += _to_float(suite.attrib.get("time"))

    failed_total = failures + errors
    passed = max(tests - failed_total - skipped, 0)
    return {
        "files_total": len(files),
        "files_parsed": parsed_files,
        "files_broken": broken_files,
        "tests_total": tests,
        "tests_passed": passed,
        "tests_failed": failures,
        "tests_errors": errors,
        "tests_skipped": skipped,
        "failed_total": failed_total,
        "pass_rate_pct": _pct(passed, tests) if tests else 0.0,
        "duration_seconds": round(duration_seconds, 4),
    }


def _parse_coverage_xml(files: list[Path]) -> dict[str, Any]:
    parsed_files = 0
    broken_files: list[str] = []
    total_lines_covered = 0
    total_lines_valid = 0
    total_branches_covered = 0
    total_branches_valid = 0

    for path in files:
        try:
            root = ET.parse(path).getroot()
        except Exception:
            broken_files.append(str(path))
            continue
        parsed_files += 1

        lc = _to_int(root.attrib.get("lines-covered"))
        lv = _to_int(root.attrib.get("lines-valid"))
        bc = _to_int(root.attrib.get("branches-covered"))
        bv = _to_int(root.attrib.get("branches-valid"))

        if lv <= 0:
            line_rate = _to_float(root.attrib.get("line-rate"), 0.0)
            lv = 10000
            lc = int(round(line_rate * lv))
        if bv <= 0:
            branch_rate = _to_float(root.attrib.get("branch-rate"), 0.0)
            if branch_rate > 0:
                bv = 10000
                bc = int(round(branch_rate * bv))

        total_lines_covered += max(lc, 0)
        total_lines_valid += max(lv, 0)
        total_branches_covered += max(bc, 0)
        total_branches_valid += max(bv, 0)

    lines_pct = _pct(total_lines_covered, total_lines_valid)
    branches_pct = _pct(total_branches_covered, total_branches_valid)
    return {
        "files_total": len(files),
        "files_parsed": parsed_files,
        "files_broken": broken_files,
        "lines_covered": total_lines_covered,
        "lines_valid": total_lines_valid,
        "lines_pct": lines_pct,
        "branches_covered": total_branches_covered,
        "branches_valid": total_branches_valid,
        "branches_pct": branches_pct,
    }


def _parse_coverage_summary(files: list[Path]) -> dict[str, Any]:
    parsed_files = 0
    broken_files: list[str] = []
    lines_total = 0
    lines_covered = 0
    branches_total = 0
    branches_covered = 0
    functions_total = 0
    functions_covered = 0
    statements_total = 0
    statements_covered = 0

    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            broken_files.append(str(path))
            continue

        total = payload.get("total")
        if not isinstance(total, dict):
            broken_files.append(str(path))
            continue

        parsed_files += 1
        lines = total.get("lines", {})
        branches = total.get("branches", {})
        functions = total.get("functions", {})
        statements = total.get("statements", {})

        lines_total += _to_int(lines.get("total"))
        lines_covered += _to_int(lines.get("covered"))
        branches_total += _to_int(branches.get("total"))
        branches_covered += _to_int(branches.get("covered"))
        functions_total += _to_int(functions.get("total"))
        functions_covered += _to_int(functions.get("covered"))
        statements_total += _to_int(statements.get("total"))
        statements_covered += _to_int(statements.get("covered"))

    return {
        "files_total": len(files),
        "files_parsed": parsed_files,
        "files_broken": broken_files,
        "lines_total": lines_total,
        "lines_covered": lines_covered,
        "lines_pct": _pct(lines_covered, lines_total),
        "branches_total": branches_total,
        "branches_covered": branches_covered,
        "branches_pct": _pct(branches_covered, branches_total),
        "functions_total": functions_total,
        "functions_covered": functions_covered,
        "functions_pct": _pct(functions_covered, functions_total),
        "statements_total": statements_total,
        "statements_covered": statements_covered,
        "statements_pct": _pct(statements_covered, statements_total),
    }


def _parse_mutation(files: list[Path]) -> dict[str, Any]:
    parsed_files = 0
    broken_files: list[str] = []
    killed = 0
    survived = 0
    total = 0

    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            broken_files.append(str(path))
            continue
        parsed_files += 1
        killed += _to_int(payload.get("killed"))
        survived += _to_int(payload.get("survived"))
        total += _to_int(payload.get("total"))

    effective = killed + survived
    score_pct = _pct(killed, effective)
    return {
        "files_total": len(files),
        "files_parsed": parsed_files,
        "files_broken": broken_files,
        "killed": killed,
        "survived": survived,
        "total": total,
        "effective": effective,
        "score_pct": score_pct,
    }


def _parse_workflow_topology(files: list[Path]) -> dict[str, Any]:
    text = "\n".join(path.read_text(encoding="utf-8") for path in files if path.is_file())
    return {
        "workflow_files": len(files),
        "normalize_steps": len(re.findall(r"normalize-self-hosted-workspace|Normalize self-hosted workspace", text)),
        "setup_python_steps": len(re.findall(r"actions/setup-python@|setup-python-uv", text)),
        "setup_node_steps": len(re.findall(r"actions/setup-node@|setup-web-node", text)),
        "cache_steps": len(re.findall(r"actions/cache@", text)),
        "install_web_deps_steps": len(re.findall(r"npm --prefix apps/web ci", text)),
    }


def _github_json(url: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _github_bytes(url: str, token: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _parse_run_metrics(repo: str, run_id: str, run_attempt: str, token: str) -> dict[str, Any]:
    jobs_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/attempts/{run_attempt}/jobs?per_page=100"
    payload = _github_json(jobs_url, token)
    jobs = payload.get("jobs", [])
    total_duration = 0.0
    for job in jobs:
        started = job.get("started_at")
        completed = job.get("completed_at")
        if not started or not completed:
            continue
        started_dt = dt.datetime.fromisoformat(started.replace("Z", "+00:00"))
        completed_dt = dt.datetime.fromisoformat(completed.replace("Z", "+00:00"))
        total_duration += max((completed_dt - started_dt).total_seconds(), 0.0)

    cache_hits = 0
    cache_misses = 0
    logs_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/attempts/{run_attempt}/logs"
    try:
        archive = _github_bytes(logs_url, token)
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            for name in zf.namelist():
                content = zf.read(name).decode("utf-8", errors="replace")
                cache_hits += len(re.findall(r"Cache restored from key|cache hit occurred on the primary key", content, flags=re.IGNORECASE))
                cache_misses += len(re.findall(r"Cache not found for input keys|cache miss", content, flags=re.IGNORECASE))
    except Exception:
        pass

    return {
        "status": "ok",
        "jobs_total": len(jobs),
        "jobs_duration_seconds": round(total_duration, 4),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    j = payload["kpi"]["junit"]
    cp = payload["kpi"]["coverage_python"]
    cw = payload["kpi"]["coverage_web"]
    m = payload["kpi"]["mutation"]

    lines: list[str] = []
    lines.append("# CI KPI Summary")
    lines.append("")
    lines.append(f"- generated_at: `{payload['generated_at']}`")
    lines.append("")
    lines.append("## Artifact Inputs")
    lines.append("")
    for name, values in payload["inputs"].items():
        lines.append(f"- {name}: `{len(values)}` files")
    lines.append("")
    lines.append("## KPI Table")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| junit.tests_total | {j['tests_total']} |")
    lines.append(f"| junit.tests_passed | {j['tests_passed']} |")
    lines.append(f"| junit.failed_total | {j['failed_total']} |")
    lines.append(f"| junit.tests_skipped | {j['tests_skipped']} |")
    lines.append(f"| junit.pass_rate_pct | {j['pass_rate_pct']:.2f}% |")
    lines.append(f"| junit.duration_seconds | {j['duration_seconds']:.2f} |")
    lines.append(f"| coverage_python.lines_pct | {cp['lines_pct']:.2f}% |")
    lines.append(f"| coverage_python.branches_pct | {cp['branches_pct']:.2f}% |")
    lines.append(f"| coverage_web.lines_pct | {cw['lines_pct']:.2f}% |")
    lines.append(f"| coverage_web.branches_pct | {cw['branches_pct']:.2f}% |")
    lines.append(f"| coverage_web.functions_pct | {cw['functions_pct']:.2f}% |")
    lines.append(f"| mutation.score_pct | {m['score_pct']:.2f}% |")
    lines.append(f"| mutation.killed | {m['killed']} |")
    lines.append(f"| mutation.survived | {m['survived']} |")
    run = payload["kpi"].get("run", {})
    topology = payload["kpi"].get("topology", {})
    artifacts = payload["kpi"].get("artifacts", {})
    if run:
        if run.get("status") != "ok":
            lines.append(f"| run.status | {run.get('status', 'unknown')} |")
            warning = str(run.get("warning", "")).strip()
            if warning:
                lines.append(f"| run.warning | {warning} |")
        lines.append(f"| run.jobs_total | {run.get('jobs_total', 0)} |")
        lines.append(f"| run.jobs_duration_seconds | {run.get('jobs_duration_seconds', 0):.2f} |")
        lines.append(f"| run.cache_hits | {run.get('cache_hits', 0)} |")
        lines.append(f"| run.cache_misses | {run.get('cache_misses', 0)} |")
    if topology:
        lines.append(f"| topology.normalize_steps | {topology.get('normalize_steps', 0)} |")
        lines.append(f"| topology.setup_python_steps | {topology.get('setup_python_steps', 0)} |")
        lines.append(f"| topology.setup_node_steps | {topology.get('setup_node_steps', 0)} |")
        lines.append(f"| topology.cache_steps | {topology.get('cache_steps', 0)} |")
        lines.append(f"| topology.install_web_deps_steps | {topology.get('install_web_deps_steps', 0)} |")
    if artifacts:
        lines.append(f"| artifacts.total_bytes | {artifacts.get('total_bytes', 0)} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect CI KPI from junit/coverage/mutation artifacts and output JSON + Markdown."
    )
    parser.add_argument(
        "--junit-glob",
        action="append",
        default=[],
        help="Glob for JUnit XML artifacts. Can be passed multiple times.",
    )
    parser.add_argument(
        "--coverage-xml-glob",
        action="append",
        default=[],
        help="Glob for Cobertura/Coverage XML artifacts. Can be passed multiple times.",
    )
    parser.add_argument(
        "--coverage-summary-glob",
        action="append",
        default=[],
        help="Glob for web coverage summary json artifacts.",
    )
    parser.add_argument(
        "--mutation-glob",
        action="append",
        default=[],
        help="Glob for mutation stats json artifacts.",
    )
    parser.add_argument(
        "--artifact-glob",
        action="append",
        default=[],
        help="Glob for downloaded artifacts used to estimate total artifact size.",
    )
    parser.add_argument(
        "--workflow-glob",
        action="append",
        default=[],
        help="Glob for workflow files used to compute topology duplication metrics.",
    )
    parser.add_argument("--repo", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--run-attempt", default="")
    parser.add_argument(
        "--json-out",
        default="reports/release-readiness/ci-kpi-summary.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--md-out",
        default="reports/release-readiness/ci-kpi-summary.md",
        help="Output Markdown path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.junit_glob:
        args.junit_glob = [
            ".runtime-cache/**/*junit*.xml",
            ".runtime-cache/**/*tests-junit*.xml",
        ]
    if not args.coverage_xml_glob:
        args.coverage_xml_glob = [
            ".runtime-cache/**/*coverage*.xml",
            ".runtime-cache/python-coverage.xml",
        ]
    if not args.coverage_summary_glob:
        args.coverage_summary_glob = ["apps/web/coverage/coverage-summary.json"]
    if not args.mutation_glob:
        args.mutation_glob = [
            "mutants/mutmut-cicd-stats.json",
            ".runtime-cache/**/*mutmut*.json",
        ]
    if not args.artifact_glob:
        args.artifact_glob = [".runtime-cache/ci-kpi-inputs/**/*"]
    if not args.workflow_glob:
        args.workflow_glob = [".github/workflows/*.yml"]

    junit_files = _expand_globs(args.junit_glob)
    coverage_xml_files = _expand_globs(args.coverage_xml_glob)
    coverage_summary_files = _expand_globs(args.coverage_summary_glob)
    mutation_files = _expand_globs(args.mutation_glob)
    artifact_files = _expand_globs(args.artifact_glob)
    workflow_files = _expand_globs(args.workflow_glob)

    payload: dict[str, Any] = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs": {
            "junit_files": [str(p) for p in junit_files],
            "coverage_xml_files": [str(p) for p in coverage_xml_files],
            "coverage_summary_files": [str(p) for p in coverage_summary_files],
            "mutation_files": [str(p) for p in mutation_files],
            "artifact_files": [str(p) for p in artifact_files],
            "workflow_files": [str(p) for p in workflow_files],
        },
        "kpi": {
            "junit": _parse_junit(junit_files),
            "coverage_python": _parse_coverage_xml(coverage_xml_files),
            "coverage_web": _parse_coverage_summary(coverage_summary_files),
            "mutation": _parse_mutation(mutation_files),
            "artifacts": {
                "files_total": len(artifact_files),
                "total_bytes": _total_bytes(artifact_files),
            },
            "topology": _parse_workflow_topology(workflow_files),
        },
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if args.repo and args.run_id and args.run_attempt and token:
        try:
            payload["kpi"]["run"] = _parse_run_metrics(args.repo, args.run_id, args.run_attempt, token)
        except Exception as exc:
            payload["kpi"]["run"] = {
                "status": "degraded",
                "warning": f"run-metrics unavailable: {type(exc).__name__}: {exc}",
                "jobs_total": 0,
                "jobs_duration_seconds": 0.0,
                "cache_hits": 0,
                "cache_misses": 0,
            }
    else:
        payload["kpi"]["run"] = {
            "status": "degraded",
            "warning": "run-metrics unavailable: missing repo/run-id/run-attempt or GITHUB_TOKEN",
            "jobs_total": 0,
            "jobs_duration_seconds": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(_render_markdown(payload), encoding="utf-8")

    print(f"[collect-ci-kpi] json={json_out}")
    print(f"[collect-ci-kpi] markdown={md_out}")
    print(
        "[collect-ci-kpi] summary:"
        f" tests={payload['kpi']['junit']['tests_total']},"
        f" failed={payload['kpi']['junit']['failed_total']},"
        f" py_cov={payload['kpi']['coverage_python']['lines_pct']:.2f}%,"
        f" web_cov={payload['kpi']['coverage_web']['lines_pct']:.2f}%,"
        f" mutation={payload['kpi']['mutation']['score_pct']:.2f}%,"
        f" artifacts={payload['kpi']['artifacts']['total_bytes']}B"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
