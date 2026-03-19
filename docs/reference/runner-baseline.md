# Self-Hosted Runner Baseline

This document defines the minimum contract for self-hosted runners. The goal is not to let workflows install whatever is missing on the fly, but to require the runner to satisfy fixed prerequisites before repository CI starts.

## Sources Of Truth

- Contract file: `infra/config/self_hosted_runner_baseline.json`
- Check script: `scripts/governance/check_runner_baseline.py`
- Call sites:
  - `.github/workflows/_preflight-fast-steps.yml` uses `--profile preflight-fast`
  - `.github/workflows/runner-health.yml` uses `--profile runner-health`

## Current Profiles

### `preflight-fast`

Must exist:

- `bash`
- `python3`
- `git`
- `docker`
- `rg`
- `docker compose`

### `runner-health`

Must exist:

- `bash`
- `python3`
- `git`
- `docker`
- `gh`
- `gcloud`
- `jq`
- `rg`

## Governance Rules

- Workflows must no longer patch missing runner tools with `apt-get install`.
- If the runner is missing a contract-required tool, fail directly in preflight or runner-health.
- `runner-health.yml` owns runner control-plane health checks; the main `ci.yml` no longer carries runner-ops duties.
