# Script Env Overrides Reference

本页收纳脚本层环境变量全集（从历史 `.env.example` 脚本区块迁移而来）。

使用原则：

- 新手启动优先使用 `.env.example` 最小模板。
- 仅在需要覆盖脚本默认行为时，再设置本文变量。
- 推荐临时按命令注入（`VAR=value ./scripts/xxx.sh`），避免长期污染 `.env`。

## Daily Digest Script (`scripts/run_daily_digest.sh`)

This script no longer consumes `DIGEST_*` env vars.
Use CLI flags instead (`--date`, `--channel`, `--dry-run`, `--force`, `--to-email`, `--fallback-enabled`, `--api-base-url`).

## Live Smoke Script (`scripts/e2e_live_smoke.sh`)

- `LIVE_SMOKE_REQUIRE_API` (default: `1`)
- `LIVE_SMOKE_REQUIRE_SECRETS` (default: `0`)
- `LIVE_SMOKE_COMPUTER_USE_STRICT` (default: `1`)
- `LIVE_SMOKE_COMPUTER_USE_SKIP` (default: `0`)
- `LIVE_SMOKE_COMPUTER_USE_SKIP_REASON` (required when skip=1)
- `YOUTUBE_SMOKE_URL` (default: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`)

Batch B 口径：以下参数已切换为 CLI 优先（legacy env 仅兼容，不建议继续配置）：

- `LIVE_SMOKE_API_BASE_URL` -> `--api-base-url`
- `LIVE_SMOKE_TIMEOUT_SECONDS` -> `--timeout-seconds`
- `LIVE_SMOKE_POLL_INTERVAL_SECONDS` -> `--poll-interval-seconds`
- `LIVE_SMOKE_HEARTBEAT_SECONDS` -> `--heartbeat-seconds`
- `LIVE_SMOKE_HEALTH_PATH` -> `--health-path`
- `LIVE_SMOKE_EXTERNAL_PROBE_TIMEOUT_SECONDS` -> `--external-probe-timeout-seconds`
- `LIVE_SMOKE_MAX_RETRIES` -> `--max-retries`
- `LIVE_SMOKE_DIAGNOSTICS_JSON` -> `--diagnostics-json`
- `LIVE_SMOKE_COMPUTER_USE_CMD` -> `--computer-use-cmd`
- `BILIBILI_SMOKE_URL` -> `--bilibili-url`

## PR Real LLM Smoke (`scripts/smoke_llm_real_local.sh`)

- `PR_LLM_REAL_SMOKE_API_BASE_URL` (default: `http://127.0.0.1:8000`)

Batch B 口径：以下参数已切换为 CLI 优先（legacy env 仅兼容，不建议继续配置）：

- `PR_LLM_REAL_SMOKE_API_BASE_URL` -> `--api-base-url`
- `PR_LLM_REAL_SMOKE_DIAGNOSTICS_JSON` -> `--diagnostics-json`
- `PR_LLM_REAL_SMOKE_HEARTBEAT_SECONDS` -> `--heartbeat-seconds`
- `PR_LLM_REAL_SMOKE_MAX_RETRIES` -> `--max-retries`

## External Playwright Smoke (`scripts/external_playwright_smoke.sh`)

This script no longer consumes `EXTERNAL_SMOKE_*` env vars.
Use CLI flags instead (`--url`, `--browser`, `--timeout-ms`, `--expect-text`, `--output-dir`, `--retries`, `--diagnostics-json`, `--heartbeat-seconds`).

## Failure Alerts Script (`scripts/run_failure_alerts.sh`)

This script no longer consumes `FAILURE_*` env vars.
Use CLI flags instead (`--channel`, `--lookback-hours`, `--limit`, `--dry-run`, `--force`, `--to-email`, `--fallback-enabled`, `--api-base-url`).

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

- `OPS_DAILY_LOCAL_HOUR` (default: `9`)
- `OPS_DAILY_TIMEZONE` (default: `system-local`)
- `OPS_NOTIFICATION_INTERVAL_MINUTES` (default: `10`)
- `OPS_NOTIFICATION_RETRY_BATCH_LIMIT` (default: `50`)
- `OPS_CANARY_INTERVAL_HOURS` (default: `1`)
- `OPS_CANARY_TIMEOUT_SECONDS` (default: `8`)
- `OPS_CLEANUP_INTERVAL_HOURS` (default: `6`)
- `OPS_CLEANUP_OLDER_THAN_HOURS` (default: `24`)
- `OPS_CLEANUP_CACHE_OLDER_THAN_HOURS` (optional)
- `OPS_CLEANUP_CACHE_MAX_SIZE_MB` (optional)
- `OPS_CLEANUP_WORKSPACE_DIR` (optional)
- `OPS_CLEANUP_CACHE_DIR` (optional)

`scripts/start_ops_workflows.sh` CLI flags (replace Batch A env controls):

- `--daily-workflow-id` (default: `daily-digest-workflow`)
- `--daily-run-once` (default: disabled)
- `--daily-timezone-offset-minutes` (optional)
- `--notification-workflow-id` (default: `notification-retry-workflow`)
- `--notification-run-once` (default: disabled)
- `--canary-workflow-id` (default: `provider-canary-workflow`)
- `--canary-run-once` (default: disabled)
- `--cleanup-workflow-id` (default: `cleanup-workspace-workflow`)
- `--cleanup-run-once` (default: disabled)
- `--show-hints` / `--no-show-hints` (default: show)
- `--dry-run` (default: disabled)

Batch A legacy env controls have been removed from env contracts and are deprecated:

- `OPS_DAILY_WORKFLOW_ID` -> `--daily-workflow-id`
- `OPS_DAILY_RUN_ONCE` -> `--daily-run-once`
- `OPS_DAILY_TIMEZONE_OFFSET_MINUTES` -> `--daily-timezone-offset-minutes`
- `OPS_NOTIFICATION_WORKFLOW_ID` -> `--notification-workflow-id`
- `OPS_NOTIFICATION_RUN_ONCE` -> `--notification-run-once`
- `OPS_CANARY_WORKFLOW_ID` -> `--canary-workflow-id`
- `OPS_CANARY_RUN_ONCE` -> `--canary-run-once`
- `OPS_CLEANUP_WORKFLOW_ID` -> `--cleanup-workflow-id`
- `OPS_CLEANUP_RUN_ONCE` -> `--cleanup-run-once`
- `OPS_SHOW_HINTS` -> `--show-hints` / `--no-show-hints`
- `OPS_DRY_RUN` -> `--dry-run`

## Full Stack Helper Scripts (`scripts/bootstrap_full_stack.sh`, `scripts/full_stack.sh`, `scripts/smoke_full_stack.sh`)

- `PROFILE` (default: `local`)
- `WITH_CORE_SERVICES` (default: `1`)
- `WITH_READER_STACK` (default: `1`)
- `OFFLINE_FALLBACK` (default: `1`)
- `FULL_STACK_REQUIRE_READER` (default: `1`)

## Recreate GCE Instance (`scripts/recreate_gce_instance.sh`)

This script no longer consumes env vars for GCE recreate options.
Use CLI flags instead (`--project`, `--zone`, `--instance`, `--machine`, `--disk-size`, `--image-family`, `--image-project`, `--repo`, `--force-delete-instance`, `--force-replace-app-dir`).
