# Public Repo Readiness

This repository is published as a **public source-first, limited-maintenance engineering repository**.

It is **not** the same thing as:

- a hosted product,
- an adoption-grade open source distribution,
- or a claim that every external lane is currently verified.

In plain English:

- the repository is safe to inspect,
- its boundaries are meant to be explicit,
- and its repo-side proof model is intentionally strict,
- but public visibility alone does not prove full external distribution closure.

## Current Public Posture

- Posture: `public source-first`
- Maintenance model: `limited-maintenance`
- Intended public promise: **reviewable source, explicit boundaries, honest repo-side verification**
- Not promised by default:
  - hosted service support,
  - registry-first delivery,
  - or automatic external verification for every lane on every head

The remote repository is already public.
That still does **not** mean:

- GHCR distribution is fully closed,
- release evidence for the current head is externally verified,
- or provider/live lanes are all green for public consumption.

## Public Reviewable vs Safe Open Source

This repository makes a deliberate distinction:

- **public reviewable** means the source tree and governance surface are intentionally visible,
- **safe open source** requires clearer contribution rights, contributor-facing collaboration boundaries, and trustworthy external distribution semantics.

Today, the repository is closer to **public reviewable** than to **fully safe open source distribution**.

## Required Public Governance Pack

The minimum public governance pack includes:

- `LICENSE`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SUPPORT.md`
- `.github/CODEOWNERS`
- `.github/ISSUE_TEMPLATE/*`
- `.github/PULL_REQUEST_TEMPLATE.md`

Boundary explanation entrypoints:

- `docs/reference/public-rights-and-provenance.md`
- `docs/reference/public-privacy-and-data-boundary.md`
- `docs/reference/public-brand-boundary.md`
- `docs/reference/contributor-rights-model.md`

## Public Boundary

### Public-safe

- source code,
- contracts,
- governance control-plane files,
- generated reference docs,
- sanitized performance budgets,
- historical examples that are explicitly marked non-canonical,
- sanitized public samples only.

### Internal or conditional

- provider-level secrets and live tokens,
- GHCR / public distribution proof,
- samples that still point at production-like identities, routes, or credentials,
- any contribution surface whose rights basis is still unclear.

## Platform Truth Rule

Platform capability claims must come from current probe artifacts, not from tracked policy prose alone.

For example:

- private vulnerability reporting may only be described as `enabled`, `disabled`, or `unverified`,
- and that status must come from `.runtime-cache/reports/governance/remote-platform-truth.json`.

The same rule applies to external closure:

- `ready`, `queued`, and `historical` are **not** equivalent to `verified`,
- and old successful workflows must not impersonate current-head proof.

## Security Freshness Rule

Public security claims also require fresh proof.

For example:

- `gitleaks` history and working-tree receipts must align with the current head,
- and an old receipt must not be reused as current security proof.

Canonical artifacts:

- `.runtime-cache/reports/governance/remote-platform-truth.json`
- `.runtime-cache/reports/governance/open-source-audit-freshness.json`

## Collaboration Boundary

The repository now treats contributor-facing governance as an explicit public boundary.

That means:

- contribution rights must be explainable,
- automation-authored changes need a documented responsibility model,
- and deep-water contributor/runtime/governance surfaces are expected to be English-first for public collaboration.

See:

- `docs/reference/contributor-rights-model.md`
- `docs/reference/public-rights-and-provenance.md`

## Product-output Locale Boundary

This repository also distinguishes between:

- **governance/contributor/runtime-facing deep-water surfaces**, which are expected to be English-first,
- and **product-output surfaces**, which may still use Chinese when that language is part of the intended end-user experience.

At the moment, the following rule applies:

- internal prompt/control text must stay English-first, while digest templates and repository-generated end-user content may remain localized as a **controlled locale allowlist**,
- those product-output surfaces must stay explicitly separated from governance, CI, runbook, and contributor guidance layers,
- and future Chinese additions outside the product-output allowlist should be treated as governance drift.

Current explicit allowlist examples:

- `apps/worker/worker/pipeline/steps/artifacts.py`
- `apps/worker/worker/pipeline/runner_rendering.py`
- `apps/worker/templates/digest.md.mustache`

In plain English:

- Chinese may still exist where the repository is deliberately producing user-facing content,
- but it must not leak back into the places where contributors, operators, and reviewers need stable global collaboration semantics.

## Source-first Quickstart

Public entrypoints:

1. `README.md`
2. `docs/start-here.md`
3. `docs/reference/done-model.md`

Public repo-side verification commands:

```bash
./bin/governance-audit --mode audit
./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

Read current public/security state from:

- `.runtime-cache/reports/governance/remote-platform-truth.json`
- `.runtime-cache/reports/governance/open-source-audit-freshness.json`
- `.runtime-cache/reports/governance/current-state-summary.md`
