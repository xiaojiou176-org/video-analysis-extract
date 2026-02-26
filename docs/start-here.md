# Start Here (1-Minute Onboarding)

这是仓库唯一上手入口。先照抄执行，再按导航 Lazy-Load 到对应模块。

## AI 导航索引（Lazy-Load）

1. 根级治理（先读）
- `AGENTS.md`
- `CLAUDE.md`

2. 模块按需加载（只在改对应模块时再读）
- API：`apps/api/AGENTS.md`、`apps/api/CLAUDE.md`
- Worker：`apps/worker/AGENTS.md`、`apps/worker/CLAUDE.md`
- Web：`apps/web/AGENTS.md`、`apps/web/CLAUDE.md`

3. 运行与契约（按问题深度继续）
- `docs/runbook-local.md`
- `docs/state-machine.md`
- `docs/testing.md`
- `ENVIRONMENT.md`

## 你需要先知道的 4 件事

1. 流程口径：`ProcessJobWorkflow = 3 阶段 + 9-step pipeline`（详见 `docs/state-machine.md`）。
2. 环境文件：本地以 `.env` 为主；仅当 `.env` 缺失时才回退 `.env.local`。
3. Python 命令统一使用 `python3`。
4. AI/自动化执行必须在标准环境：优先 `.devcontainer/devcontainer.json`，基础设施使用 `infra/compose/*.compose.yml`。

## 标准环境入口（AI 必须）

```bash
# VS Code: Dev Containers: Reopen in Container
# CLI:
devcontainer up --workspace-folder .
```

标准环境内再执行下文 6 步或一键路径，确保 lint/test/live smoke 结果可复现。

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

## 一键路径（推荐）

```bash
./scripts/bootstrap_full_stack.sh
./scripts/full_stack.sh up
./scripts/smoke_full_stack.sh
```

默认行为：
- `bootstrap_full_stack.sh` 会拉起 core services + Miniflux + Nextflux。
- `full_stack.sh up` 会等待 API health(`GET /healthz`) 与 Web 端口可用；后台模式会关闭 API reload（`DEV_API_RELOAD=0`）以避免 PID 漂移误判。
- `smoke_full_stack.sh` 会执行本地联调烟测并覆盖 reader 栈检查。

边界说明：
- 这里的一键 smoke 指本地联调烟测，不等同于 CI 的 live-smoke。
- CI `live-smoke` 仅在 `main` push / nightly schedule 强制执行，且要求外部 provider secrets 完整（详见 `docs/testing.md`）。
- PR 阶段仅有条件触发真实 LLM 烟测（`pr-llm-real-smoke`）；`web-e2e` 默认仍是 mock API 路径。

可选阅读栈（Miniflux + Nextflux）：

```bash
cp .env.example .env.reader-stack
./scripts/bootstrap_full_stack.sh --with-reader-stack 1 --reader-env-file .env.reader-stack
```

## 下一步看哪里

- 本地运维与参数细节：`docs/runbook-local.md`
- 状态机与处理契约：`docs/state-machine.md`
- 环境变量契约：`ENVIRONMENT.md`
- 协作与文档漂移规则：`AGENTS.md`
- 全文档索引：`docs/index.md`
