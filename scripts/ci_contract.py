#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = REPO_ROOT / "infra" / "config" / "strict_ci_contract.json"


def load_contract(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(contract: dict[str, Any], path: str) -> Any:
    current: Any = contract
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def standard_image_ref(contract: dict[str, Any]) -> str:
    image = contract["standard_image"]
    digest = str(image.get("digest", "") or "").strip()
    if digest:
        return f'{image["repository"]}@{digest}'
    return f'{image["repository"]}:{image["tag"]}'


def shell_exports(contract: dict[str, Any]) -> str:
    image = contract["standard_image"]
    toolchain = contract["toolchain"]
    quality = contract["quality"]
    cache = contract["cache"]
    payload = {
        "STRICT_CI_CONTRACT_PATH": str(DEFAULT_CONTRACT_PATH),
        "STRICT_CI_STANDARD_IMAGE_REPOSITORY": image["repository"],
        "STRICT_CI_STANDARD_IMAGE_TAG": image["tag"],
        "STRICT_CI_STANDARD_IMAGE_DIGEST": image.get("digest", ""),
        "STRICT_CI_STANDARD_IMAGE_REF": standard_image_ref(contract),
        "STRICT_CI_STANDARD_IMAGE_DOCKERFILE": image["dockerfile"],
        "STRICT_CI_STANDARD_IMAGE_WORKDIR": image["workdir"],
        "STRICT_CI_PYTHON_VERSION": toolchain["python_version"],
        "STRICT_CI_UV_VERSION": toolchain["uv_version"],
        "STRICT_CI_NODE_MAJOR": toolchain["node_major"],
        "STRICT_CI_TEMPORAL_CLI_VERSION": toolchain["temporal_cli_version"],
        "STRICT_CI_TEMPORAL_CLI_SHA256_LINUX_AMD64": toolchain["temporal_cli_sha256_linux_amd64"],
        "STRICT_CI_TEMPORAL_CLI_SHA256_LINUX_ARM64": toolchain["temporal_cli_sha256_linux_arm64"],
        "STRICT_CI_MUTATION_MIN_SCORE": str(quality["mutation_min_score"]),
        "STRICT_CI_MUTATION_MIN_EFFECTIVE_RATIO": str(quality["mutation_min_effective_ratio"]),
        "STRICT_CI_MUTATION_MAX_NO_TESTS_RATIO": str(quality["mutation_max_no_tests_ratio"]),
        "STRICT_CI_COVERAGE_MIN": str(quality["coverage_min"]),
        "STRICT_CI_CORE_COVERAGE_MIN": str(quality["core_coverage_min"]),
        "STRICT_CI_WEB_BUTTON_COMBINED_THRESHOLD": str(quality["web_button_combined_threshold"]),
        "STRICT_CI_WEB_BUTTON_E2E_THRESHOLD": str(quality["web_button_e2e_threshold"]),
        "STRICT_CI_WEB_BUTTON_UNIT_THRESHOLD": str(quality["web_button_unit_threshold"]),
        "STRICT_CI_CACHE_ROOT": cache["root"],
        "STRICT_CI_UV_CACHE_DIR": cache["uv"],
        "STRICT_CI_PLAYWRIGHT_BROWSERS_PATH": cache["playwright"],
        "STRICT_CI_PRE_COMMIT_HOME": cache["pre_commit"],
        "STRICT_CI_PROFILE_GOVERNANCE_PUSH_RELEASE": "1" if contract["trigger_policy"]["profile_governance_push_release"] else "0",
        "STRICT_CI_LIVE_SMOKE_PUSH_RELEASE": "1" if contract["trigger_policy"]["live_smoke_push_release"] else "0",
        "STRICT_CI_LIVE_SMOKE_SCHEDULE_CRON": contract["trigger_policy"]["live_smoke_schedule_cron"],
    }
    return "\n".join(
        f"export {key}={shlex.quote(value)}" for key, value in payload.items()
    )


def github_outputs(contract: dict[str, Any]) -> str:
    image = contract["standard_image"]
    toolchain = contract["toolchain"]
    quality = contract["quality"]
    cache = contract["cache"]
    outputs = {
        "standard_image_repository": image["repository"],
        "standard_image_tag": image["tag"],
        "standard_image_digest": image.get("digest", ""),
        "standard_image_ref": standard_image_ref(contract),
        "standard_image_workdir": image["workdir"],
        "standard_image_dockerfile": image["dockerfile"],
        "python_version": toolchain["python_version"],
        "uv_version": toolchain["uv_version"],
        "node_major": toolchain["node_major"],
        "temporal_cli_version": toolchain["temporal_cli_version"],
        "temporal_cli_sha256_linux_amd64": toolchain["temporal_cli_sha256_linux_amd64"],
        "temporal_cli_sha256_linux_arm64": toolchain["temporal_cli_sha256_linux_arm64"],
        "mutation_min_score": str(quality["mutation_min_score"]),
        "mutation_min_effective_ratio": str(quality["mutation_min_effective_ratio"]),
        "mutation_max_no_tests_ratio": str(quality["mutation_max_no_tests_ratio"]),
        "coverage_min": str(quality["coverage_min"]),
        "core_coverage_min": str(quality["core_coverage_min"]),
        "web_button_combined_threshold": str(quality["web_button_combined_threshold"]),
        "web_button_e2e_threshold": str(quality["web_button_e2e_threshold"]),
        "web_button_unit_threshold": str(quality["web_button_unit_threshold"]),
        "cache_root": cache["root"],
        "uv_cache_dir": cache["uv"],
        "playwright_browsers_path": cache["playwright"],
        "pre_commit_home": cache["pre_commit"],
        "profile_governance_push_release": "true" if contract["trigger_policy"]["profile_governance_push_release"] else "false",
        "live_smoke_push_release": "true" if contract["trigger_policy"]["live_smoke_push_release"] else "false",
        "live_smoke_schedule_cron": contract["trigger_policy"]["live_smoke_schedule_cron"],
    }
    return "\n".join(f"{key}={value}" for key, value in outputs.items())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract",
        type=Path,
        default=DEFAULT_CONTRACT_PATH,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("path")

    subparsers.add_parser("image-ref")
    subparsers.add_parser("shell-exports")
    subparsers.add_parser("github-outputs")

    args = parser.parse_args()
    contract = load_contract(args.contract)

    if args.command == "get":
        value = resolve_path(contract, args.path)
        if isinstance(value, (dict, list)):
            json.dump(value, sys.stdout, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            print(value)
        return 0
    if args.command == "image-ref":
        print(standard_image_ref(contract))
        return 0
    if args.command == "shell-exports":
        print(shell_exports(contract))
        return 0
    if args.command == "github-outputs":
        print(github_outputs(contract))
        return 0
    raise AssertionError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
