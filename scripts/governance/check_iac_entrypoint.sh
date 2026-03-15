#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

has_devcontainer=0
has_compose=0
has_nix=0

if [[ -f ".devcontainer/devcontainer.json" ]]; then
  has_devcontainer=1
fi

if ls infra/compose/*.compose.yml >/dev/null 2>&1; then
  has_compose=1
fi

if [[ -f "flake.nix" || -f "shell.nix" || -f "default.nix" ]]; then
  has_nix=1
fi

if (( has_devcontainer == 0 && has_compose == 0 && has_nix == 0 )); then
  echo "[iac-entrypoint] FAIL: missing standard IaC entrypoint (devcontainer/compose/nix)." >&2
  exit 1
fi

if (( has_compose == 1 )) && [[ ! -f "infra/compose/core-services.compose.yml" ]]; then
  echo "[iac-entrypoint] FAIL: compose detected but infra/compose/core-services.compose.yml missing." >&2
  exit 1
fi

echo "[iac-entrypoint] PASS: devcontainer=${has_devcontainer} compose=${has_compose} nix=${has_nix}"
