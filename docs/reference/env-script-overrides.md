# Script Env Overrides Reference

本页收纳脚本层环境变量全集（从历史 `.env.example` 脚本区块迁移而来）。

使用原则：
- 新手启动优先使用 `.env.example` 最小模板。
- 仅在需要覆盖脚本默认行为时，再设置本文变量。
- 推荐临时按命令注入（`VAR=value ./scripts/xxx.sh`），避免长期污染 `.env`。

## Daily Digest Script (`scripts/run_daily_digest.sh`)

- `DIGEST_CHANNEL` (default: `email`)
- `DIGEST_DRY_RUN` (default: `false`)
- `DIGEST_FORCE` (default: `false`)
- `DIGEST_FALLBACK_ENABLED` (default: `1`)
- `DIGEST_TO_EMAIL` (optional)
- `DIGEST_DATE` (optional, `YYYY-MM-DD`)

## Live Smoke Script (`scripts/e2e_live_smoke.sh`)

- `LIVE_SMOKE_API_BASE_URL` (default: empty -> follow `API_PORT`)
- `LIVE_SMOKE_HEALTH_PATH` (default: `/healthz`)
- `LIVE_SMOKE_TIMEOUT_SECONDS` (default: `180`)
- `LIVE_SMOKE_EXTERNAL_PROBE_TIMEOUT_SECONDS` (default: `20`)
- `LIVE_SMOKE_REQUIRE_API` (default: `1`)
- `LIVE_SMOKE_REQUIRE_SECRETS` (default: `0`)
- `LIVE_SMOKE_POLL_INTERVAL_SECONDS` (default: `3`)
- `LIVE_SMOKE_HEARTBEAT_SECONDS` (default: `30`)
- `LIVE_SMOKE_MAX_RETRIES` (default: `2`)
- `LIVE_SMOKE_DIAGNOSTICS_JSON` (default: `.runtime-cache/e2e-live-smoke-result.json`)
- `LIVE_SMOKE_COMPUTER_USE_STRICT` (default: `1`)
- `LIVE_SMOKE_COMPUTER_USE_SKIP` (default: `0`)
- `LIVE_SMOKE_COMPUTER_USE_SKIP_REASON` (required when skip=1)
- `LIVE_SMOKE_COMPUTER_USE_CMD` (default: `scripts/smoke_computer_use_local.sh`)
- `YOUTUBE_SMOKE_URL` (default: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`)
- `BILIBILI_SMOKE_URL` (default: `https://www.bilibili.com/video/BV1xx411c7mD`)

## PR Real LLM Smoke (`scripts/smoke_llm_real_local.sh`)

- `PR_LLM_REAL_SMOKE_API_BASE_URL` (default: `http://127.0.0.1:8000`)
- `PR_LLM_REAL_SMOKE_DIAGNOSTICS_JSON` (default: `.runtime-cache/pr-llm-real-smoke-result.json`)
- `PR_LLM_REAL_SMOKE_HEARTBEAT_SECONDS` (default: `30`)

## External Playwright Smoke (`scripts/external_playwright_smoke.sh`)

- `EXTERNAL_SMOKE_URL` (default: `https://example.com`)
- `EXTERNAL_SMOKE_BROWSER` (default: `chromium`)
- `EXTERNAL_SMOKE_TIMEOUT_MS` (default: `45000`)
- `EXTERNAL_SMOKE_EXPECT_TEXT` (default: `Example Domain`)
- `EXTERNAL_SMOKE_OUTPUT_DIR` (default: `.runtime-cache/external-playwright-smoke`)
- `EXTERNAL_SMOKE_RETRIES` (default: `2`)
- `EXTERNAL_SMOKE_DIAGNOSTICS_JSON` (default: `.runtime-cache/external-playwright-smoke-result.json`)
- `EXTERNAL_SMOKE_HEARTBEAT_SECONDS` (default: `30`)

## Failure Alerts Script (`scripts/run_failure_alerts.sh`)

- `FAILURE_CHANNEL` (default: `email`)
- `FAILURE_LOOKBACK_HOURS` (default: `24`)
- `FAILURE_LIMIT` (default: `20`)
- `FAILURE_DRY_RUN` (default: `false`)
- `FAILURE_FORCE` (default: `false`)
- `FAILURE_FALLBACK_ENABLED` (default: `1`)
- `FAILURE_TO_EMAIL` (optional)

## Script Entry Overrides (`scripts/dev_*.sh`, `scripts/init_env_example.sh`)

- `API_APP` (default: `apps.api.app.main:app`)
- `API_HOST` (default: `127.0.0.1`)
- `API_PORT` (default: `8000`)
- `API_HEALTH_URL` (default: `http://127.0.0.1:8000/healthz`)
- `DEV_API_RELOAD` (default: `1`)
- `WORKER_DIR` (default: `$PWD/apps/worker`)
- `WORKER_ENTRY` (default: `worker.main`)
- `WORKER_COMMAND` (default: `run-worker`)
- `DEV_WORKER_SHOW_HINTS` (default: `1`)
- `MCP_DIR` (default: `$PWD/apps/mcp`)
- `MCP_ENTRY` (default: `apps.mcp.server`)
- `OUTPUT_PATH` (default: `$PWD/.env.output.example`)
- `INIT_ENV_FORCE` (default: `0`)

## Ops Workflow Bootstrap (`scripts/start_ops_workflows.sh`)

- `OPS_DAILY_LOCAL_HOUR` (default: fallback `DIGEST_DAILY_LOCAL_HOUR` -> `9`)
- `OPS_DAILY_TIMEZONE` (default: fallback `DIGEST_LOCAL_TIMEZONE` -> `system-local`)
- `OPS_DAILY_TIMEZONE_OFFSET_MINUTES` (optional)
- `OPS_DAILY_WORKFLOW_ID` (default: `daily-digest-workflow`)
- `OPS_DAILY_RUN_ONCE` (default: `0`)
- `OPS_NOTIFICATION_INTERVAL_MINUTES` (default: `10`)
- `OPS_NOTIFICATION_RETRY_BATCH_LIMIT` (default: `50`)
- `OPS_NOTIFICATION_WORKFLOW_ID` (default: `notification-retry-workflow`)
- `OPS_NOTIFICATION_RUN_ONCE` (default: `0`)
- `OPS_CANARY_INTERVAL_HOURS` (default: `1`)
- `OPS_CANARY_TIMEOUT_SECONDS` (default: `8`)
- `OPS_CANARY_WORKFLOW_ID` (default: `provider-canary-workflow`)
- `OPS_CANARY_RUN_ONCE` (default: `0`)
- `OPS_CLEANUP_INTERVAL_HOURS` (default: `6`)
- `OPS_CLEANUP_OLDER_THAN_HOURS` (default: `24`)
- `OPS_CLEANUP_CACHE_OLDER_THAN_HOURS` (optional)
- `OPS_CLEANUP_CACHE_MAX_SIZE_MB` (optional)
- `OPS_CLEANUP_WORKSPACE_DIR` (optional)
- `OPS_CLEANUP_CACHE_DIR` (optional)
- `OPS_CLEANUP_WORKFLOW_ID` (default: `cleanup-workspace-workflow`)
- `OPS_CLEANUP_RUN_ONCE` (default: `0`)
- `OPS_DRY_RUN` (default: `0`)
- `OPS_SHOW_HINTS` (default: `1`)

## Full Stack Helper Scripts (`scripts/bootstrap_full_stack.sh`, `scripts/full_stack.sh`, `scripts/smoke_full_stack.sh`)

- `PROFILE` (default: `local`)
- `WITH_CORE_SERVICES` (default: `1`)
- `WITH_READER_STACK` (default: `1`)
- `OFFLINE_FALLBACK` (default: `1`)
- `FULL_STACK_REQUIRE_READER` (default: `1`)

## Recreate GCE Instance (`scripts/recreate_gce_instance.sh`)

- `GCP_PROJECT` (required when running recreate script)
- `GCP_ZONE` (default: `us-west1-b`)
- `INSTANCE_NAME` (default: `vd-prod`)
- `MACHINE_TYPE` (default: `e2-standard-2`)
- `DISK_SIZE` (default: `50GB`)
- `IMAGE_FAMILY` (default: `debian-12`)
- `IMAGE_PROJECT` (default: `debian-cloud`)
- `GITHUB_REPO_URL` (optional)
- `FORCE_DELETE_INSTANCE` (default: `0`)
- `FORCE_REPLACE_APP_DIR` (default: `0`)
- `INSTALL_DEPS` (default: `1`)
