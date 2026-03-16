#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import current_git_commit, read_runtime_metadata, repo_root


def main() -> int:
    root = repo_root()
    path = root / ".runtime-cache" / "reports" / "governance" / "newcomer-result-proof.json"
    errors: list[str] = []
    if not path.is_file():
        print("[newcomer-result-proof-check] FAIL")
        print("  - newcomer result proof report missing")
        return 1

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print("[newcomer-result-proof-check] FAIL")
        print(f"  - invalid JSON: {exc}")
        return 1

    metadata = read_runtime_metadata(path)
    if metadata is None:
        errors.append("report missing runtime metadata")
    else:
        if str(metadata.get("source_commit") or "") != current_git_commit():
            errors.append("report runtime metadata source_commit does not match current HEAD")

    if str(payload.get("source_commit") or "") != current_git_commit():
        errors.append("report source_commit does not match current HEAD")

    newcomer = payload.get("newcomer_preflight") or {}
    if newcomer.get("status") != "pass":
        errors.append("newcomer preflight must be pass for the current report")
    if newcomer.get("resolved_env_exists") is not True:
        errors.append("newcomer preflight must point to an existing resolved env receipt")

    governance = payload.get("governance_audit_receipt") or {}
    if governance.get("status") not in {"pass", "in_progress"}:
        errors.append("governance audit receipt must be `pass` or `in_progress` in newcomer result proof")

    strict_receipt = payload.get("repo_side_strict_receipt") or {}
    allowed = {"pass", "missing_current_receipt"}
    if strict_receipt.get("status") not in allowed:
        errors.append("repo_side_strict_receipt must be `pass` or `missing_current_receipt`")

    eval_regression = payload.get("eval_regression") or {}
    if not eval_regression:
        errors.append("eval regression summary missing")

    if errors:
        print("[newcomer-result-proof-check] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[newcomer-result-proof-check] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
