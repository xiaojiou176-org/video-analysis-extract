# Logging Governance

## Scope

本仓库日志策略覆盖：

- 开发启动脚本：`scripts/dev_api.sh`、`scripts/dev_worker.sh`、`scripts/dev_mcp.sh`
- 通知脚本：`scripts/runtime/run_daily_digest.sh`、`scripts/runtime/run_failure_alerts.sh`
- 服务运行日志（Uvicorn/Worker/MCP）

## Output Contract

- 开发脚本默认输出到标准输出/标准错误；需要跨运行关联的结构化事件写入 `.runtime-cache/logs/**`，例如 API HTTP 请求日志会写入 `.runtime-cache/logs/app/api-http.jsonl`。
- 计划任务（cron/launchd）场景，日志统一重定向到 `.runtime-cache/logs/`，不再向仓库根级 `logs/` 写入。
- 脚本日志必须带前缀（如 `[run_daily_digest]`、`[dev_worker]`）以便 grep。
- 关键运行链必须能按“案号”串联：HTTP 至少保留 `trace_id/request_id`，异步作业至少保留 `run_id`。

## No Logs No Merge

- 关键路径（鉴权、第三方 API 调用、异常处理）必须输出结构化日志，否则不得合并。
- 关键日志字段至少包含：`trace_id`、`user`、`error`（异常路径还需 stack，使用 `logger.exception(...)`）。
- 禁止空洞日志文案（如 `Something went wrong`、`unexpected error`、`error occurred`、`unknown error`）。
- 质量门禁包含空洞日志检查：`./bin/quality-gate --mode pre-commit`。
- 质量门禁包含结构化日志关键路径检查：`python3 scripts/governance/check_structured_logs.py`（由 `quality_gate.sh` 与 CI `preflight` 执行）。

## Log Directory Initialization

首次启用定时任务或常驻 ops workflow 前，先创建日志目录：

```bash
mkdir -p .runtime-cache/logs/app .runtime-cache/logs/governance
touch .runtime-cache/logs/app/daily_digest.log \
  .runtime-cache/logs/app/failure_alerts.log \
  .runtime-cache/logs/governance/workflows.log
```

推荐重定向方式：

```bash
./scripts/runtime/start_ops_workflows.sh >> ./.runtime-cache/logs/governance/workflows.log 2>&1
```

脚本入口参数（Batch C）：

- `./bin/dev-api --app ... --reload|--no-reload`
- `./bin/dev-worker --worker-dir ... --entry ... --command ... --show-hints|--no-show-hints`
- `./bin/dev-mcp --entry ... --mcp-dir ...`

启动约束补充：

- `scripts/dev_api.sh` 在检测到 `uv` 时通过 `uv run python -m uvicorn ...` 启动 API，不依赖 `uvicorn` console entry；日志排障时若看到 `Failed to spawn: uvicorn`，优先检查是否绕开了该脚本入口。
- `scripts/full_stack.sh` 与 `scripts/ci/api_real_smoke_local.sh` 会把 API 启动日志落到 `.runtime-cache/logs/components/full-stack/api.log` 与 `.runtime-cache/logs/tests/api-real-smoke-local.log`；本地严格验收时优先检查这两个文件。
- `ci_pr_llm_real_smoke.sh`、`ci_live_smoke.sh`、`ci_web_e2e.sh` 的测试日志统一进入 `.runtime-cache/logs/tests/`，对应 JUnit/diagnostics 进入 `.runtime-cache/reports/tests/`，浏览器证据进入 `.runtime-cache/evidence/tests/`。
- `scripts/full_stack.sh` 还会把运行时路由决议写到 `.runtime-cache/run/full-stack/resolved.env`；排查“明明起在 18001，前端还在打 9000”这类问题时，应把它和 `.runtime-cache/logs/components/full-stack/*.log` 一起看。
- `scripts/ci/api_real_smoke_local.sh` 会刻意让 pytest 子进程保持“未配置写 token”的 integration harness 语义，同时允许 `dev_api.sh` 为真实 HTTP smoke 进程注入本地 token；排查 401/403 时要区分“测试进程环境”和“API 进程环境”。

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
./bin/dev-api
./bin/dev-worker
./bin/dev-mcp
```

查看计划任务日志：

```bash
tail -f .runtime-cache/logs/app/daily_digest.log
tail -f .runtime-cache/logs/app/failure_alerts.log
```

筛选错误：

```bash
rg -n "ERROR|failed|status=5" .runtime-cache/logs scripts -g '*.log'
```

定位 Computer Use（函数调用）安全闸/终止原因：

```bash
rg -n "function_calling|termination_reason|max_function_call_rounds|tool_not_allowed" .runtime-cache/logs -g '*.log'
```

定位缓存自愈与缓存来源：

```bash
rg -n "cache_hit|cache_recreate|cache_bypass_reason|checkpoint_recovered|cache_meta|cache_key" .runtime-cache/logs -g '*.log'
```

定位 thought metadata/signatures（来自 job read model）：

```bash
rg -n "thought_signatures|thought_signature_digest|thought_metadata|llm_meta" .runtime-cache/logs -g '*.log'
```

## Rotation and Retention

日志与证据保留不再只靠系统级约定，仓库级维护入口如下：

```bash
python3 scripts/runtime/prune_logs_and_evidence.py --assert-clean
python3 scripts/governance/check_log_retention.py
python3 scripts/runtime/build_evidence_index.py --rebuild-all
python3 scripts/governance/check_no_unindexed_evidence.py
```

当前统一要求：

- 结构化日志必须包含：`run_id`、`trace_id`、`request_id`、`repo_commit`、`entrypoint`、`env_profile`
- `tests` 通道额外必须带 `test_run_id`
- `governance` 通道额外必须带 `gate_run_id`
- `reports` / `evidence` artifact 必须带 sidecar metadata，避免历史 artifact 冒充 current verification

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

## CI 写权限日志边界（2026-03）

- `live-smoke` 与其他 CI 写路径不再依赖 `VD_ALLOW_UNAUTH_WRITE` / `VD_CI_ALLOW_UNAUTH_WRITE` 的 GitHub Actions 旁路。
- CI 写路径必须使用显式测试 token 或 `X-Web-Session`，以便 `auth_write_access_denied` / `auth_write_access_bypassed` 日志能明确区分“真实认证流”与“pytest-only 豁免”。
- `VD_ALLOW_UNAUTH_WRITE` 现在仅允许在 `PYTEST_CURRENT_TEST` 上下文中生效；若在 CI 非测试上下文命中未认证写请求，应记录为拒绝而不是旁路通过。


<!-- doc-sync: api/worker reliability + auth guard update (2026-03-03) -->
