#!/usr/bin/env python3
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from common import load_governance_json, repo_root


def main() -> int:
    payload = load_governance_json("public-surface-policy.json")
    policy = payload.get("contact_policy", {})
    root = repo_root()
    errors: list[str] = []

    for rel, rules in policy.items():
        path = root / str(rel)
        if not path.is_file():
            errors.append(f"missing required contact surface: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in rules.get("must_contain", []):
            if needle not in text:
                errors.append(f"{rel}: missing required text `{needle}`")
        for needle in rules.get("must_not_contain", []):
            if needle in text:
                errors.append(f"{rel}: forbidden placeholder text `{needle}` still present")

    if errors:
        print("[public-contact-points] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[public-contact-points] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
