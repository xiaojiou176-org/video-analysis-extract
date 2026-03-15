#!/usr/bin/env python3
"""Sync GitHub Actions secrets/variables from local env sources.

- Discovers required keys from `.github/workflows/*.yml` via `secrets.NAME` and `vars.NAME`.
- Reads values from process env first, then `.env` file.
- Writes to GitHub repository actions secrets/variables via `gh` CLI.

Usage:
  python3 scripts/governance/sync_github_actions_env.py --repo owner/repo --apply
  python3 scripts/governance/sync_github_actions_env.py --repo owner/repo --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

SECRETS_PATTERN = re.compile(r"\bsecrets\.([A-Z0-9_]+)\b")
VARS_PATTERN = re.compile(r"\bvars\.([A-Z0-9_]+)\b")


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue

        name, raw_value = line.split("=", 1)
        key = name.strip()
        if not key or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue

        value = raw_value.strip()
        if not value:
            values[key] = ""
            continue

        try:
            parts = shlex.split(value, posix=True)
            parsed = parts[0] if parts else ""
        except ValueError:
            parsed = value.strip("\"'")

        if "$HOME" in parsed:
            parsed = parsed.replace("$HOME", str(Path.home()))
        values[key] = parsed

    return values


def discover_workflow_refs(workflows_dir: Path) -> tuple[set[str], set[str]]:
    secrets: set[str] = set()
    variables: set[str] = set()

    for wf in sorted(workflows_dir.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        secrets.update(SECRETS_PATTERN.findall(text))
        variables.update(VARS_PATTERN.findall(text))

    return secrets, variables


def run_gh(args: list[str], stdin_value: str | None = None) -> None:
    completed = subprocess.run(
        ["gh", *args],
        input=stdin_value,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        msg = completed.stderr.strip() or completed.stdout.strip() or "unknown gh error"
        raise RuntimeError(msg)


def list_remote_names(repo: str, resource: str) -> set[str]:
    completed = subprocess.run(
        ["gh", resource, "list", "--repo", repo],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return set()
    names: set[str] = set()
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        names.add(line.split()[0])
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync GitHub Actions secrets/vars from local env")
    parser.add_argument("--repo", required=True, help="GitHub repo in owner/name form")
    parser.add_argument("--env-file", default=".env", help="Path to env file (default: .env)")
    parser.add_argument("--workflows-dir", default=".github/workflows", help="Workflows dir")
    parser.add_argument("--apply", action="store_true", help="Apply changes to GitHub")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes only")
    args = parser.parse_args()

    if args.apply and args.dry_run:
        print("error: --apply and --dry-run are mutually exclusive", file=sys.stderr)
        return 2

    env_file_values = parse_env_file(Path(args.env_file))
    discovered_secrets, discovered_vars = discover_workflow_refs(Path(args.workflows_dir))

    env_merged: dict[str, str] = dict(env_file_values)
    for key, value in os.environ.items():
        env_merged[key] = value

    remote_secret_names = list_remote_names(args.repo, "secret")
    remote_var_names = list_remote_names(args.repo, "variable")

    secret_ready: list[str] = []
    secret_missing_local: list[str] = []
    secret_missing_but_remote: list[str] = []
    for name in sorted(discovered_secrets):
        value = env_merged.get(name, "")
        if value:
            secret_ready.append(name)
        elif name in remote_secret_names:
            secret_missing_but_remote.append(name)
        else:
            secret_missing_local.append(name)

    var_ready: list[str] = []
    var_missing_local: list[str] = []
    var_missing_but_remote: list[str] = []
    for name in sorted(discovered_vars):
        value = env_merged.get(name, "")
        if value:
            var_ready.append(name)
        elif name in remote_var_names:
            var_missing_but_remote.append(name)
        else:
            var_missing_local.append(name)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[sync-gh-actions-env] mode={mode} repo={args.repo}")
    print(
        f"[sync-gh-actions-env] discovered secrets={len(discovered_secrets)} vars={len(discovered_vars)}"
    )
    print(
        "[sync-gh-actions-env] "
        f"ready secrets={len(secret_ready)} missing(local)={len(secret_missing_local)} "
        f"remote-only={len(secret_missing_but_remote)}"
    )
    print(
        "[sync-gh-actions-env] "
        f"ready vars={len(var_ready)} missing(local)={len(var_missing_local)} "
        f"remote-only={len(var_missing_but_remote)}"
    )

    if secret_missing_local:
        print(
            "[sync-gh-actions-env] missing secrets (not found in local env/.env and not present remotely):"
        )
        for name in secret_missing_local:
            print(f"  - {name}")
    if secret_missing_but_remote:
        print(
            "[sync-gh-actions-env] secrets absent in local source but already configured remotely:"
        )
        for name in secret_missing_but_remote:
            print(f"  - {name}")
    if var_missing_local:
        print(
            "[sync-gh-actions-env] missing vars (not found in local env/.env and not present remotely):"
        )
        for name in var_missing_local:
            print(f"  - {name}")
    if var_missing_but_remote:
        print("[sync-gh-actions-env] vars absent in local source but already configured remotely:")
        for name in var_missing_but_remote:
            print(f"  - {name}")

    if not args.apply:
        return 0

    failures: list[str] = []

    for name in secret_ready:
        try:
            run_gh(["secret", "set", name, "--repo", args.repo], stdin_value=env_merged[name])
            print(f"[sync-gh-actions-env] updated secret: {name}")
        except Exception as exc:  # pragma: no cover
            failures.append(f"secret {name}: {exc}")

    for name in var_ready:
        try:
            run_gh(["variable", "set", name, "--repo", args.repo, "--body", env_merged[name]])
            print(f"[sync-gh-actions-env] updated var: {name}")
        except Exception as exc:  # pragma: no cover
            failures.append(f"var {name}: {exc}")

    if failures:
        print("[sync-gh-actions-env] failures:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print("[sync-gh-actions-env] completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
