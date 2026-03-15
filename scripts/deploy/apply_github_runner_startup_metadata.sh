#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_ID="${GCP_PROJECT_ID:-}"
ZONE="${GCP_ZONE:-us-central1-a}"
SCRIPT_PATH="$ROOT_DIR/infra/gce/github-runner-org-startup.sh"
INSTANCES=()

usage() {
  cat <<'USAGE'
Usage:
  scripts/deploy/apply_github_runner_startup_metadata.sh \
    --project PROJECT_ID \
    --zone us-central1-a \
    --instance github-runner-core-02 [--instance github-runner-core-03 ...]
USAGE
}

while (($# > 0)); do
  case "$1" in
    --project) PROJECT_ID="${2:-}"; shift 2 ;;
    --zone) ZONE="${2:-}"; shift 2 ;;
    --instance) INSTANCES+=("${2:-}"); shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$PROJECT_ID" ]] || { echo "missing --project" >&2; exit 2; }
[[ -f "$SCRIPT_PATH" ]] || { echo "missing startup script: $SCRIPT_PATH" >&2; exit 2; }
if ((${#INSTANCES[@]} == 0)); then
  echo "missing at least one --instance" >&2
  exit 2
fi

for instance in "${INSTANCES[@]}"; do
  echo "[runner-startup-sync] applying startup-script to ${instance}"
  gcloud compute instances add-metadata "$instance" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --metadata-from-file="startup-script=${SCRIPT_PATH}"
done
