<!-- generated: docs governance control plane; do not edit directly -->

# External Lane Truth Entry

This tracked page is a machine-rendered pointer only.

It does not carry commit-sensitive current verdicts.
Current external state must be read from runtime-owned reports under `.runtime-cache/reports/**`.

## Canonical Runtime Reports

| Lane | Canonical Artifact | Reading Rule |
| --- | --- | --- |
| `remote-platform-integrity` | `.runtime-cache/reports/governance/remote-platform-truth.json` | read runtime artifact directly; tracked docs only explain semantics |
| `ghcr-standard-image` | `.runtime-cache/reports/governance/standard-image-publish-readiness.json` | read runtime artifact directly; tracked docs only explain semantics |
| `release-evidence-attestation` | `.runtime-cache/reports/release/release-evidence-attest-readiness.json` | read runtime artifact directly; tracked docs only explain semantics |

## Reading Rule

- explanation lives in `docs/reference/external-lane-status.md`
- current state must come from runtime-owned reports under `.runtime-cache/reports/**`
- tracked docs may explain state semantics, but must not carry current verdict payload
- runtime metadata `source_commit` must match the current HEAD before any report can be treated as current truth
- `ready` means preflight inputs exist; it does not mean the external lane has closed successfully

## Canonical Commands

- `python3 scripts/governance/probe_remote_platform_truth.py --repo xiaojiou176-org/video-analysis-extract`
- `python3 scripts/governance/check_remote_required_checks.py`
- `bash scripts/ci/check_standard_image_publish_readiness.sh`
- `python3 scripts/release/check_release_evidence_attest_readiness.py --release-tag <tag>`
