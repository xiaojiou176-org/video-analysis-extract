# Start Here (1-Minute Onboarding)

这是仓库唯一上手入口。先照抄执行，再按链接深入。

## 你需要先知道的 4 件事

1. 流程口径：`ProcessJobWorkflow = 3 阶段 + 9-step pipeline`（详情见 `docs/state-machine.md`）。
2. 环境文件：本地以 `.env` 为主；仅当 `.env` 缺失时才回退 `.env.local`。
3. Python 命令统一使用 `python3`。
4. 本地启动标准流程固定为 6 步（下方命令）。

## 6 步启动（可直接执行）

```bash
uv sync --frozen --extra dev --extra e2e
npm --prefix apps/web ci

brew services start postgresql@16
brew services start redis
temporal server start-dev --ip 127.0.0.1 --port 7233

./scripts/init_env_example.sh
cp .env.example .env
python3 scripts/check_env_contract.py --strict
set -a; source .env; set +a

createdb video_analysis 2>/dev/null || true
for migration in $(ls infra/migrations/*.sql | sort); do
  psql "postgresql://localhost:5432/video_analysis" -v ON_ERROR_STOP=1 -f "$migration"
done
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql

./scripts/dev_api.sh
./scripts/dev_worker.sh
./scripts/dev_mcp.sh

curl -sS http://127.0.0.1:8000/healthz
curl -sS -X POST http://127.0.0.1:8000/api/v1/ingest/poll -H 'Content-Type: application/json' -d '{"max_new_videos": 20}'
```

## 下一步看哪里

- 本地运维与参数细节：`docs/runbook-local.md`
- 状态机与处理契约：`docs/state-machine.md`
- 环境变量契约：`ENVIRONMENT.md`
- 协作与文档漂移规则：`AGENTS.md`
- 全文档索引：`docs/index.md`
