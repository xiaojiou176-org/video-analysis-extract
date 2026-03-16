#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

sys.dont_write_bytecode = True

from common import load_governance_json, repo_root, write_runtime_metadata


REQUIRED_FIELDS = {
    "name",
    "kind",
    "owner",
    "upgrade_owner",
    "source",
    "pin",
    "interface_type",
    "integration_surface",
    "how_introduced",
    "private_coupling_risk",
    "verification_suite",
    "rollback_path",
    "evidence_artifact",
    "license",
    "security_posture",
    "risk_class",
    "support_tier",
    "freshness_required_hours",
    "latest_verification_status",
    "latest_verification_age_hours",
    "contract_kind",
    "stability_class",
    "degradation_mode",
    "blame_surface",
    "owner_rotation",
}
KNOWN_KINDS = {"api", "image", "binary", "schema", "vendor", "fork", "patch"}
KNOWN_RISK_CLASSES = {"low", "medium", "high", "critical"}
KNOWN_SUPPORT_TIERS = {"tier-1", "tier-2", "tier-3"}
KNOWN_INTEGRATION_SURFACES = {"public_api", "public_cli", "public_schema", "public_image", "public_binary"}
KNOWN_PRIVATE_COUPLING_RISKS = {"none", "localized", "structural"}
KNOWN_VERIFICATION_STATUSES = {"declared", "verified", "pending", "waived"}
KNOWN_BLOCKING_LEVELS = {"blocker", "important", "enhancement"}
KNOWN_VERIFICATION_LANES = {"repo-side", "external", "provider"}
KNOWN_CONTRACT_KINDS = {"public-api-contract", "digest-pinned-image", "public-binary-contract", "vendor-contract"}
KNOWN_STABILITY_CLASSES = {"managed", "community-supported", "community-platform"}
KNOWN_BLAME_SURFACES = {"api-boundary", "runtime-image-boundary", "binary-boundary", "vendor-boundary"}
KNOWN_HOW_INTRODUCED = {
    "api",
    "image",
    "binary",
    "runtime_download",
    "vendor",
    "template_only",
    "environment_contract",
}


def main() -> int:
    root = repo_root()
    upstreams = load_governance_json("active-upstreams.json")
    templates = load_governance_json("upstream-templates.json")
    registry = load_governance_json("upstream-registry.json")
    matrix = load_governance_json("upstream-compat-matrix.json")
    strict_ci_contract = json.loads(
        (root / "infra" / "config" / "strict_ci_contract.json").read_text(encoding="utf-8")
    )

    errors: list[str] = []
    entries = upstreams.get("entries", [])
    template_entries = templates.get("entries", [])
    registry_active = {str(item) for item in registry.get("active", [])}
    registry_template = {str(item) for item in registry.get("template", [])}
    seen: set[str] = set()
    image_sources = set()
    for entry in entries:
        missing = sorted(REQUIRED_FIELDS - set(entry))
        if missing:
            errors.append(
                f"upstream entry {entry.get('name', '<unknown>')} missing fields: {', '.join(missing)}"
            )
            continue
        name = str(entry["name"])
        if name in seen:
            errors.append(f"duplicate upstream entry: {name}")
        seen.add(name)
        kind = str(entry["kind"])
        if kind not in KNOWN_KINDS:
            errors.append(f"upstream entry {name} uses unsupported kind `{kind}`")
        risk_class = str(entry["risk_class"])
        if risk_class not in KNOWN_RISK_CLASSES:
            errors.append(f"upstream entry {name} uses unsupported risk_class `{risk_class}`")
        support_tier = str(entry["support_tier"])
        if support_tier not in KNOWN_SUPPORT_TIERS:
            errors.append(f"upstream entry {name} uses unsupported support_tier `{support_tier}`")
        integration_surface = str(entry["integration_surface"])
        if integration_surface not in KNOWN_INTEGRATION_SURFACES:
            errors.append(f"upstream entry {name} uses unsupported integration_surface `{integration_surface}`")
        how_introduced = str(entry["how_introduced"])
        if how_introduced not in KNOWN_HOW_INTRODUCED:
            errors.append(f"upstream entry {name} uses unsupported how_introduced `{how_introduced}`")
        private_coupling_risk = str(entry["private_coupling_risk"])
        if private_coupling_risk not in KNOWN_PRIVATE_COUPLING_RISKS:
            errors.append(f"upstream entry {name} uses unsupported private_coupling_risk `{private_coupling_risk}`")
        contract_kind = str(entry["contract_kind"])
        if contract_kind not in KNOWN_CONTRACT_KINDS:
            errors.append(f"upstream entry {name} uses unsupported contract_kind `{contract_kind}`")
        stability_class = str(entry["stability_class"])
        if stability_class not in KNOWN_STABILITY_CLASSES:
            errors.append(f"upstream entry {name} uses unsupported stability_class `{stability_class}`")
        blame_surface = str(entry["blame_surface"])
        if blame_surface not in KNOWN_BLAME_SURFACES:
            errors.append(f"upstream entry {name} uses unsupported blame_surface `{blame_surface}`")
        freshness_required_hours = entry["freshness_required_hours"]
        if not isinstance(freshness_required_hours, int) or freshness_required_hours <= 0:
            errors.append(f"upstream entry {name} must declare positive freshness_required_hours")
        latest_verification_status = str(entry["latest_verification_status"])
        if latest_verification_status not in KNOWN_VERIFICATION_STATUSES:
            errors.append(f"upstream entry {name} uses unsupported latest_verification_status `{latest_verification_status}`")
        latest_verification_age_hours = entry["latest_verification_age_hours"]
        if not isinstance(latest_verification_age_hours, int) or latest_verification_age_hours < 0:
            errors.append(f"upstream entry {name} must declare non-negative latest_verification_age_hours")
        if latest_verification_status == "verified" and latest_verification_age_hours > freshness_required_hours:
            errors.append(
                f"upstream entry {name} claims verified but latest_verification_age_hours exceeds freshness_required_hours"
            )
        if not str(entry["degradation_mode"]).strip():
            errors.append(f"upstream entry {name} must declare non-empty degradation_mode")
        if not str(entry["owner_rotation"]).strip():
            errors.append(f"upstream entry {name} must declare non-empty owner_rotation")
        upgrade_owner = str(entry["upgrade_owner"]).strip()
        if not upgrade_owner:
            errors.append(f"upstream entry {name} must declare non-empty upgrade_owner")
        if kind == "image":
            source = str(entry["source"])
            if "@sha256:" not in source and "sha256:" not in str(entry["pin"]):
                errors.append(f"image upstream {name} must use digest pinning")
            image_sources.add(source)
        if kind == "binary":
            usage_patterns = entry.get("usage_patterns", [])
            if not isinstance(usage_patterns, list) or not usage_patterns:
                errors.append(f"binary upstream {name} must declare non-empty usage_patterns")
        evidence_artifact = str(entry["evidence_artifact"])
        if not evidence_artifact.startswith(".runtime-cache/reports/"):
            errors.append(
                f"upstream entry {name} evidence_artifact must live under .runtime-cache/reports/: "
                f"{evidence_artifact}"
            )
        if kind in {"vendor", "fork", "patch"}:
            lock_files = list((root / "vendor").rglob("UPSTREAM.lock")) if (root / "vendor").exists() else []
            if not lock_files:
                errors.append(f"active upstream `{name}` requires live vendor/fork/patch evidence under vendor/")
        if name not in registry_active:
            errors.append(f"active upstream `{name}` missing from config/governance/upstream-registry.json active set")

    for entry in template_entries:
        missing = sorted(REQUIRED_FIELDS - set(entry))
        if missing:
            errors.append(
                f"template upstream entry {entry.get('name', '<unknown>')} missing fields: {', '.join(missing)}"
            )
            continue
        name = str(entry["name"])
        if name not in registry_template:
            errors.append(f"template upstream `{name}` missing from config/governance/upstream-registry.json template set")

    for name in sorted(registry_active - seen):
        errors.append(f"upstream registry active name missing from active-upstreams.json: {name}")

    for image in strict_ci_contract.get("service_images", {}).values():
        if "@sha256:" not in image:
            errors.append(f"strict_ci_contract image is not digest-pinned: {image}")
        if not any(image in source for source in image_sources):
            errors.append(f"service image missing from config/governance/active-upstreams.json: {image}")

    standard_image = strict_ci_contract.get("standard_image", {})
    standard_ref = f"{standard_image.get('repository', '')}@{standard_image.get('digest', '')}"
    if standard_ref not in image_sources:
        errors.append("strict CI standard image missing from config/governance/active-upstreams.json")

    matrix_entries = matrix.get("matrix", [])
    if len(matrix_entries) < 4:
        errors.append("upstream compatibility matrix must define at least four supported combinations")
    for item in matrix_entries:
        for field in (
            "name",
            "supported",
            "owner",
            "blocking_level",
            "verification_entrypoint",
            "verification_status",
            "verification_lane",
            "last_verified_at",
            "last_verified_run_id",
            "verification_artifacts",
            "evidence_artifact",
            "failure_signature",
            "freshness_window_hours",
            "verification_scope",
        ):
            if field not in item:
                errors.append(
                    f"compatibility matrix entry {item.get('name', '<unknown>')} missing field `{field}`"
                )
        evidence_artifact = str(item.get("evidence_artifact", ""))
        if evidence_artifact and not evidence_artifact.startswith(".runtime-cache/reports/"):
            errors.append(
                f"compatibility matrix entry {item.get('name', '<unknown>')} evidence_artifact "
                f"must live under .runtime-cache/reports/: {evidence_artifact}"
            )
        if str(item.get("verification_status", "")) not in KNOWN_VERIFICATION_STATUSES:
            errors.append(
                f"compatibility matrix entry {item.get('name', '<unknown>')} uses unsupported verification_status"
            )
        if str(item.get("verification_lane", "")) not in KNOWN_VERIFICATION_LANES:
            errors.append(
                f"compatibility matrix entry {item.get('name', '<unknown>')} uses unsupported verification_lane"
            )
        if str(item.get("blocking_level", "")) not in KNOWN_BLOCKING_LEVELS:
            errors.append(
                f"compatibility matrix entry {item.get('name', '<unknown>')} uses unsupported blocking_level"
            )
        freshness_window_hours = item.get("freshness_window_hours")
        if not isinstance(freshness_window_hours, int) or freshness_window_hours <= 0:
            errors.append(
                f"compatibility matrix entry {item.get('name', '<unknown>')} must declare positive freshness_window_hours"
            )
        artifacts = item.get("verification_artifacts", [])
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(
                f"compatibility matrix entry {item.get('name', '<unknown>')} must declare non-empty verification_artifacts"
            )

    report_path = root / ".runtime-cache" / "reports" / "governance" / "upstream-compat-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "version": 1,
        "active_entry_count": len(entries),
        "template_entry_count": len(template_entries),
        "matrix_count": len(matrix_entries),
        "standard_image": standard_ref,
        "service_images": strict_ci_contract.get("service_images", {}),
        "vendor_surface_status": "active" if (root / "vendor").exists() else "not_applicable",
        "matrix_rows": [
            {
                "name": item.get("name"),
                "supported": item.get("supported"),
                "verification_status": item.get("verification_status"),
                "verification_lane": item.get("verification_lane"),
                "verification_entrypoint": item.get("verification_entrypoint"),
                "verification_artifacts": item.get("verification_artifacts"),
                "last_verified_at": item.get("last_verified_at"),
                "last_verified_run_id": item.get("last_verified_run_id"),
            }
            for item in matrix_entries
        ],
        "status": "fail" if errors else "pass",
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_runtime_metadata(
        report_path,
        source_entrypoint="scripts/governance/check_upstream_governance.py",
        verification_scope="upstream-governance",
        source_run_id="governance-upstream-compat-report",
        freshness_window_hours=24,
        extra={"report_kind": "upstream-compat-report"},
    )

    if errors:
        print("[upstream-governance] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(
        f"[upstream-governance] PASS ({len(entries)} active entries, {len(template_entries)} templates, {len(matrix_entries)} matrix rows)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
