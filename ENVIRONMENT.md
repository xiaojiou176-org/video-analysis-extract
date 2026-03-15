# Environment Governance

This repository uses a contract-first environment model:

1. Source of truth: `infra/config/env.contract.json`
2. Local template: `.env.example` (copied to `.env`)
3. Runtime access: configuration modules (`apps/api/app/config.py`, `apps/worker/worker/config.py`, `apps/mcp/server.py`)
4. Gate: `python3 scripts/governance/check_env_contract.py --strict`

`.env.example` is intentionally minimal (required + critical + high-frequency overrides). For the full script override catalog, see `docs/reference/env-script-overrides.md`.
Standard initialization path is fixed to `.env.example -> .env` (`cp .env.example .env`); `scripts/env/init_example.sh` is an optional helper for generating auxiliary templates only.

## Core/Profile Overlay Architecture

Environment configuration is split into one core layer plus profile overlays:

1. Core baseline: `.env`
2. Profile overlay:
   - `env/profiles/reader.env` (reader-only overlay; loaded only by reader-related scripts)
3. Process environment: explicit command/session overrides

Overlay scope rules:

- `.env` is the canonical runtime baseline for API/Worker/MCP/Web scripts.
- `env/profiles/reader.env` is not global; it is applied only in reader-stack flows such as:
  - `scripts/deploy/reader_stack.sh` (default path: `env/profiles/reader.env`)
  - `scripts/ci/smoke_full_stack.sh` (reader checks)
  - `scripts/runtime/run_ai_feed_sync.sh` (reader sync path)
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

## Full-Stack Routing Truth Source

For full-stack local scripts (`bootstrap_full_stack.sh` / `full_stack.sh` / `smoke_full_stack.sh`):

1. `API_PORT` and `WEB_PORT` are the routing source of truth.
2. `VD_API_BASE_URL` and `NEXT_PUBLIC_API_BASE_URL` are derived URLs by default (unless explicitly overridden by CLI flags such as `--api-base-url`).
3. Runtime decisions (port fallback, derived routing values) are written to `.runtime-cache/run/full-stack/resolved.env`.
4. `bootstrap_full_stack.sh` does not persist runtime decisions back into `.env` (except first-copy from `.env.example` when `.env` is missing).
5. `bootstrap_full_stack.sh` defaults to `--offline-fallback 1` (may write `.runtime-cache/run/full-stack/offline-fallback.flag`), while `smoke_full_stack.sh` defaults to `--offline-fallback 0`; reader checks are skipped only when smoke is explicitly run with `--offline-fallback 1` and the marker exists.

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
4. `full_stack.sh up` cannot reach `TEMPORAL_TARGET_HOST` (Worker Temporal preflight; default `localhost:7233`).

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
- `GITHUB_TOKEN` (CI-only, used by reporting scripts such as KPI/flaky collectors; injected by GitHub Actions, not required in local `.env`)

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
- Computer use: `GEMINI_COMPUTER_USE_MODEL` (default `gemini-2.5-computer-use-preview-10-2025`; this must point at the dedicated computer-use preview model, not the generic `GEMINI_MODEL`)

### Secret Source and Logging Policy

- Secret keys must come from process environment or local `.env` file only.
- Reader-stack secrets (if used) must come from `env/profiles/reader.env` for reader-stack commands.
- Do not hard-code keys in source code, tests, or documentation examples.
- Runtime logs and diagnostics must never print full secret values; only masked summaries are allowed when needed for troubleshooting.
- `.env.local`, `.env.bak`, shell login profiles, and documentation snippets are not allowed as secret sources for runtime/CI.

### Embedding / Retrieval Entry

- Embedding model entry: `GEMINI_EMBEDDING_MODEL` (env contract + worker settings).
- Retrieval entry today: artifact-level retrieval via `jobs.artifacts_index` (API/MCP/Web).
- Vector retrieval API is not yet exposed as a public runtime endpoint in this phase.

### API / MCP / Web

- Routing truth source for local full-stack scripts: `API_PORT`, `WEB_PORT`.
- API/MCP runtime: `VD_API_BASE_URL`, `VD_API_TIMEOUT_SEC`, `VD_API_KEY`, `VD_ALLOW_UNAUTH_WRITE`, `VD_CI_ALLOW_UNAUTH_WRITE`, `VD_API_RETRY_ATTEMPTS`, `VD_API_RETRY_BACKOFF_SEC`
- Web runtime: `NEXT_PUBLIC_API_BASE_URL` (web client only reads this variable for API base URL; usually derived from `API_PORT` in local full-stack flows)
- `UI_AUDIT_GEMINI_ENABLED` (API-side Gemini UI audit toggle, default `true`)
- `UI_AUDIT_ARTIFACT_BASE_ROOT` (UI audit artifact directory whitelist root; only `artifact_root` paths within this base are accepted; defaults to OS temp directory when unset)
- `UI_AUDIT_RUN_STORE_DIR` (persisted UI audit run snapshot directory, default `.runtime-cache/evidence/tests/ui-audit-runs`)
- `UV_PROJECT_ENVIRONMENT` (hard-cut Python virtual environment path; recommended local default `$HOME/.cache/video-digestor/project-venv`, replacing workspace-root `.venv`)
- `VD_MCP_MAX_BASE64_BYTES` (MCP base64 payload size limit, bytes)
- `WEB_ACTION_SESSION_TOKEN` (optional server-action session secret)
- CI UI/UX audit report output path is fixed to `.runtime-cache/reports/ui-audit/gemini-ui-ux-audit-report.json` in the strict CI workflow.

Write auth behavior contract (`apps/api/app/security.py`):

- Default secure mode: protected write routes require token auth, even when `VD_API_KEY` is unset/blank.
- Compatibility override: write routes are allowed without token only when:
  - test runtime sets `PYTEST_CURRENT_TEST`, or
  - GitHub Actions CI explicitly opts in with all of `VD_ALLOW_UNAUTH_WRITE=true`, `CI=true`, `GITHUB_ACTIONS=true`, and `VD_CI_ALLOW_UNAUTH_WRITE=true`.
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
- If `VD_API_KEY` is unset/blank, write requests return `401` unless either `PYTEST_CURRENT_TEST` is present, or GitHub Actions CI satisfies all of `VD_ALLOW_UNAUTH_WRITE=true`, `CI=true`, `GITHUB_ACTIONS=true`, and `VD_CI_ALLOW_UNAUTH_WRITE=true`.

MCP upstream retry behavior (`apps/mcp/server.py`):

- `VD_API_RETRY_ATTEMPTS` controls retry count for retryable methods (`GET/HEAD/OPTIONS`), clamped to `1..5` (default `1`).
- `VD_API_RETRY_BACKOFF_SEC` controls exponential backoff base seconds, clamped to `0..5` (default `0.2`).

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
- `scripts/runtime/run_daily_digest.sh` now uses CLI flags only (no `DIGEST_*` env contract vars)
- `scripts/runtime/run_failure_alerts.sh` now uses CLI flags only (no `FAILURE_*` env contract vars)
- Live-smoke and PR LLM smoke controls are CLI-first (see `docs/reference/env-script-overrides.md`).
- `scripts/ci/external_playwright_smoke.sh` now uses CLI flags only (no `EXTERNAL_SMOKE_*` env contract vars)
- Script entry controls for `dev_api/dev_worker/dev_mcp/init_env_example` are CLI-only after Batch C (see `docs/reference/env-script-overrides.md`)
- `scripts/deploy/recreate_gce_instance.sh` now uses CLI flags only (no GCE recreate env contract vars)
- `CORE_POSTGRES_PORT`, `CORE_POSTGRES_PASSWORD` (docker compose core-services overrides)
- `GHCR_USERNAME`, `GHCR_TOKEN` are optional local-only credentials for pulling the private strict CI standard image from `ghcr.io` during `scripts/strict_ci_entry.sh` runs.
- `VD_STANDARD_ENV_LOAD_PLATFORM_ARCH`, `API_REAL_SMOKE_DATABASE_URL`, `API_REAL_SMOKE_TEMPORAL_TARGET_HOST`, and `FULL_STACK_TEMPORAL_POLLER_READY_TIMEOUT_SECONDS` are optional script/runtime overrides for strict standard image loading, API real-smoke targeting, and full-stack Temporal readiness waits.
- `TMPDIR`, `UV_LINK_MODE`, `UV_PROJECT_ENVIRONMENT`, and `PYTHONDONTWRITEBYTECODE` are optional local strict-runtime overrides used by `scripts/ci/bootstrap_strict_ci_runtime.sh`, `scripts/ci/python_tests.sh`, and `scripts/governance/quality_gate.sh` to keep Python verification environments out of the workspace and suppress repo-side `__pycache__` / `*.pyc` residue.
- `GCP_PROJECT_ID`, `GCP_ZONE` are optional defaults for runner maintenance helpers:
  - `scripts/governance/audit_github_runner_host.sh`
  - `scripts/deploy/apply_github_runner_startup_metadata.sh`
  - CLI flags still take precedence over env defaults

Live smoke includes strict computer-use controls via CLI flags in `scripts/ci/e2e_live_smoke.sh`.
- `scripts/ci/e2e_live_smoke.sh` default contract is `--require-api=1` and `--require-secrets=1`; `scripts/quality_gate.sh` live-smoke profile gate enforces these defaults.

- `scripts/ci/smoke_computer_use_local.sh` uses CLI flags (`--retries`, `--heartbeat-seconds`) with internal defaults.
- `YOUTUBE_API_KEY` resolution for live smoke: current environment / `.env`; no `.env.local` / `.env.bak` / shell login fallback probing.
- Batch B CLI controls in `scripts/ci/e2e_live_smoke.sh` (not env contract vars):
  - `--health-path` (default `/healthz`)
  - `--timeout-seconds` (default `180`)
  - `--poll-interval-seconds` (default `3`)
  - `--heartbeat-seconds` (default `30`)
  - `--external-probe-timeout-seconds` (default `20`)
  - `--max-retries` (default `2`)
  - `--diagnostics-json` (default `.runtime-cache/reports/tests/e2e-live-smoke-result.json`)
  - `--computer-use-cmd` (default `scripts/ci/smoke_computer_use_local.sh`)
  - `--bilibili-url` (default `https://www.bilibili.com/video/BV1xx411c7mD`)
- Full-stack bootstrap/smoke fallback behavior is controlled by CLI flags in the scripts above.
- Failure-kind contract alignment: `e2e_live_smoke` diagnostics keep `failure_kind` in `{code_logic_error, network_or_environment_timeout}`; enabling offline fallback does not add new `failure_kind` enum values.
- `LIVE_SMOKE_API_BASE_URL` is the canonical live-smoke API target variable for manual smoke runs; CI live-smoke jobs pin the local target to `http://127.0.0.1:18080`.
- CI runtime process probes for live-smoke use ephemeral env vars exported by workflow steps:
  - `LIVE_SMOKE_API_PID`
  - `LIVE_SMOKE_WORKER_PID`
  - `LIVE_SMOKE_TEMPORAL_PID`
- CI pins Temporal CLI download integrity with `TEMPORAL_CLI_VERSION`, `TEMPORAL_CLI_SHA256_LINUX_AMD64`, and `TEMPORAL_CLI_SHA256_LINUX_ARM64`.
- CI/Test behavior flags are contract-registered:
  - `CI` / `GITHUB_ACTIONS`: CI context detection flags (hosted CI normally injects these automatically).
  - `API_INTEGRATION_SMOKE_STRICT`: local strictness override for `apps/api/tests/test_api_integration_smoke.py`.
    - `unset/0`: local default fast mode; unmet real-Postgres requirements can `xfail`.
    - `1`: strict mode; unmet requirements or failures are blocking.
  - `WEB_E2E_USE_MOCK_API`: local-only debug toggle for web E2E mock API wiring; CI/mainline must keep real API path.
- `WEB_E2E_NEXT_DIST_DIR`: optional E2E-only Next.js distDir isolation; used to avoid concurrent `.next/dev/lock` contention across parallel E2E workers.
- `WEB_RUNTIME_WEB_DIR`: runtime workspace path prepared by `scripts/ci/prepare_web_runtime.sh`; points to the isolated apps/web execution tree under `.runtime-cache/tmp/web-runtime`.
- `WEB_E2E_RUNTIME_WEB_DIR`: optional E2E override for the prepared runtime apps/web workspace path.
- `VIDEO_ANALYSIS_REPO_ROOT`: explicit repo root override used when Web runtime workspaces execute from copied paths outside the checked-in `apps/web` tree.

Local verification boundary:

- `DATABASE_URL='sqlite+pysqlite:///:memory:'` is the default fast regression path.
- Real Postgres integration smoke must run separately via `./scripts/ci/api_real_smoke_local.sh` (for CI parity), and `smoke_full_stack.sh` is not a replacement for that backend integration gate.

`scripts/ci/external_playwright_smoke.sh` defaults (override via CLI flags):

- `--url=https://example.com`
- `--browser=chromium`
- `--timeout-ms=45000`
- `--expect-text='Example Domain'`
- `--output-dir=.runtime-cache/evidence/tests/external-playwright-smoke`
- `--retries=2`
- `--diagnostics-json=.runtime-cache/reports/tests/external-playwright-smoke-result.json`
- `--heartbeat-seconds=30`

`scripts/ci/smoke_llm_real_local.sh` defaults:

- API base URL defaults to `http://127.0.0.1:8000` unless overridden by CLI.
- `--diagnostics-json=.runtime-cache/reports/tests/pr-llm-real-smoke-result.json` (CLI)
- `--heartbeat-seconds=30` (CLI)
- `--max-retries=2` (CLI)

`--web-e2e-base-url` controls web e2e target mode:

- unset/empty: pytest starts local Next.js (`npm run dev`) and injects real API base URL from `--web-e2e-api-base-url` (default `http://127.0.0.1:18080`).
- set to absolute `http(s)://...`: pytest reuses the external web instance and skips local web boot.
- mock API is local debug only: enable via `--web-e2e-use-mock-api=1` or `WEB_E2E_USE_MOCK_API=1`.

## Local Setup

```bash
cp .env.example .env
# edit .env
```

Optional helper (not the default path):

```bash
./scripts/env/init_example.sh --output .runtime-cache/tmp/.env.generated.example --force
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

- Core shared variables above
- Optional features add their own required vars:
  - Notifications: `NOTIFICATION_ENABLED=true` requires `RESEND_API_KEY` + `RESEND_FROM_EMAIL`
  - Live smoke with strict secrets requires provider keys in `.env` or process env

### `gce` profile

- Core shared variables above
- Infra/recreate scripts additionally require corresponding `GCP_*` / instance settings when invoked

### Reader overlay (`env/profiles/reader.env`, optional)

Required when running reader sync / reader stack related commands:

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

- `validate_profile.sh` writes resolved snapshot to `.runtime-cache/tmp/.env.<profile>.resolved`.
- For debugging resolved values, run:
  - `bash scripts/env/compose_env.sh --profile local --write .runtime-cache/tmp/.env.local.resolved`

1. Create canonical core env:
   - `cp .env.example .env`
2. Keep all app runtime/provider secrets in `.env` (or injected process env in CI).
3. If using reader stack, update the dedicated overlay file:
   - `env/profiles/reader.env`
   - keep reader-only credentials in `env/profiles/reader.env`
4. Do not use `.env.local` / `.env.bak` as runtime secret inputs.
5. Validate contract:
   - `python3 scripts/governance/check_env_contract.py --strict`
6. For reader stack startup, use explicit env file flag:
   - default: `./scripts/deploy/reader_stack.sh up`
   - custom path: `./scripts/deploy/reader_stack.sh up --env-file <path>`

## Env Budget Guard (Anti-Bloat)

Quality gates enforce hard ceilings through `python3 scripts/governance/check_env_budget.py`:

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
   - `python3 scripts/governance/check_env_contract.py --strict --env-file .env.example`
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
- Output artifact: `autofix-dry-run-report-<run_id>-<run_attempt>` containing `.runtime-cache/reports/autofix/autofix-report.json`.
- Safety: dry-run only, no code mutation.

## CI Job Topology and Cache Policy (`.github/workflows/ci.yml`)

- Job topology:
  - `preflight-fast` is the primary prerequisite gate; `preflight-heavy` depends on `preflight-fast` and is enforced by `aggregate-gate`.
  - `db-migration-smoke` / `python-tests` / `api-real-smoke` / `pr-llm-real-smoke` / `backend-lint` / `frontend-lint` / `web-test-build` / `web-e2e` / `external-playwright-smoke` / `dependency-vuln-scan` depend on `preflight-fast` (directly or through shared setup).
  - `aggregate-gate` depends on `preflight-fast` + `preflight-heavy` and all jobs above. It allows `pr-llm-real-smoke` and `external-playwright-smoke` to be `success` or `skipped` (depending on trigger boundary / change scope); required jobs must be `success`.
  - `live-smoke` depends on `aggregate-gate`; it is required on `main` push and nightly schedule. Missing required secrets fails the job (not skipped).
  - `autofix-dry-run` depends on `python-tests` and `web-e2e`, and runs only when either one fails.
  - `ci-final-gate` is the final gate: it always checks `aggregate-gate`, and additionally enforces `live-smoke` on `main` push / nightly schedule.
- Cache and artifacts:
  - Node deps: `actions/setup-node@v4` with `cache: npm` and `apps/web/package-lock.json`.
  - Python deps: deterministic `uv sync --frozen --extra dev --extra e2e` + explicit `actions/cache@v4` for `~/.cache/uv`.
  - Test diagnostics: `.runtime-cache/*.xml` and `.runtime-cache/*.log` are uploaded as CI artifacts; web e2e traces/videos are uploaded from `.runtime-cache/evidence/tests/web-e2e-artifacts`.

### CI Trigger Boundary (PR vs main vs nightly)

- `pull_request`: runs aggregate test/lint/build gates; `external-playwright-smoke` is not triggered on PR and is accepted as `skipped`. `live-smoke` is optional (`skipped` is allowed). `pr-llm-real-smoke` is conditional and only runs when all are true: same-repo PR (`head.repo.full_name == github.repository`) and `needs.changes.outputs.backend_changed == 'true'`; otherwise `skipped`. If it runs but `GEMINI_API_KEY` is missing, the job fails.
- `push` to `main`: `live-smoke` becomes mandatory and must be `success`.
- `schedule` nightly: both `live-smoke` and `nightly-flaky-*` subsets are mandatory.

### Live Smoke Secret Contract (CI Required)

When `live-smoke` is required (`main` push / nightly schedule), these secrets must be configured:

- `GEMINI_API_KEY`
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `YOUTUBE_API_KEY`

Without any of the above, `live-smoke` fails and `ci-final-gate` blocks merge/release.
