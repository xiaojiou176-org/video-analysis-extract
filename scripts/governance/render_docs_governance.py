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


def _maybe_load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return _load_json(path)


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


def _extract_workflow_job_runs_on(workflow_text: str, job_name: str) -> str | None:
    match = re.search(
        rf"^\s{{2}}{re.escape(job_name)}:\n(?P<body>(?:^\s{{4}}.*\n?)*)",
        workflow_text,
        flags=re.MULTILINE,
    )
    if not match:
        return None
    body = match.group("body")
    runner_match = re.search(r"^\s{4}runs-on:\s*(.+)$", body, flags=re.MULTILINE)
    if not runner_match:
        return None
    return runner_match.group(1).strip()


def _render_standard_image_publish_line() -> str:
    workflow_text = _read_text(REPO_ROOT / ".github" / "workflows" / "build-ci-standard-image.yml")
    runner = _extract_workflow_job_runs_on(workflow_text, "publish") or "unknown"
    buildx_index = workflow_text.find("Set up Docker Buildx")
    build_script_index = workflow_text.find("./scripts/ci/build_standard_image.sh")
    if buildx_index >= 0 and build_script_index >= 0 and buildx_index < build_script_index:
        return (
            "- GHCR image publish workflow runs on "
            f"`{runner}` and sets up Docker Buildx before calling `scripts/ci/build_standard_image.sh`"
        )
    if build_script_index >= 0:
        return (
            "- GHCR image publish workflow runs on "
            f"`{runner}` and calls `scripts/ci/build_standard_image.sh` in the `publish` job"
        )
    return f"- GHCR image publish workflow runs on `{runner}`"


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
        f"- root allowlist entries: `{len(root_allowlist.get('tracked_root_allowlist', []))}`",
        f"- local-private root tolerations: `{len(root_allowlist.get('local_private_root_tolerations', []))}`",
        f"- runtime root: `{runtime_outputs.get('runtime_root', '.runtime-cache')}`",
        "- current-run CI KPI summary: `.runtime-cache/reports/release-readiness/ci-kpi-summary.json`",
        "- current-run rollback/readiness reports: `.runtime-cache/reports/release-readiness/`",
        "- current-run release-evidence attestation readiness: `.runtime-cache/reports/release/release-evidence-attest-readiness.json`",
        f"- active upstream inventory entries: `{len(upstreams.get('entries', []))}`",
        f"- upstream templates: `{len(templates.get('entries', []))}`",
        "- governance gate entrypoint: `./bin/governance-audit --mode pre-commit|pre-push|ci|audit`",
        _render_standard_image_publish_line(),
        "",
        "## Aggregate Gate Inventory",
        "",
        "## Completion Lanes",
        "",
        "- repo-side canonical path: `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`",
        "- external lane path: `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`",
        "- source of truth: `docs/reference/done-model.md`",
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
        "This page answers one narrow question in plain English: has the required-check list that controls PR/merge drifted or not?",
        "In other words, it lists the merge-relevant required checks shared by branch protection and `aggregate-gate`; that list now **includes** `remote-integrity`.",
        "`remote-required-checks=status=pass` only proves merge-relevant required-check integrity, which means branch protection and aggregate-required-check integrity stay aligned. It does **not** prove `ci-final-gate`, `live-smoke`, or nightly terminal closure.",
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
            "- current-run rollback/readiness reports are emitted under `.runtime-cache/reports/release-readiness/`",
        "- current-run release-evidence attestation readiness is emitted under `.runtime-cache/reports/release/`",
        "- long-lived tracked artifacts now live under `artifacts/`, not the repository root hallway",
        "- root cleanliness is re-checked by `check_root_dirtiness_after_tasks.py` during monthly governance audit",
        "- repo-side / external completion split is documented in `docs/reference/done-model.md`",
        "- repo-side strict canonical path is `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`",
        "- image-publish workflows now prime Docker Buildx explicitly before multi-arch standard-image builds",
        "- remote integrity now serves both as a reusable merge-relevant CI lane and a manual audit workflow: `remote-integrity-audit.yml`",
        "- standard image publish lane now runs a repo-owned readiness preflight before build/push",
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
            "- `docs/reference/done-model.md`",
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
        "- repo-side closure and external closure must be reported separately; see `docs/reference/done-model.md`",
        "- external lane live status is tracked in `docs/reference/external-lane-status.md`",
        "- current run evidence is the only canonical source for release verdicts, and its runtime metadata `source_commit` must match the current HEAD",
        "- current-run CI KPI summaries live under `.runtime-cache/reports/release-readiness/`",
        "- current-run release-evidence attestation readiness lives under `.runtime-cache/reports/release/release-evidence-attest-readiness.json`",
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
            "- readiness preflight: `scripts/release/check_release_evidence_attest_readiness.py`",
            "- GHCR standard-image publish lane primes Docker Buildx before invoking the multi-arch image build script",
            "",
            "## Adjacent Governance Evidence",
            "",
            f"- upstream inventory entries tracked: `{len(upstreams.get('entries', []))}`",
            f"- compatibility matrix rows tracked: `{len(compat.get('matrix', []))}`",
            "- external lane truth entry: `docs/generated/external-lane-snapshot.md` (tracked pointer) + `.runtime-cache/reports/governance/*.json` / `.runtime-cache/reports/release/*.json` (current verdict)",
        ]
    )
    if "monthly-governance-audit" in monthly_audit_text:
        outputs.append("- monthly governance audit snapshots are complementary hygiene evidence, not release verdict proof")
    return "\n".join(outputs).rstrip() + "\n"


def _render_external_lane_snapshot() -> str:
    contract = _load_json(REPO_ROOT / "config" / "governance" / "external-lane-contract.json")
    outputs = [
        GENERATED_HEADER,
        "# External Lane Truth Entry",
        "",
        "This tracked page is a machine-rendered pointer only.",
        "",
        "It does not carry commit-sensitive current verdicts.",
        "Current external state must be read from runtime-owned reports under `.runtime-cache/reports/**`.",
        "",
        "## Canonical Runtime Reports",
        "",
        "| Lane | Canonical Artifact | Reading Rule |",
        "| --- | --- | --- |",
    ]
    for lane in contract.get("lanes", []):
        if not isinstance(lane, dict):
            continue
        name = str(lane.get("name") or "").strip()
        artifact = str(lane.get("canonical_artifact") or "").strip()
        reading_rule = "read runtime artifact directly; tracked docs only explain semantics"
        outputs.append(f"| `{name}` | `{artifact}` | {reading_rule} |")

    outputs.extend(
        [
            "",
            "## Reading Rule",
            "",
            "- explanation lives in `docs/reference/external-lane-status.md`",
            "- current state must come from runtime-owned reports under `.runtime-cache/reports/**`",
            "- tracked docs may explain state semantics, but must not carry current verdict payload",
            "- runtime metadata `source_commit` must match the current HEAD before any report can be treated as current truth",
            "- `.runtime-cache/reports/governance/current-state-summary.md` is also commit-sensitive; if its own `.meta.json` source_commit is stale, treat the whole page as historical until rerendered",
            "- old remote workflow runs may explain `historical` state, but they must not be upgraded into current `verified` wording by any summary or pointer page",
            "- `ready` means preflight inputs exist; it does not mean the external lane has closed successfully",
            "",
            "## Canonical Commands",
            "",
            "- `python3 scripts/governance/probe_remote_platform_truth.py --repo xiaojiou176-org/video-analysis-extract`",
            "- `python3 scripts/governance/check_remote_required_checks.py`",
            "- `bash scripts/ci/check_standard_image_publish_readiness.sh`",
            "- `python3 scripts/release/check_release_evidence_attest_readiness.py --release-tag <tag>`",
        ]
    )
    return "\n".join(outputs).rstrip() + "\n"


def _fragment_lines(boundary: dict) -> dict[str, str]:
    trust = boundary["trust_boundary"]
    return {
        "readme_governance_snapshot": "\n".join(
            [
                "## Governance Snapshot",
                "",
                f"- **Docs control plane**: `config/docs/*.json` is the source of truth for docs governance, and `docs/generated/*.md` is the render layer.",
                f"- **CI trust boundary**: `{trust['mode']}`. Fork and untrusted PRs must not enter the privileged self-hosted path.",
                "- **Strict CI source of truth**: `infra/config/strict_ci_contract.json`.",
                "- **Repo-side done model**: `docs/reference/done-model.md`.",
                "- **Generated references**: `docs/generated/ci-topology.md`, `docs/generated/runner-baseline.md`, `docs/generated/release-evidence.md`, and `docs/generated/external-lane-snapshot.md`.",
            ]
        )
        + "\n",
        "start_here_governance_snapshot": "\n".join(
            [
                "## Generated Governance Snapshot",
                "",
                "- High-drift facts have been pulled into `docs/generated/*.md`; entry docs now keep only the onboarding-critical surface.",
                f"- Self-hosted CI only accepts **trusted internal PRs**; fork PRs are blocked at the trust-boundary gate.",
                "- Repo-side strict entrypoint: `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`.",
                "- External lane entrypoint: `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`.",
                "- External lane truth entry: `docs/generated/external-lane-snapshot.md` (tracked pointer) plus `.runtime-cache/reports/**` (current verdict).",
                "- Contract sources now live under `contracts/`, and long-lived tracked artifacts now live under `artifacts/`.",
            ]
        )
        + "\n",
        "runbook_governance_snapshot": "\n".join(
            [
                "## Generated Governance Snapshot",
                "",
                "- Runbook pages explain execution and troubleshooting semantics only; high-drift CI/runner/release inventories live in `docs/generated/*.md`.",
                "- Runner baseline reference: `docs/generated/runner-baseline.md`.",
                "- CI topology and aggregate-gate inventory: `docs/generated/ci-topology.md`.",
                "- Release evidence structure and canonical rules: `docs/generated/release-evidence.md`.",
                "- External lane truth entry: `docs/generated/external-lane-snapshot.md` (tracked pointer) plus `.runtime-cache/reports/**` (current verdict).",
                "- Repo-side versus external completion model: `docs/reference/done-model.md`.",
            ]
        )
        + "\n",
        "testing_governance_snapshot": "\n".join(
            [
                "## Generated Governance Snapshot",
                "",
                "- `docs/testing.md` is now primarily a policy explanation page; high-drift job inventory has moved to `docs/generated/ci-topology.md`.",
                "- PR trust model: only trusted internal PRs from the same repository may enter the self-hosted path.",
                "- The docs gate now requires `config/docs/*.json` control-plane alignment, fresh render outputs, and no manual-boundary violations.",
                "- Repo-side strict canonical path: `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`.",
                "- External current-state claims are only allowed through generated snapshots or runtime reports.",
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
        REPO_ROOT / "docs" / "generated" / "external-lane-snapshot.md": _render_external_lane_snapshot(),
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
