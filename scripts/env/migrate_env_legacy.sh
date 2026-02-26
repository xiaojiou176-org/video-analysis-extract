#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="migrate_env_legacy"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_PATH="$ROOT_DIR/env/profiles/reader.env"

usage() {
  cat <<'USAGE'
Usage: bash scripts/env/migrate_env_legacy.sh [--target <path>]

Migrate reader-related legacy variables from:
  .env.local, .env.bak
into:
  env/profiles/reader.env (default target)

Examples:
  bash scripts/env/migrate_env_legacy.sh
  bash scripts/env/migrate_env_legacy.sh --target env/profiles/reader.env
USAGE
}

log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2; }
heartbeat() { printf '[%s] heartbeat: %s\n' "$SCRIPT_NAME" "$*" >&2; }
die() { printf '[%s] error: %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET_PATH="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -z "${TARGET_PATH:-}" || "$TARGET_PATH" == "$ROOT_DIR/env/profiles/reader.env" ]]; then
        TARGET_PATH="$1"
        shift
      else
        die "unknown argument: $1 (run --help for usage)"
      fi
      ;;
  esac
done

[[ -n "${TARGET_PATH:-}" ]] || die "target path is empty."

extract_reader_vars_from() {
  local source_file="$1"
  local tmp_out="$2"
  if [[ ! -f "$source_file" ]]; then
    return 0
  fi

  awk '
    /^[[:space:]]*(export[[:space:]]+)?MINIFLUX_[A-Z0-9_]*[[:space:]]*=/ { print; next }
    /^[[:space:]]*(export[[:space:]]+)?NEXTFLUX_PORT[[:space:]]*=/ { print; next }
  ' "$source_file" \
    | sed -E 's/^[[:space:]]*export[[:space:]]+//' \
    >> "$tmp_out"
}

heartbeat "phase 1/3 scanning legacy files"
mkdir -p "$(dirname "$TARGET_PATH")"

if [[ ! -f "$TARGET_PATH" ]]; then
  cp "$ROOT_DIR/env/profiles/reader.env" "$TARGET_PATH" 2>/dev/null || true
fi

tmp_vars="$(mktemp)"
extract_reader_vars_from "$ROOT_DIR/.env.local" "$tmp_vars"
extract_reader_vars_from "$ROOT_DIR/.env.bak" "$tmp_vars"

scanned_sources=()
[[ -f "$ROOT_DIR/.env.local" ]] && scanned_sources+=(".env.local")
[[ -f "$ROOT_DIR/.env.bak" ]] && scanned_sources+=(".env.bak")

if [[ ! -s "$tmp_vars" ]]; then
  rm -f "$tmp_vars"
  log "No reader variables found in legacy files; nothing to migrate."
  log "summary: target=$TARGET_PATH, scanned_sources=${scanned_sources[*]:-none}, migrated_keys=0"
  log "risk hint: legacy files are preserved; stale values may continue to drift from .env/.env.reader-stack."
  exit 0
fi

# Merge strategy: source files (.env.local/.env.bak) override existing target keys.
heartbeat "phase 2/3 merging keys into target profile"
tmp_summary="$(mktemp)"
TARGET_PATH="$TARGET_PATH" TMP_VARS="$tmp_vars" SUMMARY_PATH="$tmp_summary" python3 - <<'PY'
import os
from pathlib import Path


def parse_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        data[key] = value.strip()
    return data


def dump_env(path: Path, original_lines: list[str], merged: dict[str, str]) -> None:
    kept: list[str] = []
    seen: set[str] = set()
    for raw in original_lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            kept.append(raw)
            continue
        line = stripped
        if line.startswith("export "):
            line = line[len("export "):]
        key = line.split("=", 1)[0].strip()
        if key in merged and key not in seen:
            kept.append(f"{key}={merged[key]}")
            seen.add(key)
        elif key not in merged:
            kept.append(raw)

    for key, value in sorted(merged.items()):
        if key not in seen:
            kept.append(f"{key}={value}")

    path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")


target = Path(os.environ["TARGET_PATH"])
tmp_vars = Path(os.environ["TMP_VARS"])
summary_path = Path(os.environ["SUMMARY_PATH"])
existing_lines = target.read_text(encoding="utf-8").splitlines() if target.exists() else []
existing = parse_env(target)
updates = parse_env(tmp_vars)
reader_updates = {
    k: v
    for k, v in updates.items()
    if k.startswith("MINIFLUX_") or k == "NEXTFLUX_PORT"
}
merged = {**existing, **reader_updates}
updated_existing = sorted([k for k in reader_updates if k in existing])
added_new = sorted([k for k in reader_updates if k not in existing])
dump_env(target, existing_lines, merged)
summary_path.write_text(
    "\n".join(
        [
            f"total={len(reader_updates)}",
            f"updated_existing={len(updated_existing)}",
            f"added_new={len(added_new)}",
            f"keys={','.join(sorted(reader_updates.keys()))}",
        ]
    )
    + "\n",
    encoding="utf-8",
)
PY

rm -f "$tmp_vars"
heartbeat "phase 3/3 migration completed"
summary_total="$(sed -n 's/^total=//p' "$tmp_summary")"
summary_updated="$(sed -n 's/^updated_existing=//p' "$tmp_summary")"
summary_added="$(sed -n 's/^added_new=//p' "$tmp_summary")"
summary_keys="$(sed -n 's/^keys=//p' "$tmp_summary")"
rm -f "$tmp_summary"

log "Migrated reader variables into: $TARGET_PATH"
log "summary: scanned_sources=${scanned_sources[*]:-none}, migrated_keys=${summary_total:-0}, updated_existing=${summary_updated:-0}, added_new=${summary_added:-0}"
log "summary keys: ${summary_keys:-none}"
log "Legacy files were preserved: .env.local / .env.bak"
log "risk hint: migration is additive and keeps legacy files untouched; ensure runtime now loads .env/.env.reader-stack instead of legacy files."
log "next step: bash scripts/env/validate_profile.sh --profile local"
