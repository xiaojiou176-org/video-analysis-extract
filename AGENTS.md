# 仓库协作规范

本文件定义本仓库的人类/AI 协作协议，目标是让接手者在 1 分钟定位真相源，在 10 分钟完成本地启动与最小验收。

## -1. 15 条强制标准（MUST）

以下 15 条为仓库强制标准，`AGENTS.md` 与 `CLAUDE.md` 必须保持一致，且必须使用 MUST/必须语气：

1. **项目目的/技术栈/导航入口必须明确。**
2. **文档真相源与冲突优先级必须明确。**
3. **启动模式必须提供双路径（手动 6 步 + 一键 full-stack）。**
4. **Golden Commands 必须可直接执行且与仓库脚本一致。**
5. **Safety 边界必须明确列出禁止项与确认项。**
6. **文档漂移触发器必须定义且与代码变更联动。**
7. **Git Hooks 对齐规则必须明确并可追溯到实际脚本。**
8. **最小 DoD 必须定义且包含标准环境 + env/test/lint/smoke 门禁。**
9. **交付格式必须固定为 4 段：修改文件/执行命令/结果/风险与后续。**
10. **大型模块（`apps/api`、`apps/worker`、`apps/mcp`、`apps/web`）必须同时维护 `AGENTS.md` 与 `CLAUDE.md`，且内容一致。**
11. **Live 测试在链路涉及外部依赖时必须使用真实 Key、真实浏览器、真实外部 API/网页。**
12. **Pre-Commit 必须拦截所有 Linter Error 与安慰剂断言。**
13. **覆盖率与变异测试门禁必须满足：总覆盖率 `>=85%`、重要模块覆盖率 `>=95%`、Python 核心模块 mutation score `>=0.60`。**
14. **长测试必须输出 heartbeat，且必须先短测后长测；可并发任务必须并发执行。**
15. **远程 CI（含 GitHub Actions 重跑）必须以后端/前端本地 pre-push 门禁全绿为前提；若远程失败，必须先完成本地复现与修复再触发下一次远程运行。**

## 0. 项目目的、技术栈与导航入口

### 0.1 项目目的

本项目用于把视频内容（YouTube/Bilibili 等）转成可检索、可订阅、可分发的结构化信息流，核心目标是：

- 自动拉取与分析视频内容（metadata / subtitles / comments / frames / LLM digest）。
- 统一通过 API/MCP/Web 暴露处理结果与操作入口。
- 保持本地优先可运行，并具备可验证质量门禁（env/test/lint/smoke）。

### 0.2 技术栈（当前）

- Backend/API：Python + FastAPI + SQLAlchemy
- Worker：Python + Temporal + pipeline steps
- MCP：FastMCP 工具层
- Frontend：Next.js（`apps/web`）
- Data：PostgreSQL + SQLite（状态存储）+ Redis（可选）
- Tooling：uv、pytest、Playwright、npm lint/test、ruff

### 0.3 导航入口（先后顺序）

1. `docs/start-here.md`（唯一 1 分钟入口）
2. `README.md`（仓库前门）
3. `docs/runbook-local.md`（本地运行权威手册）
4. `docs/state-machine.md`（3 阶段 + 9-step 契约）
5. `docs/testing.md`（CI/Hook/Smoke 口径）

## 0.4 AI 导航索引（Lazy-Load）

按需加载，先根后模块：

1. **Root Governance**（全局规则与命令）
   - `AGENTS.md`
   - `CLAUDE.md`
2. **Start Here**（最短启动路径）
   - `docs/start-here.md`
3. **API Module**（仅在涉及 API 改动时加载）
   - `apps/api/AGENTS.md`
   - `apps/api/CLAUDE.md`
4. **Worker Module**（仅在涉及流水线/Temporal 改动时加载）
   - `apps/worker/AGENTS.md`
   - `apps/worker/CLAUDE.md`
5. **MCP Module**（仅在涉及 MCP 工具层改动时加载）
   - `apps/mcp/AGENTS.md`
   - `apps/mcp/CLAUDE.md`
6. **Web Module**（仅在涉及前端/UI/E2E 改动时加载）
   - `apps/web/AGENTS.md`
   - `apps/web/CLAUDE.md`

## 1. 文档真相源（优先级）

1. `docs/start-here.md`：唯一 1 分钟入口。
2. `docs/runbook-local.md`：本地运行权威手册。
3. `docs/state-machine.md`：状态机与处理流程契约。
4. `ENVIRONMENT.md` + `infra/config/env.contract.json`：环境变量真相源与严格契约。
5. `docs/testing.md`：测试分层、smoke/live-smoke 口径。
6. 模块文档：`apps/*/(AGENTS.md|CLAUDE.md)`（模块级执行约束）。
7. `README.md`：仓库前门与导航。

冲突处理原则：按上述优先级覆盖，低优先级文档必须回写修正。

## 2. 启动模式（双路径）

### 模式 A：手动标准 6 步

1) 安装依赖  
2) 启动基础服务  
3) 初始化环境  
4) 执行迁移  
5) 启动 API/Worker/MCP  
6) 最小验收

### 模式 B：一键 full-stack

- `./scripts/bootstrap_full_stack.sh`
- `./scripts/full_stack.sh up`
- `./scripts/smoke_full_stack.sh`

### 模式 C：标准环境（AI 执行必须）

- DevContainer：`.devcontainer/devcontainer.json`
- 基础设施 Compose：`infra/compose/core-services.compose.yml`、`infra/compose/miniflux-nextflux.compose.yml`
- 进入标准环境后再执行模式 A/B 的命令，避免“宿主机漂移”导致门禁结果不一致。

补充命令：

- 查看状态：`./scripts/full_stack.sh status`
- 查看日志：`./scripts/full_stack.sh logs`
- 停止栈：`./scripts/full_stack.sh down`

## 3. Golden Commands（只保留仓库内已验证命令）

### 3.1 安装依赖

```bash
uv sync --frozen --extra dev --extra e2e
npm --prefix apps/web ci
```

### 3.2 初始化环境

```bash
./scripts/init_env_example.sh
cp .env.example .env
python3 scripts/check_env_contract.py --strict
set -a; source .env; set +a
```

### 3.2.1 环境分层与密钥注入策略（强制）

- 必须采用 `core + profile overlay`：
  - core：`.env`
  - profile：`PROFILE=local|gce`
  - overlay：`env/profiles/reader.env`（reader 栈 profile 模板）
- 密钥只允许通过 `.env` 或进程环境注入。
- 禁止将 shell 登录配置作为运行时密钥来源。
- 初始化环境时必须执行：
  - `cp .env.example .env`
  - `python3 scripts/check_env_contract.py --strict`

### 3.3 启动基础服务

```bash
brew services start postgresql@16
brew services start redis
temporal server start-dev --ip 127.0.0.1 --port 7233
```

### 3.4 执行迁移

```bash
createdb video_analysis 2>/dev/null || true
for migration in $(ls infra/migrations/*.sql | sort); do
  psql "postgresql://localhost:5432/video_analysis" -v ON_ERROR_STOP=1 -f "$migration"
done
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql
```

### 3.5 启动服务（手动模式）

```bash
./scripts/dev_api.sh
./scripts/dev_worker.sh
./scripts/dev_mcp.sh
```

### 3.6 最小验收

```bash
curl -sS http://127.0.0.1:8000/healthz
curl -sS -X POST http://127.0.0.1:8000/api/v1/ingest/poll \
  -H 'Content-Type: application/json' \
  -d '{"max_new_videos": 20}'
```

### 3.7 全链路烟测（full-stack）

```bash
./scripts/bootstrap_full_stack.sh
./scripts/full_stack.sh up
./scripts/smoke_full_stack.sh
```

### 3.8 安装 Git 门禁 Hooks

```bash
./scripts/install_git_hooks.sh
```

## 4. Safety 边界（强制）

### 4.1 Git 与文件系统红线

- 禁止危险 Git 命令：`git push --force`、`git reset --hard`、`git clean -fd`。
- 禁止未确认的破坏性删除：`rm -rf`、批量覆盖、不可逆清理。
- 未经明确要求，不执行 commit/amend/push。

### 4.2 生产/高风险操作红线

- 未经明确授权，不连接或修改生产环境资源。
- 涉及密钥/令牌/密码时先确认再执行。
- 涉及数据库破坏性动作（drop/truncate/不可逆迁移）时先确认再执行。

## 5. 文档漂移触发器（必须同步更新）

- 变更 `infra/migrations/*.sql`：同步 `README.md` 与 `docs/runbook-local.md`。
- 变更 `apps/worker/worker/pipeline/types.py` 的 `PIPELINE_STEPS`：同步 `docs/state-machine.md`。
- 新增/修改环境变量：同步 `.env.example`、`ENVIRONMENT.md`、`infra/config/env.contract.json`。
- 变更 `apps/api/app/routers/*.py`：同步 `docs/reference/mcp-tool-routing.md` 与 `README.md`（若接口/路由行为变化）。
- 变更 `apps/api/app/schemas/*.py`：同步 `docs/state-machine.md` 与 `README.md`（若输入输出契约变化）。
- 调整本地启动脚本参数/默认值：同步 `docs/start-here.md`、`docs/runbook-local.md`、`README.md`。
- 调整 `infra/compose/*.compose.yml` 或 `.devcontainer/**`：同步 `README.md`、`docs/start-here.md`、`docs/runbook-local.md`。
- 调整日志策略：同步 `docs/reference/logging.md`。
- 调整缓存策略：同步 `docs/reference/cache.md`。
- 调整依赖策略：同步 `docs/reference/dependency-governance.md`。

### 5.1 与 Git Hooks 对齐（必须遵守）

- `.githooks/commit-msg` → `npx --yes --package @commitlint/cli commitlint --config <tmp-config> --edit <commit-msg-file>`
  - Conventional Commits 强制门禁（无根级 `package.json` 依赖时，使用 `npx --yes` + hook 内置最小规则配置）
- `.githooks/pre-commit` → `./scripts/quality_gate.sh --mode pre-commit --profile local`
  - 包含：`scripts/ci_or_local_gate_doc_drift.sh --scope staged`
  - 包含：`check_test_assertions`、`web lint`、`ruff critical`、`secrets scan`、`gitleaks fast scan`、`structured log guard`、`env budget guard`、`IaC entrypoint guard`
- `.githooks/pre-push` → `./scripts/quality_gate.sh --mode pre-push --heartbeat-seconds 20 --mutation-min-score 0.62 --mutation-min-effective-ratio 0.25 --mutation-max-no-tests-ratio 0.75 --profile ci --profile live-smoke --ci-dedupe 1`
  - 包含：`scripts/ci_or_local_gate_doc_drift.sh --scope push`
  - 包含：`coverage>=85`、`core coverage>=95`、`web unit tests`、`python tests(no-silent-skip)`、`api cors preflight smoke`、`contract diff local gate`
  - 包含：与 `preflight-fast`/`web-test-build` 对齐的本地硬门禁：`check_ci_docs_parity`、`docs env canonical guard`、`provider residual guard`、`worker line limits guard`、`schema parity gate`、`web design token guard`、`web build`、`web button coverage`
  - 分层解释：本地 pre-push 比 pre-commit 更严格；启用变更感知，后端变更命中时强制 mutation，无后端变更时跳过 mutation 以避免无效本地消耗。

### 5.2 远程 CI 成本治理（必须遵守）

- 触发或重跑任意远程 CI 前，必须先本地执行并通过：`./scripts/quality_gate.sh --mode pre-push --heartbeat-seconds 20 --mutation-min-score 0.62 --mutation-min-effective-ratio 0.25 --mutation-max-no-tests-ratio 0.75 --profile ci --profile live-smoke --ci-dedupe 1`。
- 上述本地 pre-push 必须覆盖与远程 CI 同级的核心阻断检查（至少包括 `preflight-fast` + `web-test-build` 关键门禁）；远程 CI 仅作为 double-check，不得替代本地验收。
- 远程 CI 失败后，必须先在本地复现并修复，再执行下一次远程触发；禁止“连续重跑碰运气”。
- 同一分支存在被新提交覆盖的 in-progress 远程运行时，必须主动取消旧运行，避免重复计费。
- 预算受限或计费异常期间，必须冻结非必要远程重跑，仅保留一次验证性运行。

## 6. 最小 DoD（Definition of Done）

满足以下条件才算完成：

1. 文档联动已完成（触发器对应文档已同步）。
2. 变更由标准环境执行（`.devcontainer/devcontainer.json` 或等价隔离环境）并保留命令证据。
3. 环境契约校验通过：`python3 scripts/check_env_contract.py --strict`。
4. 后端测试通过：
   - `PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q`
5. 前端 lint 通过：`npm --prefix apps/web run lint`。
6. 假断言门禁通过：`python3 scripts/check_test_assertions.py`。
7. 改动启动或链路逻辑时至少执行一次 smoke：`./scripts/smoke_full_stack.sh`。
8. 变异测试门禁通过：`DATABASE_URL='sqlite+pysqlite:///:memory:' uv run --extra dev --with mutmut mutmut run` 且 score `>=0.60`。

## 7. 交付格式（提交结果必须包含）

每次任务交付至少包含以下四段：

1. 修改文件：列出实际变更路径。
2. 执行命令：列出实际执行命令（含关键参数）。
3. 结果：逐条给出成功/失败与关键输出摘要。
4. 风险与后续：说明未覆盖验证项、潜在影响、建议下一步。

---

维护要求：任何人更新本文件时，必须保证命令可在仓库根目录直接执行，并与 `docs/start-here.md`、`docs/runbook-local.md` 保持一致。
