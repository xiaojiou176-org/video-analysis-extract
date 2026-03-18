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

Current platform truth for private reporting must come from the latest runtime probe:

- `.runtime-cache/reports/governance/remote-platform-truth.json`
- `private_vulnerability_reporting.status = enabled|disabled|unverified`

Use this private path only if the latest probe reports `private_vulnerability_reporting.status=enabled`:

1. GitHub Security Advisories / private vulnerability reporting:
   `https://github.com/xiaojiou176-org/video-analysis-extract/security`

If the latest probe reports `disabled` or `unverified`, do **not** assume private vulnerability reporting is enabled just because this file exists.
In that case:

1. open a minimal public issue that asks maintainers to enable private reporting
2. do **not** include exploit details, secrets, routes, or reproduction payloads
3. wait for a private intake path before sharing sensitive proof

This repository does not offer email-based private vulnerability intake.
Do not send sensitive details to public issues or placeholder email aliases.

Include:

- affected file or command,
- reproduction steps,
- expected impact,
- whether secrets, provider keys, or production-like data are involved.

## Response Expectations

- This repository is maintained on a best-effort basis.
- Triage aims to acknowledge valid reports within **5 business days**.
- Fix timing is not guaranteed for non-blocker issues or for issues that only affect optional external lanes.

## Current-Proof Reminder

- `SECURITY.md` is policy, not runtime truth.
- `enabled` means the probe observed an explicit platform capability.
- `disabled` means the probe observed an explicit negative platform capability.
- `unverified` means the probe could not prove either state; it must not be reported as enabled.
