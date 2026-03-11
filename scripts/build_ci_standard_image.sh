#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PUSH_IMAGE="0"
LOAD_IMAGE="0"
TAG_OVERRIDE=""
PLATFORMS="${VD_STANDARD_ENV_BUILD_PLATFORMS:-linux/amd64}"

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
  buildx build
  --platform "$PLATFORMS"
  --file "$STRICT_CI_STANDARD_IMAGE_DOCKERFILE"
  --tag "${image_repository}:${image_tag}"
)

if [[ "$PUSH_IMAGE" == "1" ]]; then
  docker_args+=(--push)
fi
if [[ "$LOAD_IMAGE" == "1" ]]; then
  docker_args+=(--load)
fi

docker_args+=("${build_args[@]}" "$ROOT_DIR")

docker "${docker_args[@]}"
