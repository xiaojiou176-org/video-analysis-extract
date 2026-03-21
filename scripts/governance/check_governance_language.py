#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from common import repo_root


CHECK_PATHS = [
    "README.md",
    "docs/start-here.md",
    "docs/runbook-local.md",
    "docs/testing.md",
    "docs/state-machine.md",
    "docs/reference/cache.md",
    "docs/reference/logging.md",
    "docs/reference/dependency-governance.md",
    "docs/reference/env-script-overrides.md",
    "docs/deploy/full-stack-gce.md",
]

FORBIDDEN_SNIPPETS = [
    "兼容旧行为",
    "兼容历史",
    "迁移期保留",
    "过渡期",
    "legacy env 仅兼容",
]

STRICT_ENGLISH_PATHS = [
    "AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "apps/api/AGENTS.md",
    "apps/api/CLAUDE.md",
    "apps/worker/AGENTS.md",
    "apps/worker/CLAUDE.md",
    "apps/mcp/AGENTS.md",
    "apps/mcp/CLAUDE.md",
    "apps/web/AGENTS.md",
    "apps/web/CLAUDE.md",
    "apps/worker/worker/pipeline/steps/llm_prompts.py",
    "scripts/governance/render_current_state_summary.py",
    "scripts/governance/render_docs_governance.py",
    "scripts/ci/e2e_live_smoke.sh",
    "scripts/ci/autofix.py",
    "scripts/deploy/recreate_gce_instance.sh",
    "docs/reference/done-model.md",
    "docs/reference/external-lane-status.md",
    "docs/reference/public-repo-readiness.md",
    "docs/reference/public-rights-and-provenance.md",
    "docs/reference/contributor-rights-model.md",
    "docs/reference/runner-baseline.md",
    "docs/reference/root-governance.md",
    "docs/reference/upstream-compatibility-policy.md",
    "docs/reference/mcp-tool-routing.md",
]

PRODUCT_OUTPUT_LOCALE_ALLOWLIST_PATHS = [
    "apps/worker/worker/pipeline/steps/artifacts.py",
    "apps/worker/worker/pipeline/runner_rendering.py",
    "apps/worker/templates/digest.md.mustache",
]

HAN_RE = re.compile(r"[\u4e00-\u9fff]")


def main() -> int:
    root = repo_root()
    errors: list[str] = []
    advisories: list[str] = []
    for rel in CHECK_PATHS:
        path = root / rel
        if not path.is_file():
            errors.append(f"{rel}: missing governance language check target")
            continue
        content = path.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in content:
                errors.append(f"{rel}: contains forbidden governance legacy phrase `{snippet}`")

    for rel in STRICT_ENGLISH_PATHS:
        path = root / rel
        if not path.is_file():
            errors.append(f"{rel}: missing strict English governance target")
            continue
        content = path.read_text(encoding="utf-8")
        if HAN_RE.search(content):
            errors.append(f"{rel}: contains non-English governance/runtime text on a strict-English surface")

    for rel in PRODUCT_OUTPUT_LOCALE_ALLOWLIST_PATHS:
        path = root / rel
        if not path.is_file():
            advisories.append(f"{rel}: missing product-output locale allowlist target")
            continue
        content = path.read_text(encoding="utf-8")
        if HAN_RE.search(content):
            advisories.append(
                f"{rel}: contains Chinese content inside the explicit product-output locale allowlist; do not let this exception leak back into contributor/runtime/governance surfaces"
            )

    if errors:
        print("[governance-language] FAIL")
        for item in errors:
            print(f"  - {item}")
        if advisories:
            print("[governance-language] ADVISORY")
            for item in advisories:
                print(f"  - {item}")
        return 1

    print("[governance-language] PASS")
    if advisories:
        print("[governance-language] ADVISORY")
        for item in advisories:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
