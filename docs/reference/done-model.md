# Done Model

Completion signals in this repository are split into two layers. They must not be mixed.

## Layer A: Repo-side Done

In plain English, this layer asks: “can the repository stand on its own?” It does not require every external platform, registry, or provider lane to be perfect. It only requires the repository control plane, source tree, docs, tests, and standard local environment to form a trustworthy closure.

| Dimension | Repo-side Done Standard |
| --- | --- |
| Root / source hygiene | The root passes the allowlist gate, and repo-owned source roots contain no `__pycache__`, `*.pyc`, or runtime residue |
| Governance | `./bin/governance-audit --mode audit` passes freshly, and canonical current-proof artifacts have `source_commit` aligned with the current HEAD. This is necessary but not sufficient for repo-side done |
| Docs truth | Generated docs are fresh and their key semantics match the control plane |
| Strict path | `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` produces a fresh PASS receipt for the current HEAD. Repo-side done requires this strict receipt; the existence of the command is not enough |
| Compat | Repo-side required rows in `upstream-compat-matrix` are in the expected state |
| Public/source-first onboarding | Source-first entrypoints are explainable, executable, and clearly separate public docs from the internal runbook |
| Public governance pack | `README.md`, `SECURITY.md`, `SUPPORT.md`, `.github/CODEOWNERS`, `docs/reference/public-repo-readiness.md`, and `docs/reference/public-artifact-exposure.md` contain no placeholder routing, and the public-safe surface, policy allowlist, and tracked files stay aligned |
| Public security proof | `private_vulnerability_reporting` must come from the latest `remote-platform-truth.json` with an explicit `enabled|disabled|unverified` state, and `gitleaks` history / working-tree freshness reports must align with the current HEAD |

Additional Hard Rules:

- A fresh `governance-audit` PASS does not equal repo-side done; it only proves the control plane and governance surfaces are standing.
- Repo-side done requires all of the following at once: governance PASS + strict current receipt + docs truth + current-proof alignment.
- `newcomer-result-proof.json` now includes a dedicated `current_workspace_verdict`. Think of it as the final switchboard verdict that decides whether those green lights count as evidence for the **current workspace**.
- A dirty worktree must not be auto-wrapped into `pass` by commit-aligned current receipts. If the current worktree has uncommitted changes, `current_workspace_verdict.status` must fail-close to `partial`, and `blocking_conditions` must explicitly include `dirty_worktree`.
- If `current_proof_alignment` is missing or stale, the repo-side receipt is like a receipt with yesterday’s date: it proves you paid yesterday, not that the order in your hands is settled right now. In that case the verdict can be at most `partial`, never `pass`.
- If `newcomer-result-proof.json` shows `repo_side_strict_receipt=status=missing_current_receipt`, then the current HEAD still cannot honestly claim repo-side done.

## Layer B: External Done

In plain English, this layer asks: “can the outside world also prove what you claim?” It covers the GHCR pinned image, real provider lanes, public release assets, remote workflows, and other external proof surfaces.

| Dimension | External Done Standard |
| --- | --- |
| Image distribution | The GHCR pinned image is pullable and provable, and only a `verified` external lane counts toward External Done |
| Public release | Release bundle, attestation, and public distribution wording are aligned |
| Provider verification | Provider/live rows have fresh same-run proof |
| Remote platform | Remote workflows and platform configuration reproduce the external closure |

Additional Hard Rules:

- Even when a remote workflow succeeds, it only counts as historical evidence unless its `headSha` equals the current HEAD.
- `ready`, `queued`, and `in_progress` only mean the outer lane exists or is currently running; they do not prove external closure.
- `remote-required-checks=status=pass` only proves branch protection and aggregate-required-check integrity stay aligned. It is not a terminal CI receipt and cannot replace current closure proof from `ci-final-gate`, `live-smoke`, or `nightly-flaky-*`.

## Not In Scope For Repo-side Completion

- GHCR publish-permission problems
- External provider quotas and platform-account state
- Private deployment topology that is not published
- Registry-first delivery modes that sit outside the current source-first public posture

## Canonical Commands

Repo-side canonical commands:

```bash
./bin/governance-audit --mode audit
./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

External lane commands:

```bash
./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
./bin/upstream-verify
```

External lane state tracking:

- `docs/reference/external-lane-status.md`
- `docs/reference/newcomer-result-proof.md`
- `docs/generated/external-lane-snapshot.md` is now only a tracked pointer and reading rule
- `.runtime-cache/reports/governance/current-state-summary.md` is the runtime-owned current-state summary
- `.runtime-cache/reports/governance/newcomer-result-proof.json` is the entrypoint for repo-side newcomer / strict receipts
- Read `current_workspace_verdict.status` and `blocking_conditions` from `newcomer-result-proof.json` first. Do not assemble “overall done” by hand from isolated green sub-lights.
- Current-state docs and runtime reports may only consume current-commit-aligned canonical artifacts; historical examples stay examples and must not impersonate the current verdict
- A page like `.runtime-cache/reports/governance/current-state-summary.md` must pass the same date-check rule itself: only treat it as current when its own `.meta.json` `source_commit` equals the current HEAD; otherwise it is a historical snapshot and must be rerendered first
