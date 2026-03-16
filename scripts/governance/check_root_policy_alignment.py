#!/usr/bin/env python3
from __future__ import annotations

import re
import sys

sys.dont_write_bytecode = True

from common import load_governance_json, repo_root


DOCS_REQUIRING_MANAGED_UV = [
    "README.md",
    "docs/start-here.md",
    "docs/runbook-local.md",
]


def main() -> int:
    root = repo_root()
    runtime_outputs = load_governance_json("runtime-outputs.json")
    root_policy = load_governance_json("root-runtime-policy.json")
    forbidden = {str(item) for item in runtime_outputs.get("root_forbidden", [])}
    errors: list[str] = []
    if str(root_policy.get("runtime_root") or "") != str(runtime_outputs.get("runtime_root") or ""):
        errors.append("root-runtime-policy.json runtime_root drifted from runtime-outputs.json")
    if {str(item) for item in root_policy.get("forbidden_root_virtualenvs", [])} != {".venv", "venv"}:
        errors.append("root-runtime-policy.json must declare `.venv` and `venv` as forbidden root virtualenvs")

    residue_text = (root / "scripts/runtime/clean_source_runtime_residue.py").read_text(encoding="utf-8")
    for entry in sorted({".venv", "venv"} & forbidden):
        if f'ROOT / "{entry}"' in residue_text:
            errors.append(f"residue cleaner still whitelists forbidden root path `{entry}`")

    gitignore_lines = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    if ".agents/" in {line.strip() for line in gitignore_lines}:
        errors.append("`.agents/` must not be ignored wholesale; keep Plans tracked and scope ignores to subpaths")
    if "!.agents/Plans/" not in {line.strip() for line in gitignore_lines}:
        errors.append("`.agents/Plans/` must be explicitly unignored")

    raw_uv_sync = re.compile(r"(?m)^uv sync --frozen --extra dev --extra e2e$")
    for rel in DOCS_REQUIRING_MANAGED_UV:
        text = (root / rel).read_text(encoding="utf-8")
        if raw_uv_sync.search(text):
            errors.append(f"{rel}: raw `uv sync --frozen --extra dev --extra e2e` still appears without managed UV_PROJECT_ENVIRONMENT")

    if errors:
        print("[root-policy-alignment] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[root-policy-alignment] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
