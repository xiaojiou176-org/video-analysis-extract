#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINTS = {
    "bin/bootstrap-full-stack",
    "bin/dev-api",
    "bin/dev-mcp",
    "bin/dev-worker",
    "bin/full-stack",
    "bin/governance-audit",
    "bin/quality-gate",
    "bin/strict-ci",
    "bin/upstream-verify",
    "bin/doctor",
    "bin/prune-runtime",
    "bin/clean-runtime",
    "bin/run-ai-feed-sync",
}
REQUIRED_SNIPPETS = (
    'source "$ROOT_DIR/scripts/runtime/entrypoint.sh"',
    "vd_entrypoint_bootstrap",
)


def main() -> int:
    errors: list[str] = []
    for rel in sorted(ENTRYPOINTS):
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"missing public entrypoint: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for snippet in REQUIRED_SNIPPETS:
            if snippet not in text:
                errors.append(f"{rel}: missing public-entrypoint manifest snippet `{snippet}`")

    if errors:
        print("[public-entrypoint-manifests] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"[public-entrypoint-manifests] PASS ({len(ENTRYPOINTS)} entrypoints checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
