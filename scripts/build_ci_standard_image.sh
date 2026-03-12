#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PUSH_IMAGE="0"
LOAD_IMAGE="0"
TAG_OVERRIDE=""
PLATFORMS="${VD_STANDARD_ENV_BUILD_PLATFORMS:-linux/amd64,linux/arm64}"

resolve_local_load_platform() {
  local arch="${VD_STANDARD_ENV_LOAD_PLATFORM_ARCH:-$(uname -m)}"
  case "$arch" in
    x86_64|amd64)
      printf 'linux/amd64\n'
      ;;
    arm64|aarch64)
      printf 'linux/arm64\n'
      ;;
    *)
      echo "[build-ci-standard-image] unsupported local load architecture: $arch" >&2
      exit 2
      ;;
  esac
}

usage() {
  cat <<'EOF'
Usage: ./scripts/build_ci_standard_image.sh [--push] [--load] [--tag <tag>]
EOF
}

while (($# > 0)); do
  case "$1" in
    --push)
      PUSH_IMAGE="1"
      shift
      ;;
    --load)
      LOAD_IMAGE="1"
      shift
      ;;
    --tag)
      TAG_OVERRIDE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[build-ci-standard-image] unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

eval "$(python3 scripts/ci_contract.py shell-exports)"

image_repository="$STRICT_CI_STANDARD_IMAGE_REPOSITORY"
image_tag="$STRICT_CI_STANDARD_IMAGE_TAG"
if [[ -n "$TAG_OVERRIDE" ]]; then
  image_tag="$TAG_OVERRIDE"
fi

build_args=(
  --build-arg "STRICT_CI_BASE_IMAGE=$(python3 scripts/ci_contract.py get toolchain.base_image)"
  --build-arg "STRICT_CI_NODE_MAJOR=$STRICT_CI_NODE_MAJOR"
  --build-arg "STRICT_CI_UV_VERSION=$STRICT_CI_UV_VERSION"
  --build-arg "STRICT_CI_TEMPORAL_CLI_VERSION=$STRICT_CI_TEMPORAL_CLI_VERSION"
  --build-arg "STRICT_CI_TEMPORAL_CLI_SHA256_LINUX_AMD64=$STRICT_CI_TEMPORAL_CLI_SHA256_LINUX_AMD64"
  --build-arg "STRICT_CI_TEMPORAL_CLI_SHA256_LINUX_ARM64=$STRICT_CI_TEMPORAL_CLI_SHA256_LINUX_ARM64"
)

docker_args=(
  --file "$STRICT_CI_STANDARD_IMAGE_DOCKERFILE"
  --tag "${image_repository}:${image_tag}"
)

if [[ "$LOAD_IMAGE" == "1" ]]; then
  PLATFORMS="$(resolve_local_load_platform)"
fi

if [[ "$PUSH_IMAGE" == "1" ]]; then
  docker_args=(buildx build "${docker_args[@]}")
  docker_args+=(--push --platform "$PLATFORMS")
elif [[ "$LOAD_IMAGE" == "1" ]]; then
  docker_args=(build "${docker_args[@]}")
  docker_args+=(--platform "$PLATFORMS")
else
  docker_args=(buildx build "${docker_args[@]}")
  docker_args+=(--platform "$PLATFORMS")
fi

docker_args+=("${build_args[@]}" "$ROOT_DIR")

docker "${docker_args[@]}"
