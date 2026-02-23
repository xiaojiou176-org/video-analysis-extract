# AGENTS

本文件定义本仓库的人类/AI 协作最小协议，目标是让接手者在 1 分钟理解入口、10 分钟完成本地启动与问题定位。

## 1. 文档真相源（优先级）
1. `docs/start-here.md`：唯一 1 分钟入口（先看这个）
2. `docs/runbook-local.md`：本地运行标准流程（6 步）
3. `docs/state-machine.md`：状态机与流程契约（3 阶段 + 9-step pipeline）
4. `ENVIRONMENT.md` + `infra/config/env.contract.json`：环境变量契约
5. `docs/reference/*.md`：日志/缓存/依赖治理细则
6. `README.md`：仓库前门与导航

## 2. Golden Commands

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

## 3. 文档漂移触发器（必须同步更新）
- 变更 `infra/migrations/*.sql`：同步 `README.md` 与 `docs/runbook-local.md` 的迁移说明。
- 变更 `apps/worker/worker/pipeline/runner.py` 的 `PIPELINE_STEPS`：同步 `docs/state-machine.md`。
- 新增/修改环境变量：同步 `.env.example`、`ENVIRONMENT.md`、`infra/config/env.contract.json`。
- 调整日志/缓存/依赖策略：同步 `docs/reference/logging.md`、`docs/reference/cache.md`、`docs/reference/dependency-governance.md`。

## 4. 最小验收
```bash
python3 scripts/check_env_contract.py --strict
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q
npm --prefix apps/web run lint
```
