<!-- generated: docs governance control plane; do not edit directly -->

# Runner Baseline Reference

Generated from `infra/config/self_hosted_runner_baseline.json`.

## `preflight-fast`

- docker compose required: `True`
- disk budget: tmp>=4GiB, workspace>=4GiB
- commands: `bash`, `python3`, `git`, `docker`, `rg`
- purge paths:
  - `.runtime-cache`
  - `mutants/`
  - `/tmp/video-digestor-strict-ci`

## `runner-health`

- docker compose required: `False`
- disk budget: tmp>=4GiB, workspace>=4GiB
- commands: `bash`, `python3`, `git`, `docker`, `gh`, `gcloud`, `jq`, `rg`
- purge paths:
  - `.runtime-cache`
  - `_diag/pages/*`

## `ci-heavy`

- docker compose required: `False`
- disk budget: tmp>=8GiB, workspace>=8GiB
- commands: `bash`, `python3`, `git`, `rg`
- purge paths:
  - `.runtime-cache`
  - `mutants/`
  - `/tmp/video-digestor-strict-ci`
  - `/tmp/video-digestor-*`
  - `/tmp/temporal-cli-*`

## Governance Hygiene Hooks

- runtime output root enforced by governance: `.runtime-cache`
- current-run release/readiness reports are emitted under `.runtime-cache/reports/release-readiness/`
- long-lived tracked artifacts now live under `artifacts/`, not the repository root hallway
- root cleanliness is re-checked by `check_root_dirtiness_after_tasks.py` during monthly governance audit
- monthly governance audit reuses self-hosted pre-checkout normalization before checkout
