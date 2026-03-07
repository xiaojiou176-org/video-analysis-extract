#!/usr/bin/env bash
set -euo pipefail

log() { echo "[runner-org-only] $*"; }

REPO_PATTERN='actions.runner.xiaojiou176-org-ui-pressure-test-private.pool-*.service'
ORG_PATTERN='actions.runner.xiaojiou176-org.pool-*.service'
LEFTOVER_PATTERNS=(
  'Runner.Listener'
  'runsvc.sh'
  'Runner.Worker'
  'RunnerService.js'
)
WAIT_SECONDS="${RUNNER_STOP_WAIT_SECONDS:-20}"

list_units() {
  local pattern="$1"
  systemctl list-unit-files "$pattern" --no-legend 2>/dev/null | awk '{print $1}' || true
}

stop_units() {
  local units="$1"
  [[ -n "$units" ]] || return 0
  while IFS= read -r unit; do
    [[ -z "$unit" ]] && continue
    systemctl stop "$unit" || true
    systemctl disable "$unit" >/dev/null 2>&1 || true
  done <<<"$units"
}

enable_and_start_units() {
  local units="$1"
  [[ -n "$units" ]] || return 0
  while IFS= read -r unit; do
    [[ -z "$unit" ]] && continue
    systemctl reset-failed "$unit" >/dev/null 2>&1 || true
    systemctl enable "$unit" >/dev/null 2>&1 || true
    systemctl start "$unit"
  done <<<"$units"
}

kill_leftovers() {
  for pattern in "${LEFTOVER_PATTERNS[@]}"; do
    pkill -f "$pattern" || true
  done
}

wait_for_leftovers_to_exit() {
  local waited=0
  while (( waited < WAIT_SECONDS )); do
    local found=0
    for pattern in "${LEFTOVER_PATTERNS[@]}"; do
      if pgrep -f "$pattern" >/dev/null 2>&1; then
        found=1
        break
      fi
    done
    if (( found == 0 )); then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done

  log "left-over runner processes still present after ${WAIT_SECONDS}s, escalating to SIGKILL"
  for pattern in "${LEFTOVER_PATTERNS[@]}"; do
    pkill -9 -f "$pattern" || true
  done
}

main() {
  log "start: $(date -Is)"

  local repo_svcs org_svcs
  repo_svcs="$(list_units "$REPO_PATTERN")"
  org_svcs="$(list_units "$ORG_PATTERN")"

  stop_units "$repo_svcs"
  stop_units "$org_svcs"

  kill_leftovers
  wait_for_leftovers_to_exit

  if [[ -z "$org_svcs" ]]; then
    log "no org services found"
    exit 1
  fi

  enable_and_start_units "$org_svcs"
  sleep 5

  log "service snapshot"
  systemctl list-units "$ORG_PATTERN" --all --no-pager || true
  log "listener snapshot"
  pgrep -af 'runsvc.sh|Runner.Listener|RunnerService.js' || true
  log "done: $(date -Is)"
}

main "$@"
