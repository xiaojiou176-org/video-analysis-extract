# CLAUDE.md

## Role / Scope
- 你是本仓库的 Claude Code 执行代理，职责是执行用户任务、最小化改动、保持可验证结果。
- 本文件只定义执行策略、命令入口、安全与测试闸门，不重复业务设计文档。
- 优先做与请求直接相关的最小变更；避免无关重构。

## Truth Sources
- 项目事实真相源以 `AGENTS.md` 为准；若本文件与 `AGENTS.md` 冲突，**一律以 `AGENTS.md` 优先**。
- 文档优先级遵循 `AGENTS.md`：
  1. `docs/start-here.md`
  2. `docs/runbook-local.md`
  3. `docs/state-machine.md`
  4. `ENVIRONMENT.md` + `infra/config/env.contract.json`
  5. `docs/testing.md`
  6. `docs/reference/*.md`
  7. `README.md`
- 涉及运行、迁移、环境变量、状态机行为的结论，必须可回溯到上述文档。

## Golden Commands
以下命令需与仓库当前标准保持一致。

### 安装依赖
```bash
uv sync --frozen --extra dev --extra e2e
npm --prefix apps/web ci
```

### 初始化环境
```bash
./scripts/init_env_example.sh
cp .env.example .env
python3 scripts/check_env_contract.py --strict
```
说明：运行时优先读取仓库根 `.env`，仅在 `.env` 缺失时回退 `.env.local`。

### 启动基础服务
```bash
brew services start postgresql@16
brew services start redis
temporal server start-dev --ip 127.0.0.1 --port 7233
```

### 执行迁移
```bash
createdb video_analysis 2>/dev/null || true
for migration in $(ls infra/migrations/*.sql | sort); do
  psql "postgresql://localhost:5432/video_analysis" -v ON_ERROR_STOP=1 -f "$migration"
done
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql
```

### 启动服务
```bash
./scripts/dev_api.sh
./scripts/dev_worker.sh
./scripts/dev_mcp.sh
```

## Agent Collaboration
- 可将独立子任务并发处理（如：文档核对、代码修改、测试验证），但同一文件写操作必须串行。
- 推荐执行顺序：
  1. 读取真相源并确认约束
  2. 实施最小改动
  3. 运行强制闸门
  4. 汇总证据（改动文件、命令、结果）
- 输出时给出可追溯证据，不只给结论。

## Mandatory Validation Gates
每次涉及代码、配置、流程变更时，至少执行以下门禁：

```bash
python3 scripts/check_env_contract.py --strict
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q
npm --prefix apps/web run lint
```

- 若因环境限制无法完整执行，必须明确说明未执行项、原因与风险。

## Security Guardrails
- 禁止危险命令：`git push --force`、`git reset --hard`、`git clean -fd`、绕过校验的 `--no-verify`。
- 不得在代码、日志、文档、提交记录中暴露密钥（如 API Key、Token、密码、私钥）。
- `.env` 仅用于本地；对外只提供 `.env.example`。
- 涉及删除数据、破坏性迁移、生产操作时，先停下并请求明确确认。

## Docs Drift Rules
出现以下变更时，必须同步更新文档：
- 变更 `infra/migrations/*.sql`：同步 `README.md` 与 `docs/runbook-local.md` 的迁移说明。
- 变更 `apps/worker/worker/pipeline/types.py` 的 `PIPELINE_STEPS`：同步 `docs/state-machine.md`。
- 新增/修改环境变量：同步 `.env.example`、`ENVIRONMENT.md`、`infra/config/env.contract.json`。
- 调整日志/缓存/依赖策略：同步 `docs/reference/logging.md`、`docs/reference/cache.md`、`docs/reference/dependency-governance.md`。

## Done Criteria
满足以下条件才可判定完成：
- 请求范围内改动已完成，且仅包含必要文件。
- Mandatory Validation Gates 已通过；或未通过项已记录原因与风险。
- 文档联动更新已完成（若触发 Docs Drift Rules）。
- 输出包含：变更摘要、验证结果、残余风险（如有）。
