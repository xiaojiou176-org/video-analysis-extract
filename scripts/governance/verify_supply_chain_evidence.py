#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from scripts.ci.contract import DEFAULT_CONTRACT_PATH, load_contract


def _github_json(url: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def verify_supply_chain(
    *,
    contract_path: Path,
    repo: str,
    workflow_file: str,
    token: str,
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    image = contract["standard_image"]
    contract_tag = str(image["tag"])
    contract_digest = str(image["digest"])
    payload: dict[str, Any] = {
        "status": "supply_chain_unverified",
        "reason": "successful supply-chain workflow run not found for current contract tag",
        "contract_tag": contract_tag,
        "contract_digest": contract_digest,
        "workflow_file": workflow_file,
        "repo": repo,
    }

    if not repo.strip():
        payload["reason"] = "missing repo"
        return payload
    if not workflow_file.strip():
        payload["reason"] = "missing workflow file"
        return payload
    if not token.strip():
        payload["reason"] = "missing token"
        return payload

    encoded_workflow = urllib.parse.quote(workflow_file, safe="")
    url = (
        f"https://api.github.com/repos/{repo}/actions/workflows/{encoded_workflow}/runs"
        "?status=completed&per_page=50"
    )
    runs_payload = _github_json(url, token)
    runs = runs_payload.get("workflow_runs", [])
    for run in runs:
        if str(run.get("conclusion")) != "success":
            continue
        if str(run.get("head_sha")) != contract_tag:
            continue
        payload.update(
            {
                "status": "verified",
                "reason": "matching successful workflow run found for current contract tag",
                "workflow_run_id": run.get("id"),
                "workflow_run_url": run.get("html_url"),
            }
        )
        return payload

    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--repo", default="")
    parser.add_argument("--workflow-file", default="build-ci-standard-image.yml")
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    result = verify_supply_chain(
        contract_path=args.contract,
        repo=args.repo,
        workflow_file=args.workflow_file,
        token=os.getenv(args.token_env, "").strip(),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and result["status"] != "verified":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
