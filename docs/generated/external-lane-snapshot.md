<!-- generated: docs governance control plane; do not edit directly -->

# External Lane Snapshot

This page is machine-rendered from current external-lane contracts and runtime reports.

| Lane | Current State | Blocker / Evidence | Canonical Artifact |
| --- | --- | --- | --- |
| `remote-platform-integrity` | `pass` | `ok` | `.runtime-cache/reports/governance/remote-platform-truth.json` |
| `ghcr-standard-image` | `blocked` | `buildx-runtime-preparation-failure; historical remote workflow targets `07324519dba2feddafef4a36f4340d8ff476258e`, current HEAD is `c7ddaed526671b927396063f2812978b9a739a15`` | `.runtime-cache/reports/governance/standard-image-publish-readiness.json` |
| `release-evidence-attestation` | `ready` | `ok; historical remote workflow targets `9ba1c564b1840472a51946db21a10ffd831d1dae`, current HEAD is `c7ddaed526671b927396063f2812978b9a739a15`` | `.runtime-cache/reports/release/release-evidence-attest-readiness.json` |
| `rsshub-youtube-ingest-chain` | `verified` | `provider` | `.runtime-cache/reports/governance/upstream-compat-report.json` |
| `resend-digest-delivery-chain` | `verified` | `provider` | `.runtime-cache/reports/governance/upstream-compat-report.json` |
| `strict-ci-compose-image-set` | `pending` | `external` | `.runtime-cache/reports/governance/upstream-compat-report.json` |

## Reading Rule

- explanation lives in `docs/reference/external-lane-status.md`
- current status must come from this generated page or the underlying runtime reports
- current-state runtime reports must be current-commit aligned; stale commit artifacts are historical evidence only
- actor-sensitive remote truth is carried by `.runtime-cache/reports/governance/remote-platform-truth.json`
- `ready` means preflight/evidence inputs are in place; it does not mean the external lane has already closed successfully
