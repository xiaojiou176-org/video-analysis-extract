#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify recent governance observation history.")
    parser.add_argument("--kind", required=True)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--history-path", default=".runtime-cache/reports/governance/observation-history.jsonl")
    args = parser.parse_args()

    history_path = Path(args.history_path)
    if not history_path.is_file():
        raise SystemExit(f"observation history missing: {history_path}")

    rows = [
        json.loads(line)
        for line in history_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    matching = [row for row in rows if row.get("kind") == args.kind]
    if len(matching) < args.count:
        raise SystemExit(
            f"expected at least {args.count} observations for kind={args.kind}, found {len(matching)}"
        )
    recent = matching[-args.count :]
    failing = [row for row in recent if row.get("status") != "pass"]
    if failing:
        raise SystemExit(
            f"recent observation window contains failures for kind={args.kind}: "
            + ", ".join(str(row.get("run_id")) for row in failing)
        )

    print(
        f"[governance-observation-window] PASS kind={args.kind} count={args.count} "
        f"run_ids={','.join(str(row.get('run_id')) for row in recent)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
