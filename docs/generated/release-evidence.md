<!-- generated: docs governance control plane; do not edit directly -->

# Release Evidence Reference

Generated from the release evidence workflow and manifest capture script.

## Canonical Rules

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

## Adjacent Governance Evidence

- upstream inventory entries tracked: `19`
- compatibility matrix rows tracked: `7`
- monthly governance audit snapshots are complementary hygiene evidence, not release verdict proof
