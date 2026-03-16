#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config" / "docs"


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _check_paths_exist(paths: list[str], *, allow_missing: bool = False) -> list[str]:
    failures: list[str] = []
    for raw in paths:
        target = REPO_ROOT / raw
        if allow_missing:
            continue
        if not target.exists():
            failures.append(f"missing path: {raw}")
    return failures


def _check_control_plane() -> list[str]:
    failures: list[str] = []
    nav = _load_json(CONFIG_DIR / "nav-registry.json")
    manifest = _load_json(CONFIG_DIR / "render-manifest.json")
    boundary = _load_json(CONFIG_DIR / "boundary-policy.json")
    change_contract = _load_json(CONFIG_DIR / "change-contract.json")

    nav_docs = []
    for section in nav.get("sections", []):
        nav_docs.extend(section.get("docs", []))
    failures.extend(_check_paths_exist(nav_docs))

    render_paths = [entry["path"] for entry in manifest.get("generated_docs", [])]
    failures.extend(_check_paths_exist(render_paths))

    fragment_paths = [entry["path"] for entry in manifest.get("fragments", [])]
    failures.extend(_check_paths_exist(fragment_paths))

    manual_docs = boundary.get("manual_docs", {})
    for path, payload in manual_docs.items():
        target = REPO_ROOT / path
        if not target.exists():
            failures.append(f"manual boundary doc missing: {path}")
            continue
        text = target.read_text(encoding="utf-8")
        for marker in payload.get("generated_markers", []):
            start = f"<!-- docs:generated {marker} start -->"
            end = f"<!-- docs:generated {marker} end -->"
            if start not in text or end not in text:
                failures.append(f"manual doc missing generated marker `{marker}`: {path}")

    for rule in change_contract.get("rules", []):
        failures.extend(_check_paths_exist(rule.get("required_paths", [])))

    if not boundary.get("trust_boundary", {}).get("mode"):
        failures.append("boundary policy missing trust_boundary.mode")

    return failures


def _check_render_freshness() -> list[str]:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "governance" / "render_docs_governance.py"), "--check"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    lines = [line for line in result.stdout.splitlines() + result.stderr.splitlines() if line.strip()]
    return lines or ["docs governance render freshness failed"]


def _check_generated_doc_semantics() -> list[str]:
    failures: list[str] = []
    runtime_outputs = _load_json(REPO_ROOT / "config" / "governance" / "runtime-outputs.json")
    root_allowlist = _load_json(REPO_ROOT / "config" / "governance" / "root-allowlist.json")
    compat = _load_json(REPO_ROOT / "config" / "governance" / "upstream-compat-matrix.json")

    ci_topology = (REPO_ROOT / "docs" / "generated" / "ci-topology.md").read_text(encoding="utf-8")
    expected_root_line = f"- root allowlist entries: `{len(root_allowlist.get('tracked_root_allowlist', []))}`"
    if expected_root_line not in ci_topology:
        failures.append("docs/generated/ci-topology.md: root allowlist count drifted from control plane")
    expected_runtime_root = f"- runtime root: `{runtime_outputs.get('runtime_root', '.runtime-cache')}`"
    if expected_runtime_root not in ci_topology:
        failures.append("docs/generated/ci-topology.md: runtime root drifted from control plane")

    release_reference = (REPO_ROOT / "docs" / "generated" / "release-evidence.md").read_text(
        encoding="utf-8"
    )
    expected_rows_line = f"- compatibility matrix rows tracked: `{len(compat.get('matrix', []))}`"
    if expected_rows_line not in release_reference:
        failures.append("docs/generated/release-evidence.md: compatibility row count drifted from control plane")
    if "docs/reference/done-model.md" not in release_reference:
        failures.append("docs/generated/release-evidence.md: missing done-model reference")

    governance_dashboard = (
        REPO_ROOT / "docs" / "generated" / "governance-dashboard.md"
    ).read_text(encoding="utf-8")
    if "docs/reference/done-model.md" not in governance_dashboard:
        failures.append("docs/generated/governance-dashboard.md: missing done-model reference")
    return failures


def main() -> int:
    failures = _check_control_plane()
    failures.extend(_check_render_freshness())
    failures.extend(_check_generated_doc_semantics())
    if failures:
        print("docs governance check failed:")
        for item in failures:
            print(f"- {item}")
        return 1
    print("docs governance check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
