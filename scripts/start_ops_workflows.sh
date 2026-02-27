#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Optional env overrides (all have safe defaults):
#   OPS_DAILY_LOCAL_HOUR=9
#   OPS_DAILY_TIMEZONE=Asia/Shanghai
#   OPS_NOTIFICATION_INTERVAL_MINUTES=10
#   OPS_NOTIFICATION_RETRY_BATCH_LIMIT=50
#   OPS_CANARY_INTERVAL_HOURS=1
#   OPS_CANARY_TIMEOUT_SECONDS=8
#   OPS_CLEANUP_INTERVAL_HOURS=6
#   OPS_CLEANUP_OLDER_THAN_HOURS=24
#   OPS_CLEANUP_CACHE_OLDER_THAN_HOURS=
#   OPS_CLEANUP_CACHE_MAX_SIZE_MB=
#   OPS_CLEANUP_WORKSPACE_DIR=
#   OPS_CLEANUP_CACHE_DIR=
#   (worker hints now controlled via --show-hints / --no-show-hints in this script)

OPS_DAILY_LOCAL_HOUR="${OPS_DAILY_LOCAL_HOUR:-9}"
OPS_DAILY_TIMEZONE="${OPS_DAILY_TIMEZONE:-system-local}"
OPS_DAILY_TIMEZONE_OFFSET_MINUTES=""
OPS_DAILY_WORKFLOW_ID="daily-digest-workflow"
OPS_DAILY_RUN_ONCE="0"

OPS_NOTIFICATION_INTERVAL_MINUTES="${OPS_NOTIFICATION_INTERVAL_MINUTES:-10}"
OPS_NOTIFICATION_RETRY_BATCH_LIMIT="${OPS_NOTIFICATION_RETRY_BATCH_LIMIT:-50}"
OPS_NOTIFICATION_WORKFLOW_ID="notification-retry-workflow"
OPS_NOTIFICATION_RUN_ONCE="0"

OPS_CANARY_INTERVAL_HOURS="${OPS_CANARY_INTERVAL_HOURS:-1}"
OPS_CANARY_TIMEOUT_SECONDS="${OPS_CANARY_TIMEOUT_SECONDS:-8}"
OPS_CANARY_WORKFLOW_ID="provider-canary-workflow"
OPS_CANARY_RUN_ONCE="0"

OPS_CLEANUP_INTERVAL_HOURS="${OPS_CLEANUP_INTERVAL_HOURS:-6}"
OPS_CLEANUP_OLDER_THAN_HOURS="${OPS_CLEANUP_OLDER_THAN_HOURS:-24}"
OPS_CLEANUP_CACHE_OLDER_THAN_HOURS="${OPS_CLEANUP_CACHE_OLDER_THAN_HOURS:-}"
OPS_CLEANUP_CACHE_MAX_SIZE_MB="${OPS_CLEANUP_CACHE_MAX_SIZE_MB:-}"
OPS_CLEANUP_WORKSPACE_DIR="${OPS_CLEANUP_WORKSPACE_DIR:-}"
OPS_CLEANUP_CACHE_DIR="${OPS_CLEANUP_CACHE_DIR:-}"
OPS_CLEANUP_WORKFLOW_ID="cleanup-workspace-workflow"
OPS_CLEANUP_RUN_ONCE="0"

OPS_SHOW_HINTS="1"
OPS_DRY_RUN="0"

validate_cleanup_dir() {
  local name="$1"
  local raw="$2"
  if [[ -z "$raw" ]]; then
    return 0
  fi
  if [[ "${raw:0:1}" != "/" ]]; then
    echo "[start_ops_workflows] ${name} must be an absolute path: $raw" >&2
    exit 2
  fi
  local resolved
  resolved="$(
    python3 - "$raw" <<'PY'
import pathlib
import sys

print(pathlib.Path(sys.argv[1]).expanduser().resolve())
PY
  )"

  local -a allowed_prefixes=(
    "$ROOT_DIR/.runtime-cache"
    "$ROOT_DIR/cache"
    "$ROOT_DIR/.cache"
    "/tmp/video-digestor"
    "/tmp/video-analysis"
  )
  local prefix
  for prefix in "${allowed_prefixes[@]}"; do
    if [[ "$resolved" == "$prefix" || "$resolved" == "$prefix/"* ]]; then
      printf '%s' "$resolved"
      return 0
    fi
  done
  echo "[start_ops_workflows] ${name} is outside allowed cleanup prefixes: $resolved" >&2
  echo "[start_ops_workflows] allowed prefixes: ${allowed_prefixes[*]}" >&2
  exit 2
}

print_help() {
  cat <<'EOM'
Usage: ./scripts/start_ops_workflows.sh [--dry-run] [--help]

Start/ensure long-running ops workflows:
- daily_digest
- notification_retry
- provider_canary
- cleanup_workspace

Options:
  --daily-workflow-id <id>         Daily workflow id (default: daily-digest-workflow)
  --daily-run-once                 Run daily workflow once (default: disabled)
  --daily-timezone-offset-minutes <minutes>
                                   Daily timezone offset override in minutes
  --notification-workflow-id <id>  Notification workflow id (default: notification-retry-workflow)
  --notification-run-once          Run notification workflow once (default: disabled)
  --canary-workflow-id <id>        Canary workflow id (default: provider-canary-workflow)
  --canary-run-once                Run canary workflow once (default: disabled)
  --cleanup-workflow-id <id>       Cleanup workflow id (default: cleanup-workspace-workflow)
  --cleanup-run-once               Run cleanup workflow once (default: disabled)
  --show-hints                     Print startup summary logs (default)
  --no-show-hints                  Disable startup summary logs
  --dry-run, -n                    Print worker commands without executing them
  --help, -h                       Show this help message
EOM
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --daily-workflow-id)
      if [[ $# -lt 2 ]]; then
        echo "[start_ops_workflows] --daily-workflow-id requires a value" >&2
        exit 2
      fi
      OPS_DAILY_WORKFLOW_ID="${2:-}"
      shift 2
      ;;
    --daily-run-once)
      OPS_DAILY_RUN_ONCE=1
      shift
      ;;
    --daily-timezone-offset-minutes)
      if [[ $# -lt 2 ]]; then
        echo "[start_ops_workflows] --daily-timezone-offset-minutes requires a value" >&2
        exit 2
      fi
      OPS_DAILY_TIMEZONE_OFFSET_MINUTES="${2:-}"
      shift 2
      ;;
    --notification-workflow-id)
      if [[ $# -lt 2 ]]; then
        echo "[start_ops_workflows] --notification-workflow-id requires a value" >&2
        exit 2
      fi
      OPS_NOTIFICATION_WORKFLOW_ID="${2:-}"
      shift 2
      ;;
    --notification-run-once)
      OPS_NOTIFICATION_RUN_ONCE=1
      shift
      ;;
    --canary-workflow-id)
      if [[ $# -lt 2 ]]; then
        echo "[start_ops_workflows] --canary-workflow-id requires a value" >&2
        exit 2
      fi
      OPS_CANARY_WORKFLOW_ID="${2:-}"
      shift 2
      ;;
    --canary-run-once)
      OPS_CANARY_RUN_ONCE=1
      shift
      ;;
    --cleanup-workflow-id)
      if [[ $# -lt 2 ]]; then
        echo "[start_ops_workflows] --cleanup-workflow-id requires a value" >&2
        exit 2
      fi
      OPS_CLEANUP_WORKFLOW_ID="${2:-}"
      shift 2
      ;;
    --cleanup-run-once)
      OPS_CLEANUP_RUN_ONCE=1
      shift
      ;;
    --show-hints)
      OPS_SHOW_HINTS=1
      shift
      ;;
    --no-show-hints)
      OPS_SHOW_HINTS=0
      shift
      ;;
    --dry-run|-n)
      OPS_DRY_RUN=1
      shift
      ;;
    --help|-h)
      print_help
      exit 0
      ;;
    *)
      echo "[start_ops_workflows] unknown argument: $1" >&2
      print_help >&2
      exit 2
      ;;
  esac
done

require_non_empty_arg() {
  local flag="$1"
  local value="$2"
  if [[ -z "$value" || "$value" == --* ]]; then
    echo "[start_ops_workflows] ${flag} requires a non-empty value" >&2
    exit 2
  fi
}

require_non_empty_arg --daily-workflow-id "$OPS_DAILY_WORKFLOW_ID"
require_non_empty_arg --notification-workflow-id "$OPS_NOTIFICATION_WORKFLOW_ID"
require_non_empty_arg --canary-workflow-id "$OPS_CANARY_WORKFLOW_ID"
require_non_empty_arg --cleanup-workflow-id "$OPS_CLEANUP_WORKFLOW_ID"
if [[ -n "$OPS_DAILY_TIMEZONE_OFFSET_MINUTES" ]]; then
  require_non_empty_arg --daily-timezone-offset-minutes "$OPS_DAILY_TIMEZONE_OFFSET_MINUTES"
fi

if [[ -n "$OPS_CLEANUP_WORKSPACE_DIR" ]]; then
  OPS_CLEANUP_WORKSPACE_DIR="$(validate_cleanup_dir OPS_CLEANUP_WORKSPACE_DIR "$OPS_CLEANUP_WORKSPACE_DIR")"
fi
if [[ -n "$OPS_CLEANUP_CACHE_DIR" ]]; then
  OPS_CLEANUP_CACHE_DIR="$(validate_cleanup_dir OPS_CLEANUP_CACHE_DIR "$OPS_CLEANUP_CACHE_DIR")"
fi

if [[ "$OPS_SHOW_HINTS" == "1" ]]; then
  cat <<EOM
[start_ops_workflows] Bootstrapping realtime ops workflows
[start_ops_workflows] daily_digest: hour=$OPS_DAILY_LOCAL_HOUR tz=$OPS_DAILY_TIMEZONE run_once=$OPS_DAILY_RUN_ONCE workflow_id=$OPS_DAILY_WORKFLOW_ID
[start_ops_workflows] notification_retry: interval_minutes=$OPS_NOTIFICATION_INTERVAL_MINUTES retry_batch_limit=$OPS_NOTIFICATION_RETRY_BATCH_LIMIT run_once=$OPS_NOTIFICATION_RUN_ONCE workflow_id=$OPS_NOTIFICATION_WORKFLOW_ID
[start_ops_workflows] provider_canary: interval_hours=$OPS_CANARY_INTERVAL_HOURS timeout_seconds=$OPS_CANARY_TIMEOUT_SECONDS run_once=$OPS_CANARY_RUN_ONCE workflow_id=$OPS_CANARY_WORKFLOW_ID
[start_ops_workflows] cleanup_workspace: interval_hours=$OPS_CLEANUP_INTERVAL_HOURS older_than_hours=$OPS_CLEANUP_OLDER_THAN_HOURS run_once=$OPS_CLEANUP_RUN_ONCE workflow_id=$OPS_CLEANUP_WORKFLOW_ID
EOM
  if [[ -n "$OPS_DAILY_TIMEZONE_OFFSET_MINUTES" ]]; then
    echo "[start_ops_workflows] daily_digest timezone_offset_minutes=$OPS_DAILY_TIMEZONE_OFFSET_MINUTES"
  fi
  if [[ -n "$OPS_CLEANUP_CACHE_OLDER_THAN_HOURS" ]]; then
    echo "[start_ops_workflows] cleanup_workspace cache_older_than_hours=$OPS_CLEANUP_CACHE_OLDER_THAN_HOURS"
  fi
  if [[ -n "$OPS_CLEANUP_CACHE_MAX_SIZE_MB" ]]; then
    echo "[start_ops_workflows] cleanup_workspace cache_max_size_mb=$OPS_CLEANUP_CACHE_MAX_SIZE_MB"
  fi
  if [[ -n "$OPS_CLEANUP_WORKSPACE_DIR" ]]; then
    echo "[start_ops_workflows] cleanup_workspace workspace_dir=$OPS_CLEANUP_WORKSPACE_DIR"
  fi
  if [[ -n "$OPS_CLEANUP_CACHE_DIR" ]]; then
    echo "[start_ops_workflows] cleanup_workspace cache_dir=$OPS_CLEANUP_CACHE_DIR"
  fi
  if [[ "$OPS_DRY_RUN" == "1" ]]; then
    echo "[start_ops_workflows] dry-run enabled: no commands will be executed"
  fi
fi

run_worker_command() {
  local worker_command="$1"
  shift
  if [[ "$OPS_DRY_RUN" == "1" ]]; then
    printf '[start_ops_workflows] dry-run WORKER_COMMAND=%s %q ' "$worker_command" "$ROOT_DIR/scripts/dev_worker.sh"
    printf '%q ' "$@"
    printf '\n'
    return 0
  fi
  "$ROOT_DIR/scripts/dev_worker.sh" --no-show-hints --command "$worker_command" "$@"
}

start_daily() {
  local -a args=()
  args+=(--local-hour "$OPS_DAILY_LOCAL_HOUR")
  args+=(--timezone-name "$OPS_DAILY_TIMEZONE")
  args+=(--workflow-id "$OPS_DAILY_WORKFLOW_ID")
  if [[ -n "$OPS_DAILY_TIMEZONE_OFFSET_MINUTES" ]]; then
    args+=(--timezone-offset-minutes "$OPS_DAILY_TIMEZONE_OFFSET_MINUTES")
  fi
  if [[ "$OPS_DAILY_RUN_ONCE" == "1" ]]; then
    args+=(--run-once)
  fi
  echo "[start_ops_workflows] ensure daily_digest"
  run_worker_command start-daily-workflow "${args[@]}"
}

start_notification_retry() {
  local -a args=()
  args+=(--interval-minutes "$OPS_NOTIFICATION_INTERVAL_MINUTES")
  args+=(--retry-batch-limit "$OPS_NOTIFICATION_RETRY_BATCH_LIMIT")
  args+=(--workflow-id "$OPS_NOTIFICATION_WORKFLOW_ID")
  if [[ "$OPS_NOTIFICATION_RUN_ONCE" == "1" ]]; then
    args+=(--run-once)
  fi
  echo "[start_ops_workflows] ensure notification_retry"
  run_worker_command start-notification-retry-workflow "${args[@]}"
}

start_provider_canary() {
  local -a args=()
  args+=(--interval-hours "$OPS_CANARY_INTERVAL_HOURS")
  args+=(--timeout-seconds "$OPS_CANARY_TIMEOUT_SECONDS")
  args+=(--workflow-id "$OPS_CANARY_WORKFLOW_ID")
  if [[ "$OPS_CANARY_RUN_ONCE" == "1" ]]; then
    args+=(--run-once)
  fi
  echo "[start_ops_workflows] ensure provider_canary"
  run_worker_command start-provider-canary-workflow "${args[@]}"
}

start_cleanup() {
  local -a args=()
  args+=(--interval-hours "$OPS_CLEANUP_INTERVAL_HOURS")
  args+=(--older-than-hours "$OPS_CLEANUP_OLDER_THAN_HOURS")
  args+=(--workflow-id "$OPS_CLEANUP_WORKFLOW_ID")
  if [[ -n "$OPS_CLEANUP_CACHE_OLDER_THAN_HOURS" ]]; then
    args+=(--cache-older-than-hours "$OPS_CLEANUP_CACHE_OLDER_THAN_HOURS")
  fi
  if [[ -n "$OPS_CLEANUP_CACHE_MAX_SIZE_MB" ]]; then
    args+=(--cache-max-size-mb "$OPS_CLEANUP_CACHE_MAX_SIZE_MB")
  fi
  if [[ -n "$OPS_CLEANUP_WORKSPACE_DIR" ]]; then
    args+=(--workspace-dir "$OPS_CLEANUP_WORKSPACE_DIR")
  fi
  if [[ -n "$OPS_CLEANUP_CACHE_DIR" ]]; then
    args+=(--cache-dir "$OPS_CLEANUP_CACHE_DIR")
  fi
  if [[ "$OPS_CLEANUP_RUN_ONCE" == "1" ]]; then
    args+=(--run-once)
  fi
  echo "[start_ops_workflows] ensure cleanup_workspace"
  run_worker_command start-cleanup-workflow "${args[@]}"
}

start_daily
start_notification_retry
start_provider_canary
start_cleanup

echo "[start_ops_workflows] done"
