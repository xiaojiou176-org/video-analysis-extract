#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Append one governance observation record.")
    parser.add_argument("--kind", required=True)
    parser.add_argument("--status", required=True, choices=("pass", "fail"))
    parser.add_argument("--evidence-artifact", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--history-path", default=".runtime-cache/reports/governance/observation-history.jsonl")
    args = parser.parse_args()

    run_id = args.run_id.strip() or uuid.uuid4().hex
    payload = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "kind": args.kind,
        "status": args.status,
        "run_id": run_id,
        "evidence_artifact": args.evidence_artifact,
    }

    history_path = Path(args.history_path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    print(f"[governance-observation] recorded kind={args.kind} status={args.status} run_id={run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
