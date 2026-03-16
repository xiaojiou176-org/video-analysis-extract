# Security Policy

## Supported Model

This repository is maintained with a **source-first public-ready, limited-maintenance** governance pack.
Security fixes are considered for the current default branch and for release-tag
evidence that still maps to the current contract surfaces.

Unsupported reports include:

- issues that only affect historical sample artifacts,
- requests to support private forks or unpublished deployment topologies,
- vulnerabilities that require secrets or infrastructure the repository does not ship.

## Reporting a Vulnerability

Please do **not** open a public GitHub issue for a suspected vulnerability.

Use this private path instead:

1. GitHub Security Advisories / private vulnerability reporting:
   `https://github.com/xiaojiou176-org/video-analysis-extract/security`

This repository does not offer email-based private vulnerability intake.
Do not send sensitive details to public issues or placeholder email aliases.
If the repository security page does not currently expose a private submission UI,
open a minimal public issue that asks maintainers to enable private reporting,
but do not include exploit details, secrets, routes, or reproduction payloads.

Include:

- affected file or command,
- reproduction steps,
- expected impact,
- whether secrets, provider keys, or production-like data are involved.

## Response Expectations

- This repository is maintained on a best-effort basis.
- Triage aims to acknowledge valid reports within **5 business days**.
- Fix timing is not guaranteed for non-blocker issues or for issues that only affect optional external lanes.
