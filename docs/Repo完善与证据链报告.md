# Repo完善与证据链报告

## 1. 审计范围与方法

- 范围：`apps/api`、`apps/worker`、`apps/mcp`、`apps/web`、`docs`、根目录运行文档。
- 方法：

1. 仓库静态扫描（路由、模型、配置、测试、文档对齐）。
2. 本地最小验收命令执行（env contract、后端测试、前端 lint）。
3. 外部权威来源核验（官方文档/官方仓库优先）。

## 2. 当前结论（先给结果）

### 2.1 总体评估

- 当前仓库已达到“工程上较成熟、可持续演进”的状态，但尚未达到“完美”：

1. AI/Gemini 能力接入较完整（thinking、schema、context cache、computer use）。
2. MCP 工具已收敛为 13 个，且已有路由指南与组合示例。
3. 测试与 lint 当前可通过（见第 6 节证据）。
4. 关键未完成项：AI Feed 一等入口、订阅分类能力、按分类通知路由、来源适配器化。

### 2.2 “完美”定义下的差距

1. 功能闭环差距：缺 `GET /api/v1/feed/digests` 与 `/feed` 页面主入口。
2. 业务建模差距：订阅模型仍是平台硬编码，缺 `category/tags`。
3. 策略能力差距：通知仍以全局配置为主，缺 category-aware 路由策略。

## 3. 仓库内证据（可定位）

### 3.1 Gemini 关键能力现状

1. Thinking 机制：
   - 文档明确“复杂任务强制 include_thoughts=true 且缺签名硬失败”：`README.md`
   - 运行配置存在 `GEMINI_THINKING_LEVEL` 与 `GEMINI_INCLUDE_THOUGHTS`：`.env.example`、`apps/worker/worker/config.py`
   - 结果字段可见 `thought_signatures/thought_signature_digest`：`README.md`、`apps/api/app/services/jobs.py`
2. Structured Outputs：
   - 严格 schema 模式配置存在：`.env.example`、`apps/worker/worker/config.py`
   - API/MCP 类型契约与测试存在：`apps/mcp/schemas/tools.json`、`apps/mcp/tests/test_tools_schema_parity.py`
3. Computer Use：
   - API 与 worker 工具链接入存在：`apps/api/app/routers/computer_use.py`、`apps/worker/worker/pipeline/steps/llm_client.py`
   - 默认仍有确认门禁：`README.md`、`apps/worker/worker/config.py`
4. Context Caching：
   - `GEMINI_CONTEXT_CACHE_*` 全套配置已接入：`.env.example`、`ENVIRONMENT.md`、`apps/worker/worker/config.py`
   - tools 场景绕过缓存有明确语义：`apps/worker/worker/pipeline/steps/llm_client.py`
5. Media Resolution：
   - 当前规范化级别包含 `low/medium/high/ultra_high`：`apps/worker/worker/pipeline/runner_policies.py`

### 3.2 MCP 包装与“不会迷路”程度

1. 工具总数：13（已收敛）
   - 来源：`apps/mcp/schemas/tools.json`
2. 工具名单：
   - `vd.jobs.get`
   - `vd.videos.list`
   - `vd.videos.process`
   - `vd.retrieval.search`
   - `vd.workflows.run`
   - `vd.ingest.poll`
   - `vd.computer_use.run`
   - `vd.ui_audit.run`
   - `vd.health.get`
   - `vd.subscriptions.manage`
   - `vd.notifications.manage`
   - `vd.artifacts.get`
   - `vd.ui_audit.read`
3. 路由说明：
   - 体系映射：`docs/phase3-architecture.md`
   - Agent 路由手册：`docs/reference/mcp-tool-routing.md`
4. 本次补强：
   - 已补充“失败语义 + I/O 示例”：`docs/reference/mcp-tool-routing.md`

### 3.3 订阅/通知/阅读主入口差距证据

1. 订阅仍平台硬编码：
   - `platform IN ('bilibili','youtube')`：`apps/api/app/models/subscription.py`
   - `source_type` 仅三种：`apps/api/app/models/subscription.py`、`apps/api/app/routers/subscriptions.py`
2. 通知以全局配置为主：
   - `daily_digest_enabled/daily_digest_hour_utc`：`apps/api/app/routers/notifications.py`、`apps/api/app/services/notifications.py`
3. 缺 AI Feed 路由：
   - 现有为 `artifacts` 按 job/video 查询：`apps/api/app/routers/artifacts.py`
   - Web 导航无 `/feed`：`apps/web/components/nav.tsx`

### 3.4 Branch / Worktree 现状

1. 本地分支：`main`
2. 远端分支：`origin/main`、`origin/chore/ci-hardening-final`、`origin/release/final-hardening`
3. worktree：1 个（当前主工作树在 `main`）

## 4. 外网事实核验（权威来源）

1. RSSHub 官方文档（路由、部署、使用语境）
   - <https://docs.rsshub.app/>
2. RSSHub 官方仓库（部署与生态基线）
   - <https://github.com/DIYgod/RSSHub>
3. Miniflux 官方 API 文档（可用于你的 AI 流水线回写/读取）
   - <https://miniflux.app/docs/api.html>
4. Miniflux 官方文档主页
   - <https://miniflux.app/docs/>
5. Nextflux 官方仓库（前端阅读器）
   - <https://github.com/electh/nextflux>
6. Follow/Folo 官方仓库（客户端与项目边界以仓库说明为准）
   - <https://github.com/RSSNext/Follow>
7. Google Gemini API 文档（thinking/function calling/structured output/computer use/context caching）
   - <https://ai.google.dev/gemini-api/docs/thinking>
   - <https://ai.google.dev/gemini-api/docs/function-calling>
   - <https://ai.google.dev/gemini-api/docs/structured-output>
   - <https://ai.google.dev/gemini-api/docs/computer-use>
   - <https://ai.google.dev/gemini-api/docs/context-caching>

## 5. 改进计划（从“可用”到“有理有据且接近完美”）

1. P0：AI Feed 主入口
   - 新增 `GET /api/v1/feed/digests`（时间线分页）
   - 新增 Web `/feed` 页面并入导航
2. P1：订阅分类 + 分类通知
   - 订阅模型新增 `category/tags`
   - 通知规则新增 category-aware 路由
3. P2：来源适配器化
   - 从平台硬编码迁移到 `adapter + source_url`
   - 先接标准 RSS，再扩到论坛/X 等

> 详细实施蓝图见：`Repo_Next_Step_Plan.md`

## 6. 可执行验证证据

1. 环境变量契约检查通过：

```bash
uv run python scripts/check_env_contract.py --strict
```

2. 后端测试通过（134 passed）：

```bash
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q
```

3. 前端 lint 通过：

```bash
npm --prefix apps/web run lint
```

## 7. 本次实际改动

1. 新增报告：`Repo完善与证据链报告.md`
2. MCP 路由文档增强（失败语义 + I/O 示例）：`docs/reference/mcp-tool-routing.md`
3. 既有实施计划（详细蓝图）已存在：`Repo_Next_Step_Plan.md`

## 8. 阻塞与说明

1. SubAgent 并发执行在当前会话被系统上限阻塞（`agent thread limit reached (max 16)`），本次改为主会话并行执行等价审计与核验。
2. 该阻塞不影响仓库结论可信度，但影响“子代理证据链”形式。
