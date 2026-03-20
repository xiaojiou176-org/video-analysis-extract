# Public Rights And Provenance

This page answers one concrete question:

**what in the repository is ours to publish, what is third-party material, and what still depends on a separate rights or proof boundary.**

## Canonical Sources

- project license: `LICENSE`
- contributor rights policy: `docs/reference/contributor-rights-model.md`
- third-party rights ledger: `THIRD_PARTY_NOTICES.md`
- third-party dependency inventory: `artifacts/licenses/third-party-license-inventory.json`
- public-safe artifact boundary: `docs/reference/public-artifact-exposure.md`
- public posture: `docs/reference/public-repo-readiness.md`

## Rights Model

### Repository-owned material

- repository source code and repository governance docs are governed by the repository's published license and contribution policy,
- accepted contributions must satisfy the repository's inbound-rights rule,
- automation-authored changes are not treated as independent legal actors; they still require a human maintainer review path and contribution-rights justification.

### Third-party material

- third-party dependencies do **not** become repository-owned just because the repository is MIT-licensed,
- their notice and license obligations continue to follow `THIRD_PARTY_NOTICES.md` and the generated inventory,
- copied, vendored, patched, or imported third-party material must carry an explicit provenance basis before it becomes part of the tracked public tree.

### Platform references

- platform names, APIs, and service references describe integration dependencies,
- they do **not** imply endorsement, partnership, affiliation, or delegated rights.

## Automation Contribution Rule

The repository explicitly distinguishes:

- **automation as an execution identity**, and
- **maintainers as the humans responsible for merge authority and rights confirmation**.

So:

- an automation identity may appear in git history,
- but that does not remove the maintainer's duty to confirm the contribution can be published,
- and automation output must not be merged on the theory that "the tool wrote it, so rights are automatic."

For the governing policy, see `docs/reference/contributor-rights-model.md`.

## Historical Examples Rule

- checked-in examples under `artifacts/releases/*` are **historical examples**, not current release verdicts,
- current release / attestation / external-lane conclusions may only be derived from current runtime-owned proof artifacts,
- and any retained historical example must carry explicit "historical example / not canonical verdict" wording.

## Third-party Content Rule

- do not describe third-party dependencies, platforms, or toolchains as repository-original capabilities,
- do not hand-maintain large dependency-attribution tables; use the machine-generated ledger,
- and do not merge new vendored, copied, or patched third-party content without provenance and license explanation.

## Decision Boundary

### May be published

- source code,
- contracts,
- governance control-plane files,
- sanitized performance examples,
- historical examples with explicit non-canonical wording.

### Must not be treated as current official proof

- checked-in historical release evidence,
- successful external workflows from an old head,
- any stale artifact that is not current-proof aligned.

### Must not be inferred from public visibility alone

- that registry distribution is already mature,
- that platform permissions are fully closed,
- that brand affiliation exists,
- or that contribution rights have already been completely resolved.

### Must not be inferred from tracked policy files alone

- that private vulnerability reporting is currently enabled,
- that GHCR package permissions are currently sufficient,
- or that release-distribution UI/platform state is currently healthy.

Those states must come from current runtime probe artifacts.

## Reporting Rule

When describing rights and provenance publicly, always include:

- the repository license entrypoint,
- the contributor-rights policy entrypoint,
- the third-party rights ledger entrypoint,
- the historical-vs-current proof boundary,
- and the fact that platform references are not affiliation claims.
