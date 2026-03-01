# Start Here (1-Minute Onboarding)

这是仓库唯一上手入口。先照抄执行，再按导航 Lazy-Load 到对应模块。

## AI 导航索引（Lazy-Load）

1. 根级治理（先读）

- `AGENTS.md`
- `CLAUDE.md`

2. 模块按需加载（只在改对应模块时再读）

- API：`apps/api/AGENTS.md`、`apps/api/CLAUDE.md`
- Worker：`apps/worker/AGENTS.md`、`apps/worker/CLAUDE.md`
- MCP：`apps/mcp/AGENTS.md`、`apps/mcp/CLAUDE.md`
- Web：`apps/web/AGENTS.md`、`apps/web/CLAUDE.md`

3. 运行与契约（按问题深度继续）

- `docs/runbook-local.md`
- `docs/state-machine.md`
- `docs/testing.md`
- `ENVIRONMENT.md`

## 你需要先知道的 5 件事

1. 流程口径：`ProcessJobWorkflow = 3 阶段 + 9-step pipeline`（详见 `docs/state-machine.md`）。
2. 环境分层：采用 `core + profile overlay` 架构，`.env` 是 core，`env/profiles/reader.env` 是 reader profile 模板，脚本通过 `--profile local|gce` 控制行为。
3. 密钥策略：只允许通过 `.env` 或进程环境注入；禁止依赖 shell 登录配置作为密钥来源。
4. Python 命令统一使用 `python3`。
5. AI/自动化执行必须在标准环境：优先 `.devcontainer/devcontainer.json`，基础设施使用 `infra/compose/*.compose.yml`。

## 环境文件准备（必做）

```bash
cp .env.example .env
python3 scripts/check_env_contract.py --strict
```

说明：

- `.env.example` 现在只保留最小可启动键和少量高频覆盖键，默认足够完成一次本地启动。
- 脚本参数全集见 `docs/reference/env-script-overrides.md`（按需覆盖，不必全量写入 `.env`）。

## 一键验证（最短路径）

```bash
bash scripts/env/validate_profile.sh --profile local
```

## 初始化质量门禁（建议在首次 clone 后执行）

```bash
./scripts/install_git_hooks.sh
```

可选：如果你希望把 `pre-commit` framework 也直接挂到 Git 生命周期（除仓库默认 `.githooks` 外），执行：

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

说明：

- 仓库当前默认强制链路是 `.githooks/* -> scripts/quality_gate.sh`。
- `.pre-commit-config.yaml` 用于统一定义可复用检查集合，适合手动全量清洗与依赖更新。
- 若执行 `pre-commit install`，会写入当前 `core.hooksPath` 下的 hook 文件；执行前请确认团队约定。

## Big Bang 全量清洗（可选）

```bash
pre-commit run --all-files
```

用途：在大规模重构前、长期分支回收前，先把格式/拼写/基础静态问题一次性清干净。

## detect-secrets baseline（可选补充，与当前强制门禁并行）

当前仓库强制 secrets 门禁来自 `gitleaks + quality_gate`；`detect-secrets` 不是默认强制项。若你希望补充 baseline 工作流，可执行：

```bash
uv run --with detect-secrets detect-secrets scan > .secrets.baseline
uv run --with detect-secrets detect-secrets audit .secrets.baseline
uv run --with detect-secrets detect-secrets scan --baseline .secrets.baseline > .secrets.baseline
```

三步含义：

- 初始化：`scan > .secrets.baseline`
- 审核：`audit .secrets.baseline`（标记真实风险 vs 误报）
- 更新：`scan --baseline ... > .secrets.baseline`（代码变更后重算基线）

## pre-commit 月度保养（可选）

```bash
pre-commit autoupdate
pre-commit run --all-files
```

建议频率：每月一次；更新后至少跑一轮全量检查再提交。

可选排障命令：

```bash
bash scripts/env/compose_env.sh --profile local --write .runtime-cache/temp/.env.resolved
```

迁移规则：

- `.env`：放 core/runtime 与 provider 密钥。
- `env/profiles/reader.env`：只放 Miniflux/Nextflux 相关变量。

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
- `core-services.compose.yml` 的 `redis/temporal` 端口与 Postgres `DB/User` 已收口为固定默认（`6379` / `7233` / `video_analysis` / `postgres`）。
- `miniflux-nextflux.compose.yml` 的 Miniflux 端口与 `DB/User/DB_NAME` 已收口为固定默认（`8080` / `miniflux` / `miniflux`）。
- `full_stack.sh up` 会等待 API health(`GET /healthz`) 与 Web 端口可用；后台模式会调用 `./scripts/dev_api.sh --no-reload` 以避免 PID 漂移误判。
- `smoke_full_stack.sh` 会执行本地联调烟测并覆盖 reader 栈检查。

边界说明：

- 这里的一键 smoke 指本地联调烟测，不等同于 CI 的 live-smoke。
- CI `live-smoke` 仅在 `main` push / nightly schedule 强制执行，且要求外部 provider secrets 完整（详见 `docs/testing.md`）。
- PR 阶段仅有条件触发真实 LLM 烟测（`pr-llm-real-smoke`）；`web-e2e` 在 CI 主路径默认走 real API，mock API 仅用于本地调试。

可选阅读栈（Miniflux + Nextflux）：

```bash
./scripts/bootstrap_full_stack.sh --with-reader-stack 1 --reader-env-file env/profiles/reader.env
```

## 下一步看哪里

- 本地运维与参数细节：`docs/runbook-local.md`
- 状态机与处理契约：`docs/state-machine.md`
- 环境变量契约：`ENVIRONMENT.md`
- 协作与文档漂移规则：`AGENTS.md`
- 全文档索引：`docs/index.md`
