# Environment Governance

This repository uses a contract-first environment model:

1. Source of truth: `infra/config/env.contract.json`
2. Local template: `.env.example` (copied to `.env.local`)
3. Runtime access: configuration modules (`apps/api/app/config.py`, `apps/worker/worker/config.py`, `apps/mcp/server.py`)
4. Gate: `python scripts/check_env_contract.py --strict`

## Loading Order

1. Process environment variables
2. `.env.local` (auto-loaded by `scripts/dev_*.sh` and `scripts/run_*.sh`, when present)
3. Code defaults (only for optional values)

## Fail-Fast Rules

Startup validation fails when:

1. Core runtime fields are blank:
   - `DATABASE_URL`
   - `TEMPORAL_TARGET_HOST`
   - `TEMPORAL_NAMESPACE`
   - `TEMPORAL_TASK_QUEUE`
   - `SQLITE_STATE_PATH` (API)
   - `SQLITE_PATH`, `PIPELINE_WORKSPACE_DIR`, `PIPELINE_ARTIFACT_ROOT` (Worker)
2. `NOTIFICATION_ENABLED=true` but either `RESEND_API_KEY` or `RESEND_FROM_EMAIL` is missing/blank.

## Variable Tiers

### Core Runtime

- `DATABASE_URL`
- `TEMPORAL_TARGET_HOST`
- `TEMPORAL_NAMESPACE`
- `TEMPORAL_TASK_QUEUE`
- `SQLITE_PATH`
- `SQLITE_STATE_PATH`
- `PIPELINE_WORKSPACE_DIR`
- `PIPELINE_ARTIFACT_ROOT`

### Notifications

- `NOTIFICATION_ENABLED`
- `RESEND_API_KEY` (secret)
- `RESEND_FROM_EMAIL`
- `NOTIFY_TO_EMAIL`

### Worker Optional

- `RSSHUB_BASE_URL`, `FEED_URLS`, `FEED_PATHS`
- `REQUEST_TIMEOUT_SECONDS`, `REQUEST_RETRY_ATTEMPTS`, `REQUEST_RETRY_BACKOFF_SECONDS`
- `COMMENTS_TOP_N`, `COMMENTS_REPLIES_PER_COMMENT`, `COMMENTS_REQUEST_TIMEOUT_SECONDS`
- `PIPELINE_LLM_INPUT_MODE`, `PIPELINE_LLM_INCLUDE_FRAMES`
- `GEMINI_API_KEY`, `GEMINI_MODEL`, `YOUTUBE_API_KEY`

### API / MCP / Web

- `VD_API_BASE_URL`, `VD_API_TIMEOUT_SEC`, `VD_API_KEY`
- `NEXT_PUBLIC_API_BASE_URL`

### Script Runtime

- `DIGEST_*`
- `FAILURE_*`
- `API_*`, `WORKER_*`, `MCP_*`, `OUTPUT_PATH`, `INIT_ENV_FORCE`

## Local Setup

```bash
./scripts/init_env_example.sh
cp .env.local.example .env.local
# edit .env.local
```

## CI Gate

GitHub Actions workflow: `.github/workflows/env-governance.yml`

1. Environment contract check:
   - `python scripts/check_env_contract.py --strict`
2. Secret scanning:
   - `gitleaks detect --source . --verbose --redact`
