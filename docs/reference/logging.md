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

## Sensitive Data Rules
`run_daily_digest.sh` 与 `run_failure_alerts.sh` 内置 `safe_body_preview`，会对以下模式脱敏：
- `Bearer <token>`
- `sk-*`（OpenAI 形态）
- `ghp_*`（GitHub token 形态）
- `AKIA*`（AWS key 形态）
- URL query 中的 `api_key/token/secret/password/auth*`

约束：
- 禁止在日志中直接打印完整密钥与凭证。
- 错误信息允许输出摘要，禁止输出原始敏感 payload。

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

## Doc Drift Trigger
如修改日志格式、脱敏规则或日志落盘策略，必须同步更新本文件与 `docs/runbook-local.md`。
