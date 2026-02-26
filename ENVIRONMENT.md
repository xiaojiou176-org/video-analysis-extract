# Environment Governance

This repository uses a contract-first environment model:

1. Source of truth: `infra/config/env.contract.json`
2. Local template: `.env.example` (copied to `.env`)
3. Runtime access: configuration modules (`apps/api/app/config.py`, `apps/worker/worker/config.py`, `apps/mcp/server.py`)
4. Gate: `python3 scripts/check_env_contract.py --strict`

`.env.example` is intentionally minimal (required + critical + high-frequency overrides). For the full script override catalog, see `docs/reference/env-script-overrides.md`.

## Core/Profile Overlay Architecture

Environment configuration is split into one core layer plus profile overlays:

1. Core baseline: `.env`
2. Profile overlay:
   - `PROFILE=local|gce` (used by bootstrap/runtime decisions)
   - `env/profiles/reader.env` (reader-only overlay; loaded only by reader-related scripts)
3. Process environment: explicit command/session overrides

Overlay scope rules:

- `.env` is the canonical runtime baseline for API/Worker/MCP/Web scripts.
- `env/profiles/reader.env` is not global; it is applied only in reader-stack flows such as:
  - `scripts/deploy_reader_stack.sh` (default path: `env/profiles/reader.env`)
  - `scripts/smoke_full_stack.sh` (reader checks)
  - `scripts/run_ai_feed_sync.sh` (reader sync path)
- Process env is allowed for temporary overrides and CI injection.

## Loading Order

1. Repo env files (`env/core.env` or fallback `env/core.env.example` -> `env/profiles/<profile>.env` -> `.env`)
2. Restore parent shell environment snapshot (same-name vars override loaded file values)
3. Code defaults (only for optional values; required variables must come from environment)

### Effective Precedence (Important)

Because most repo scripts call `load_repo_env` (which restores exported parent-shell values after loading env files), effective precedence is:

1. Script-specific explicit override handling (highest; e.g. preserved vars in `e2e_live_smoke.sh`)
2. Inherited parent-shell environment
3. Repo env files loaded by repo scripts (`env/core.env`/`env/profiles/<profile>.env`/`.env`)
4. Code defaults for optional fields only

Notes:

- In general runtime scripts, inherited parent-shell variables can overwrite `.env` values.
- For one-off overrides, use script-supported flags or explicit per-command env where documented.

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
   - `NEXT_PUBLIC_API_BASE_URL` (required for web runtime)

## Variable Tiers

### Core Runtime

- `DATABASE_URL`
- `TEMPORAL_TARGET_HOST`
- `TEMPORAL_NAMESPACE`
- `TEMPORAL_TASK_QUEUE`
- `API_TEMPORAL_CONNECT_TIMEOUT_SECONDS` (optional, API Temporal connect timeout, default `5`)
- `API_TEMPORAL_START_TIMEOUT_SECONDS` (optional, API Temporal workflow start timeout, default `10`)
- `API_TEMPORAL_RESULT_TIMEOUT_SECONDS` (optional, API Temporal workflow result timeout, default `180`)
- `API_RETRIEVAL_EMBEDDING_TIMEOUT_SECONDS` (optional, API retrieval embedding timeout, default `8`)
- `SQLITE_PATH`
- `SQLITE_STATE_PATH`
- `PIPELINE_WORKSPACE_DIR`
- `PIPELINE_ARTIFACT_ROOT`

### Notifications

- `NOTIFICATION_ENABLED`
- `RESEND_API_KEY` (secret)
- `RESEND_FROM_EMAIL`

### Worker Optional

- `RSSHUB_BASE_URL`, `RSSHUB_PUBLIC_FALLBACK_BASE_URL`, `RSSHUB_FALLBACK_BASE_URLS`, `FEED_URLS`
- `REQUEST_TIMEOUT_SECONDS`, `REQUEST_RETRY_ATTEMPTS`, `REQUEST_RETRY_BACKOFF_SECONDS`
- `COMMENTS_TOP_N`, `COMMENTS_REPLIES_PER_COMMENT`, `COMMENTS_REQUEST_TIMEOUT_SECONDS`
- `PIPELINE_LLM_INPUT_MODE`, `PIPELINE_LLM_INCLUDE_FRAMES`
- `PIPELINE_LLM_HARD_REQUIRED`, `PIPELINE_LLM_FAIL_ON_PROVIDER_ERROR`, `PIPELINE_LLM_MAX_RETRIES`
- `PIPELINE_RETRY_TRANSIENT_*`, `PIPELINE_RETRY_RATE_LIMIT_*`, `PIPELINE_RETRY_AUTH_*`, `PIPELINE_RETRY_FATAL_ATTEMPTS`
- `LLM_PROVIDER` (must be `gemini` in current runtime)
- `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_OUTLINE_MODEL`, `GEMINI_DIGEST_MODEL`
- `GEMINI_FAST_MODEL`, `GEMINI_COMPUTER_USE_MODEL`, `GEMINI_EMBEDDING_MODEL`, `YOUTUBE_API_KEY`
- `GEMINI_THINKING_LEVEL`, `GEMINI_INCLUDE_THOUGHTS`, `GEMINI_STRICT_SCHEMA_MODE`
- `GEMINI_CONTEXT_CACHE_ENABLED`, `GEMINI_CONTEXT_CACHE_TTL_SECONDS`, `GEMINI_CONTEXT_CACHE_MIN_CHARS`, `GEMINI_CONTEXT_CACHE_MAX_KEYS`, `GEMINI_CONTEXT_CACHE_LOCAL_TTL_SECONDS`, `GEMINI_CONTEXT_CACHE_SWEEP_INTERVAL_SECONDS`
- `GEMINI_COMPUTER_USE_ENABLED`, `GEMINI_COMPUTER_USE_REQUIRE_CONFIRMATION`
- `GEMINI_COMPUTER_USE_MAX_STEPS`, `GEMINI_COMPUTER_USE_TIMEOUT_SECONDS`

## Gemini-Only Model Strategy

LLM generation is Gemini-only in this repository:

1. Provider: `gemini`
   - Runtime guard: `LLM_PROVIDER` must resolve to `gemini`
2. Structured output: `response_mime_type=application/json` + strict Pydantic schema validation
3. Function calling: enabled for `llm_outline` and `llm_digest`; disabled in translation fallback
4. Thinking control: `GEMINI_THINKING_LEVEL` plus per-request override `overrides.llm.thinking_level`
5. Context cache: `GEMINI_CONTEXT_CACHE_*` controls cached prompt reuse in text mode
6. Media resolution: final multimodal input shape is resolved by
   - `PIPELINE_LLM_INPUT_MODE` (`auto|text|video_text|frames_text`)
   - `PIPELINE_MAX_FRAMES` and `overrides.frames.max_frames`
   - runtime `llm_media_input` (`video_available`, `frame_count`)

Default model lane:

- Default selected: `gemini-3.1-pro-preview`
- Supported alternates: `gemini-3.0-pro`, `gemini-3.0-flash`
- Embedding: `gemini-embedding-001`
- Computer use: `GEMINI_COMPUTER_USE_MODEL` (default `gemini-3.1-pro-preview`; can follow dedicated computer-use model when adopted)

### Secret Source and Logging Policy

- Secret keys must come from process environment or local `.env` file only.
- Reader-stack secrets (if used) must come from `env/profiles/reader.env` (or an explicit `READER_ENV_FILE` path) for reader-stack commands.
- Do not hard-code keys in source code, tests, or documentation examples.
- Runtime logs and diagnostics must never print full secret values; only masked summaries are allowed when needed for troubleshooting.
- `.env.local`, `.env.bak`, shell login profiles, and documentation snippets are not allowed as secret sources for runtime/CI.

### Embedding / Retrieval Entry

- Embedding model entry: `GEMINI_EMBEDDING_MODEL` (env contract + worker settings).
- Retrieval entry today: artifact-level retrieval via `jobs.artifacts_index` (API/MCP/Web).
- Vector retrieval API is not yet exposed as a public runtime endpoint in this phase.

### API / MCP / Web

- API/MCP runtime: `VD_API_BASE_URL`, `VD_API_TIMEOUT_SEC`, `VD_API_KEY`, `VD_ALLOW_UNAUTH_WRITE`
- Web runtime: `NEXT_PUBLIC_API_BASE_URL` (web client only reads this variable for API base URL)
- `UI_AUDIT_GEMINI_ENABLED` (API-side Gemini UI audit toggle, default `true`)
- `UI_AUDIT_ARTIFACT_BASE_ROOT` (UI audit artifact directory whitelist root; only `artifact_root` paths within this base are accepted; defaults to OS temp directory when unset)
- `VD_MCP_MAX_BASE64_BYTES` (MCP base64 payload size limit, bytes)
- `WEB_ACTION_SESSION_TOKEN` (optional server-action session secret)

Write auth behavior contract (`apps/api/app/security.py`):

- Default secure mode: protected write routes require token auth, even when `VD_API_KEY` is unset/blank.
- Compatibility override: write routes are allowed without token only when `VD_ALLOW_UNAUTH_WRITE=true`.
- Recommended production posture: set `VD_API_KEY` and keep `VD_ALLOW_UNAUTH_WRITE=false`.
- Accepted auth headers:
  - `Authorization: Bearer <VD_API_KEY>`
  - `X-API-Key: <VD_API_KEY>`
- Protected routes:
  - `POST /api/v1/subscriptions`
  - `POST /api/v1/subscriptions/batch-update-category`
  - `DELETE /api/v1/subscriptions/{id}`
  - `POST /api/v1/ingest/poll`
  - `POST /api/v1/videos/process`
  - `PUT /api/v1/notifications/config`
  - `POST /api/v1/notifications/test`
  - `POST /api/v1/notifications/category/send`
  - `POST /api/v1/reports/daily/send`
  - `POST /api/v1/workflows/run`
  - `POST /api/v1/computer-use/run`
  - `POST /api/v1/ui-audit/run`
  - `POST /api/v1/ui-audit/{run_id}/autofix`
- If `VD_API_KEY` is unset/blank and `VD_ALLOW_UNAUTH_WRITE` is not explicitly true, write requests return `401`.

Exception detail sanitization contract:

- API routers using `sanitize_exception_detail` will redact sensitive substrings before returning error details.
- Redaction patterns include:
  - `Bearer ...`, `Basic ...`
  - URL credentials (`scheme://user:pass@host`)
  - `sk-*`, `ghp_*`, `AKIA*`
  - query keys such as `api_key`, `token`, `access_token`, `refresh_token`, `jwt`, `secret`, `client_secret`, `password`, `session`, `authorization`, `signature`
- Sanitized error detail is truncated to 500 characters.

### Script Runtime

- Full script override catalog: `docs/reference/env-script-overrides.md`
- `scripts/run_daily_digest.sh` now uses CLI flags only (no `DIGEST_*` env contract vars)
- `scripts/run_failure_alerts.sh` now uses CLI flags only (no `FAILURE_*` env contract vars)
- `LIVE_SMOKE_*`
- `PR_LLM_REAL_SMOKE_*` (local PR real LLM smoke helper defaults)
- `scripts/external_playwright_smoke.sh` now uses CLI flags only (no `EXTERNAL_SMOKE_*` env contract vars)
- `OPS_*` (workflow bootstrap overrides for `scripts/start_ops_workflows.sh`, including `OPS_CLEANUP_*`, `OPS_SHOW_HINTS`, `OPS_DRY_RUN`)
- `API_*`, `WORKER_*`, `MCP_*`, `OUTPUT_PATH`, `INIT_ENV_FORCE`
- `DEV_API_RELOAD` (controls `scripts/dev_api.sh` reload mode; `scripts/full_stack.sh up` forces `0` for stable background startup)
- `API_HEALTH_URL` (optional full-stack readiness probe URL; defaults to `http://127.0.0.1:${API_PORT}/healthz`)
- `scripts/recreate_gce_instance.sh` now uses CLI flags only (no GCE recreate env contract vars)
- `WEB_BASE_URL` (web e2e target override)
- `NEXT_DIST_DIR` (optional Next.js dist directory override for parallel web e2e workers)
- `PYTEST_XDIST_WORKER` (optional worker id used by web e2e fixtures to isolate runtime dirs)
- `CORE_POSTGRES_PORT`, `CORE_POSTGRES_DB`, `CORE_POSTGRES_USER`, `CORE_POSTGRES_PASSWORD`, `CORE_REDIS_PORT`, `CORE_TEMPORAL_PORT` (docker compose core-services overrides)

`LIVE_SMOKE_*` includes strict computer-use controls:

- `LIVE_SMOKE_API_BASE_URL`: API target override for live smoke. Leave empty to follow `API_PORT` (fallback: `http://127.0.0.1:${API_PORT:-8000}`). Parent shell values have higher priority than values loaded from `.env`.
- `LIVE_SMOKE_HEALTH_PATH`: Health endpoint path used by live smoke (default `/healthz`).
- `LIVE_SMOKE_EXTERNAL_PROBE_TIMEOUT_SECONDS`: timeout seconds for provider endpoint probes in preflight (default `20`).
- `LIVE_SMOKE_HEARTBEAT_SECONDS`: heartbeat interval seconds for long-running live smoke polling logs (default `30`).
- `LIVE_SMOKE_DIAGNOSTICS_JSON`: diagnostics JSON output path (default `.runtime-cache/e2e-live-smoke-result.json`).
- `LIVE_SMOKE_COMPUTER_USE_STRICT`: defaults to strict mode (`1`) so missing/failing computer-use smoke command fails the run.
- `LIVE_SMOKE_COMPUTER_USE_SKIP`: optional explicit skip switch; when `1`, `LIVE_SMOKE_COMPUTER_USE_SKIP_REASON` must be non-empty.
- `LIVE_SMOKE_COMPUTER_USE_CMD`: optional shell command override for computer-use smoke. By default, the script runs `scripts/smoke_computer_use_local.sh`.
- `scripts/smoke_computer_use_local.sh` uses CLI flags (`--retries`, `--heartbeat-seconds`) with internal defaults.
- `YOUTUBE_API_KEY` resolution for live smoke: current environment / `.env`; no `.env.local` / `.env.bak` / shell login fallback probing.
- `OFFLINE_FALLBACK`: profile-layer fallback switch for full-stack bootstrap/smoke (`scripts/bootstrap_full_stack.sh`, `scripts/smoke_full_stack.sh`):
  - default in `env/profiles/local.env`: `0`
  - default in `env/profiles/ci.env`: `0`
  - default in `env/profiles/live-smoke.env`: `0`
  - behavior when `0`: fail-fast on core service/reader stack issues (preferred to expose real failures)
  - behavior when `1`: allow degraded path via `.runtime-cache/full-stack/offline-fallback.flag` (reader checks can be skipped)
- Failure-kind contract alignment: `e2e_live_smoke` diagnostics keep `failure_kind` in `{code_logic_error, network_or_environment_timeout}`; enabling offline fallback does not add new `failure_kind` enum values.

`scripts/external_playwright_smoke.sh` defaults (override via CLI flags):

- `--url=https://example.com`
- `--browser=chromium`
- `--timeout-ms=45000`
- `--expect-text='Example Domain'`
- `--output-dir=.runtime-cache/external-playwright-smoke`
- `--retries=2`
- `--diagnostics-json=.runtime-cache/external-playwright-smoke-result.json`
- `--heartbeat-seconds=30`

`PR_LLM_REAL_SMOKE_*` defaults (used by `scripts/smoke_llm_real_local.sh`):

- `PR_LLM_REAL_SMOKE_API_BASE_URL=http://127.0.0.1:8000`
- `PR_LLM_REAL_SMOKE_DIAGNOSTICS_JSON=.runtime-cache/pr-llm-real-smoke-result.json`
- `PR_LLM_REAL_SMOKE_HEARTBEAT_SECONDS=30`

`WEB_BASE_URL` controls web e2e target mode:

- unset/empty: pytest starts local Next.js (`npm run dev`) and injects mock API base URL.
- set to absolute `http(s)://...`: pytest reuses the external web instance and skips local web boot.

## Local Setup

```bash
./scripts/init_env_example.sh
cp .env.example .env
# edit .env
```

## Minimal Required Variables by Profile

### Shared Core (all profiles)

- `DATABASE_URL`
- `TEMPORAL_TARGET_HOST`
- `TEMPORAL_NAMESPACE`
- `TEMPORAL_TASK_QUEUE`
- `SQLITE_PATH`
- `SQLITE_STATE_PATH`
- `PIPELINE_WORKSPACE_DIR`
- `PIPELINE_ARTIFACT_ROOT`

### `local` profile

- `PROFILE=local`
- Core shared variables above
- Optional features add their own required vars:
  - Notifications: `NOTIFICATION_ENABLED=true` requires `RESEND_API_KEY` + `RESEND_FROM_EMAIL`
  - Live smoke with strict secrets requires provider keys in `.env` or process env

### `gce` profile

- `PROFILE=gce`
- Core shared variables above
- Infra/recreate scripts additionally require corresponding `GCP_*` / instance settings when invoked

### Reader overlay (`env/profiles/reader.env`, optional)

Required only when enabling reader stack (`WITH_READER_STACK=1`) or running reader sync:

- `MINIFLUX_DB_PASSWORD`
- `MINIFLUX_ADMIN_PASSWORD`
- `MINIFLUX_BASE_URL`
- Miniflux polling/cleanup values use defaults in `infra/compose/miniflux-nextflux.compose.yml` and are no longer contract-managed env keys.

## Migration Guide: Core/Profile Overlay

Fast path (recommended):

```bash
bash scripts/env/validate_profile.sh --profile local
```

Notes:

- `validate_profile.sh` writes resolved snapshot to `.runtime-cache/temp/.env.<profile>.resolved`.
- For debugging resolved values, run:
  - `bash scripts/env/compose_env.sh --profile local --write .runtime-cache/temp/.env.local.resolved`

1. Create canonical core env:
   - `cp .env.example .env`
2. Keep all app runtime/provider secrets in `.env` (or injected process env in CI).
3. If using reader stack, update the dedicated overlay file:
   - `env/profiles/reader.env`
   - keep reader-only credentials in `env/profiles/reader.env`
4. Do not use `.env.local` / `.env.bak` as runtime secret inputs.
5. Validate contract:
   - `python3 scripts/check_env_contract.py --strict`
6. For reader stack startup, use explicit env file flag:
   - default: `./scripts/deploy_reader_stack.sh up`
   - custom path: `./scripts/deploy_reader_stack.sh up --env-file <path>`

## Env Budget Guard (Anti-Bloat)

Quality gates enforce hard ceilings through `python3 scripts/check_env_budget.py`:

- `core <= 20`
- `runtime <= 100`
- `scripts <= 120`
- `universe <= 216`

If a change must exceed any limit, raise a governance PR that includes:

- rationale for the new variable(s),
- merge/reuse alternatives considered,
- synchronized updates to contract/profile/docs,
- and updated budget thresholds.

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
  - `db-migration-smoke` / `python-tests` / `api-real-smoke` / `pr-llm-real-smoke` / `backend-lint` / `frontend-lint` / `web-test-build` / `web-e2e` / `external-playwright-smoke` / `dependency-vuln-scan` all depend on `preflight` (directly or through shared setup).
  - `aggregate-gate` depends on `preflight` and all jobs above. It allows `pr-llm-real-smoke` to be `success` or `skipped`; all other listed jobs must be `success`.
  - `live-smoke` depends on `aggregate-gate`; it is required on `main` push and nightly schedule. Missing required secrets fails the job (not skipped).
  - `autofix-dry-run` depends on `python-tests` and `web-e2e`, and runs only when either one fails.
  - `ci-final-gate` is the final gate: it always checks `aggregate-gate`, and additionally enforces `live-smoke` on `main` push / nightly schedule.
- Cache and artifacts:
  - Node deps: `actions/setup-node@v4` with `cache: npm` and `apps/web/package-lock.json`.
  - Python deps: deterministic `uv sync --frozen --extra dev --extra e2e` + explicit `actions/cache@v4` for `~/.cache/uv`.
  - Test diagnostics: `.runtime-cache/*.xml` and `.runtime-cache/*.log` are uploaded as CI artifacts; web e2e traces/videos are uploaded from `.runtime-cache/web-e2e-artifacts`.

### CI Trigger Boundary (PR vs main vs nightly)

- `pull_request`: runs aggregate test/lint/build gates (including `external-playwright-smoke`), while `live-smoke` is optional (`skipped` is allowed). It may also run conditional real LLM smoke `pr-llm-real-smoke` only when all are true: same-repo PR (`head.repo.full_name == github.repository`) and non-empty `GEMINI_API_KEY`; otherwise `skipped`.
- `push` to `main`: `live-smoke` becomes mandatory and must be `success`.
- `schedule` nightly: both `live-smoke` and `nightly-flaky-*` subsets are mandatory.

### Live Smoke Secret Contract (CI Required)

When `live-smoke` is required (`main` push / nightly schedule), these secrets must be configured:

- `GEMINI_API_KEY`
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `YOUTUBE_API_KEY`

Without any of the above, `live-smoke` fails and `ci-final-gate` blocks merge/release.
