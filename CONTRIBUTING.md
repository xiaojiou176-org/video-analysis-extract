# Contributing

## Maintenance Posture

This repository accepts issues and narrowly scoped pull requests, but it is run
as a **limited-maintenance, source-first** project. The main goal is to keep
the repo-side contracts, docs, and verification lanes honest.

Good contributions:

- fix a reproducible bug,
- tighten an existing contract or guardrail,
- improve source-first onboarding or public boundary clarity,
- add tests that close a concrete regression gap.

Out of scope by default:

- large product direction changes,
- new providers or deployment targets without prior design alignment,
- cosmetic refactors that do not reduce maintenance risk,
- changes that weaken gates or replace root-cause fixes with fallback behavior.

## Before Opening a Pull Request

1. Read `README.md` and `docs/start-here.md`.
2. Keep changes surgical and contract-aware.
3. Update docs when you change behavior, environment contracts, governance surfaces, or public-facing commands.
4. Run the smallest truthful verification set for your change.

Preferred repo-side checks:

```bash
./bin/governance-audit --mode audit
./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

## Pull Request Expectations

- Explain the user-visible or governance-visible change.
- List the exact commands you ran.
- Call out whether the change only closes a repo-side lane or also closes an external lane.
- Do not hide unresolved risks; list them explicitly.
