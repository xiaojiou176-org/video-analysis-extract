#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config" / "docs"
GENERATED_HEADER = "<!-- generated: docs governance control plane; do not edit directly -->\n"
FRAGMENT_START = "<!-- docs:generated {marker} start -->"
FRAGMENT_END = "<!-- docs:generated {marker} end -->"


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _load_configs() -> tuple[dict, dict, dict, dict]:
    nav = _load_json(CONFIG_DIR / "nav-registry.json")
    manifest = _load_json(CONFIG_DIR / "render-manifest.json")
    boundary = _load_json(CONFIG_DIR / "boundary-policy.json")
    change_contract = _load_json(CONFIG_DIR / "change-contract.json")
    return nav, manifest, boundary, change_contract


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_aggregate_jobs(ci_text: str) -> list[str]:
    match = re.search(
        r"aggregate-gate:\n(?:.*\n)*?\s{4}needs:\n((?:\s{6}- .+\n)+)",
        ci_text,
        flags=re.MULTILINE,
    )
    if not match:
        return []
    block = match.group(1)
    jobs = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            jobs.append(stripped[2:].strip())
    return jobs


def _extract_ci_trigger_lines(ci_text: str) -> list[str]:
    lines = []
    for pattern in (
        r"pull_request:",
        r"push:\n(?:\s{4}.+\n)+",
        r"schedule:\n(?:\s{4}- .+\n)+",
    ):
        match = re.search(pattern, ci_text)
        if match:
            cleaned = " ".join(part.strip() for part in match.group(0).splitlines())
            lines.append(cleaned)
    return lines


def _render_ci_topology(manifest: dict, boundary: dict) -> str:
    ci_text = _read_text(REPO_ROOT / ".github" / "workflows" / "ci.yml")
    monthly_audit_text = _read_text(REPO_ROOT / ".github" / "workflows" / "monthly-governance-audit.yml")
    strict_contract = _load_json(REPO_ROOT / "infra" / "config" / "strict_ci_contract.json")
    root_allowlist = _load_json(REPO_ROOT / "config" / "governance" / "root-allowlist.json")
    runtime_outputs = _load_json(REPO_ROOT / "config" / "governance" / "runtime-outputs.json")
    upstreams = _load_json(REPO_ROOT / "config" / "governance" / "active-upstreams.json")
    templates = _load_json(REPO_ROOT / "config" / "governance" / "upstream-templates.json")
    aggregate_jobs = _extract_aggregate_jobs(ci_text)
    trigger_lines = _extract_ci_trigger_lines(ci_text)
    trust_boundary = boundary["trust_boundary"]
    outputs = [
        GENERATED_HEADER,
        "# CI Topology Reference",
        "",
        "## Trust Boundary",
        "",
        f"- mode: `{trust_boundary['mode']}`",
        f"- summary: {trust_boundary['summary']}",
        "- policy source: `config/docs/boundary-policy.json`",
        "",
        "## Strict Runtime Contract",
        "",
        f"- standard image repository: `{strict_contract['standard_image']['repository']}`",
        f"- standard image workdir: `{strict_contract['standard_image']['workdir']}`",
        f"- python version: `{strict_contract['toolchain']['python_version']}`",
        f"- node major: `{strict_contract['toolchain']['node_major']}`",
        f"- coverage min: `{strict_contract['quality']['coverage_min']}`",
        f"- core coverage min: `{strict_contract['quality']['core_coverage_min']}`",
        f"- mutation min score: `{strict_contract['quality']['mutation_min_score']}`",
        "",
        "## Governance Control Plane",
        "",
        f"- root allowlist entries: `{len(root_allowlist.get('entries', []))}`",
        f"- runtime root: `{runtime_outputs.get('runtime_root', '.runtime-cache')}`",
        "- current-run CI KPI summary: `.runtime-cache/reports/release-readiness/ci-kpi-summary.json`",
        "- current-run readiness reports: `.runtime-cache/reports/release-readiness/`",
        f"- active upstream inventory entries: `{len(upstreams.get('entries', []))}`",
        f"- upstream templates: `{len(templates.get('entries', []))}`",
        "- governance gate entrypoint: `./bin/governance-audit --mode pre-commit|pre-push|ci|audit`",
        "",
        "## Aggregate Gate Inventory",
        "",
        "| Job | Role |",
        "| --- | --- |",
    ]
    for job in aggregate_jobs:
        role = "required chain input"
        if job in {"external-playwright-smoke", "pr-llm-real-smoke"}:
            role = "conditional edge or live evidence input"
        elif "lint" in job:
            role = "fast/static correctness"
        elif "smoke" in job or "e2e" in job:
            role = "integration or end-to-end evidence"
        outputs.append(f"| `{job}` | {role} |")
    outputs.extend(
        [
            "",
            "## Governance Audit Workflows",
            "",
        ]
    )
    if "monthly-governance-audit" in monthly_audit_text:
        outputs.append("- `monthly-governance-audit.yml`: emits recurring root/runtime/logging/upstream governance evidence")
    outputs.extend(
        [
            "",
            "## Trigger Surfaces",
            "",
        ]
    )
    outputs.extend(f"- {line}" for line in trigger_lines)
    outputs.extend(
        [
            "",
            "## Docs Control Plane Outputs",
            "",
        ]
    )
    for entry in manifest["generated_docs"]:
        outputs.append(f"- `{entry['path']}`")
    return "\n".join(outputs).rstrip() + "\n"


def _render_required_checks() -> str:
    ci_text = _read_text(REPO_ROOT / ".github" / "workflows" / "ci.yml")
    jobs = _extract_aggregate_jobs(ci_text)
    outputs = [
        GENERATED_HEADER,
        "# Required Checks Reference",
        "",
        "Generated from `aggregate-gate` in `.github/workflows/ci.yml`.",
        "",
        "| Check | Classification |",
        "| --- | --- |",
    ]
    for job in jobs:
        classification = "required"
        if job in {"pr-llm-real-smoke", "external-playwright-smoke"}:
            classification = "conditional"
        outputs.append(f"| `{job}` | {classification} |")
    return "\n".join(outputs).rstrip() + "\n"


def _render_runner_baseline() -> str:
    baseline = _load_json(REPO_ROOT / "infra" / "config" / "self_hosted_runner_baseline.json")
    monthly_audit_text = _read_text(REPO_ROOT / ".github" / "workflows" / "monthly-governance-audit.yml")
    runtime_outputs = _load_json(REPO_ROOT / "config" / "governance" / "runtime-outputs.json")
    outputs = [
        GENERATED_HEADER,
        "# Runner Baseline Reference",
        "",
        "Generated from `infra/config/self_hosted_runner_baseline.json`.",
        "",
    ]
    for profile_name, profile in baseline.get("profiles", {}).items():
        outputs.extend(
            [
                f"## `{profile_name}`",
                "",
                f"- docker compose required: `{profile.get('docker_compose_required', False)}`",
            ]
        )
        disk_budget = profile.get("disk_budget_gb", {})
        if disk_budget:
            outputs.append(
                f"- disk budget: tmp>={disk_budget.get('min_free_gb_tmp', 0)}GiB, workspace>={disk_budget.get('min_free_gb_workspace', 0)}GiB"
            )
        commands = ", ".join(f"`{item}`" for item in profile.get("commands", []))
        outputs.append(f"- commands: {commands}")
        purge_paths = profile.get("purge_paths", [])
        if purge_paths:
            outputs.append("- purge paths:")
            for item in purge_paths:
                outputs.append(f"  - `{item}`")
        outputs.append("")
    outputs.extend(
        [
            "## Governance Hygiene Hooks",
            "",
            f"- runtime output root enforced by governance: `{runtime_outputs.get('runtime_root', '.runtime-cache')}`",
            "- current-run release/readiness reports are emitted under `.runtime-cache/reports/release-readiness/`",
            "- long-lived tracked artifacts now live under `artifacts/`, not the repository root hallway",
            "- root cleanliness is re-checked by `check_root_dirtiness_after_tasks.py` during monthly governance audit",
        ]
    )
    if "Normalize self-hosted workspace (pre-checkout)" in monthly_audit_text:
        outputs.append("- monthly governance audit reuses self-hosted pre-checkout normalization before checkout")
    return "\n".join(outputs).rstrip() + "\n"


def _render_governance_dashboard(nav: dict, manifest: dict, boundary: dict) -> str:
    upstreams = _load_json(REPO_ROOT / "config" / "governance" / "active-upstreams.json")
    templates = _load_json(REPO_ROOT / "config" / "governance" / "upstream-templates.json")
    compat = _load_json(REPO_ROOT / "config" / "governance" / "upstream-compat-matrix.json")
    kpi_path = REPO_ROOT / ".runtime-cache" / "reports" / "release-readiness" / "ci-kpi-summary.json"
    kpi_status = "missing"
    kpi_summary = "ci-kpi summary not generated yet"
    if kpi_path.exists():
        payload = json.loads(kpi_path.read_text(encoding="utf-8"))
        run = payload.get("kpi", {}).get("run", {})
        kpi_status = str(run.get("status", "unknown"))
        kpi_summary = str(run.get("warning", "current summary available")).strip() or "current summary available"

    outputs = [
        GENERATED_HEADER,
        "# Governance Dashboard",
        "",
        "This page is generated from the docs control plane and CI contracts.",
        "",
        "## Control Plane Summary",
        "",
        f"- nav sections: `{len(nav.get('sections', []))}`",
        f"- render-only docs: `{len(manifest.get('generated_docs', []))}`",
        f"- fragment injections: `{len(manifest.get('fragments', []))}`",
        f"- trust boundary: `{boundary['trust_boundary']['mode']}`",
        "",
        "## Generated Surfaces",
        "",
    ]
    outputs.extend(f"- `{entry['path']}`" for entry in manifest.get("generated_docs", []))
    outputs.extend(
        [
            "",
            "## KPI Snapshot",
            "",
            f"- ci-kpi status: `{kpi_status}`",
            f"- ci-kpi note: {kpi_summary}",
            f"- active upstreams: `{len(upstreams.get('entries', []))}`",
            f"- upstream templates: `{len(templates.get('entries', []))}`",
            f"- compat rows: `{len(compat.get('matrix', []))}`",
            "",
            "## Entry Links",
            "",
            "- `docs/generated/ci-topology.md`",
            "- `docs/generated/required-checks.md`",
            "- `docs/generated/runner-baseline.md`",
            "- `docs/generated/release-evidence.md`",
        ]
    )
    return "\n".join(outputs).rstrip() + "\n"


def _render_release_evidence() -> str:
    workflow_text = _read_text(REPO_ROOT / ".github" / "workflows" / "release-evidence-attest.yml")
    monthly_audit_text = _read_text(REPO_ROOT / ".github" / "workflows" / "monthly-governance-audit.yml")
    upstreams = _load_json(REPO_ROOT / "config" / "governance" / "active-upstreams.json")
    compat = _load_json(REPO_ROOT / "config" / "governance" / "upstream-compat-matrix.json")
    readme_text = _read_text(REPO_ROOT / "artifacts" / "releases" / "README.md")
    inputs = sorted(set(re.findall(r"artifacts/releases/<tag>/[^\n`]+", readme_text)))
    outputs = [
        GENERATED_HEADER,
        "# Release Evidence Reference",
        "",
        "Generated from the release evidence workflow and manifest capture script.",
        "",
        "## Canonical Rules",
        "",
        "- current run evidence is the only canonical source for release verdicts",
        "- current-run KPI and readiness summaries live under `.runtime-cache/reports/release-readiness/`",
        "- historical examples under `artifacts/releases/*` are documentation examples, not release verdict proof",
        "- manifest paths must be repo-relative, not host-absolute",
        "",
        "## Required Evidence Files",
        "",
    ]
    outputs.extend(f"- `{item}`" for item in inputs)
    outputs.extend(
        [
            "",
            "## Workflow Triggers",
            "",
        ]
    )
    if "workflow_dispatch" in workflow_text:
        outputs.append("- `workflow_dispatch` supported")
    if re.search(r"push:\n\s+tags:", workflow_text):
        outputs.append("- `push tags` supported")
    outputs.extend(
        [
            "",
            "## Attestation",
            "",
            "- provenance action: `actions/attest-build-provenance`",
            "- bundle source: `scripts/release/capture_release_manifest.sh`",
            "",
            "## Adjacent Governance Evidence",
            "",
            f"- upstream inventory entries tracked: `{len(upstreams.get('entries', []))}`",
            f"- compatibility matrix rows tracked: `{len(compat.get('matrix', []))}`",
        ]
    )
    if "monthly-governance-audit" in monthly_audit_text:
        outputs.append("- monthly governance audit snapshots are complementary hygiene evidence, not release verdict proof")
    return "\n".join(outputs).rstrip() + "\n"


def _fragment_lines(boundary: dict) -> dict[str, str]:
    trust = boundary["trust_boundary"]
    return {
        "readme_governance_snapshot": "\n".join(
            [
                "## Governance Snapshot",
                "",
                f"- **Docs control plane**：`config/docs/*.json` 现在是文档治理真相源；reference 由 `docs/generated/*.md` 承担。",
                f"- **CI 信任边界**：`{trust['mode']}`。fork / untrusted PR 不进入 privileged self-hosted 主链。",
                "- **Strict CI 真相源**：`infra/config/strict_ci_contract.json`。",
                "- **Generated references**：`docs/generated/ci-topology.md`、`docs/generated/runner-baseline.md`、`docs/generated/release-evidence.md`。",
            ]
        )
        + "\n",
        "start_here_governance_snapshot": "\n".join(
            [
                "## Generated Governance Snapshot",
                "",
                "- 文档高漂移事实已开始收口到 `docs/generated/*.md`；入口文档只保留 onboarding 必需信息。",
                f"- self-hosted CI 只接受 **trusted internal PR**；若 PR 来自 fork，GitHub Actions 会在边界门禁直接阻断。",
                "- 严格验收仍以 `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 为唯一权威入口。",
                "- 契约主层已迁到 `contracts/`，长期跟踪 artifact 已迁到 `artifacts/`。",
            ]
        )
        + "\n",
        "runbook_governance_snapshot": "\n".join(
            [
                "## Generated Governance Snapshot",
                "",
                "- 运行说明文档只解释执行与排障语义；高漂移 CI/runner/release 清单见 `docs/generated/*.md`。",
                "- runner baseline 参考页：`docs/generated/runner-baseline.md`。",
                "- CI 主链与 aggregate gate 清单：`docs/generated/ci-topology.md`。",
                "- release evidence 结构与 canonical 规则：`docs/generated/release-evidence.md`。",
            ]
        )
        + "\n",
        "testing_governance_snapshot": "\n".join(
            [
                "## Generated Governance Snapshot",
                "",
                "- `docs/testing.md` 现在以**策略解释**为主；高漂移 job inventory 已移到 `docs/generated/ci-topology.md`。",
                "- PR 信任模型：仅同仓 trusted internal PR 允许进入 self-hosted 主链。",
                "- docs gate 现在同时要求：`config/docs/*.json` control plane 一致、render output 新鲜、manual boundary 不越界。",
            ]
        )
        + "\n",
    }


def _replace_fragment(text: str, marker: str, body: str) -> str:
    start = FRAGMENT_START.format(marker=marker)
    end = FRAGMENT_END.format(marker=marker)
    replacement = f"{start}\n{body.rstrip()}\n{end}"
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end),
        flags=re.DOTALL,
    )
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    insertion = f"\n{replacement}\n"
    return text.rstrip() + insertion


def _write_or_check(path: Path, content: str, check: bool) -> list[str]:
    problems: list[str] = []
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current != content:
        if check:
            problems.append(str(path.relative_to(REPO_ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    nav, manifest, boundary, _ = _load_configs()

    expected: dict[Path, str] = {
        REPO_ROOT / "docs" / "generated" / "governance-dashboard.md": _render_governance_dashboard(nav, manifest, boundary),
        REPO_ROOT / "docs" / "generated" / "ci-topology.md": _render_ci_topology(manifest, boundary),
        REPO_ROOT / "docs" / "generated" / "required-checks.md": _render_required_checks(),
        REPO_ROOT / "docs" / "generated" / "runner-baseline.md": _render_runner_baseline(),
        REPO_ROOT / "docs" / "generated" / "release-evidence.md": _render_release_evidence(),
    }

    fragments = _fragment_lines(boundary)
    for entry in manifest["fragments"]:
        target = REPO_ROOT / entry["path"]
        original = _read_text(target)
        expected[target] = _replace_fragment(original, entry["marker"], fragments[entry["id"]])

    stale: list[str] = []
    for path, content in expected.items():
        stale.extend(_write_or_check(path, content, args.check))

    if args.check and stale:
        print("docs governance render freshness failed:")
        for item in stale:
            print(f"- {item}")
        print("run: python3 scripts/governance/render_docs_governance.py")
        return 1

    if not args.check:
        print("docs governance render completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
