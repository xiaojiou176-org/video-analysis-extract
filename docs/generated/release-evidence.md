<!-- generated: docs governance control plane; do not edit directly -->

# Release Evidence Reference

Generated from the release evidence workflow and manifest capture script.

## Canonical Rules

- repo-side closure and external closure must be reported separately; see `docs/reference/done-model.md`
- external lane live status is tracked in `docs/reference/external-lane-status.md`
- current run evidence is the only canonical source for release verdicts
- current-run KPI and readiness summaries live under `.runtime-cache/reports/release-readiness/`
- historical examples under `artifacts/releases/*` are documentation examples, not release verdict proof
- manifest paths must be repo-relative, not host-absolute

## Required Evidence Files

- `artifacts/releases/<tag>/canary/canary-rollout-dryrun.log`
- `artifacts/releases/<tag>/canary/canary-rollout-evidence.json`
- `artifacts/releases/<tag>/checksums.sha256`
- `artifacts/releases/<tag>/manifest.json`
- `artifacts/releases/<tag>/rollback/db-rollback-readiness.json`
- `artifacts/releases/<tag>/rollback/drill.json`

## Workflow Triggers

- `workflow_dispatch` supported
- `push tags` supported

## Attestation

- provenance action: `actions/attest-build-provenance`
- bundle source: `scripts/release/capture_release_manifest.sh`
- readiness preflight: `scripts/release/check_release_evidence_attest_readiness.py`
- GHCR standard-image publish lane primes Docker Buildx before invoking the multi-arch image build script

## Adjacent Governance Evidence

- upstream inventory entries tracked: `19`
- compatibility matrix rows tracked: `7`
- external lane current snapshot: `docs/generated/external-lane-snapshot.md`
- monthly governance audit snapshots are complementary hygiene evidence, not release verdict proof
