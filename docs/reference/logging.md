# Logging Governance

## Scope

本仓库日志策略覆盖：

- 开发启动脚本：`scripts/dev_api.sh`、`scripts/dev_worker.sh`、`scripts/dev_mcp.sh`
- 通知脚本：`scripts/run_daily_digest.sh`、`scripts/run_failure_alerts.sh`
- 服务运行日志（Uvicorn/Worker/MCP）

## Output Contract

- 默认输出到标准输出/标准错误，不在代码内写固定日志文件。
- 计划任务（cron/launchd）场景，日志应重定向到 `logs/`（该目录已在 `.gitignore`）。
- 脚本日志必须带前缀（如 `[run_daily_digest]`、`[dev_worker]`）以便 grep。

## No Logs No Merge

- 关键路径（鉴权、第三方 API 调用、异常处理）必须输出结构化日志，否则不得合并。
- 关键日志字段至少包含：`trace_id`、`user`、`error`（异常路径还需 stack，使用 `logger.exception(...)`）。
- 禁止空洞日志文案（如 `Something went wrong`、`unexpected error`、`error occurred`、`unknown error`）。
- 质量门禁包含空洞日志检查：`./scripts/quality_gate.sh --mode pre-commit`。
- 质量门禁包含结构化日志关键路径检查：`python3 scripts/check_structured_logs.py`（由 `quality_gate.sh` 与 CI `preflight` 执行）。

## Log Directory Initialization

首次启用定时任务或常驻 ops workflow 前，先创建日志目录：

```bash
mkdir -p logs logs/ops
touch logs/daily_digest.log logs/failure_alerts.log logs/ops/workflows.log
```

推荐重定向方式：

```bash
./scripts/start_ops_workflows.sh >> ./logs/ops/workflows.log 2>&1
```

脚本入口参数（Batch C）：

- `./scripts/dev_api.sh --app ... --reload|--no-reload`
- `./scripts/dev_worker.sh --worker-dir ... --entry ... --command ... --show-hints|--no-show-hints`
- `./scripts/dev_mcp.sh --entry ... --mcp-dir ...`

## Sensitive Data Rules

`run_daily_digest.sh` 与 `run_failure_alerts.sh` 内置 `safe_body_preview`，会对以下模式脱敏：

- `Bearer <token>`
- `sk-*`（通用 API 密钥形态）
- `ghp_*`（GitHub token 形态）
- `AKIA*`（AWS key 形态）
- URL query 中的 `api_key/token/secret/password/auth*`

API 异常详情（`apps/api/app/security.py`）使用 `sanitize_exception_detail`，在返回 `HTTPException.detail` 前会额外脱敏：

- `Basic <credential>`
- URL 凭证段（`scheme://user:pass@host`）
- query 中的 `access_token/refresh_token/id_token/jwt/client_secret/session/signature`
- 脱敏后最大返回长度 `500` 字符（超出追加 `...[truncated]`）

约束：

- 禁止在日志中直接打印完整密钥与凭证。
- 错误信息允许输出摘要，禁止输出原始敏感 payload。
- 密钥来源仅允许 `.env`、`env/profiles/reader.env`（reader profile 模板）或进程环境注入；日志中不得输出其原值。
- 禁止将 shell 登录配置作为运行时密钥输入来源。

## Recommended Operations

查看实时日志：

```bash
./scripts/dev_api.sh
./scripts/dev_worker.sh
./scripts/dev_mcp.sh
```

查看计划任务日志：

```bash
tail -f logs/daily_digest.log
tail -f logs/failure_alerts.log
```

筛选错误：

```bash
rg -n "ERROR|failed|status=5" logs scripts -g '*.log'
```

定位 Computer Use（函数调用）安全闸/终止原因：

```bash
rg -n "function_calling|termination_reason|max_function_call_rounds|tool_not_allowed" logs -g '*.log'
```

定位缓存自愈与缓存来源：

```bash
rg -n "cache_hit|cache_recreate|cache_bypass_reason|checkpoint_recovered|cache_meta|cache_key" logs -g '*.log'
```

定位 thought metadata/signatures（来自 job read model）：

```bash
rg -n "thought_signatures|thought_signature_digest|thought_metadata|llm_meta" logs -g '*.log'
```

## Rotation and Retention

建议使用系统轮转器（`logrotate` 或 `newsyslog`），避免日志无限增长。

建议参数：

- 轮转周期：`daily`
- 单文件大小：`50M`（触发提前轮转）
- 保留策略：
  - `logs/ops/workflows.log`：保留 `30` 天（运维审计）
  - `logs/daily_digest.log`、`logs/failure_alerts.log`：保留 `14` 天
- 压缩：开启（`compress`）

互斥策略（必须）：

- `cron` 与 `start_ops_workflows.sh` 常驻 workflow 二选一。
- 若已启用常驻 workflow，不应再用 cron 重复触发相同任务，避免重复执行与重复日志。

## Doc Drift Trigger

如修改日志格式、脱敏规则或日志落盘策略，必须同步更新本文件与 `docs/runbook-local.md`。

## Notification Retry Idempotency 日志要点（2026-03）

失败投递重试链路新增了外发幂等键透传（`Idempotency-Key`），用于降低重复领取窗口下的重复发送概率。

- 关键链路：
  - `activities_delivery_retry` 生成稳定重试键：`delivery-retry:{delivery_id}:attempt-{n}`
  - `activities_email.send_with_resend` 将该键写入请求头 `Idempotency-Key`
- 日志建议：
  - 允许记录幂等键摘要（如 hash/前缀），用于定位重复发送问题
  - 禁止完整输出敏感 token/authorization 头值
  - 失败排查时优先关联：`delivery_id`、`attempt_count`、`Idempotency-Key` 摘要、`provider_message_id`


<!-- doc-sync: api/worker reliability + auth guard update (2026-03-03) -->
