#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import write_json_artifact

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / ".runtime-cache" / "reports" / "governance" / "ghcr-registry-auth-probe.json"
CONTRACT_PATH = ROOT / "infra" / "config" / "strict_ci_contract.json"


def _read_expected_repository() -> str:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return str(payload["standard_image"]["repository"])


def _run(cmd: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


def _discover_accounts() -> list[dict[str, str]]:
    code, stdout, _ = _run(["gh", "auth", "status"])
    if code != 0:
        return []
    blocks = [block.strip() for block in stdout.split("\n\n") if block.strip()]
    accounts: list[dict[str, str]] = []
    for block in blocks:
        login_match = re.search(r"Logged in to github\.com account (?P<login>[^\s]+)", block)
        if not login_match:
            continue
        login = login_match.group("login")
        active = "- Active account: true" in block
        token_cmd = ["gh", "auth", "token"]
        if not active:
            token_cmd += ["--user", login]
        token_code, token_stdout, _ = _run(token_cmd)
        if token_code != 0 or not token_stdout.strip():
            continue
        scope_match = re.search(r"- Token scopes: (?P<scopes>.+)", block)
        scopes = scope_match.group("scopes").strip() if scope_match else ""
        accounts.append(
            {
                "login": login,
                "active": "true" if active else "false",
                "scopes": scopes,
                "token": token_stdout.strip(),
            }
        )
    return accounts


def _http_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    timeout: int = 20,
) -> dict[str, object]:
    request = urllib.request.Request(url, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
            return {
                "status": response.getcode(),
                "headers": dict(response.headers),
                "body": body[:500],
            }
    except urllib.error.HTTPError as exc:
        return {
            "status": exc.code,
            "headers": dict(exc.headers),
            "body": exc.read().decode("utf-8", "replace")[:500],
        }
    except Exception as exc:  # pragma: no cover - network probe surface
        return {
            "status": 0,
            "headers": {},
            "body": str(exc),
        }


def _exchange_registry_token(*, login: str, token: str, repository_path: str, challenge_scope: str) -> dict[str, object]:
    requested_scope = f"repository:{repository_path}:pull,push"
    basic = base64.b64encode(f"{login}:{token}".encode("utf-8")).decode("ascii")
    params = urllib.parse.urlencode({"service": "ghcr.io", "scope": requested_scope})
    response = _http_request(
        f"https://ghcr.io/token?{params}",
        headers={"Authorization": f"Basic {basic}"},
    )
    payload: dict[str, object] = {
        "challenge_scope": challenge_scope,
        "requested_scope": requested_scope,
        "status": response["status"],
        "body": str(response["body"]),
    }
    body_text = str(response["body"])
    bearer_token = ""
    if response["status"] == 200:
        try:
            body_json = json.loads(body_text)
        except json.JSONDecodeError:
            body_json = {}
        payload["token_keys"] = sorted(body_json.keys())
        bearer_token = str(body_json.get("token") or body_json.get("access_token") or "")
        payload["token_length"] = len(bearer_token)
        payload["body"] = "<redacted: registry bearer token issued>"
    if bearer_token:
        upload = _http_request(
            f"https://ghcr.io/v2/{repository_path}/blobs/uploads/",
            method="POST",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        payload["upload_probe"] = {
            "status": upload["status"],
            "headers": upload["headers"],
            "body": upload["body"],
        }
    else:
        payload["upload_probe"] = {
            "status": 0,
            "headers": {},
            "body": "token exchange did not yield a bearer token",
        }
    return payload


def main() -> int:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    expected_repository = _read_expected_repository()
    repository_path = expected_repository.removeprefix("ghcr.io/").strip("/")

    anonymous_challenge = _http_request(
        f"https://ghcr.io/v2/{repository_path}/blobs/uploads/",
        method="POST",
    )
    challenge_header = str(anonymous_challenge.get("headers", {}).get("www-authenticate", ""))
    challenge_scope_match = re.search(r'scope="([^"]+)"', challenge_header)
    challenge_scope = challenge_scope_match.group(1) if challenge_scope_match else ""

    payload: dict[str, object] = {
        "version": 1,
        "expected_repository": expected_repository,
        "repository_path": repository_path,
        "anonymous_challenge": {
            "status": anonymous_challenge["status"],
            "www_authenticate": challenge_header,
            "body": anonymous_challenge["body"],
        },
        "accounts": [],
    }

    for account in _discover_accounts():
        payload["accounts"].append(
            {
                "login": account["login"],
                "active": account["active"] == "true",
                "scopes": account["scopes"],
                "registry_exchange": _exchange_registry_token(
                    login=account["login"],
                    token=account["token"],
                    repository_path=repository_path,
                    challenge_scope=challenge_scope,
                ),
            }
        )

    write_json_artifact(
        output_path,
        payload,
        source_entrypoint="scripts/governance/probe_ghcr_registry_auth.py",
        verification_scope="ghcr-registry-auth-probe",
        source_run_id="ghcr-registry-auth-probe",
        freshness_window_hours=24,
        extra={"report_kind": "ghcr-registry-auth-probe"},
    )
    print(f"[ghcr-registry-auth-probe] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
