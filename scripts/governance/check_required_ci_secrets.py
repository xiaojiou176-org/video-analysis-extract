#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys


def _parse_required(raw: list[str]) -> list[str]:
    names: list[str] = []
    for item in raw:
        for token in item.split(","):
            name = token.strip()
            if not name:
                continue
            names.append(name)
    return sorted(set(names))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-fast gate: required CI secrets/env vars must be non-empty."
    )
    parser.add_argument(
        "--required",
        action="append",
        required=True,
        help="Required env var names. Repeatable or comma-separated.",
    )
    args = parser.parse_args()

    required = _parse_required(args.required)
    if not required:
        print("required-ci-secrets gate failed: empty required list", file=sys.stderr)
        return 2

    missing: list[str] = []
    present: list[str] = []
    for name in required:
        value = os.getenv(name, "").strip()
        if value:
            present.append(name)
        else:
            missing.append(name)

    if missing:
        print(
            "required-ci-secrets gate failed: missing required secrets/env vars: "
            + ", ".join(missing),
            file=sys.stderr,
        )
        if present:
            print("present vars: " + ", ".join(present), file=sys.stderr)
        return 1

    print("required-ci-secrets gate passed: " + ", ".join(required))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
