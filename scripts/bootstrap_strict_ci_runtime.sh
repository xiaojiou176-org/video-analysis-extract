#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

is_linux_arm64() {
  local kernel machine
  kernel="$(uname -s)"
  machine="$(uname -m)"
  [[ "$kernel" == "Linux" && ( "$machine" == "aarch64" || "$machine" == "arm64" ) ]]
}

configure_strict_ci_python_environment() {
  local platform_id env_root repo_hash env_dir
  platform_id="$(uname -s)-$(uname -m)"
  env_root="${TMPDIR:-/tmp}"
  repo_hash="$(
    python3 - "$ROOT_DIR" <<'PY'
import hashlib
import sys

print(hashlib.sha256(sys.argv[1].encode("utf-8")).hexdigest()[:12])
PY
  )"
  env_dir="${UV_PROJECT_ENVIRONMENT:-${env_root%/}/video-digestor-strict-ci/${repo_hash}/${platform_id}}"
  export UV_PROJECT_ENVIRONMENT="$env_dir"
  export VIRTUAL_ENV="$env_dir"
  export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
  case ":$PATH:" in
    *":$env_dir/bin:"*) ;;
    *) export PATH="$env_dir/bin:$PATH" ;;
  esac
}

read_web_locked_version() {
  local package_name="$1"
  python3 - "$package_name" <<'PY'
import json
import sys
from pathlib import Path

lockfile = Path("apps/web/package-lock.json")
packages = json.loads(lockfile.read_text(encoding="utf-8")).get("packages", {})
version = packages.get(f"node_modules/{sys.argv[1]}", {}).get("version", "")
if not version:
    raise SystemExit(f"missing locked version for {sys.argv[1]}")
print(version)
PY
}

web_node_modules_ready() {
  [[ -d "apps/web/node_modules" ]] || return 1
  [[ -x "apps/web/node_modules/.bin/eslint" ]] || return 1

  (
    cd apps/web
    node <<'EOF'
const fs = require("fs");
const checks = [
  () => require.resolve("eslint/package.json"),
  () => require.resolve("eslint-visitor-keys/package.json"),
  () => require("eslint"),
  () => {
    if (process.platform === "linux" && process.arch === "arm64") {
      if (!fs.existsSync("node_modules/@rollup/rollup-linux-arm64-gnu/rollup.linux-arm64-gnu.node")) {
        throw new Error("missing @rollup/rollup-linux-arm64-gnu native binary");
      }
      if (!fs.existsSync("node_modules/lightningcss/lightningcss.linux-arm64-gnu.node")) {
        throw new Error("missing lightningcss linux arm64 native binary");
      }
    }
  },
];

for (const check of checks) {
  try {
    check();
  } catch (error) {
    process.stderr.write(`[bootstrap_strict_ci_runtime] invalid apps/web/node_modules: ${error.message}\n`);
    process.exit(1);
  }
}
EOF
  )
}

ensure_web_arm64_native_optional_deps() {
  if ! is_linux_arm64; then
    return
  fi

  local -a missing_packages=()
  local -a install_specs=()
  local version

  if [[ ! -f "apps/web/node_modules/@rollup/rollup-linux-arm64-gnu/rollup.linux-arm64-gnu.node" ]]; then
    missing_packages+=("@rollup/rollup-linux-arm64-gnu")
  fi
  if [[ ! -f "apps/web/node_modules/lightningcss/lightningcss.linux-arm64-gnu.node" ]]; then
    missing_packages+=("lightningcss-linux-arm64-gnu")
  fi

  if [[ ${#missing_packages[@]} -eq 0 ]]; then
    return
  fi

  printf '[bootstrap_strict_ci_runtime] repairing linux-arm64 optional deps: %s\n' "${missing_packages[*]}" >&2
  for package_name in "${missing_packages[@]}"; do
    version="$(read_web_locked_version "$package_name")"
    install_specs+=("${package_name}@${version}")
  done

  npm --prefix apps/web install --no-save --no-package-lock --include=optional --ignore-scripts=false "${install_specs[@]}"

  if [[ -f "apps/web/node_modules/lightningcss-linux-arm64-gnu/lightningcss.linux-arm64-gnu.node" ]]; then
    cp \
      "apps/web/node_modules/lightningcss-linux-arm64-gnu/lightningcss.linux-arm64-gnu.node" \
      "apps/web/node_modules/lightningcss/lightningcss.linux-arm64-gnu.node"
  fi

  [[ -f "apps/web/node_modules/@rollup/rollup-linux-arm64-gnu/rollup.linux-arm64-gnu.node" ]]
  [[ -f "apps/web/node_modules/lightningcss/lightningcss.linux-arm64-gnu.node" ]]
}

install_web_npm_wrapper() {
  if ! is_linux_arm64; then
    return
  fi

  local real_npm wrapper_dir wrapper_path
  real_npm="$(command -v npm)"
  wrapper_dir="$ROOT_DIR/.runtime-cache/strict-ci-bin"
  wrapper_path="$wrapper_dir/npm"
  mkdir -p "$wrapper_dir"

  cat >"$wrapper_path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

real_npm="${STRICT_CI_REAL_NPM:?}"
"$real_npm" "$@"

if [[ "${STRICT_CI_WEB_NATIVE_REPAIR_ACTIVE:-0}" == "1" ]]; then
  exit 0
fi

prefix=""
command_name=""
args=("$@")
index=0
while [[ $index -lt ${#args[@]} ]]; do
  current="${args[$index]}"
  if [[ "$current" == "--prefix" ]]; then
    index=$((index + 1))
    if [[ $index -lt ${#args[@]} ]]; then
      prefix="${args[$index]}"
    fi
    index=$((index + 1))
    continue
  fi
  command_name="$current"
  break
done

if [[ "$prefix" == "apps/web" && ( "$command_name" == "ci" || "$command_name" == "install" ) ]]; then
  (
    export STRICT_CI_WEB_NATIVE_REPAIR_ACTIVE=1
    export STRICT_CI_BOOTSTRAP_LOAD_HELPERS_ONLY=1
    cd "${STRICT_CI_ROOT_DIR:?}"
    source "${STRICT_CI_BOOTSTRAP_SCRIPT:?}"
    ensure_web_arm64_native_optional_deps
  )
fi
EOF
  chmod +x "$wrapper_path"
  export STRICT_CI_REAL_NPM="$real_npm"
  export STRICT_CI_ROOT_DIR="$ROOT_DIR"
  export STRICT_CI_BOOTSTRAP_SCRIPT="$ROOT_DIR/scripts/bootstrap_strict_ci_runtime.sh"
  export PATH="$wrapper_dir:$PATH"
  export STRICT_CI_BOOTSTRAP_RUNTIME_READY=1
}

if [[ "${STRICT_CI_BOOTSTRAP_LOAD_HELPERS_ONLY:-0}" != "1" ]]; then
  mkdir -p .runtime-cache
  export DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:///:memory:}"
  export TEMPORAL_TARGET_HOST="${TEMPORAL_TARGET_HOST:-127.0.0.1:7233}"
  export TEMPORAL_NAMESPACE="${TEMPORAL_NAMESPACE:-default}"
  export TEMPORAL_TASK_QUEUE="${TEMPORAL_TASK_QUEUE:-video-analysis-worker}"
  export SQLITE_STATE_PATH="${SQLITE_STATE_PATH:-/tmp/video-digestor-strict-api.db}"
  export SQLITE_PATH="${SQLITE_PATH:-/tmp/video-digestor-strict-worker.db}"
  configure_strict_ci_python_environment
  install_web_npm_wrapper
  uv sync --frozen --extra dev --extra e2e

  platform_id="$(uname -s)-$(uname -m)"
  web_hash_file=".runtime-cache/strict-ci-web-${platform_id}.sha256"
  web_hash="$(
    {
      sha256sum apps/web/package-lock.json
      sha256sum apps/web/package.json
      printf '%s\n' "$platform_id"
    } | sha256sum | awk '{print $1}'
  )"
  existing_web_hash=""
  if [[ -f "$web_hash_file" ]]; then
    existing_web_hash="$(cat "$web_hash_file" 2>/dev/null || true)"
  fi

  if ! web_node_modules_ready || [[ "$existing_web_hash" != "$web_hash" ]]; then
    rm -rf apps/web/node_modules
    export npm_config_jobs="${npm_config_jobs:-1}"
    npm --prefix apps/web ci --no-audit --no-fund
    ensure_web_arm64_native_optional_deps
    web_node_modules_ready
    printf '%s' "$web_hash" > "$web_hash_file"
  fi
fi
