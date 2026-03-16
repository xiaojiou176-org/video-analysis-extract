# Security Policy

## Supported Model

This repository is published as a **source-first, limited-maintenance** project.
Security fixes are considered for the current default branch and for release-tag
evidence that still maps to the current contract surfaces.

Unsupported reports include:

- issues that only affect historical sample artifacts,
- requests to support private forks or unpublished deployment topologies,
- vulnerabilities that require secrets or infrastructure the repository does not ship.

## Reporting a Vulnerability

Please do **not** open a public GitHub issue for a suspected vulnerability.

Use one of these private paths instead:

1. GitHub private vulnerability reporting, if it is enabled for this repository.
2. The maintainer email alias in `.github/CODEOWNERS`: `codex-test@example.com`.

Include:

- affected file or command,
- reproduction steps,
- expected impact,
- whether secrets, provider keys, or production-like data are involved.

## Response Expectations

- This repository is maintained on a best-effort basis.
- Triage aims to acknowledge valid reports within **5 business days**.
- Fix timing is not guaranteed for non-blocker issues or for issues that only affect optional external lanes.
