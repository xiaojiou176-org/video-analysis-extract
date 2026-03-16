#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import current_git_commit, write_json_artifact


WORKFLOW_MAP = {
    "ghcr-standard-image": "build-ci-standard-image.yml",
    "release-evidence-attestation": "release-evidence-attest.yml",
}


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), cwd=ROOT, check=check, capture_output=True, text=True)


def _repo_slug() -> str:
    remote = _run("git", "config", "--get", "remote.origin.url").stdout.strip()
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$", remote)
    if not match:
        raise SystemExit(f"unable to derive GitHub repository slug from remote.origin.url: {remote}")
    return f"{match.group('owner')}/{match.group('repo')}"


def _json_or_none(command: list[str]) -> tuple[Any | None, dict[str, Any] | None]:
    result = _run(*command, check=False)
    if result.returncode == 0:
        return json.loads(result.stdout), None
    return None, {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _lane_state(run: dict[str, Any] | None) -> tuple[str, str]:
    if not run:
        return "missing", "no remote workflow run found"
    status = str(run.get("status") or "")
    conclusion = str(run.get("conclusion") or "")
    if status in {"queued", "pending"}:
        return "queued", "remote workflow queued"
    if status == "in_progress":
        return "in_progress", "remote workflow in progress"
    if conclusion == "success":
        return "verified", "remote workflow completed successfully"
    if conclusion:
        return "blocked", f"remote workflow concluded `{conclusion}`"
    return "blocked", f"unexpected workflow state status={status} conclusion={conclusion}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture latest remote workflow states for external lanes.")
    parser.add_argument("--repo", default="", help="Explicit owner/repo slug. Defaults to origin remote.")
    parser.add_argument(
        "--output",
        default=".runtime-cache/reports/governance/external-lane-workflows.json",
        help="Output report path.",
    )
    args = parser.parse_args()

    repo = args.repo.strip() or _repo_slug()
    actor_payload, actor_error = _json_or_none(["gh", "api", "user"])
    actor = str((actor_payload or {}).get("login") or "")

    lanes: list[dict[str, Any]] = []
    overall_status = "pass"
    for lane_name, workflow_file in WORKFLOW_MAP.items():
        payload, error = _json_or_none(
            [
                "gh",
                "run",
                "list",
                "--repo",
                repo,
                "--workflow",
                workflow_file,
                "--limit",
                "1",
                "--json",
                "databaseId,workflowName,status,conclusion,displayTitle,headSha,updatedAt,url",
            ]
        )
        latest_run = payload[0] if isinstance(payload, list) and payload else None
        lane_state, note = _lane_state(latest_run)
        if lane_state == "blocked":
            overall_status = "blocked"
        lanes.append(
            {
                "name": lane_name,
                "workflow_file": workflow_file,
                "state": lane_state,
                "note": note,
                "latest_run": latest_run,
                "error": error,
            }
        )

    report = {
        "version": 1,
        "status": overall_status,
        "repo": repo,
        "actor": actor,
        "actor_error": actor_error,
        "source_commit": current_git_commit(),
        "lanes": lanes,
    }
    write_json_artifact(
        ROOT / args.output,
        report,
        source_entrypoint="scripts/governance/probe_external_lane_workflows.py",
        verification_scope="external-lane-workflows",
        source_run_id="external-lane-workflows",
        freshness_window_hours=24,
        extra={"report_kind": "external-lane-workflows"},
    )

    print("[external-lane-workflows] PASS")
    for lane in lanes:
        latest_run = lane.get("latest_run") or {}
        run_id = latest_run.get("databaseId", "")
        print(f"  - {lane['name']}: {lane['state']} run_id={run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
