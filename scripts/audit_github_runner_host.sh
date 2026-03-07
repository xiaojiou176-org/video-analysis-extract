#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ID="${GCP_PROJECT_ID:-}"
ZONE="${GCP_ZONE:-us-central1-a}"
INSTANCE=""
RUNNER_NAME="pool-core02-03"
REPO_NAME="video-analysis-extract"
OUT_DIR=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/audit_github_runner_host.sh \
    --project PROJECT_ID \
    --zone us-central1-a \
    --instance github-runner-core-02 \
    [--runner-name pool-core02-03] \
    [--repo-name video-analysis-extract] \
    [--out-dir .runtime-cache/temp/runner-health/core02]
USAGE
}

while (($# > 0)); do
  case "$1" in
    --project) PROJECT_ID="${2:-}"; shift 2 ;;
    --zone) ZONE="${2:-}"; shift 2 ;;
    --instance) INSTANCE="${2:-}"; shift 2 ;;
    --runner-name) RUNNER_NAME="${2:-}"; shift 2 ;;
    --repo-name) REPO_NAME="${2:-}"; shift 2 ;;
    --out-dir) OUT_DIR="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$PROJECT_ID" ]] || { echo "missing --project" >&2; exit 2; }
[[ -n "$INSTANCE" ]] || { echo "missing --instance" >&2; exit 2; }

if [[ -z "$OUT_DIR" ]]; then
  OUT_DIR="$ROOT_DIR/.runtime-cache/temp/runner-health/${INSTANCE}"
fi
mkdir -p "$OUT_DIR"

WORK_ROOT="/home/ubuntu/actions-runner/${RUNNER_NAME}/_work"
REPO_ROOT="${WORK_ROOT}/${REPO_NAME}"

echo "[runner-audit] out_dir=${OUT_DIR}"

gcloud compute instances describe "$INSTANCE" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --format='yaml(name,status,lastStartTimestamp,lastStopTimestamp,labels,tags.items,networkInterfaces[0].networkIP,networkInterfaces[0].accessConfigs[0].natIP,metadata.items)' \
  > "${OUT_DIR}/instance.yaml"

gcloud compute instances get-serial-port-output "$INSTANCE" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --port=1 \
  --start=0 \
  > "${OUT_DIR}/serial-port.log"

gcloud compute ssh "$INSTANCE" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --command="
set -euo pipefail
echo '=== service snapshot ==='
systemctl list-units 'actions.runner.xiaojiou176-org.pool-*.service' --all --no-pager || true
echo
echo '=== listener processes ==='
pgrep -af 'runsvc.sh|Runner.Listener|RunnerService.js' || true
echo
echo '=== work root ==='
echo '${WORK_ROOT}'
ls -1 '${WORK_ROOT}' | sed -n '1,120p' || true
echo
echo '=== cache-like paths ==='
sudo find '${WORK_ROOT}' -maxdepth 6 \\( -path '*/~/.cache/*' -o -path '*/.cache/*' -o -path '*/.runtime-cache/ms-playwright*' \\) -print | sed -n '1,200p'
echo
echo '=== non-ubuntu owners in work root ==='
sudo find '${WORK_ROOT}' -maxdepth 2 \\! -user ubuntu -printf '%u:%g %m %p\\n' | sed -n '1,200p'
echo
echo '=== repo-specific cache-like paths ==='
sudo find '${REPO_ROOT}' -maxdepth 6 \\( -path '*/~/.cache/*' -o -path '*/.cache/*' -o -path '*/.runtime-cache/ms-playwright*' \\) -print | sed -n '1,200p' || true
echo
echo '=== repo-specific non-ubuntu owners ==='
sudo find '${REPO_ROOT}' -maxdepth 6 \\! -user ubuntu -printf '%u:%g %m %p\\n' | sed -n '1,200p' || true
echo
echo '=== repo disk usage ==='
du -sh '${REPO_ROOT}' 2>/dev/null || true
" > "${OUT_DIR}/ssh-audit.txt"

{
  echo "leftover_process_markers:"
  rg -n "left-over process|remains running after unit stopped|Runner listener exited with error code 143" "${OUT_DIR}/serial-port.log" || true
} > "${OUT_DIR}/summary.txt"

echo "[runner-audit] wrote:"
printf '  - %s\n' "${OUT_DIR}/instance.yaml" "${OUT_DIR}/serial-port.log" "${OUT_DIR}/ssh-audit.txt" "${OUT_DIR}/summary.txt"
