# Script Runtime Overrides (CLI-First)

本页是脚本运行参数的唯一参考口径。

原则：

- 运行参数优先使用 CLI flags。
- `.env` 仅保留核心运行配置与密钥，不承载脚本行为开关。
- 如需覆盖默认值，优先在命令行一次性传参。

## Daily Digest (`scripts/runtime/run_daily_digest.sh`)

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
./scripts/runtime/run_daily_digest.sh --date 2026-02-27 --to-email you@example.com --api-base-url http://127.0.0.1:9000
```

## Failure Alerts (`scripts/runtime/run_failure_alerts.sh`)

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
./scripts/runtime/run_failure_alerts.sh --lookback-hours 6 --limit 10 --to-email you@example.com --api-base-url http://127.0.0.1:9000
```

## Live Smoke (`scripts/ci/e2e_live_smoke.sh`)

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
./scripts/ci/e2e_live_smoke.sh \
  --api-base-url http://127.0.0.1:9000 \
  --timeout-seconds 240 \
  --heartbeat-seconds 20 \
  --diagnostics-json .runtime-cache/reports/tests/e2e-live-smoke-result.json
```

## PR LLM Smoke (`scripts/ci/smoke_llm_real_local.sh`)

使用 CLI flags：

- `--api-base-url`
- `--diagnostics-json`
- `--heartbeat-seconds`
- `--max-retries`

迁移示例：

```bash
export VD_API_KEY='local-dev-token'
./scripts/ci/smoke_llm_real_local.sh --api-base-url http://127.0.0.1:18081 --heartbeat-seconds 20
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

### `scripts/env/init_example.sh`

- `--output`
- `--force`

说明：

- 该脚本只是辅助模板生成工具，不是默认初始化入口。
- 标准初始化路径固定为：`cp .env.example .env`。

## Ops Workflows (`scripts/runtime/start_ops_workflows.sh`)

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
./scripts/runtime/start_ops_workflows.sh \
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

说明：

- `bootstrap_full_stack.sh` 不再持久化改写 `.env`（仅在 `.env` 缺失时复制 `.env.example`）。
- 端口冲突与运行时路由决策会写入 `.runtime-cache/run/full-stack/resolved.env`。
- 本地路由真相源是 `API_PORT/WEB_PORT`；`VD_API_BASE_URL` 与 `NEXT_PUBLIC_API_BASE_URL` 为派生地址。

### `scripts/full_stack.sh`

- `--profile`
- `--api-port`
- `--web-port`
- `--api-health-url`

说明：

- `full_stack.sh` 读取 `API_PORT/WEB_PORT` 作为本地路由真相源。
- `VD_API_BASE_URL` 与 `NEXT_PUBLIC_API_BASE_URL` 默认由路由真相源派生，必要时可通过 CLI 显式覆盖。

### `scripts/ci/smoke_full_stack.sh`

- `--profile`
- `--api-base-url`
- `--web-base-url`
- `--require-reader`
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
./scripts/ci/smoke_full_stack.sh \
  --profile local \
  --require-reader 1 \
  --live-smoke-api-base-url http://127.0.0.1:9000
```

说明：

- `env/profiles/reader.env` 仅用于补齐 reader 相关默认值（如 `MINIFLUX_BASE_URL`、`NEXTFLUX_PORT`）。
- 当前 shell 已显式注入的 `MINIFLUX_*` / `NEXTFLUX_*` 变量优先级更高，不会被 reader profile 模板覆盖。

### `bin/run-ai-feed-sync`

- `--profile`
- `--reader-env-file`
- `--api-base-url`
- `--miniflux-base-url`

迁移示例：

```bash
./bin/run-ai-feed-sync \
  --profile local \
  --reader-env-file env/profiles/reader.env \
  --api-base-url http://127.0.0.1:9000 \
  --miniflux-base-url http://127.0.0.1:8080
```

## Recreate GCE Instance (`scripts/deploy/recreate_gce_instance.sh`)

使用 CLI flags：

- `--project`
- `--zone`
- `--instance`
- `--machine`
- `--disk-size`
- `--image-family`
- `--image-project`
- `--scopes`（默认最小权限 scopes；如需旧行为可显式设为 `https://www.googleapis.com/auth/cloud-platform`）
- `--repo`
- `--force-delete-instance`
- `--force-replace-app-dir`

## Env Governance Report (`scripts/governance/report_env_governance.py`)

用于输出环境变量治理报表（删除候选、残留引用、文档漂移）。

示例：

```bash
python3 scripts/governance/report_env_governance.py \
  --json-out .runtime-cache/reports/governance/env-governance.json \
  --md-out .runtime-cache/reports/governance/env-governance.md
```

输出说明：

- JSON 报表包含 `summary`、`delete_candidates`、`residual_refs`、`doc_drift`
- Markdown 报表用于人工审阅与 PR 附件
- 默认 `--fail-on residual_refs,doc_drift`，命中返回码 `1`
