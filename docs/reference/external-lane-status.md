# External Lane Status

This page answers one narrow question: **after the repository goes green internally, does the outside world also accept the claim?**

## Current Snapshot Source

The external-lane **state table itself** no longer lives in tracked docs. Read these runtime-owned artifacts directly:

- `.runtime-cache/reports/governance/remote-platform-truth.json`
- `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
- `.runtime-cache/reports/release/release-evidence-attest-readiness.json`

`docs/generated/external-lane-snapshot.md` now keeps only the pointer / reading rule. It no longer carries the current-verdict payload.

The canonical lane names are still:

- GHCR standard image
- Release evidence attestation
- `rsshub-youtube-ingest-chain`
- `resend-digest-delivery-chain`

Those current-state artifacts must also satisfy one additional rule:

- runtime metadata `source_commit` must align with the current HEAD; artifacts from an old commit are historical records, not a current snapshot

## Verification Rules

- Repo-side green does not equal external-lane green.
- `governance-audit PASS` also does not equal external-lane green; it cannot even replace the repo-side strict current receipt on its own.
- `remote-required-checks=status=pass` only proves merge-relevant required-check integrity, meaning `docs/generated/required-checks.md` and remote branch-protection required checks have not drifted apart. It answers “is the required lane list aligned for PR/merge,” not “did `ci-final-gate`, `live-smoke`, or nightly terminal closure pass.”
- An external lane counts as `verified` only when fresh artifacts, runtime metadata, and same-run proof all line up.
- For lanes that consume remote workflow results, `verified` also requires the latest successful run to have `headSha == current HEAD`.
- If a remote workflow succeeded on an old commit, that run is historical evidence only and must not upgrade the current state.
- Platform permission problems must be reported as platform blockers instead of being disguised as repository bugs.
- If a GHCR lane workflow artifact records `failed_step_name=Build and push strict CI standard image` and `failure_signature=blob-head-403-forbidden`, interpret it as: preflight passed, and the real failure landed on the registry blob-write boundary.
- `check_standard_image_publish_readiness.sh` now checks more than token-path visibility and GitHub Packages API visibility. When an explicit token path is available, it also probes `ghcr.io/v2/<repo>/blobs/uploads/`. Only `202` counts as a blob-write preflight pass; `401/403` must be treated as platform write-permission blockers.
- For hosted `build-ci-standard-image.yml` runs, GHCR readiness intentionally uses `github.actor + GITHUB_TOKEN` first so a stale `GHCR_WRITE_*` secret cannot mask a healthier repository-scoped token path. Local debug paths still check explicit `GHCR_WRITE_*`, then `GHCR_*`, and finally GitHub Actions / `gh auth`.
- Whether the remote repository is public and whether branch-protection platform capabilities are enabled are also external truths; local docs must not declare them unilaterally.
- Actor-sensitive remote truth must come from `remote-platform-truth.json`; do not turn one probe’s account context into a permanent fact.
- `ready`, `queued`, and `in_progress` only mean “not yet closed,” and must not be wrapped into external done.

## Reading Rule

- The explanation layer only answers “why blocked / verified.”
- For repo-side newcomer / strict receipts, read `.runtime-cache/reports/governance/newcomer-result-proof.json`, especially `current_workspace_verdict.status` and `blocking_conditions`. Think of that as reading the court verdict before reading supporting evidence; this page does not rescue repo-side done on its own.
- Current state may only be cited from runtime reports; tracked generated docs are pointers and reading rules only.
- A runtime aggregate page such as `.runtime-cache/reports/governance/current-state-summary.md` must also pass its own “receipt date check”: inspect whether its `.meta.json` `source_commit` equals the current HEAD. If not, treat it as a historical snapshot.
- If `current-state-summary.md` shows `current workspace verdict=partial|missing`, read it fail-close. Do not mentally promote the whole page to “current workspace closed” because one sub-line says `repo-side-strict receipt=pass` or one external row is green.
- If a runtime report’s `source_commit` does not equal the current HEAD, the report is historical evidence only and must not be treated as current state.
- If remote probe results, GHCR readiness, release-evidence readiness, and explanation docs disagree, runtime reports win.
- `remote-required-checks` is an external reading-rule check for merge-relevant required-lane alignment, not a terminal CI receipt; `ci-final-gate`, `live-smoke`, and nightly lanes still need their own current runtime/workflow proof.
- When the current GHCR blocked run provides an explicit failed step or failure signature, use that data first to distinguish preflight failures from buildx-setup failures or final build-and-push failures.
- If the remote workflow still points at an old head, the summary/pointer may only honestly say `historical`, `ready`, or `blocked`. It must never wrap that old run into current `verified`.

## Canonical Commands

Remote platform truth:

```bash
./bin/remote-platform-probe --repo xiaojiou176-org/video-analysis-extract
python3 scripts/governance/check_remote_required_checks.py
```

GHCR / external image:

```bash
./scripts/ci/check_standard_image_publish_readiness.sh
./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
gh workflow run build-ci-standard-image.yml --ref main
```

Release evidence:

```bash
python3 scripts/release/check_release_evidence_attest_readiness.py --release-tag <tag>
gh workflow run release-evidence-attest.yml --ref main -f release_tag=v0.1.0
gh attestation verify <bundle> --repo xiaojiou176-org/video-analysis-extract
```

Provider lanes:

```bash
./bin/bootstrap-full-stack
./bin/full-stack up
./bin/smoke-full-stack
./bin/run-daily-digest --to-email <verified-recipient>
./bin/run-failure-alerts --to-email <verified-recipient>
```

## Reporting Rule

When reporting the external lane, always include at least:

- how far the lane got
- which artifact / log / run id proves it
- if it failed, whether the final stop was platform permission, provider account state, or repository script logic
- for GHCR lanes, include the failed job/step or failure signature whenever the current workflow already exposes that data
- never let repo-side governance or newcomer receipts stand in for external-lane proof
