# Script Runtime Overrides (CLI-First)

本页是脚本运行参数的唯一参考口径。

原则：

- 运行参数优先使用 CLI flags。
- `.env` 仅保留核心运行配置与密钥，不承载脚本行为开关。
- 如需覆盖默认值，优先在命令行一次性传参。

## Daily Digest (`scripts/run_daily_digest.sh`)

使用 CLI flags：

- `--date`
- `--channel`
- `--dry-run`
- `--force`
- `--to-email`
- `--fallback-enabled`
- `--api-base-url`

迁移示例：

```bash
# 旧：通过环境变量覆盖
# 新：直接传 flag
./scripts/run_daily_digest.sh --date 2026-02-27 --to-email you@example.com --api-base-url http://127.0.0.1:8000
```

## Failure Alerts (`scripts/run_failure_alerts.sh`)

使用 CLI flags：

- `--channel`
- `--lookback-hours`
- `--limit`
- `--dry-run`
- `--force`
- `--to-email`
- `--fallback-enabled`
- `--api-base-url`

迁移示例：

```bash
./scripts/run_failure_alerts.sh --lookback-hours 6 --limit 10 --to-email you@example.com --api-base-url http://127.0.0.1:8000
```

## Live Smoke (`scripts/e2e_live_smoke.sh`)

使用 CLI flags：

- `--api-base-url`
- `--timeout-seconds`
- `--poll-interval-seconds`
- `--heartbeat-seconds`
- `--health-path`
- `--external-probe-timeout-seconds`
- `--max-retries`
- `--diagnostics-json`
- `--computer-use-cmd`
- `--youtube-url`
- `--bilibili-url`
- `--require-api`
- `--require-secrets`
- `--computer-use-strict`
- `--computer-use-skip`
- `--computer-use-skip-reason`

迁移示例：

```bash
./scripts/e2e_live_smoke.sh \
  --api-base-url http://127.0.0.1:8000 \
  --timeout-seconds 240 \
  --heartbeat-seconds 20 \
  --diagnostics-json .runtime-cache/e2e-live-smoke-result.json
```

## PR LLM Smoke (`scripts/smoke_llm_real_local.sh`)

使用 CLI flags：

- `--api-base-url`
- `--diagnostics-json`
- `--heartbeat-seconds`
- `--max-retries`

迁移示例：

```bash
./scripts/smoke_llm_real_local.sh --api-base-url http://127.0.0.1:18081 --heartbeat-seconds 20
```

## Script Entrypoints

### `scripts/dev_api.sh`

- `--app` (default: `apps.api.app.main:app`)
- `--reload` / `--no-reload`

### `scripts/dev_worker.sh`

- `--worker-dir`
- `--entry`
- `--command`
- `--show-hints` / `--no-show-hints`

### `scripts/dev_mcp.sh`

- `--entry`
- `--mcp-dir`

### `scripts/init_env_example.sh`

- `--output`
- `--force`

## Ops Workflows (`scripts/start_ops_workflows.sh`)

基础频率和调度参数：

- `--daily-local-hour`
- `--daily-timezone`
- `--notification-interval-minutes`
- `--notification-retry-batch-limit`
- `--canary-interval-hours`
- `--canary-timeout-seconds`
- `--cleanup-interval-hours`
- `--cleanup-older-than-hours`
- `--cleanup-cache-older-than-hours`
- `--cleanup-cache-max-size-mb`
- `--cleanup-workspace-dir`
- `--cleanup-cache-dir`

workflow 管理参数：

- `--daily-workflow-id`
- `--notification-workflow-id`
- `--canary-workflow-id`
- `--cleanup-workflow-id`
- `--daily-run-once`
- `--notification-run-once`
- `--canary-run-once`
- `--cleanup-run-once`
- `--daily-timezone-offset-minutes`
- `--show-hints` / `--no-show-hints`
- `--dry-run`

迁移示例：

```bash
./scripts/start_ops_workflows.sh \
  --daily-local-hour 9 \
  --daily-timezone Asia/Shanghai \
  --notification-interval-minutes 5 \
  --notification-retry-batch-limit 100 \
  --canary-interval-hours 1 \
  --canary-timeout-seconds 8 \
  --cleanup-interval-hours 6 \
  --cleanup-older-than-hours 24 \
  --show-hints
```

## Full-Stack Helpers

### `scripts/bootstrap_full_stack.sh`

- `--profile`
- `--api-port`
- `--web-port`
- `--install-deps`
- `--with-core-services`
- `--with-reader-stack`
- `--reader-env-file`
- `--offline-fallback`

### `scripts/full_stack.sh`

- `--profile`
- `--api-port`
- `--web-port`
- `--api-health-url`

### `scripts/smoke_full_stack.sh`

- `--profile`
- `--api-base-url`
- `--web-base-url`
- `--require-reader`
- `--offline-fallback`
- `--reader-env-file`
- `--heartbeat-seconds`
- `--live-smoke-api-base-url`
- `--live-smoke-require-api`
- `--live-smoke-require-secrets`
- `--live-smoke-computer-use-strict`
- `--live-smoke-computer-use-skip`
- `--live-smoke-computer-use-skip-reason`
- `--youtube-smoke-url`
- `--live-diagnostics-json`

迁移示例：

```bash
./scripts/smoke_full_stack.sh \
  --profile local \
  --require-reader 1 \
  --offline-fallback 0 \
  --live-smoke-api-base-url http://127.0.0.1:8000
```

## Recreate GCE Instance (`scripts/recreate_gce_instance.sh`)

使用 CLI flags：

- `--project`
- `--zone`
- `--instance`
- `--machine`
- `--disk-size`
- `--image-family`
- `--image-project`
- `--repo`
- `--force-delete-instance`
- `--force-replace-app-dir`
