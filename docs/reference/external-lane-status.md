# External Lane Status

This page answers one narrow question: **after the repository goes green internally, does the outside world also accept the claim?**

## Current Snapshot Source

The external-lane **state table itself** no longer lives in tracked docs. Read these runtime-owned artifacts directly:

- `.runtime-cache/reports/governance/remote-platform-truth.json`
- `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
- `.runtime-cache/reports/governance/ghcr-registry-auth-probe.json`
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
- `remote-required-checks=status=pass` only proves merge-relevant required-check integrity, meaning `docs/generated/required-checks.md`, branch protection, and merge-relevant lanes such as `remote-integrity` have not drifted apart. It answers “is the required lane list aligned for PR/merge,” not “did `ci-final-gate`, `live-smoke`, or nightly terminal closure pass.”
- `runner-health` is platform telemetry only. You can think of it as checking whether the delivery trucks are awake, not whether today’s package was delivered. It must never be cited as repo closure, current-head closure, or external-lane success.
- An external lane counts as `verified` only when fresh artifacts, runtime metadata, and same-run proof all line up.
- For lanes that consume remote workflow results, `verified` also requires the latest successful run to have `headSha == current HEAD`.
- If a remote workflow succeeded on an old commit, that run is historical evidence only and must not upgrade the current state.
- `current-head closure` means the proof was produced by a run that actually executed against the current commit, and that the proof closes the lane you are talking about. A green helper run on another commit, or a green platform-health run on the same commit, does not satisfy that closure.
- Platform permission problems must be reported as platform blockers instead of being disguised as repository bugs.
- If a GHCR lane workflow artifact records `failed_step_name=Build and push strict CI standard image` and `failure_signature=blob-head-403-forbidden`, interpret it as: preflight passed, and the real failure landed on the registry blob-write boundary.
- `check_standard_image_publish_readiness.sh` now checks more than token-path visibility and GitHub Packages API visibility. When an explicit token path is available, it also probes `ghcr.io/v2/<repo>/blobs/uploads/`. Only `202` counts as a blob-write preflight pass; `401/403` must be treated as platform write-permission blockers.
- For hosted `build-ci-standard-image.yml` runs, GHCR readiness now tries `github.actor + GITHUB_TOKEN` first. If that hosted repository token fails the blob-upload preflight, the workflow may fall back to explicit `GHCR_WRITE_*` credentials when they are present. If the explicit writer path still cannot prove blob upload during preflight, the hosted run may continue in a `fallback-unverified` mode so the real build/push step can provide the decisive evidence. Local debug paths still check explicit `GHCR_WRITE_*`, then `GHCR_*`, and finally GitHub Actions / `gh auth`.
- GitHub's container-registry docs also state that a **command-line image push is not linked to a repository by default**, even when the image path matches the repository name. The strict CI standard-image build path must therefore carry `org.opencontainers.image.source=https://github.com/<owner>/<repo>` so GHCR can connect the package back to the repository and let repository-scoped workflow permissions inherit correctly.
- If a package lookup with a token that claims `write:packages` still returns `404`, treat that as a possible **package-path / ownership / visibility** boundary problem, not as proof that the lane is healthy.
- If a token with `write:packages` can list packages for the target org/user/repository and all three views still come back empty while the expected package path returns `404`, treat that as stronger evidence that the package has **not been created under the expected namespace or has not been linked there yet**.
- If a digest-pinned manifest probe still returns `manifest unknown`, treat that as additional evidence that the package path, ownership, visibility, or publication state is unresolved. Do not reduce it to a generic auth-only story.
- If the hosted workflow log explicitly shows `GITHUB_TOKEN Permissions -> Packages: write` and `docker login ghcr.io` succeeds, do not fall back to the story that the run simply forgot to request package write scope. At that point the failure has already moved deeper into the **registry blob-write boundary** or the **package-not-created / package-not-linked** boundary.
- If a direct GHCR bearer-token exchange succeeds for `repository:<owner>/<package>:pull,push`, but `POST /v2/<repo>/blobs/uploads/` still returns `403`, read that as stronger evidence that the registry upload boundary itself is refusing the caller. The rejection reason still matters:
  - `permission_denied: write_package` means the caller is authenticated, but does not have effective package write permission for that namespace.
  - `permission_denied: The token provided does not match expected scopes.` means the caller reached the registry with a bearer token, but the token presented to the upload boundary still does not satisfy the registry's expected scope model for that package path.
- Whether the remote repository is public and whether branch-protection platform capabilities are enabled are also external truths; local docs must not declare them unilaterally.
- Actor-sensitive remote truth must come from `remote-platform-truth.json`; do not turn one probe’s account context into a permanent fact.
- `ready`, `queued`, and `in_progress` only mean “not yet closed,” and must not be wrapped into external done.

## GHCR Reading Hierarchy

For the GHCR standard-image lane, always read **two layers together**:

1. **local readiness**
   - source: `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
   - question: is the current workspace even allowed to succeed on the registry/token/write boundary
2. **remote current-head workflow state**
   - source: `.runtime-cache/reports/governance/external-lane-workflows.json`
   - question: what is the latest remote workflow currently doing for this head

Do not collapse those layers into one status sentence.

Examples:

- `local readiness = blocked` + `remote workflow = queued`
  - report both,
  - keep the lane **unverified**,
  - and explain that remote execution exists for the current head, but the write boundary is still not proven closed.
- `local readiness = blocked` + `manifest probe = manifest unknown` + `remote workflow = failed at preflight`
  - report all three,
  - keep the lane **unverified**,
  - and explain that the lane now has evidence for both a token/write boundary problem and an unresolved package-path / ownership / visibility problem.
- `local readiness = blocked` + `hosted run says Packages: write and Login Succeeded` + `org/user/repository package listings are empty`
  - report all four facts together,
  - keep the lane **unverified**,
  - and explain that the problem is no longer “workflow forgot to ask for packages write”; it is now closer to **package creation/linkage/visibility** or **registry-side write acceptance**.
- `hosted GITHUB_TOKEN preflight = blocked` + `explicit GHCR_WRITE fallback = ready`
  - report both layers,
  - keep the lane **unverified** until the current-head hosted run succeeds,
  - and explain that the repository token path is still weaker than the explicit writer path.
- `hosted GITHUB_TOKEN preflight = blocked` + `explicit GHCR_WRITE fallback = fallback-unverified`
  - allow the current-head hosted build to continue,
  - keep the lane **unverified** until the real build/push result lands,
  - and report that preflight could not prove blob upload but the workflow deliberately advanced to collect stronger evidence from the real publish path.
- `bearer token exchange = success` + `registry upload = 403 permission_denied`
  - report both layers,
  - keep the lane **unverified**,
  - and explain that token minting alone is not sufficient proof of publish viability; the decisive check is still whether the registry accepts blob upload for the expected package path.
- `registry auth probe = challenge scope matches the expected repository path` + `upload still 403`
  - report all layers together,
  - keep the lane **unverified**,
  - and explain that the remaining blocker has moved past namespace recognition and into package write acceptance / linkage / visibility / access state.
- `local readiness = ready` + `remote workflow = historical`
  - report the lane as **historical / not current-head verified**.
- `remote workflow = success` on an old head
  - still report **historical**, never `verified`.

## GHCR Platform Repair Path

When the repository-side naming, labels, and workflow permissions are already aligned, but the lane still shows:

- hosted `GITHUB_TOKEN Permissions -> Packages: write`
- `docker login ghcr.io` succeeded
- blob upload preflight still returns `401`
- org-scoped package listing stays empty or the expected package path returns `404`
- direct bearer token exchange for `repository:xiaojiou176-org/video-analysis-extract-ci-standard:pull,push` succeeds, but blob upload still returns `403`

then the fastest honest reading is:

- the problem has moved **past repository YAML**
- and into **package creation / repository linkage / visibility / package access**

Think of it like this:

- the workflow badge proves the delivery truck reached the gate
- `docker login` proves the driver showed a valid badge
- blob-upload `401` means the loading dock still refused the truck
- package API `404` / empty listings mean the warehouse slot may not exist under the expected namespace yet

Use the following repair order.

### 1. Confirm the package exists under the expected namespace

Target path for this repository:

- `ghcr.io/xiaojiou176-org/video-analysis-extract-ci-standard`

If the org package page and package API both stay empty / `404`, treat that as a **package-not-created-or-not-linked-yet** signal first.

Official basis:

- GitHub's container-registry docs say a command-line push is **not linked to a repository by default**
- GitHub's repository-connection docs say organization-scoped packages can be linked from the package page using **Connect repository**

### 2. Confirm repository linkage on the package page

On GitHub UI:

1. Open the organization page
2. Open **Packages**
3. Open the target container package
4. Under package versions, click **Connect repository**
5. Select `xiaojiou176-org/video-analysis-extract`

If the package already shows a **Repository source** section, verify it points at the same repository. If it points elsewhere, unlink and relink.

Why this matters:

- GitHub docs say a package linked to a repository can automatically inherit that repository's access permissions
- GitHub Actions workflows in the linked repository then automatically get package access unless the org has disabled automatic inheritance

### 3. Verify package inheritance / Actions access

Open the package's **Package settings** page and check two things:

1. Whether the package is inheriting access from the linked repository
2. Whether **Manage Actions access** includes `xiaojiou176-org/video-analysis-extract`

If automatic inheritance is disabled at the org or package level, manually add the repository under **Manage Actions access**.

Why this matters:

- GitHub docs explicitly say workflows using `GITHUB_TOKEN` get automatic access when the package is linked and inheritance is enabled
- The same docs also say you can grant workflow access from package settings when automatic inheritance is not enough
- Our direct registry probe now adds one more layer: GHCR can mint a bearer token for the expected repository scope, yet still refuse `POST /blobs/uploads/`. That means token minting alone does not close the lane; package write acceptance still depends on the package/linkage/access state behind the registry boundary.

### Registry auth probe reading rule

Read `.runtime-cache/reports/governance/ghcr-registry-auth-probe.json` like this:

- `anonymous_challenge.www_authenticate`
  - tells you whether GHCR recognizes the expected repository path at all
- `registry_exchange.status == 200`
  - only proves the token service was willing to mint a bearer token
- `upload_probe.status == 202`
  - is the first real sign that the registry write boundary is open
- `upload_probe.status == 403` with `permission_denied: write_package`
  - means the caller reached the upload boundary but does not have effective package write permission
- `upload_probe.status == 403` with `The token provided does not match expected scopes`
  - means the registry still rejects the bearer token presented for that package path, even after token exchange

### 4. Verify organization package-creation visibility policy

In organization settings:

1. Open **Settings**
2. Open **Packages**
3. Check **Package Creation**
4. Confirm the org allows the visibility class needed for this package

Why this matters:

- GitHub docs say organizations can restrict whether members can create public / private / internal packages
- If org policy blocks package creation, the package path may never materialize under the expected namespace

### 5. Keep repository-side metadata as-is

Do **not** remove the current repository-side source label work.

The current build path already carries:

- `org.opencontainers.image.source=https://github.com/xiaojiou176-org/video-analysis-extract`

That is still required, because GitHub's container-registry docs point to `org.opencontainers.image.source` as the metadata key used to associate the package with the repository.

### 6. Re-run the current-head hosted publish path only after the platform fix

Only after steps 1-4 are confirmed should you re-run:

- `build-ci-standard-image.yml`

Success criteria for closing the blocker:

- blob upload preflight is no longer `401/403`
- package page exists under the expected org path
- package linkage / Actions access is visible in package settings
- current-head hosted publish finishes successfully
- manifest probe stops returning `manifest unknown`

## Official Sources Used For The Repair Path

- Working with the Container registry:
  - <https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry>
- Connecting a repository to a package:
  - <https://docs.github.com/en/packages/learn-github-packages/connecting-a-repository-to-a-package>
- Configuring a package's access control and visibility:
  - <https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility>
- Publishing and installing a package with GitHub Actions:
  - <https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions>

## Reading Rule

- The explanation layer only answers “why blocked / verified.”
- For repo-side newcomer / strict receipts, read `.runtime-cache/reports/governance/newcomer-result-proof.json`, especially `current_workspace_verdict.status` and `blocking_conditions`. Think of that as reading the court verdict before reading supporting evidence; this page does not rescue repo-side done on its own.
- Current state may only be cited from runtime reports; tracked generated docs are pointers and reading rules only.
- A runtime aggregate page such as `.runtime-cache/reports/governance/current-state-summary.md` must also pass its own “receipt date check”: inspect whether its `.meta.json` `source_commit` equals the current HEAD. If not, treat it as a historical snapshot.
- If `current-state-summary.md` shows `current workspace verdict=partial|missing`, read it fail-close. Do not mentally promote the whole page to “current workspace closed” because one sub-line says `repo-side-strict receipt=pass` or one external row is green.
- If a runtime report’s `source_commit` does not equal the current HEAD, the report is historical evidence only and must not be treated as current state.
- If remote probe results, GHCR readiness, release-evidence readiness, and explanation docs disagree, runtime reports win.
- `remote-required-checks` is an external reading-rule check for merge-relevant required-lane alignment, not a terminal CI receipt; `ci-final-gate`, `live-smoke`, and nightly lanes still need their own current runtime/workflow proof.
- When GHCR has both a local readiness artifact and a remote current-head workflow record, the summary must report both layers explicitly instead of letting `queued` or `ready` sound like progress toward `verified`.
- When the current GHCR blocked run provides an explicit failed step or failure signature, use that data first to distinguish preflight failures from buildx-setup failures or final build-and-push failures.
- If the remote workflow still points at an old head, the summary/pointer may only honestly say `historical`, `ready`, or `blocked`. It must never wrap that old run into current `verified`.
- If `build-ci-standard-image.yml` publishes successfully, that still does **not** rewrite `infra/config/strict_ci_contract.json` automatically. Treat the uploaded `contract-candidate.json` artifact as evidence for a reviewed follow-up PR, not as an already-promoted repository truth.

## Current-Head Closure Checklist

When someone says “the external lane is closed,” read it like a signed delivery receipt. The receipt only counts when the package, address, and timestamp all match the shipment you care about.

Minimum checklist:

- the artifact/report says which workflow or probe produced the proof
- runtime metadata `source_commit` or remote workflow `headSha` equals the current HEAD
- the proof is for the lane itself, not for a helper lane such as `runner-health`
- if the lane depends on a remote workflow, the latest successful run for that lane is also a current-head run
- if the lane depends on both local readiness and remote execution, both layers are current-head and both are closed

Fail-close examples:

- `runner-health=success` + `build-ci-standard-image=queued`
  - the trucks are awake, but the package is not delivered; lane remains **unverified**
- `remote-integrity=success` + `ci-final-gate` missing for current HEAD
  - required-check alignment is healthy, but terminal closure is still **unverified**
- `build-ci-standard-image=success` on yesterday's SHA
  - keep it **historical**, not current-head closed

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
