<!-- generated: docs governance control plane; do not edit directly -->

# Runner Baseline Reference

Generated from `infra/config/self_hosted_runner_baseline.json`.

## `preflight-fast`

- docker compose required: `True`
- disk budget: tmp>=4GiB, workspace>=4GiB
- commands: `bash`, `python3`, `git`, `docker`, `rg`
- purge paths:
  - `.runtime-cache`
  - `.venv`
  - `apps/web/node_modules`
  - `apps/web/.next-e2e-*`
  - `mutants/`
  - `/tmp/video-digestor-strict-ci`

## `runner-health`

- docker compose required: `False`
- disk budget: tmp>=4GiB, workspace>=4GiB
- commands: `bash`, `python3`, `git`, `docker`, `gh`, `gcloud`, `jq`, `rg`
- purge paths:
  - `.runtime-cache`
  - `.venv`
  - `apps/web/node_modules`
  - `_diag/pages/*`

## `ci-heavy`

- docker compose required: `False`
- disk budget: tmp>=8GiB, workspace>=8GiB
- commands: `bash`, `python3`, `git`, `rg`
- purge paths:
  - `.runtime-cache`
  - `.venv`
  - `apps/web/node_modules`
  - `apps/web/.next-e2e-*`
  - `mutants/`
  - `/tmp/video-digestor-strict-ci`
  - `/tmp/video-digestor-*`
  - `/tmp/temporal-cli-*`
