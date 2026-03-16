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

buildx_inspect=""
if [[ "$status" == "ready" ]]; then
  if buildx_inspect="$(docker buildx inspect 2>/dev/null)"; then
    :
  else
    status="blocked"
    blocker_type="buildx-runtime-preparation-failure"
    errors+=("docker buildx inspect failed")
  fi
fi

expected_repository="$(python3 - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("infra/config/strict_ci_contract.json").read_text(encoding="utf-8"))
print(payload["standard_image"]["repository"])
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
if [[ "$expected_owner" != "$repo_owner" ]]; then
  status="blocked"
  blocker_type="package-ownership-or-write-package-failure"
  errors+=("GHCR repository owner mismatch: contract=${expected_owner} repo=${repo_owner}")
fi

token_mode="none"
token_scope_ok="false"
if [[ -n "${GITHUB_ACTIONS:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
  token_mode="github-actions-token"
  token_scope_ok="true"
elif [[ -n "${GHCR_TOKEN:-}" ]]; then
  token_mode="ghcr-token"
  token_scope_ok="true"
elif gh auth status -h github.com >/tmp/video-analysis-gh-auth-status.txt 2>/dev/null; then
  token_mode="gh-cli"
  if grep -Eq "write:packages|'repo'" /tmp/video-analysis-gh-auth-status.txt; then
    token_scope_ok="true"
  fi
fi

if [[ "$token_scope_ok" != "true" ]]; then
  status="blocked"
  blocker_type="registry-auth-failure"
  errors+=("no token path with packages write capability detected")
fi

ERRORS_JSON="$(python3 - <<'PY' "${errors[@]-}"
import json
import sys
print(json.dumps(sys.argv[1:], ensure_ascii=False))
PY
)"

python3 - <<'PY' "$OUTPUT_PATH" "$status" "$blocker_type" "$repo_slug" "$repo_owner" "$expected_repository" "$token_mode" "$token_scope_ok" "$buildx_version" "$buildx_inspect" "$ERRORS_JSON"
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
    "token_mode": sys.argv[7],
    "token_scope_ok": sys.argv[8] == "true",
    "docker_buildx_version": sys.argv[9],
    "docker_buildx_inspect": sys.argv[10],
    "errors": json.loads(sys.argv[11]),
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
