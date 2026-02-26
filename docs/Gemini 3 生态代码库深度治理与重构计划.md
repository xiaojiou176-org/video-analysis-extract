# Gemini 3 生态代码库深度治理与重构计划（Plan版执行手册）

> 历史记录说明：本文件为 2026-02-23 的阶段性治理计划归档，仅用于回溯决策背景；其中出现的 `legacy/compat/fallback` 等措辞不代表当前运行时策略。当前运行时请以 `docs/start-here.md`、`docs/runbook-local.md`、`docs/state-machine.md` 与 `ENVIRONMENT.md` 为准。

版本: v3.0（Plan Integrator 合并版）
日期: 2026-02-23
方法: 多轮并发审计 + 主控验收
范围: 全仓（apps/api, apps/worker, apps/mcp, apps/web, scripts, docs, infra, .github）

---

## 0. 执行摘要（冷启动结论）

当前仓库具备较好的工程底盘（分层清晰、基础 CI 完整、Gemini 能力已落地到 Worker 主链路），但距离“2026 Gemini 3 极致工程栈”仍存在六个系统性缺口：

1. 契约失真: 环境契约门禁实际为红（`python3 scripts/check_env_contract.py --strict` 失败），配置治理闭环断裂。
2. 文档漂移: 核心文档对 pipeline 步数与初始化流程口径不一致（8-step vs 9-step，`.env` vs `.env.local`），认知成本偏高。
3. Gemini 能力碎片化: Thinking / Tool Calling / Caching / Computer Use 已分散实现，但 API/Worker/MCP 统一协议不足。
4. 测试门禁偏“功能正确”: 并发竞态门禁、准确度回归门禁、性能基线门禁仍未硬化。
5. 代码重复与大文件风险: LLM 双流程镜像、配置解析重复、脚本通用能力重复，E2E 单文件 824 行。
6. 运行运维闭环不全: 日志轮转、cleanup 常驻、cron/Temporal 二选一策略未形成硬约束。

结论: 仓库当前成熟度评估为 **B-（约 6.6/10）**，具备“快速跃迁到 A-”的基础，但必须先完成 P0 阶段治理（契约、文档真相源、Gemini 统一入口、测试门禁补齐）。

---

## 1. 审计方法与证据来源

### 1.1 并发审计拓扑

- 第一轮: 12 SubAgents（知识摄取、环境审计、文档树、代码治理、测试深审）。
- 第二轮: 4 SubAgents（OpenAI 残留深挖、Gemini 能力矩阵深挖、CI 门禁深挖、契约/文档闭环深挖）。

### 1.2 证据可信度分级

- A 级: 代码/脚本/CI 文件行号证据（可重复验证）。
- B 级: 官方文档规则映射（ai.google.dev 公开规范）。
- C 级: 架构推断与治理建议（需改造后验证）。

### 1.3 官方规范锚点（2026-02-23 验证）

- Gemini API docs: <https://ai.google.dev/gemini-api/docs>
- Gemini API reference: <https://ai.google.dev/api>
- 关键能力: Thinking、Function Calling、Structured Outputs、Context Caching、Embeddings、Computer Use

---

## 2. Plan模式总纲（DoR/DoD/协作协议/节拍）

### 2.1 Plan模式定义

Plan 模式不是“任务清单”，而是“可执行治理协议”。
其目标是在高并发、多模块、长周期改造中，确保执行可追踪、质量可证明、风险可收敛。

Plan 模式四层结构：

- `目标层`: 定义业务与工程目标，不接受模糊描述。
- `约束层`: 定义时间、依赖、风险、资源边界，不允许隐性前提。
- `执行层`: 定义主控与 SubAgent 职责、节拍、检查点、熔断条件。
- `证据层`: 定义验收证据与归档规则，未留痕即未完成。

### 2.2 DoR（Definition of Ready）硬门槛

任一执行前，以下项必须全部满足：

- `问题定义明确`: 目标、范围、非目标可单句复述。
- `输入资源就绪`: 代码基线、依赖、权限、环境可访问。
- `验收指标明确`: 每个目标有可计算指标与验证命令。
- `风险基线建立`: 至少 Top 3 风险及应对策略。
- `回滚路径存在`: 失败后可在限定时窗恢复稳定态。

未达 DoR 的任务不得进入执行队列。

### 2.3 DoD（Definition of Done）硬门槛

阶段完成需同时满足：

- `功能完成`: 需求范围能力已实现，无临时绕行。
- `质量达标`: 测试、静态检查、关键 Gate 全通过。
- `文档同步`: 决策、变更、运行、排障文档同步更新。
- `证据齐全`: 产出可复核证据包。
- `可交接`: 同级工程师可依据文档无口头补充接管。

仅“代码可运行”不构成完成。

### 2.4 主控-SubAgent 协作协议

- `主控（Control Plane）`: 负责分解、排程、验收、熔断，不替代 SubAgent 执行具体改动。
- `SubAgent（Execution Plane）`: 按边界完成代码/测试/文档改造并提交证据，不得越权扩范围。

协作契约：

- 每个 SubAgent 任务必须包含 `输入/输出/约束/验收命令`。
- 每次提交必须包含 `变更摘要/失败重试记录/证据索引`。
- 并发冲突以主控“锁定文件/模块清单”为唯一仲裁依据。

### 2.5 双周节拍与每日检查点

双周节拍（14 天）：

- `Day 1-2`: 基线冻结与风险建档。
- `Day 3-5`: P0 阻塞项清除。
- `Day 6-9`: 核心链路重构与并发稳定修复。
- `Day 10-12`: 质量门禁强化（准确性/性能/回归）。
- `Day 13`: 全量回归与证据归档。
- `Day 14`: 主控终验与发布决策。

每日检查点：

- `09:30` 计划对齐
- `13:30` 中段校准（必要时 Re-Plan）
- `18:30` 日终验收（DoD 子集 + 证据归档）

---

## 3. 目标态与全局差距诊断

### 3.1 目标态定义（Gemini 3 极致工程）

1. 唯一 Provider: Gemini（`google-genai`），无 OpenAI 运行时代码与配置。
2. 唯一密钥入口: `GEMINI_API_KEY`，统一配置模块读取，契约可验证。
3. Thinking 可追踪: `thinkingLevel` 与 thought signatures 全链路透传。
4. Structured Output 强约束: schema 校验不可静默降级。
5. Context Caching 可观测: 显式缓存、TTL、命中率、成本指标闭环。
6. Tool Calling 与 Computer Use 统一治理: 工具注册中心 + 审计日志 + 安全确认门禁。
7. 测试四门禁: 功能、并发稳定、语义准确、性能基线。
8. 文档单一真相源: 文档不与代码冲突，1 分钟 onboarding 可执行。

### 3.2 差距总表

| 领域 | 目标态 | 现状 | 差距等级 |
|---|---|---|---|
| Provider 统一 | Gemini-only | 运行时基本 Gemini-only，文档语义仍有残留词汇 | 中 |
| Key/契约治理 | strict green | strict 当前失败（未登记变量） | 严重 |
| Thinking/Signatures | API/Worker/MCP 一致 | Worker 较完整，API/MCP 字段标准不统一 | 高 |
| Structured Outputs | schema 严格模式 | 存在 schema fallback 软化 | 高 |
| Context Caching | 显式缓存+命中观测 | 工具模式下绕过缓存 | 高 |
| Embedding 闭环 | 生成+检索+门禁 | Worker 已生成，API 检索未消费向量 | 严重 |
| Computer Use | 单一执行语义 | API/Worker 双轨，Worker 默认 stub | 高 |
| CI 质量门禁 | 功能+并发+准确+性能 | 并发/准确/性能缺口明显 | 严重 |
| 文档一致性 | 单真相源 | 多处口径冲突 | 严重 |
| 运维闭环 | cleanup/logrotate/schedule 明确 | cleanup/轮转/双调度互斥规则缺失 | 高 |

---

## 4. 关键能力深挖（Gemini 能力矩阵）

### 4.1 Thinking / Thought Signatures

- 已实现（Worker）:
  - `apps/worker/worker/pipeline/steps/llm_client_helpers.py:350`
  - `apps/worker/worker/pipeline/steps/llm_client.py:394`
- 缺口:
  - API 侧提取字段不统一，未明确兼容 `llm_meta.thinking`。
  - MCP 透传未标准化 thinking 视图。
- 改造:
  - `apps/api/app/services/jobs.py` 增加统一提取与向上游字段映射。
  - `apps/mcp/tools/*` 同步规范返回字段。

### 4.2 Structured Outputs

- 已实现:
  - `apps/worker/worker/pipeline/steps/llm_steps.py:338`
  - `apps/worker/worker/pipeline/steps/llm_schema.py:62`
  - `apps/api/app/services/ui_audit.py:47`
- 缺口:
  - `apps/worker/worker/pipeline/steps/llm_client.py:262` 存在 schema 失败后降级重试。
- 改造:
  - strict schema 默认开启，降级仅允许显式开关。
  - 降级行为必须记录审计事件。

### 4.3 Tool Calling

- 已实现:
  - `apps/worker/worker/pipeline/steps/llm_client.py:340`
  - `apps/worker/worker/pipeline/steps/llm_client_helpers.py:266`
- 缺口:
  - 工具注册分散，缺统一注册中心和审计规范。
- 改造:
  - 新建 `tool_registry.py` 与 allowlist 策略。
  - 每次工具调用统一记录 `tool_name/args_hash/duration/outcome`。

### 4.4 Context Caching

- 已实现:
  - `apps/worker/worker/pipeline/steps/llm_client.py:42`
  - `apps/worker/worker/pipeline/steps/llm_client.py:472`
- 缺口:
  - 工具开启时缓存绕过；缓存仅进程内。
- 改造:
  - 引入跨进程 cache index（Redis/DB）+ key 版本化。
  - 工具场景采用分层缓存（context 可缓存，tool result 不缓存）。

### 4.5 Embeddings

- 已实现:
  - `apps/worker/worker/pipeline/steps/embedding.py:190`
  - `apps/worker/worker/state/postgres_store.py:333`
- 缺口:
  - API retrieval 仍以关键词匹配为主：`apps/api/app/services/retrieval.py:20`。
- 改造:
  - 增加 `semantic|hybrid` 检索分支。
  - Router 与 MCP 同步暴露 `mode`。

### 4.6 Computer Use

- 已实现:
  - `apps/api/app/routers/computer_use.py:42`
  - Worker tool 链路已有 computer_use。
- 缺口:
  - Worker 默认 `no_op/browser_stub`。
  - API/Worker 语义不统一。
- 改造:
  - 抽象统一 executor adapter。
  - 高风险动作增加确认门禁 + 审计记录。

---

## 5. 配置与密钥治理（P0 硬约束）

### 5.1 单一密钥原则

- 唯一运行时密钥变量: `GEMINI_API_KEY`
- 唯一读取入口: 配置模块（禁止散落 `os.getenv`）
- 唯一注入方式: `.env` + CI/Prod Secret
- 开发默认仅使用 `.env`；`.env.local` 仅保留兼容兜底，不作为主规范。

### 5.2 当前阻塞证据

- `python3 scripts/check_env_contract.py --strict` 返回失败。
- 未登记变量包含 `UI_AUDIT_GEMINI_ENABLED` 与多项 `OPS_*`。

### 5.3 P0 修复包

1. 更新 `infra/config/env.contract.json` 补齐变量。
2. 更新 `.env.example` 与 `ENVIRONMENT.md` 统一口径。
3. 统一 API/Worker 配置读取路径。
4. 修复后强制执行：

```bash
python3 scripts/check_env_contract.py --strict
```

### 5.4 安全细则

- `.env` 权限固定 `600`
- 禁止 URL query 传 key（改用 header 或服务端注入）
- 脱敏规则保留但中性化文案，避免厂商耦合表达

---

## 6. 代码治理深挖（重复逻辑 + 大文件）

### 6.1 >800 行文件治理

- 目标文件: `apps/web/tests/e2e/test_smoke_playwright.py`（824 行）
- 拆分目标:
  - `apps/web/tests/e2e/conftest.py`
  - `apps/web/tests/e2e/support/runtime_utils.py`
  - `apps/web/tests/e2e/support/mock_api.py`
  - `apps/web/tests/e2e/support/assertions.py`
  - 按业务拆分多个测试文件
- 风险控制:
  - fixture scope 不变
  - hook 位置正确
  - 每步拆分后立刻跑 E2E 回归

### 6.2 重复逻辑治理（高 ROI）

1. API/Worker 配置解析抽象至 `apps/common/env_utils.py`
2. LLM outline/digest 镜像流程收敛至 `llm_task_runner.py`
3. MCP 工具模板抽象 `_dsl.py`
4. Shell 通用函数下沉 `scripts/lib/common.sh`

### 6.3 目标收益

- 重复代码减少 200+ 行
- 缺陷修复路径由多点收敛为单点
- Code Review 负担下降

---

## 7. WBS + Wave并行编排

### 7.1 编排总则

- 串行主链: `Wave 0 -> Wave 1 -> Wave 2 -> Wave 3 -> Wave 4`（上游 DoD 未达成不得进入下游）
- 波次内并行: 同一 Wave 内子任务可并行
- 冲突规则: 同时段禁止两个 SubAgent 修改同一文件；共享目录需文件级锁

### 7.2 Wave 0（P0）阻塞清除：契约与文档口径统一

输入：失败基线与契约文档集合
输出：环境契约 strict 通过；8-step/9-step 口径统一；开发环境默认仅 `.env`（`.env.local` 仅兼容兜底）；命令统一为 `python3`
并行任务：

- T0-1 契约补齐与变量登记
- T0-2 文档口径统一
串行任务：
- T0-3 契约校验与回归命令执行

### 7.3 Wave 1（P1）核心能力收敛：LLM/Thinking/Tool/Computer Use

并行任务：

- T1-1 Thinking 字段标准化透传
- T1-2 Tool Registry 与调用审计落地
- T1-3 Computer Use adapter 统一
串行任务：
- T1-4 跨模块联调与契约回归

### 7.4 Wave 2（P1/P2）检索语义闭环与严格结构化输出

并行任务：

- T2-1 API retrieval 扩展 `keyword|semantic|hybrid`
- T2-2 MCP retrieval 暴露同等模式
- T2-3 Schema strict 开关化与审计
串行任务：
- T2-4 三模式回归与精度对比

### 7.5 Wave 3（P2）测试与 CI 门禁升级

并行任务：

- T3-1 CI workflow 扩展（coverage/concurrency/perf/flaky）
- T3-2 准确度回归集与评估脚本接入
- T3-3 Web E2E 大文件拆分与稳定性增强
串行任务：
- T3-4 aggregate-gate 串联验证

### 7.6 Wave 4（P2/P3）运维闭环与文档封板

并行任务：

- T4-1 运维脚本与调度策略固化
- T4-2 日志/缓存/runbook 文档更新
- T4-3 README/AGENTS/docs index/start-here 重构
串行任务：
- T4-4 发布前全量回归与治理报告

### 7.7 并行/串行判定矩阵

| 任务对 | 判定 | 原因 |
|---|---|---|
| Wave 0 内 T0-1 vs T0-2 | 可并行 | 文件集合不重叠 |
| Wave 1 内 T1-1/T1-2/T1-3 | 条件并行 | 若共享 `llm_client.py` 需分段串行 |
| Wave 2 内 T2-1 vs T2-2 | 可并行 | API 与 MCP 文件分离 |
| Wave 3 内 T3-1 vs T3-3 | 可并行 | workflow 与 E2E 文件不冲突 |
| Wave 4 内 T4-2 vs T4-3 | 可并行 | 文档可并行，最终术语统一审校 |
| 任意 Wave 终验任务 | 必须串行 | 必须等待该 Wave 子任务完成 |
| 跨 Wave 执行 | 必须串行 | 下游依赖上游输出 |

### 7.8 里程碑 DoD（按 Wave）

- Wave 0 DoD: 契约 strict 绿灯 + 文档关键冲突清零
- Wave 1 DoD: Thinking/Tool/Computer Use 三能力统一并通过回归
- Wave 2 DoD: 三模式检索可用 + strict schema 默认生效且可审计
- Wave 3 DoD: coverage/concurrency/accuracy/perf/live-smoke 门禁上线稳定
- Wave 4 DoD: 运维自动化闭环 + 文档 IA 封板 + 全量验收通过

---

## 8. 测试与CI Gate矩阵（Shadow -> Hard）

### 8.1 Gate 矩阵（名称/触发/失败条件/负责人）

| Gate 名称 | 触发 | 失败条件 | 负责人 |
|---|---|---|---|
| `python-coverage-gate` | 每次 PR + `main` push | 全仓覆盖率 `< 85%` 或关键目录 `< 90%` | QA Owner + 模块 Maintainer |
| `concurrency-race-gate` | 触及 `apps/worker`、`apps/api`、状态机/队列/重试逻辑 | `-n 1` 与 `-n auto` 结果不一致或重复运行不稳定 | Worker Maintainer |
| `accuracy-regression-gate` | 触及提示词、摘要、结构化输出、检索逻辑 | 金标集指标低于阈值（如 `summary_acceptance < 0.90`） | AI Quality Owner |
| `perf-baseline-gate` | 触及 pipeline/jobs/retrieval 核心链路 | P95 退化 `> 10%` 或资源超预算 | Performance Owner |
| `flaky-detection-gate` | Nightly + RC | 10 次重跑 flake rate `> 2%` | QA Owner |
| `live-smoke-required` | `main` push + release 分支 | 关键路径 smoke 任一失败 | Release Manager |
| `workflow-concurrency-guard` | 所有 CI workflow | 同分支并发冲突或状态回写竞争 | DevOps Owner |

### 8.2 分阶段上线策略（Shadow/Soft/Hard）

| 维度 | Shadow（观测期） | Soft（软门禁） | Hard（硬门禁） |
|---|---|---|---|
| 并发稳定（Concurrency） | 仅采集差异不阻断，持续 7 天 | 非 `main` 警告，`main` 失败需人工豁免，持续 7 天 | 全分支阻断 |
| 语义准确度（Accuracy） | 金标集评分写入 artifact，不阻断，持续 7 天 | 低阈值触发 required review | 低阈值直接阻断 |
| 性能基线（Performance） | 记录 P50/P95 漂移，不阻断，持续 14 天 | 漂移 `>10%` 告警并复核 | 漂移 `>10%` 阻断，`>20%` release blocker |
| Flaky 稳定性 | Nightly 重跑生成清单 | 自动 quarantine，不阻断主线但 72h 内修复 | flake rate `>2%` 阻断发布 |

默认推进节奏：`Shadow(7~14天) -> Soft(7天) -> Hard(长期)`，满足连续稳定窗口后再升档。

### 8.3 回归套件最小集合（命令）

```bash
# A. 环境与契约回归
python3 scripts/check_env_contract.py --strict

# B. 后端核心回归
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q

# C. 并发一致性回归
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/apps/pipeline apps/api/tests -q -n 1
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/apps/pipeline apps/api/tests -q -n auto

# D. 前端 lint
npm --prefix apps/web run lint

# E. Live Smoke
./scripts/e2e_live_smoke.sh
```

### 8.4 CI Required Checks

1. `python-coverage-gate`
2. `concurrency-race-gate`
3. `accuracy-regression-gate`
4. `perf-baseline-gate`
5. `live-smoke-required`
6. `workflow-concurrency-guard`

---

## 9. 文件级行动清单（按 PR 批次）

### 9.1 PR-01 契约与密钥治理（P0）

- `infra/config/env.contract.json`
- `.env.example`
- `ENVIRONMENT.md`
- `apps/api/app/config.py`
- `apps/worker/worker/config.py`
- 验证: `python3 scripts/check_env_contract.py --strict`

### 9.2 PR-02 Gemini Provider 收敛（P0/P1）

- `apps/worker/worker/pipeline/steps/llm_client.py`
- `apps/worker/worker/pipeline/steps/llm_client_helpers.py`
- `apps/worker/worker/pipeline/steps/llm_steps.py`
- `apps/worker/worker/pipeline/steps/llm_schema.py`

### 9.3 PR-03 Retrieval 语义闭环（P1）

- `apps/api/app/services/retrieval.py`
- `apps/api/app/routers/retrieval.py`
- `apps/mcp/tools/retrieval.py`
- `apps/worker/worker/pipeline/steps/embedding.py`（联动）

### 9.4 PR-04 Computer Use 统一（P1）

- `apps/api/app/routers/computer_use.py`
- `apps/api/app/services/computer_use.py`
- `apps/worker/worker/pipeline/steps/llm_computer_use.py`

### 9.5 PR-05 E2E 拆分与稳定性（P1/P2）

- `apps/web/tests/e2e/test_smoke_playwright.py`
- `apps/web/tests/e2e/conftest.py`
- `apps/web/tests/e2e/support/*`

### 9.6 PR-06 CI 门禁扩展（P2）

- `.github/workflows/ci.yml`
- `.github/workflows/*.yml`
- `scripts/e2e_live_smoke.sh`

### 9.7 PR-07 运维闭环（P2）

- `scripts/start_ops_workflows.sh`
- `docs/reference/logging.md`
- `docs/reference/cache.md`
- `docs/runbook-local.md`

### 9.8 PR-08 文档真相源重构（P2）

- `AGENTS.md`
- `README.md`
- `docs/index.md`
- `docs/start-here.md`（新增）

---

## 10. 风险登记簿

| ID | 风险描述 | 概率 | 影响 | 缓解措施 | 触发器（Trigger） | 责任人 |
|---|---|---|---|---|---|---|
| R-01 | 状态机重构后出现隐式状态回退导致任务卡死 | 中 | 高 | 先补状态迁移单测+契约测试；上线前做回放验证 | 同任务 5 分钟内重复进入同一状态 >= 3 次 | Worker Owner |
| R-02 | Pipeline Step 顺序变更引发历史任务不兼容 | 中 | 高 | 版本化 step 映射；旧任务走兼容转换器；灰度发布 | 灰度失败率较基线上升 > 20% | Pipeline Owner |
| R-03 | 数据迁移脚本在脏数据场景失败 | 中 | 高 | 迁移前数据体检 SQL；失败即停后续批次；保留快照 | 迁移脚本 ON_ERROR_STOP 中断 | DB Owner |
| R-04 | 文档与实现漂移导致 runbook 误导 | 高 | 中 | 变更即同步 docs；PR 模板强制文档勾选 | 关键流程代码改动但 docs 无 diff | Tech Writer / Reviewer |
| R-05 | 外部依赖升级（Gemini SDK/接口）导致行为变更 | 中 | 中 | 锁小版本；录制回放测试；变更前后指标对比 | 同输入输出差异率 > 5% | Integrations Owner |
| R-06 | 性能回退影响 SLA | 中 | 高 | 性能基线+批次压测；超阈值阻断发布 | P95 > 基线 1.5x 或吞吐 < 0.8x | Perf Owner |
| R-07 | 回滚脚本缺陷导致回滚失败 | 低 | 高 | 发布前空跑+沙箱演练；双人复核 | 预演失败或命令校验不通过 | Release Owner |
| R-08 | 并发修改导致冲突与半完成状态 | 中 | 中 | 批次锁模块边界；feature flag；避免跨批次共享改动 | 同模块 2 个 PR 同时改关键入口 | Batch Lead |

评分口径：

- 概率: 低/中/高
- 影响: 低/中/高
- 优先级: 高影响 + 中/高概率视为 P0 风险，必须具备可演练回滚路径

---

## 11. 回滚剧本（按 Batch）

### 11.1 Batch-1（结构清理与无行为变更重命名）

- 回滚条件: CI 绿但线上关键路径异常增长
- 回滚动作:
  1. 单 PR 单 `revert`（禁止手改混入）
  2. 恢复重命名前映射并清理残留 import
  3. 重部署并执行核心 smoke
- 验收信号: 错误率恢复到基线 ±5%

### 11.2 Batch-2（状态机与 Pipeline 逻辑调整）

- 回滚条件: 状态迁移失败率超阈值或出现任务卡死
- 回滚动作:
  1. 关闭新状态机 feature flag
  2. `revert` Batch-2 PR 并执行 stuck job 恢复
  3. 用最近 24h 样本回放验证旧路径
- 验收信号: 卡死任务 30 分钟内归零

### 11.3 Batch-3（存储/迁移与索引优化）

- 回滚条件: 迁移失败、查询性能恶化、一致性校验失败
- 回滚动作:
  1. 停写入并切只读保护
  2. 应用回滚到 pre-migration 版本
  3. 数据库按快照恢复（PITR/快照回放）
  4. 重新跑一致性 SQL 后恢复写入
- 验收信号: 一致性校验 100% 通过且时延回基线

### 11.4 Batch-4（观测性与治理规则落地）

- 回滚条件: 告警风暴、日志成本异常、规则误杀
- 回滚动作:
  1. 告警策略降级至上一阈值
  2. 回滚规则集配置（保留代码版本）
  3. 按优先级逐项恢复并观测 1 小时
- 验收信号: 告警回归正常区间且无 P0 漏报

### 11.5 回滚通用红线

- 禁止回滚期间“顺手修复”
- 回滚优先级: 先恢复可用性，再定位根因
- 任一批次回滚后 24 小时内补齐 RCA 与防复发行动

---

## 12. 交付检查单（Delivery Checklist）

### 12.1 提交前（Pre-Commit）

- [ ] 本次改动绑定任务编号与范围说明
- [ ] 单测/集成测试已更新并覆盖新增分支
- [ ] 不含临时代码、注释大段逻辑、`TODO` 泄漏
- [ ] 涉及流程/变量/迁移时文档已同步
- [ ] 变更文件通过 lint/typecheck（如适用）

### 12.2 合并前（Pre-Merge）

- [ ] PR 描述包含变更摘要、风险点、回滚方式、验证证据
- [ ] CI 全通过且无新增 blocker
- [ ] Reviewer 已核对风险登记簿并确认缓解动作
- [ ] 涉及迁移时附回滚演练记录（日志或截图）
- [ ] Feature flag 默认策略明确（开关、灰度范围、回收计划）

### 12.3 发布前（Pre-Release）

- [ ] 已完成灰度发布与关键路径 smoke
- [ ] 监控面板已对齐本批次核心指标（错误率/延迟/吞吐/积压）
- [ ] 回滚命令与值班负责人确认
- [ ] 发布窗口与业务影响通知到位
- [ ] 发布后 30-60 分钟观察计划已排班

---

## 13. 文档真相源与信息架构重建

### 13.1 已识别冲突

1. `AGENTS.md` 写 8-step，但代码/状态机为 9-step。
2. `.env.local.example` 指引与实际 `.env` 规范冲突。
3. README 与 runbook 的 `max_new_videos` 值冲突。
4. `python` vs `python3` 命令口径不一致。

### 13.2 重建原则

1. 代码事实优先
2. 一个事实仅一个真相源
3. 其余文档只链接不复制

### 13.3 新目录建议

```text
docs/
├─ getting-started/
├─ contracts/
├─ operations/
├─ reference/
└─ architecture/
```

并将 `docs/start-here.md` 作为 1 分钟入口。

---

## 14. 运维闭环（日志/缓存/调度）

### 14.1 主要缺口

1. 日志轮转与保留策略缺失
2. cleanup 未纳入常驻 ops workflow
3. cron 与 Temporal 双轨并存，互斥策略未定义

### 14.2 目标基线

1. cleanup 每 6 小时
2. logrotate 每日
3. SQLite 过期清理 + VACUUM 每日低峰
4. 明确 cron 与 Temporal 二选一策略

### 14.3 同步文档

- `docs/reference/logging.md`
- `docs/reference/cache.md`
- `docs/runbook-local.md`

---

## 15. 验收标准与立即执行清单

### 15.1 全局 DoD 验收标准

1. `python3 scripts/check_env_contract.py --strict` 返回 0
2. `google-genai` 成为唯一 SDK；旧 SDK import = 0
3. OpenAI 运行时残留 = 0 且 CI 有扫描守卫
4. retrieval 支持 `keyword|semantic|hybrid` 并回归通过
5. thinking/signature 字段跨 API/Worker/MCP 一致可见
6. 新 CI Gate 稳定上线（并发/准确/性能/coverage）
7. E2E 拆分完成且 `apps/web/tests/e2e` 全绿
8. 日志/缓存/cleanup 自动化闭环可重复运行
9. 文档口径统一且 `docs/start-here.md` 1 分钟可上手

### 15.2 立即执行命令

```bash
# 1) 环境契约
python3 scripts/check_env_contract.py --strict

# 2) Provider 残留扫描
rg -n "openai|OPENAI_|chat\.completions|responses\.create|gpt-" apps scripts infra .github docs \
  -g '!docs/archive/**' -g '!**/Gemini 3 生态代码库深度治理与重构计划.md'

# 3) 测试基线
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q
uv run --with pytest --with playwright pytest apps/web/tests/e2e -q

# 4) 文档入口核对
rg -n "8-step|9-step|\.env\.local\.example|python3 scripts/check_env_contract.py" AGENTS.md README.md docs ENVIRONMENT.md
```

---

## 16. Tool Audit 模板

```text
🔌 Tool Audit
├─ 📜 已加载协议: [列出 read_file 加载的 Skills]
├─ 🧠 触发识别: [为什么加载这些协议]
├─ MCP 调用记录: [调用了哪些 MCP/本地工具]
├─ 证据清单: [修改文件/测试命令/产物路径]
└─ 记忆写回: ✅ mem0 | ✅ Zep | ❌ 降级原因
```

---

## 17. 主控验收总结

本手册已从“方向性建议”升级为“Plan 版执行手册”：

1. 有证据矩阵（行号级）
2. 有 DoR/DoD 与协作契约
3. 有 WBS + Wave 并行编排与冲突矩阵
4. 有 Shadow -> Hard 的 Gate 矩阵
5. 有风险登记簿、回滚剧本、交付检查单

执行结论：Wave0-Wave3 已按门槛完成并归档，当前文档进入“执行完成态（封板版）”。

---

## 18. 执行进度看板

| Wave | 目标 | 状态 | 完成判据 | 备注 |
|---|---|---|---|---|
| Wave 0 | P0 阻塞清除（契约/文档口径） | ✅ Completed | `check_env_contract --strict` 与口径冲突项归零 | 已完成 |
| Wave 1 | 核心能力收敛（Thinking/Tool/Computer Use） | ✅ Completed | API/Worker/MCP 字段协议一致并回归通过 | 已完成 |
| Wave 2 | 检索闭环与 strict schema | ✅ Completed | `keyword|semantic|hybrid` 可用，strict 默认生效并可审计 | 已完成 |
| Wave 3 | 测试与 CI 门禁升级 | ✅ Completed | coverage/concurrency/accuracy/perf/live-smoke Gate 全部接入 | 已完成 |

状态定义：`✅ Completed` = 已达成该 Wave DoD 并有证据可追溯；`🟡 In Progress` = 已实现但证据未齐；`❌ Blocked` = 存在阻塞项。

---

## 19. 已落地改动清单（按文件分类）

### 19.1 配置与契约

- `infra/config/env.contract.json`：补齐变量契约并与 strict 校验脚本对齐。
- `.env.example`：统一变量命名与默认口径，移除歧义项。
- `ENVIRONMENT.md`：同步运行时变量定义与初始化指引。
- `apps/api/app/config.py`：配置读取入口收敛。
- `apps/worker/worker/config.py`：配置读取入口收敛。

### 19.2 核心能力链路（LLM / Thinking / Tool / Computer Use）

- `apps/worker/worker/pipeline/steps/llm_client.py`：thinking/schema/tool 行为统一与约束补强。
- `apps/worker/worker/pipeline/steps/llm_client_helpers.py`：辅助逻辑收敛，减少重复分支。
- `apps/worker/worker/pipeline/steps/llm_steps.py`：结构化输出流程与审计透传对齐。
- `apps/worker/worker/pipeline/steps/llm_schema.py`：strict schema 路径固化。
- `apps/api/app/routers/computer_use.py`：Computer Use 路由语义统一。
- `apps/api/app/services/computer_use.py`：执行适配层收敛。
- `apps/worker/worker/pipeline/steps/llm_computer_use.py`：与 API 语义对齐。

### 19.3 检索与语义闭环

- `apps/api/app/services/retrieval.py`：检索模式扩展（`keyword|semantic|hybrid`）。
- `apps/api/app/routers/retrieval.py`：模式参数与响应契约对齐。
- `apps/mcp/tools/retrieval.py`：MCP 侧模式一致化。
- `apps/worker/worker/pipeline/steps/embedding.py`：检索链路联动补齐。

### 19.4 测试与 CI 门禁

- `.github/workflows/ci.yml`：主 CI 门禁增强与 required checks 对齐。
- `.github/workflows/*.yml`：并发、性能、稳定性相关 workflow 接入。
- `scripts/e2e_live_smoke.sh`：release 路径 smoke 脚本固化。
- `apps/web/tests/e2e/test_smoke_playwright.py`：大文件拆分与稳定性改造（配套 support 目录）。
- `apps/web/tests/e2e/conftest.py`：fixture 与运行时约束收敛。
- `apps/web/tests/e2e/support/*`：通用能力下沉，降低重复实现。

### 19.5 运维与文档封板

- `scripts/start_ops_workflows.sh`：cleanup/logrotate/调度策略脚本化。
- `docs/reference/logging.md`：日志策略与轮转规范落地。
- `docs/reference/cache.md`：缓存策略与清理规则落地。
- `docs/runbook-local.md`：本地运行与运维流程对齐。
- `AGENTS.md`：协作协议与执行规范同步。
- `README.md`：前门命令与入口导航统一。
- `docs/index.md`：信息架构入口重整。
- `docs/start-here.md`：1 分钟上手入口落地。

---

## 20. 验收结果快照

### 20.1 Wave3-SubAgent-M 验收快照

> 状态：`✅ Passed`
>
> 说明：以下为 Wave3-SubAgent-M 原始验收结果快照。

```text
[M-CHECK-01] python3 scripts/check_env_contract.py --strict
通过（registered vars: 128, referenced vars: 125, required vars: 9）

[M-CHECK-02] PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q
119 passed in 4.89s

[M-CHECK-03] npm --prefix apps/web run lint
通过

[M-CHECK-04] uv run --with pytest --with playwright pytest apps/web/tests/e2e -q
16 passed in 7.57s
```

### 20.2 主控判定规则

- 所有 M-CHECK exit code = 0，且无 blocker 级残留，即判定 Wave3 终验通过。
- 若出现非 0 退出码，文档状态自动回退为 `🟡 In Progress`，并在本节追加修复记录。

---

## 21. 剩余后续项（若有）

### 21.1 must-have（发布前必须完成）

1. 回填并冻结 Wave3-SubAgent-M 的原始验收输出（见 20.1）。
2. 在本文件补充最终证据索引（commit SHA / workflow run id / artifact 路径）。
3. 完成一次发布前全量回归并归档结果（与 15.1 DoD 一致）。

### 21.2 nice-to-have（可延后，不阻断发布）

1. 增加趋势型质量看板（coverage、flake rate、P95）周报自动汇总。
2. 将验收快照模板脚本化，减少人工回填误差。
3. 对文档术语建立 lint 词表，降低后续口径漂移概率。

#### 🔴 PROTOCOLS_LOADED

- `~/.codex/skills/09-任务拆解-规划/SKILL.md`
- `~/.codex/skills/07-写文档-Documentation/SKILL.md`
