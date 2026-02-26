#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="upstream_sync"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

DRY_RUN=1
ALLOW_DIRTY=0
ALLOW_MAIN=0
SQUASH=1

VENDOR=""
UPSTREAM_URL=""
UPSTREAM_REF=""
PREFIX=""
UPSTREAM_REMOTE=""
LOCK_FILE=""
SYNC_ACTOR=""

log() {
  printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2
}

fail() {
  log "ERROR: $*"
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  scripts/vendor/upstream_sync.sh \
    --vendor <name> \
    --upstream-url <git_url> \
    --upstream-ref <tag|branch|sha> \
    --prefix vendor/<name> \
    [--upstream-remote <remote_name>] \
    [--lock-file <path/to/UPSTREAM.lock>] \
    [--sync-actor <actor>] \
    [--no-squash] \
    [--allow-dirty] \
    [--allow-main] \
    [--dry-run|--execute]

Examples:
  scripts/vendor/upstream_sync.sh \
    --vendor yt-dlp \
    --upstream-url https://github.com/yt-dlp/yt-dlp.git \
    --upstream-ref refs/tags/2026.01.01 \
    --prefix vendor/yt-dlp \
    --dry-run

  scripts/vendor/upstream_sync.sh \
    --vendor yt-dlp \
    --upstream-url git@github.com:your-org/yt-dlp.git \
    --upstream-ref refs/heads/main \
    --prefix vendor/yt-dlp \
    --execute
EOF
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

run_cmd() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[%s] [dry-run] ' "$SCRIPT_NAME" >&2
    printf '%q ' "$@" >&2
    printf '\n' >&2
    return 0
  fi
  "$@"
}

validate_inputs() {
  [[ -n "$VENDOR" ]] || fail "--vendor is required"
  [[ -n "$UPSTREAM_URL" ]] || fail "--upstream-url is required"
  [[ -n "$UPSTREAM_REF" ]] || fail "--upstream-ref is required"
  [[ -n "$PREFIX" ]] || fail "--prefix is required"

  [[ "$VENDOR" =~ ^[A-Za-z0-9._-]+$ ]] || fail "--vendor has invalid characters: $VENDOR"
  [[ "$UPSTREAM_URL" =~ ^(https://|git@).+ ]] || fail "--upstream-url must start with https:// or git@"
  [[ "$UPSTREAM_REF" =~ ^[A-Za-z0-9._/\-]+$ ]] || fail "--upstream-ref contains invalid characters: $UPSTREAM_REF"
  [[ "$PREFIX" =~ ^vendor/[A-Za-z0-9._/\-]+$ ]] || fail "--prefix must start with vendor/: $PREFIX"
  [[ "$PREFIX" != *".."* ]] || fail "--prefix cannot contain '..': $PREFIX"

  if [[ -z "$UPSTREAM_REMOTE" ]]; then
    UPSTREAM_REMOTE="upstream-${VENDOR//[^A-Za-z0-9._-]/-}"
  fi
  [[ "$UPSTREAM_REMOTE" =~ ^[A-Za-z0-9._-]+$ ]] || fail "--upstream-remote has invalid characters: $UPSTREAM_REMOTE"

  if [[ -z "$LOCK_FILE" ]]; then
    LOCK_FILE="${PREFIX}/UPSTREAM.lock"
  fi
  [[ "$LOCK_FILE" =~ UPSTREAM\.lock$ ]] || fail "--lock-file must end with UPSTREAM.lock: $LOCK_FILE"
}

ensure_git_safety() {
  git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "not a git repository: $ROOT_DIR"
  local current_branch
  current_branch="$(git -C "$ROOT_DIR" branch --show-current)"
  if [[ "$ALLOW_MAIN" -eq 0 && ( "$current_branch" == "main" || "$current_branch" == "master" ) ]]; then
    fail "refuse to run on protected branch '$current_branch' (use --allow-main to bypass)"
  fi

  if [[ "$ALLOW_DIRTY" -eq 0 ]]; then
    if [[ -n "$(git -C "$ROOT_DIR" status --porcelain)" ]]; then
      fail "working tree is not clean; commit/stash changes or use --allow-dirty"
    fi
  fi
}

render_lock_content() {
  local upstream_commit="$1"
  local timestamp_utc="$2"
  local squash_value="true"
  [[ "$SQUASH" -eq 1 ]] || squash_value="false"
  cat <<EOF
schema_version: 1
vendor: $VENDOR
upstream_repo: $UPSTREAM_URL
upstream_ref: $UPSTREAM_REF
upstream_commit: $upstream_commit
subtree_prefix: $PREFIX
sync_strategy: subtree
sync_timestamp_utc: $timestamp_utc
sync_actor: $SYNC_ACTOR
squash: $squash_value
EOF
}

print_command_templates() {
  local subtree_cmd
  subtree_cmd="git subtree pull --prefix $PREFIX $UPSTREAM_REMOTE $UPSTREAM_REF"
  if [[ "$SQUASH" -eq 1 ]]; then
    subtree_cmd="$subtree_cmd --squash"
  fi

  cat <<EOF
[$SCRIPT_NAME] Command template:
  git remote add $UPSTREAM_REMOTE $UPSTREAM_URL
  git fetch --tags $UPSTREAM_REMOTE $UPSTREAM_REF
  $subtree_cmd
  bash scripts/vendor/validate_upstream_lock.sh --file $LOCK_FILE
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --vendor) VENDOR="${2:-}"; shift 2 ;;
      --upstream-url) UPSTREAM_URL="${2:-}"; shift 2 ;;
      --upstream-ref) UPSTREAM_REF="${2:-}"; shift 2 ;;
      --prefix) PREFIX="${2:-}"; shift 2 ;;
      --upstream-remote) UPSTREAM_REMOTE="${2:-}"; shift 2 ;;
      --lock-file) LOCK_FILE="${2:-}"; shift 2 ;;
      --sync-actor) SYNC_ACTOR="${2:-}"; shift 2 ;;
      --dry-run) DRY_RUN=1; shift ;;
      --execute) DRY_RUN=0; shift ;;
      --no-squash) SQUASH=0; shift ;;
      --allow-dirty) ALLOW_DIRTY=1; shift ;;
      --allow-main) ALLOW_MAIN=1; shift ;;
      -h|--help) usage; exit 0 ;;
      *) fail "unknown argument: $1 (use --help)" ;;
    esac
  done
}

main() {
  parse_args "$@"
  validate_inputs

  require_cmd git
  require_cmd date

  if [[ -z "$SYNC_ACTOR" ]]; then
    SYNC_ACTOR="${GITHUB_ACTOR:-$(git -C "$ROOT_DIR" config user.name || true)}"
  fi
  [[ -n "$SYNC_ACTOR" ]] || SYNC_ACTOR="unknown"

  ensure_git_safety
  print_command_templates

  cd "$ROOT_DIR"
  if git remote get-url "$UPSTREAM_REMOTE" >/dev/null 2>&1; then
    run_cmd git remote set-url "$UPSTREAM_REMOTE" "$UPSTREAM_URL"
  else
    run_cmd git remote add "$UPSTREAM_REMOTE" "$UPSTREAM_URL"
  fi
  run_cmd git fetch --tags "$UPSTREAM_REMOTE" "$UPSTREAM_REF"

  local subtree_cmd=(git subtree pull --prefix "$PREFIX" "$UPSTREAM_REMOTE" "$UPSTREAM_REF")
  [[ "$SQUASH" -eq 1 ]] && subtree_cmd+=(--squash)
  run_cmd "${subtree_cmd[@]}"

  local upstream_commit="<resolved-after-fetch>"
  if [[ "$DRY_RUN" -eq 0 ]]; then
    upstream_commit="$(git rev-parse --verify FETCH_HEAD)"
  fi
  local timestamp_utc
  timestamp_utc="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "[dry-run] would write lock file: $LOCK_FILE"
    render_lock_content "$upstream_commit" "$timestamp_utc" >&2
    return 0
  fi

  mkdir -p "$(dirname "$LOCK_FILE")"
  render_lock_content "$upstream_commit" "$timestamp_utc" >"$LOCK_FILE"
  log "updated lock file: $LOCK_FILE"
  log "next: bash scripts/vendor/validate_upstream_lock.sh --file $LOCK_FILE"
}

main "$@"
