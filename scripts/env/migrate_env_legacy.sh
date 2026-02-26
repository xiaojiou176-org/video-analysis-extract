#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="migrate_env_legacy"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_PATH="${1:-$ROOT_DIR/env/profiles/reader.env}"

log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2; }

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

mkdir -p "$(dirname "$TARGET_PATH")"

if [[ ! -f "$TARGET_PATH" ]]; then
  cp "$ROOT_DIR/env/profiles/reader.env" "$TARGET_PATH" 2>/dev/null || true
fi

tmp_vars="$(mktemp)"
extract_reader_vars_from "$ROOT_DIR/.env.local" "$tmp_vars"
extract_reader_vars_from "$ROOT_DIR/.env.bak" "$tmp_vars"

if [[ ! -s "$tmp_vars" ]]; then
  rm -f "$tmp_vars"
  log "No reader variables found in .env.local/.env.bak; nothing to migrate."
  exit 0
fi

# Merge strategy: source files (.env.local/.env.bak) override existing target keys.
TARGET_PATH="$TARGET_PATH" TMP_VARS="$tmp_vars" python3 - <<'PY'
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
existing_lines = target.read_text(encoding="utf-8").splitlines() if target.exists() else []
existing = parse_env(target)
updates = parse_env(tmp_vars)
reader_updates = {
    k: v
    for k, v in updates.items()
    if k.startswith("MINIFLUX_") or k == "NEXTFLUX_PORT"
}
merged = {**existing, **reader_updates}
dump_env(target, existing_lines, merged)
PY

rm -f "$tmp_vars"
log "Migrated reader variables into: $TARGET_PATH"
log "Legacy files were preserved: .env.local / .env.bak"
