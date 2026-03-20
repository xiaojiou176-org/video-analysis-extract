#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

OUTPUT_PATH="${1:-.runtime-cache/reports/governance/standard-image-publish-readiness.json}"

status="ready"
blocker_type=""
errors=()

remote_url="$(git config --get remote.origin.url)"
repo_slug="$(python3 - <<'PY' "$remote_url"
import re
import sys

remote = sys.argv[1]
match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$", remote)
if not match:
    raise SystemExit(f"unable to parse GitHub slug from remote: {remote}")
print(f"{match.group('owner')}/{match.group('repo')}")
PY
)"
repo_owner="${repo_slug%%/*}"

buildx_version=""
if buildx_version="$(docker buildx version 2>/dev/null)"; then
  :
else
  status="blocked"
  blocker_type="buildx-runtime-preparation-failure"
  errors+=("docker buildx version failed")
fi

buildx_ls=""
if [[ "$status" == "ready" ]]; then
  buildx_ls_stdout="$(mktemp)"
  buildx_ls_stderr="$(mktemp)"
  docker buildx ls >"$buildx_ls_stdout" 2>"$buildx_ls_stderr" &
  buildx_ls_pid=$!
  buildx_ls_elapsed=0
  while kill -0 "$buildx_ls_pid" 2>/dev/null; do
    if (( buildx_ls_elapsed >= 15 )); then
      kill "$buildx_ls_pid" 2>/dev/null || true
      sleep 1
      if kill -0 "$buildx_ls_pid" 2>/dev/null; then
        kill -9 "$buildx_ls_pid" 2>/dev/null || true
      fi
      wait "$buildx_ls_pid" 2>/dev/null || true
      status="blocked"
      blocker_type="buildx-runtime-preparation-failure"
      errors+=("docker buildx ls timed out after 15s")
      break
    fi
    sleep 1
    buildx_ls_elapsed=$((buildx_ls_elapsed + 1))
  done
  if [[ "$status" == "ready" ]]; then
    if wait "$buildx_ls_pid"; then
      buildx_ls="$(cat "$buildx_ls_stdout")"
      if [[ "$buildx_ls" == *"context deadline exceeded"* || "$buildx_ls" == *"Cannot load builder"* ]]; then
        status="blocked"
        blocker_type="buildx-runtime-preparation-failure"
        errors+=("docker buildx ls reports builder context deadline or daemon reachability failure")
      fi
    else
      status="blocked"
      blocker_type="buildx-runtime-preparation-failure"
      if [[ -s "$buildx_ls_stderr" ]]; then
        errors+=("docker buildx ls failed: $(tr '\n' ' ' < "$buildx_ls_stderr" | sed 's/[[:space:]]\\+/ /g; s/[[:space:]]$//')")
      else
        errors+=("docker buildx ls failed")
      fi
    fi
  fi
  rm -f "$buildx_ls_stdout" "$buildx_ls_stderr"
fi

buildx_inspect=""
if [[ "$status" == "ready" ]]; then
  inspect_stdout="$(mktemp)"
  inspect_stderr="$(mktemp)"
  docker buildx inspect >"$inspect_stdout" 2>"$inspect_stderr" &
  inspect_pid=$!
  inspect_elapsed=0
  while kill -0 "$inspect_pid" 2>/dev/null; do
    if (( inspect_elapsed >= 15 )); then
      kill "$inspect_pid" 2>/dev/null || true
      sleep 1
      if kill -0 "$inspect_pid" 2>/dev/null; then
        kill -9 "$inspect_pid" 2>/dev/null || true
      fi
      wait "$inspect_pid" 2>/dev/null || true
      status="blocked"
      blocker_type="buildx-runtime-preparation-failure"
      errors+=("docker buildx inspect timed out after 15s")
      break
    fi
    sleep 1
    inspect_elapsed=$((inspect_elapsed + 1))
  done
  if [[ "$status" == "ready" ]]; then
    if wait "$inspect_pid"; then
      buildx_inspect="$(cat "$inspect_stdout")"
    else
      status="blocked"
      blocker_type="buildx-runtime-preparation-failure"
      if [[ -s "$inspect_stderr" ]]; then
        errors+=("docker buildx inspect failed: $(tr '\n' ' ' < "$inspect_stderr" | sed 's/[[:space:]]\\+/ /g; s/[[:space:]]$//')")
      else
        errors+=("docker buildx inspect failed")
      fi
    fi
  fi
  rm -f "$inspect_stdout" "$inspect_stderr"
fi

expected_repository="$(python3 - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("infra/config/strict_ci_contract.json").read_text(encoding="utf-8"))
print(payload["standard_image"]["repository"])
PY
)"
expected_digest="$(python3 - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("infra/config/strict_ci_contract.json").read_text(encoding="utf-8"))
print(payload["standard_image"]["digest"])
PY
)"
expected_owner="$(python3 - <<'PY' "$expected_repository"
import re
import sys

repo = sys.argv[1]
match = re.match(r"ghcr\.io/(?P<owner>[^/]+)/", repo)
if not match:
    raise SystemExit(f"invalid GHCR repository: {repo}")
print(match.group("owner"))
PY
)"
expected_package_name="${expected_repository##*/}"
if [[ "$expected_owner" != "$repo_owner" ]]; then
  status="blocked"
  blocker_type="package-ownership-or-write-package-failure"
  errors+=("GHCR repository owner mismatch: contract=${expected_owner} repo=${repo_owner}")
fi

probe_github_package_api() {
  local token="$1"
  local owner="$2"
  local package_name="$3"

  python3 - <<'PY' "$token" "$owner" "$package_name"
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

token, owner, package_name = sys.argv[1:4]
endpoints = [
    f"https://api.github.com/orgs/{owner}/packages/container/{package_name}",
    f"https://api.github.com/users/{owner}/packages/container/{package_name}",
]
result = {
    "status": 0,
    "endpoint": "",
    "message": "",
}
for endpoint in endpoints:
    request = urllib.request.Request(
        endpoint,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "video-analysis-extract-standard-image-readiness",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = {
                "status": response.getcode(),
                "endpoint": endpoint,
                "message": response.read().decode("utf-8", "replace")[:500],
            }
            break
    except urllib.error.HTTPError as exc:
        result = {
            "status": exc.code,
            "endpoint": endpoint,
            "message": exc.read().decode("utf-8", "replace")[:500],
        }
        if exc.code != 404:
            break
    except Exception as exc:  # pragma: no cover - bash-driven probe surface
        result = {
            "status": 0,
            "endpoint": endpoint,
            "message": str(exc),
        }
        break

print(json.dumps(result, ensure_ascii=False))
PY
}

probe_registry_manifest() {
  local repository="$1"
  local digest="$2"

  python3 - <<'PY' "$repository" "$digest"
from __future__ import annotations

import json
import subprocess
import sys

repository, digest = sys.argv[1:3]
target = f"{repository}@{digest}"
result = subprocess.run(
    ["docker", "manifest", "inspect", target],
    capture_output=True,
    text=True,
    check=False,
)
payload = {
    "target": target,
    "returncode": result.returncode,
    "stdout": (result.stdout or "")[:500],
    "stderr": (result.stderr or "")[:500],
}
print(json.dumps(payload, ensure_ascii=False))
PY
}

probe_ghcr_blob_upload() {
  local username="$1"
  local token="$2"
  local repository="$3"

  python3 - <<'PY' "$username" "$token" "$repository"
from __future__ import annotations

import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

username, token, repository = sys.argv[1:4]
repo_path = repository.removeprefix("ghcr.io/").strip("/")
endpoint = f"https://ghcr.io/v2/{repo_path}/blobs/uploads/"
auth = base64.b64encode(f"{username}:{token}".encode("utf-8")).decode("ascii")
headers = {
    "Authorization": f"Basic {auth}",
    "User-Agent": "video-analysis-extract-standard-image-readiness",
}
result = {
    "status": 0,
    "endpoint": endpoint,
    "message": "",
    "cleanup_status": None,
}
request = urllib.request.Request(endpoint, method="POST", headers=headers)
try:
    with urllib.request.urlopen(request, timeout=15) as response:
        result["status"] = response.getcode()
        result["message"] = response.read().decode("utf-8", "replace")[:500]
        location = response.headers.get("Location") or ""
        if location:
            cleanup_target = urllib.parse.urljoin(endpoint, location)
            cleanup_request = urllib.request.Request(cleanup_target, method="DELETE", headers=headers)
            try:
                with urllib.request.urlopen(cleanup_request, timeout=15) as cleanup_response:
                    result["cleanup_status"] = cleanup_response.getcode()
            except urllib.error.HTTPError as exc:
                result["cleanup_status"] = exc.code
            except Exception:
                result["cleanup_status"] = 0
except urllib.error.HTTPError as exc:
    result["status"] = exc.code
    result["message"] = exc.read().decode("utf-8", "replace")[:500]
except Exception as exc:  # pragma: no cover - bash-driven probe surface
    result["status"] = 0
    result["message"] = str(exc)

print(json.dumps(result, ensure_ascii=False))
PY
}

token_mode="none"
token_scope_ok="false"
blob_upload_scope_ok="false"
package_probe_json='{}'
blob_upload_probe_json='{}'
manifest_probe_json='{}'
selected_token=""
selected_username="${GHCR_WRITE_USERNAME:-${GHCR_USERNAME:-${GITHUB_ACTOR:-}}}"
# In hosted GitHub Actions runs, prefer the repository-scoped GITHUB_TOKEN first
# so stale GHCR_WRITE_* secrets cannot mask a healthier current token path.
if [[ -n "${GITHUB_ACTIONS:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
  token_mode="github-actions-token"
  selected_username="${GITHUB_ACTOR:-$selected_username}"
  selected_token="$GITHUB_TOKEN"
  package_probe_json="$(probe_github_package_api "$selected_token" "$expected_owner" "$expected_package_name")"
elif [[ -n "${GHCR_WRITE_TOKEN:-}" ]]; then
  token_mode="ghcr-write-token"
  selected_token="$GHCR_WRITE_TOKEN"
  package_probe_json="$(probe_github_package_api "$selected_token" "$expected_owner" "$expected_package_name")"
elif [[ -n "${GHCR_TOKEN:-}" ]]; then
  token_mode="ghcr-token"
  selected_token="$GHCR_TOKEN"
  package_probe_json="$(probe_github_package_api "$selected_token" "$expected_owner" "$expected_package_name")"
elif gh auth status -h github.com >/tmp/video-analysis-gh-auth-status.txt 2>/dev/null; then
  token_mode="gh-cli"
  # repo scope alone does not grant GHCR package push rights, and we must only
  # inspect the active account instead of any secondary cached logins.
  if python3 - <<'PY' /tmp/video-analysis-gh-auth-status.txt
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
for block in blocks:
    if "- Active account: true" not in block:
        continue
    raise SystemExit(0 if "write:packages" in block else 1)
raise SystemExit(1)
PY
  then
    token_scope_ok="true"
  fi
fi

package_probe_status="$(python3 - <<'PY' "$package_probe_json"
import json
import sys

payload = json.loads(sys.argv[1])
print(payload.get("status", 0))
PY
)"
package_probe_endpoint="$(python3 - <<'PY' "$package_probe_json"
import json
import sys

payload = json.loads(sys.argv[1])
print(payload.get("endpoint", ""))
PY
)"
if [[ "$token_mode" == "ghcr-token" || "$token_mode" == "github-actions-token" ]]; then
  case "$package_probe_status" in
    200|404)
      token_scope_ok="true"
      ;;
    403)
      status="blocked"
      blocker_type="registry-auth-failure"
      errors+=("package access probe rejected the selected GHCR token via ${package_probe_endpoint:-github-packages-api} (HTTP 403)")
      ;;
    0)
      status="blocked"
      blocker_type="registry-auth-failure"
      errors+=("package access probe could not verify the selected GHCR token")
      ;;
    *)
      status="blocked"
      blocker_type="registry-auth-failure"
      errors+=("package access probe returned unexpected HTTP ${package_probe_status} for ${package_probe_endpoint:-github-packages-api}")
      ;;
  esac
fi

if [[ "$status" == "ready" && "$token_scope_ok" == "true" && ( "$token_mode" == "ghcr-write-token" || "$token_mode" == "ghcr-token" || "$token_mode" == "github-actions-token" ) ]]; then
  if [[ -z "$selected_username" ]]; then
    status="blocked"
    blocker_type="registry-auth-failure"
    errors+=("selected GHCR token is missing a username required for blob upload probe")
  else
    blob_upload_probe_json="$(probe_ghcr_blob_upload "$selected_username" "$selected_token" "$expected_repository")"
    blob_upload_probe_status="$(python3 - <<'PY' "$blob_upload_probe_json"
import json
import sys

payload = json.loads(sys.argv[1])
print(payload.get("status", 0))
PY
)"
    case "$blob_upload_probe_status" in
      202)
        blob_upload_scope_ok="true"
        ;;
      401|403)
        status="blocked"
        blocker_type="registry-auth-failure"
        errors+=("GHCR blob upload probe rejected the selected token via ghcr blob upload endpoint (HTTP ${blob_upload_probe_status})")
        ;;
      0)
        status="blocked"
        blocker_type="registry-auth-failure"
        errors+=("GHCR blob upload probe could not verify blob write capability")
        ;;
      *)
        status="blocked"
        blocker_type="registry-auth-failure"
        errors+=("GHCR blob upload probe returned unexpected HTTP ${blob_upload_probe_status}")
        ;;
    esac
  fi
fi

if [[ "$token_scope_ok" != "true" ]]; then
  status="blocked"
  blocker_type="registry-auth-failure"
  errors+=("no token path with packages write capability detected")
fi

manifest_probe_json="$(probe_registry_manifest "$expected_repository" "$expected_digest")"
manifest_probe_returncode="$(python3 - <<'PY' "$manifest_probe_json"
import json
import sys

payload = json.loads(sys.argv[1])
print(payload.get("returncode", 0))
PY
)"
manifest_probe_stderr="$(python3 - <<'PY' "$manifest_probe_json"
import json
import sys

payload = json.loads(sys.argv[1])
print(payload.get("stderr", ""))
PY
)"
if [[ "$manifest_probe_returncode" != "0" && "$manifest_probe_stderr" == *"manifest unknown"* ]]; then
  errors+=("GHCR manifest probe reports 'manifest unknown' for the digest-pinned standard image; this suggests package-path / ownership / visibility / publication is still unresolved")
fi

ERRORS_JSON="$(
  printf '%s\n' "${errors[@]}" | python3 -c 'import json, sys; print(json.dumps([line.rstrip("\n") for line in sys.stdin if line.rstrip("\n")], ensure_ascii=False))'
)"

python3 - <<'PY' "$OUTPUT_PATH" "$status" "$blocker_type" "$repo_slug" "$repo_owner" "$expected_repository" "$expected_digest" "$token_mode" "$token_scope_ok" "$blob_upload_scope_ok" "$buildx_version" "$buildx_ls" "$buildx_inspect" "$ERRORS_JSON" "$package_probe_json" "$blob_upload_probe_json" "$manifest_probe_json"
import json
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "scripts" / "governance"))
from common import write_json_artifact

output = Path(sys.argv[1])
payload = {
    "version": 1,
    "status": sys.argv[2],
    "blocker_type": sys.argv[3],
    "repo": sys.argv[4],
    "repo_owner": sys.argv[5],
    "expected_repository": sys.argv[6],
    "expected_digest": sys.argv[7],
    "token_mode": sys.argv[8],
    "token_scope_ok": sys.argv[9] == "true",
    "blob_upload_scope_ok": sys.argv[10] == "true",
    "docker_buildx_version": sys.argv[11],
    "docker_buildx_ls": sys.argv[12],
    "docker_buildx_inspect": sys.argv[13],
    "errors": json.loads(sys.argv[14]),
    "package_access_probe": json.loads(sys.argv[15]),
    "blob_upload_probe": json.loads(sys.argv[16]),
    "manifest_probe": json.loads(sys.argv[17]),
}
write_json_artifact(
    ROOT / output,
    payload,
    source_entrypoint="scripts/ci/check_standard_image_publish_readiness.sh",
    verification_scope="standard-image-publish-readiness",
    source_run_id="standard-image-publish-readiness",
    freshness_window_hours=24,
    extra={"report_kind": "standard-image-publish-readiness"},
)
PY

if [[ "$status" != "ready" ]]; then
  echo "[standard-image-publish-readiness] FAIL"
  for item in "${errors[@]}"; do
    echo "  - $item"
  done
  exit 1
fi

echo "[standard-image-publish-readiness] READY"
