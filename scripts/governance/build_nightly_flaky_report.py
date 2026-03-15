#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path


def github_get(url: str, token: str) -> dict:
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


def collect_recent_schedule_runs(repo: str, token: str, workflow_file: str, limit: int) -> list[dict]:
    url = (
        f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/runs"
        f"?event=schedule&per_page={limit}"
    )
    payload = github_get(url, token)
    results: list[dict] = []
    for run in payload.get("workflow_runs", []):
        jobs_url = run.get("jobs_url")
        if not jobs_url:
            continue
        jobs_payload = github_get(jobs_url, token)
        jobs = {job["name"]: job.get("conclusion") or job.get("status") for job in jobs_payload.get("jobs", [])}
        results.append(
            {
                "run_id": run.get("id"),
                "created_at": run.get("created_at"),
                "conclusion": run.get("conclusion"),
                "nightly-flaky-python": jobs.get("nightly-flaky-python"),
                "nightly-flaky-web-e2e": {
                    key: value
                    for key, value in jobs.items()
                    if key.startswith("nightly-flaky-web-e2e")
                },
            }
        )
    return results


def write_report(results: list[dict], json_path: Path, md_path: Path) -> None:
    json_path.write_text(json.dumps({"runs": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Nightly Flaky Trend",
        "",
        "| Run ID | Created At | Conclusion | nightly-flaky-python | nightly-flaky-web-e2e |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in results:
        web = row["nightly-flaky-web-e2e"]
        if isinstance(web, dict):
            web_value = ", ".join(f"{name}={value}" for name, value in sorted(web.items()))
        else:
            web_value = str(web)
        lines.append(
            f"| `{row['run_id']}` | `{row['created_at']}` | `{row['conclusion']}` | "
            f"`{row['nightly-flaky-python']}` | `{web_value}` |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--workflow-file", default="ci.yml")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--md-out", type=Path, required=True)
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")

    results = collect_recent_schedule_runs(args.repo, token, args.workflow_file, args.limit)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    write_report(results, args.json_out, args.md_out)
    print(f"nightly flaky trend report written: runs={len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
