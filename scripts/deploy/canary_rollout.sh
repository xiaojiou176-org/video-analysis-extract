#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="canary_rollout"
TARGET_WEIGHT="10"
STEP_WEIGHT="5"
SETTLE_SECONDS="20"
HEALTH_URL="http://127.0.0.1/healthz"
CANARY_HEADER_NAME="X-Vd-Canary"
CANARY_HEADER_VALUE="always"
ROUTING_SNIPPET_PATH="/etc/nginx/snippets/vd.canary-routing.conf"
RELOAD_COMMAND="sudo nginx -t && sudo systemctl reload nginx"
DRY_RUN="0"

usage() {
  cat <<'USAGE'
Usage: scripts/deploy/canary_rollout.sh [--target <0-50>] [--step <1-50>] [--settle-seconds <n>] [--health-url <url>] [--routing-snippet <path>] [--dry-run <0|1>]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET_WEIGHT="${2:-}"
      shift 2
      ;;
    --step)
      STEP_WEIGHT="${2:-}"
      shift 2
      ;;
    --settle-seconds)
      SETTLE_SECONDS="${2:-}"
      shift 2
      ;;
    --health-url)
      HEALTH_URL="${2:-}"
      shift 2
      ;;
    --routing-snippet)
      ROUTING_SNIPPET_PATH="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[$SCRIPT_NAME] unknown arg: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

for v in "$TARGET_WEIGHT" "$STEP_WEIGHT" "$SETTLE_SECONDS"; do
  if ! [[ "$v" =~ ^[0-9]+$ ]]; then
    echo "[$SCRIPT_NAME] numeric args must be integers" >&2
    exit 2
  fi
done
if (( TARGET_WEIGHT < 0 || TARGET_WEIGHT > 50 )); then
  echo "[$SCRIPT_NAME] --target must be in [0,50]" >&2
  exit 2
fi
if (( STEP_WEIGHT <= 0 || STEP_WEIGHT > 50 )); then
  echo "[$SCRIPT_NAME] --step must be in [1,50]" >&2
  exit 2
fi

log() {
  printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2
}

render_routing_snippet() {
  local weight="$1"
  cat <<ROUTE
map \$http_x_vd_canary \$vd_force_canary {
    default 0;
    "1" 1;
    "true" 1;
    "always" 1;
}

split_clients "\${remote_addr}\${http_user_agent}" \$vd_canary_bucket {
    ${weight}% "canary";
    * "stable";
}

map "\$vd_force_canary:\$vd_canary_bucket" \$vd_api_upstream {
    "1:stable" "vd_api_canary";
    "1:canary" "vd_api_canary";
    "0:canary" "vd_api_canary";
    default "vd_api_stable";
}
ROUTE
}

write_snippet() {
  local weight="$1"
  local tmp
  tmp="$(mktemp)"
  render_routing_snippet "$weight" > "$tmp"

  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY_RUN=1 rendered routing snippet with weight=${weight}%"
    cat "$tmp"
    rm -f "$tmp"
    return 0
  fi

  install -m 0644 "$tmp" "$ROUTING_SNIPPET_PATH"
  rm -f "$tmp"
  eval "$RELOAD_COMMAND"
  log "applied canary weight=${weight}%"
}

health_check() {
  curl -fsS --max-time 8 "$HEALTH_URL" >/dev/null
  curl -fsS --max-time 8 -H "$CANARY_HEADER_NAME: $CANARY_HEADER_VALUE" "$HEALTH_URL" >/dev/null
}

rollback_zero() {
  log "health check failed, rolling back canary traffic to 0%"
  write_snippet 0
}

current_weight=0
if [[ -f "$ROUTING_SNIPPET_PATH" ]]; then
  parsed="$(python3 - "$ROUTING_SNIPPET_PATH" <<'PY'
import re
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding='utf-8')
m = re.search(r'\n\s*(\d+)%\s+"canary";', text)
print(m.group(1) if m else '0')
PY
)"
  if [[ "$parsed" =~ ^[0-9]+$ ]]; then
    current_weight="$parsed"
  fi
fi

log "start canary rollout: current=${current_weight}% target=${TARGET_WEIGHT}% step=${STEP_WEIGHT}%"

if (( TARGET_WEIGHT == current_weight )); then
  log "target already reached"
  exit 0
fi

direction=1
if (( TARGET_WEIGHT < current_weight )); then
  direction=-1
fi

next_weight="$current_weight"
while (( next_weight != TARGET_WEIGHT )); do
  next_weight=$(( next_weight + direction * STEP_WEIGHT ))
  if (( direction == 1 && next_weight > TARGET_WEIGHT )); then
    next_weight="$TARGET_WEIGHT"
  fi
  if (( direction == -1 && next_weight < TARGET_WEIGHT )); then
    next_weight="$TARGET_WEIGHT"
  fi

  write_snippet "$next_weight"
  if [[ "$DRY_RUN" == "1" ]]; then
    continue
  fi

  sleep "$SETTLE_SECONDS"
  if ! health_check; then
    rollback_zero
    exit 1
  fi
  log "health check passed at weight=${next_weight}%"
done

log "canary rollout completed at weight=${TARGET_WEIGHT}%"
