# Contributor Rights Model

This page answers one practical question:

**who is allowed to contribute to this repository, under what rights model, and how automation-authored changes are treated.**

It is not a marketing page. Think of it as the repository's contribution title chain.

## Scope

This policy applies to:

- direct maintainer commits,
- pull requests from human contributors,
- patches generated or co-authored by automation identities,
- repository-owned governance, documentation, and runtime-facing changes.

It does **not** expand the repository into a broad support or commercial distribution commitment.

## Repository Maintainer Model

- The repository is maintained under a **limited-maintenance, source-first** posture.
- Maintainers decide whether a contribution is accepted.
- Acceptance means the contribution may be stored, reviewed, redistributed, and relicensed under the repository's published project license, unless a stricter third-party obligation is explicitly documented elsewhere.

In plain English:

- opening a pull request is a proposal,
- merging it is the point where the repository accepts it into the public tree,
- accepted code must have a clear right-to-contribute story.

## Inbound Rights Rule

All accepted contributions are governed by an **inbound = outbound** rule:

- by submitting a contribution, the submitter confirms they have the right to contribute the material,
- the submitter confirms the repository may redistribute the accepted contribution under the repository's project license and documented third-party obligations,
- the submitter must not contribute material that depends on undisclosed employer, client, vendor, or platform restrictions.

If a contribution contains copied, vendored, patched, or externally sourced material, the submitter must provide the provenance and license basis before it is eligible for merge.

## Automation And Agent-Generated Contributions

Automation identities are treated as **execution identities**, not as independent legal actors.

That means:

- an automation account may appear in git history,
- but the human maintainer who triggers, reviews, or merges the change remains responsible for confirming contribution rights,
- automation-generated changes must be reviewed under the same repository rules as human-authored changes,
- automation output must not be merged if the maintainer cannot explain its provenance, review path, and applicable rights basis.

In practice:

- an automation-authored commit is acceptable only when a human maintainer has reviewed it,
- the maintainer must be able to explain why the change is safe to publish,
- the maintainer must not rely on "the tool wrote it" as a rights justification.

## Third-Party And Derived Material

The following need extra care before merge:

- copied snippets from external repositories,
- vendored files,
- generated assets derived from third-party content,
- screenshots, datasets, transcripts, or samples that may contain external rights or privacy constraints,
- AI-generated output that includes recoverable third-party copyrighted material.

These materials require:

- a provenance note,
- a license or permission basis,
- and, when needed, an explicit boundary note in the repository docs.

## Locale Boundary For Contributions

This repository separates contribution surfaces by audience:

- contributor-facing, governance-facing, CI-facing, and runtime-diagnostic surfaces are expected to stay English-first,
- product-output surfaces may remain localized when that localization is part of the intended user-facing behavior.

That means maintainers must not treat product-output Chinese as a general exemption.

Instead:

- localized output must stay inside explicitly recognized product-output surfaces,
- internal prompt/control text must stay English-first even when it is steering Simplified Chinese output,
- contributors must not reintroduce Chinese into governance or runtime-diagnostic layers under the excuse that "the product is bilingual",
- and any new locale exception should be documented as an explicit allowlist decision, not as an accidental drift.

Current explicit allowlist examples:

- `apps/worker/worker/pipeline/steps/artifacts.py`
- `apps/worker/worker/pipeline/runner_rendering.py`
- `apps/worker/templates/digest.md.mustache`

## What Maintainers Must Record

For any contribution that changes the public boundary, maintainers must be able to point to:

- the source of the contribution,
- the review path,
- the governing policy or license basis,
- and any remaining limitation or exclusion.

This does not require a heavyweight legal workflow for every typo fix.
It does require that the repository can explain its public tree without hand-waving.

## Merge Eligibility Checklist

A contribution is eligible for merge only when all of the following are true:

- the submitter has the right to contribute it,
- the repository can redistribute it under the stated policy,
- any third-party material has a recorded provenance basis,
- automation-assisted changes have a human reviewer who accepts responsibility,
- the contribution does not weaken security, governance, or trust-boundary rules.

## Non-Goals

This policy does **not** claim:

- that the repository provides a corporate CLA workflow,
- that every historical commit has already been independently relicensed outside this repository context,
- or that public visibility alone proves legal or commercial adoption readiness.

## Related Sources

- `LICENSE`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `THIRD_PARTY_NOTICES.md`
- `docs/reference/public-repo-readiness.md`
- `docs/reference/public-rights-and-provenance.md`
