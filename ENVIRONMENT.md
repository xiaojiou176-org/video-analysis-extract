# Environment Governance

This repository uses a contract-first environment model:

1. Source of truth: `infra/config/env.contract.json`
2. Local template: `.env.example` (copied to `.env`)
3. Runtime access: configuration modules (`apps/api/app/config.py`, `apps/worker/worker/config.py`, `apps/mcp/server.py`)
4. Gate: `python scripts/check_env_contract.py --strict`

## Loading Order

1. Process environment variables
2. `.env` (canonical local source, auto-loaded by `scripts/dev_*.sh` and `scripts/run_*.sh`)
3. `.env.local` (legacy fallback only when `.env` is absent)
4. Code defaults (only for optional values; required variables must come from environment)

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
3. Web API client cannot resolve a valid base URL:
   - `NEXT_PUBLIC_API_BASE_URL` (preferred) or
   - `VD_API_BASE_URL` (compat fallback)

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
- `PIPELINE_LLM_HARD_REQUIRED`, `PIPELINE_LLM_FAIL_ON_PROVIDER_ERROR`, `PIPELINE_LLM_MAX_RETRIES`
- `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_OUTLINE_MODEL`, `GEMINI_DIGEST_MODEL`
- `GEMINI_FAST_MODEL`, `GEMINI_EMBEDDING_MODEL`, `YOUTUBE_API_KEY`
- `GEMINI_THINKING_LEVEL`, `GEMINI_INCLUDE_THOUGHTS`
- `GEMINI_CONTEXT_CACHE_ENABLED`, `GEMINI_CONTEXT_CACHE_TTL_SECONDS`, `GEMINI_CONTEXT_CACHE_MIN_CHARS`

## Gemini-Only Model Strategy

LLM generation is Gemini-only in this repository:

1. Provider: `gemini`
2. Structured output: `response_mime_type=application/json` + strict Pydantic schema validation
3. Function calling: enabled for `llm_outline` and `llm_digest`; disabled in translation fallback
4. Thinking control: `GEMINI_THINKING_LEVEL` plus per-request override `overrides.llm.thinking_level`
5. Context cache: `GEMINI_CONTEXT_CACHE_*` controls cached prompt reuse in text mode
6. Media resolution: final multimodal input shape is resolved by
   - `PIPELINE_LLM_INPUT_MODE` (`auto|text|video_text|frames_text`)
   - `PIPELINE_MAX_FRAMES` and `overrides.frames.max_frames`
   - runtime `llm_media_input` (`video_available`, `frame_count`)

### Embedding / Retrieval Entry

- Embedding model entry: `GEMINI_EMBEDDING_MODEL` (env contract + worker settings).
- Retrieval entry today: artifact-level retrieval via `jobs.artifacts_index` (API/MCP/Web).
- Vector retrieval API is not yet exposed as a public runtime endpoint in this phase.

### API / MCP / Web

- `VD_API_BASE_URL`, `VD_API_TIMEOUT_SEC`, `VD_API_KEY`
- `NEXT_PUBLIC_API_BASE_URL`

### Script Runtime

- `DIGEST_*`
- `FAILURE_*`
- `LIVE_SMOKE_*`
- `API_*`, `WORKER_*`, `MCP_*`, `OUTPUT_PATH`, `INIT_ENV_FORCE`

## Local Setup

```bash
./scripts/init_env_example.sh
cp .env.example .env
# edit .env
# optional legacy fallback:
# cp .env .env.local
# (only used when .env is missing)
```

## CI Gate

GitHub Actions workflow: `.github/workflows/env-governance.yml`

1. Environment contract check:
   - `python scripts/check_env_contract.py --strict`
   - Validates:
     - all referenced env vars are registered in `infra/config/env.contract.json`
     - every `required=true` contract variable has `default=null`
     - `.env.example` covers all required vars and web e2e critical vars
2. Secret scanning:
   - `gitleaks detect --source . --verbose --redact`
