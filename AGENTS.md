# AGENTS

本文件定义本仓库的人类/AI 协作协议（增强版），目标是让接手者在 1 分钟找到真相源，在 10 分钟完成本地启动、验收与问题定位。

## 1. 文档真相源（优先级）

1. `docs/start-here.md`：唯一 1 分钟入口（先看这个，含 6 步 + 一键路径）。
2. `docs/runbook-local.md`：本地运行权威手册（标准 6 步、参数、排障、运维）。
3. `docs/state-machine.md`：状态机与处理流程契约（`3 阶段 + 9-step pipeline`）。
4. `ENVIRONMENT.md` + `infra/config/env.contract.json`：环境变量真相源与严格校验契约。
5. `docs/testing.md`：CI 门禁、smoke/livesmoke 口径与测试分层。
6. `docs/reference/*.md`：日志、缓存、依赖治理细则。
7. `README.md`：仓库前门与导航。

冲突处理原则：当多文档描述冲突时，按上面的优先级覆盖；低优先级文档必须回写修正。

## 2. 启动模式（双路径）

### 模式 A：手动标准 6 步（可观测、适合定位问题）

适合首次理解系统、逐步排障、精细控制每个环节。

1) 安装依赖  
2) 启动基础服务  
3) 初始化环境  
4) 执行迁移  
5) 启动 API/Worker/MCP  
6) 最小验收  

完整命令见下方 `Golden Commands`。

### 模式 B：一键 full-stack（快速拉起，推荐日常联调）

适合 clone 后快速达到可运行状态并执行全链路烟测。

- `./scripts/bootstrap_full_stack.sh`
- `./scripts/full_stack.sh up`
- `./scripts/smoke_full_stack.sh`

常用补充命令：
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

### 3.7 全链路烟测（full-stack 推荐）

```bash
./scripts/bootstrap_full_stack.sh
./scripts/full_stack.sh up
./scripts/smoke_full_stack.sh
```

### 3.8 安装 Git 门禁 Hooks（强制 pre-commit / pre-push）

```bash
./scripts/install_git_hooks.sh
```

说明：`smoke_full_stack.sh` 默认会执行内置 live smoke、feed/web 检查，并在默认配置下校验 reader 栈与 AI Feed 回写链路。

## 4. Safety 边界（强制）

### 4.1 Git 与文件系统红线

- 禁止危险 Git 命令：`git push --force`、`git reset --hard`、`git clean -fd`。
- 禁止未确认的破坏性删除：`rm -rf`、批量覆盖、不可逆清理。
- 未经明确要求，不执行 commit/amend/push。

### 4.2 生产/高风险操作红线

- 未经明确授权，不连接或修改生产环境资源。
- 涉及密钥/令牌/密码（如 `.env`、凭据轮换、第三方服务配置）时，先确认再执行。
- 涉及数据库破坏性动作（drop/truncate/不可逆迁移）时，先确认再执行。

### 4.3 执行原则

- 优先使用仓库内脚本，不临时发明新流程。
- 先校验环境契约，再启动服务：`python3 scripts/check_env_contract.py --strict`。
- 失败时先给出可复现证据（命令 + 错误输出摘要）再改动。

## 5. 文档漂移触发器（必须同步更新）

以下代码改动发生时，文档必须同 PR 同步更新：

- 变更 `infra/migrations/*.sql`：同步 `README.md` 与 `docs/runbook-local.md` 的迁移说明。
- 变更 `apps/worker/worker/pipeline/types.py` 的 `PIPELINE_STEPS`：同步 `docs/state-machine.md`。
- 新增/修改环境变量：同步 `.env.example`、`ENVIRONMENT.md`、`infra/config/env.contract.json`。
- 调整本地启动脚本参数/默认值（如 `scripts/dev_*.sh`、`scripts/full_stack.sh`、`scripts/bootstrap_full_stack.sh`、`scripts/smoke_full_stack.sh`）：同步 `docs/start-here.md`、`docs/runbook-local.md`、`README.md`。
- 调整日志/缓存/依赖策略：同步 `docs/reference/logging.md`、`docs/reference/cache.md`、`docs/reference/dependency-governance.md`。

## 6. 最小 DoD（Definition of Done）

满足以下条件才算完成：

1. 代码与文档一致：触发器涉及的文档已同步。
2. 环境契约校验通过：
   - `python3 scripts/check_env_contract.py --strict`
3. 后端测试通过（最小集）：
   - `PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q`
4. 前端 lint 通过：
   - `npm --prefix apps/web run lint`
5. 假断言门禁通过：
   - `python3 scripts/check_test_assertions.py`
6. 若改动启动/链路逻辑，至少完成一次 smoke：
   - `./scripts/smoke_full_stack.sh`（或在说明中写明为何未执行）。

## 7. 交付格式（提交结果必须包含）

每次任务交付至少包含以下四段：

1. 修改文件
   - 列出实际变更文件路径（例如：`AGENTS.md`、`docs/runbook-local.md`）。
2. 执行命令
   - 列出实际执行过的命令（完整命令，不省略关键参数）。
3. 结果
   - 每条命令对应成功/失败状态与关键输出摘要。
4. 风险与后续
   - 未覆盖验证项、潜在影响面、建议下一步。

---

维护要求：任何人更新本文件时，必须保证命令可直接在仓库根目录执行，且与 `docs/start-here.md`、`docs/runbook-local.md` 保持一致。
