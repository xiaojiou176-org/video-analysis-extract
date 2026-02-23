# Environment Governance

This repository uses a contract-first environment model:

1. Source of truth: `infra/config/env.contract.json`
2. Local template: `.env.example` (copied to `.env`)
3. Runtime access: configuration modules (`apps/api/app/config.py`, `apps/worker/worker/config.py`, `apps/mcp/server.py`)
4. Gate: `python3 scripts/check_env_contract.py --strict`

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
- `PIPELINE_RETRY_TRANSIENT_*`, `PIPELINE_RETRY_RATE_LIMIT_*`, `PIPELINE_RETRY_AUTH_*`, `PIPELINE_RETRY_FATAL_ATTEMPTS`
- `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_OUTLINE_MODEL`, `GEMINI_DIGEST_MODEL`
- `GEMINI_FAST_MODEL`, `GEMINI_EMBEDDING_MODEL`, `YOUTUBE_API_KEY`
- `GEMINI_THINKING_LEVEL`, `GEMINI_INCLUDE_THOUGHTS`, `GEMINI_STRICT_SCHEMA_MODE`
- `GEMINI_CONTEXT_CACHE_ENABLED`, `GEMINI_CONTEXT_CACHE_TTL_SECONDS`, `GEMINI_CONTEXT_CACHE_MIN_CHARS`, `GEMINI_CONTEXT_CACHE_MAX_KEYS`, `GEMINI_CONTEXT_CACHE_LOCAL_TTL_SECONDS`, `GEMINI_CONTEXT_CACHE_SWEEP_INTERVAL_SECONDS`
- `GEMINI_COMPUTER_USE_ENABLED`, `GEMINI_COMPUTER_USE_REQUIRE_CONFIRMATION`
- `GEMINI_COMPUTER_USE_MAX_STEPS`, `GEMINI_COMPUTER_USE_TIMEOUT_SECONDS`

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
- `UI_AUDIT_GEMINI_ENABLED` (API-side Gemini UI audit toggle, default `true`)

### Script Runtime

- `DIGEST_*`
- `FAILURE_*`
- `LIVE_SMOKE_*`
- `OPS_*` (workflow bootstrap overrides for `scripts/start_ops_workflows.sh`, including `OPS_CLEANUP_*`, `OPS_SHOW_HINTS`, `OPS_DRY_RUN`)
- `API_*`, `WORKER_*`, `MCP_*`, `OUTPUT_PATH`, `INIT_ENV_FORCE`
- `WEB_BASE_URL` (web e2e target override)
- `NEXT_DIST_DIR` (optional Next.js dist directory override for parallel web e2e workers)
- `PYTEST_XDIST_WORKER` (optional worker id used by web e2e fixtures to isolate runtime dirs)

`LIVE_SMOKE_*` includes strict computer-use controls:

- `LIVE_SMOKE_API_BASE_URL` / `LIVE_SMOKE_API_PORT`: API target override for live smoke. Leave `LIVE_SMOKE_API_BASE_URL` empty to follow `API_PORT`. Parent shell values have higher priority than values loaded from `.env`.
- `LIVE_SMOKE_HEALTH_PATH`: Health endpoint path used by live smoke (default `/healthz`).
- `LIVE_SMOKE_COMPUTER_USE_STRICT`: defaults to strict mode (`1`) so missing/failing computer-use smoke command fails the run.
- `LIVE_SMOKE_COMPUTER_USE_SKIP`: optional explicit skip switch; when `1`, `LIVE_SMOKE_COMPUTER_USE_SKIP_REASON` must be non-empty.
- `LIVE_SMOKE_COMPUTER_USE_CMD`: optional shell command override for computer-use smoke. By default, the script runs `scripts/smoke_computer_use_local.sh`.

`WEB_BASE_URL` controls web e2e target mode:

- unset/empty: pytest starts local Next.js (`npm run dev`) and injects mock API base URL.
- set to absolute `http(s)://...`: pytest reuses the external web instance and skips local web boot.

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
   - `python3 scripts/check_env_contract.py --strict --env-file .env.example`
   - Validates:
     - all referenced env vars are registered in `infra/config/env.contract.json`
     - every `required=true` contract variable has `default=null`
     - `.env.example` covers all required vars and web e2e critical vars
     - env-file keys (default `.env`, CI uses `.env.example`) have no unregistered variables
2. Secret scanning:
   - `gitleaks detect --source . --verbose --redact`

## CI Autofix Dry-Run

- Workflow `ci.yml` includes `autofix-dry-run` job.
- Trigger: runs when either `python-tests` or `web-e2e` fails.
- Input artifacts: junit/log files from `.runtime-cache/`.
- Output artifact: `autofix-dry-run-report-<run_id>-<run_attempt>` containing `.runtime-cache/autofix-report.json`.
- Safety: dry-run only, no code mutation.

## CI Job Topology and Cache Policy (`.github/workflows/ci.yml`)

- Job topology:
  - `preflight` is the primary prerequisite gate.
  - `db-migration-smoke` / `python-tests` / `web-lint-build` / `web-e2e` all depend on `preflight`.
  - `aggregate-gate` depends on the four jobs above and blocks when any required job is not `success`.
  - `live-smoke` depends on `aggregate-gate` and runs only when required secrets are present.
  - `autofix-dry-run` depends on `python-tests` and `web-e2e`, and runs only when either one fails.
  - `ci-final-gate` is the final gate: it always checks `aggregate-gate`, and additionally enforces `live-smoke` on `main` push / nightly schedule.
- Cache and artifacts:
  - Node deps: `actions/setup-node@v4` with `cache: npm` and `apps/web/package-lock.json`.
  - Python deps: deterministic `uv sync --frozen --extra dev --extra e2e` + explicit `actions/cache@v4` for `~/.cache/uv`.
  - Test diagnostics: `.runtime-cache/*.xml` and `.runtime-cache/*.log` are uploaded as CI artifacts; web e2e traces/videos are uploaded from `.runtime-cache/web-e2e-artifacts`.
