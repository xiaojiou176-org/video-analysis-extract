#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import write_json_artifact


def main() -> int:
    parser = argparse.ArgumentParser(description="Write or refresh a run manifest for a stable public entrypoint.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--entrypoint", required=True)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--argv", nargs="*", default=[])
    args = parser.parse_args()

    payload = {
        "version": 1,
        "run_id": args.run_id,
        "entrypoint": args.entrypoint,
        "channel": args.channel,
        "argv": list(args.argv),
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "repo_commit": os.getenv("vd_log_repo_commit", "unknown"),
        "env_profile": os.getenv("vd_log_env_profile", os.getenv("ENV_PROFILE", "unknown")),
        "log_path": os.getenv("vd_log_path", ""),
        "test_run_id": os.getenv("vd_test_run_id", ""),
        "gate_run_id": os.getenv("vd_gate_run_id", ""),
    }
    manifest_path = ROOT / ".runtime-cache" / "run" / "manifests" / f"{args.run_id}.json"
    write_json_artifact(
        manifest_path,
        payload,
        source_entrypoint="scripts/runtime/write_run_manifest.py",
        verification_scope="run-manifest",
        source_run_id=args.run_id,
        freshness_window_hours=24,
        extra={"report_kind": "run-manifest"},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
