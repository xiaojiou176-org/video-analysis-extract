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
sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import current_git_commit, write_json_artifact


def _run(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def _repo_slug() -> str:
    remote = _run("git", "config", "--get", "remote.origin.url", check=True).stdout.strip()
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$", remote)
    if not match:
        raise SystemExit(f"unable to derive GitHub repository slug from remote.origin.url: {remote}")
    return f"{match.group('owner')}/{match.group('repo')}"


def _json_or_error(command: list[str]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    result = _run(*command)
    if result.returncode == 0:
        return json.loads(result.stdout), None
    return None, {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check release evidence attestation readiness.")
    parser.add_argument("--release-tag", required=True)
    parser.add_argument(
        "--output",
        default=".runtime-cache/reports/release/release-evidence-attest-readiness.json",
    )
    parser.add_argument("--repo", default="")
    args = parser.parse_args()

    repo = args.repo.strip() or _repo_slug()
    release_dir = ROOT / "artifacts" / "releases" / args.release_tag
    required_files = [
        release_dir / "manifest.json",
        release_dir / "checksums.sha256",
        release_dir / "rollback" / "db-rollback-readiness.json",
        release_dir / "rollback" / "drill.json",
    ]
    missing = [str(path.relative_to(ROOT).as_posix()) for path in required_files if not path.is_file()]

    actor_payload, actor_error = _json_or_error(["gh", "api", "user"])
    artifacts_payload, artifacts_error = _json_or_error(["gh", "api", f"repos/{repo}/actions/artifacts?per_page=1"])

    quota_status = "unknown"
    if artifacts_payload is not None:
        quota_status = "artifact-api-readable"
    elif artifacts_error is not None:
        quota_status = "artifact-api-unreadable"

    status = "ready"
    blocker_type = ""
    errors: list[str] = []
    if missing:
        status = "blocked"
        blocker_type = "repo-evidence-missing"
        errors.append("missing release evidence files: " + ", ".join(missing))

    report = {
        "version": 1,
        "status": status,
        "blocker_type": blocker_type,
        "repo": repo,
        "release_tag": args.release_tag,
        "source_commit": current_git_commit(),
        "actor": (actor_payload or {}).get("login", ""),
        "actor_error": actor_error,
        "required_files": [str(path.relative_to(ROOT).as_posix()) for path in required_files],
        "missing_files": missing,
        "artifact_quota_status": quota_status,
        "artifacts_api_error": artifacts_error,
        "errors": errors,
    }
    write_json_artifact(
        ROOT / args.output,
        report,
        source_entrypoint="scripts/release/check_release_evidence_attest_readiness.py",
        verification_scope="release-evidence-attest-readiness",
        source_run_id="release-evidence-attest-readiness",
        freshness_window_hours=24,
        extra={"report_kind": "release-evidence-attest-readiness"},
    )

    if status != "ready":
        print("[release-evidence-attest-readiness] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[release-evidence-attest-readiness] READY")
    if quota_status != "artifact-api-readable":
        print("  - artifact quota status unavailable; recorded as unknown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
