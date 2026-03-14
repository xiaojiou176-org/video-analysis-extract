<!-- generated: docs governance control plane; do not edit directly -->

# Release Evidence Reference

Generated from the release evidence workflow and manifest capture script.

## Canonical Rules

- current run evidence is the only canonical source for release verdicts
- historical examples under `reports/releases/*` are documentation examples, not release verdict proof
- manifest paths must be repo-relative, not host-absolute

## Required Evidence Files

- `reports/releases/<tag>/canary/canary-rollout-dryrun.log`
- `reports/releases/<tag>/canary/canary-rollout-evidence.json`
- `reports/releases/<tag>/checksums.sha256`
- `reports/releases/<tag>/manifest.json`
- `reports/releases/<tag>/rollback/db-rollback-readiness.json`
- `reports/releases/<tag>/rollback/drill.json`

## Workflow Triggers

- `workflow_dispatch` supported
- `push tags` supported

## Attestation

- provenance action: `actions/attest-build-provenance`
- bundle source: `scripts/release/capture_release_manifest.sh`
