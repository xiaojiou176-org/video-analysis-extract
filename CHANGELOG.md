# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Release observability: API now exposes `/metrics` and response `X-Trace-Id` headers.
- Release governance assets: canary rollout script, rollback runbook, release precheck generator, and release artifact manifest script.
- Performance/RUM readiness templates under `templates/release-readiness/` and baseline evidence under `reports/performance/`.

### Changed
- Hardened LLM computer-use policy: request-level overrides cannot enable computer use when `GEMINI_COMPUTER_USE_ENABLED=false`.
- Improved migration `20260222_000010_phase4_status_contract.sql` to normalize historical invalid statuses before re-applying constraints.
- CI live-smoke now targets locally started API/Worker in workflow for deterministic health checks.
- `mutation-weekly` threshold and ratio gates aligned with repository quality gate policy.

### Fixed
- Prevented historical status-contract migration failures caused by legacy job status values.

## [0.1.0] - 2026-02-21

### Added
- Initial local-first stack (API + Worker + MCP + Web) and baseline quality gates.
