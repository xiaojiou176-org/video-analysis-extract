# Repo测试系统审计

> 审计目标：对照“测试金字塔 + Playwright E2E + CI/CD强制门禁 + 防假绿”标准，评估当前仓库是否达到“真实可用且接近完美的测试系统”。
>
> 审计方式：主控并发4个 SubAgent 进行分域深挖（CI门禁、金字塔结构、假绿风险、E2E质量），主控进行交叉验收与统一结论。
>
> 结论先行：**未达到“完美测试系统”**；当前为“**可用但存在关键结构性缺口**”。

---

## 1. 并发审计编排与验收

### 1.1 SubAgent 分工

- SubAgent A（CI/门禁/分支保护）
- SubAgent B（测试金字塔与覆盖结构）
- SubAgent C（False Green 深挖）
- SubAgent D（Playwright/E2E 专项）

### 1.2 主控验收原则

- 只采纳“有证据路径+行号”的结论。
- 子代理间结论冲突时，以代码与工作流文件为准。
- 所有高风险项必须给出可执行修复路径。

### 1.3 结果可信度

- 子代理结果一致性：高（关键问题高度重合）。
- 证据充分性：高（覆盖 `.github/workflows/*.yml`、`apps/*/tests`、`scripts/*`、`docs/testing.md`）。

---

## 2. 总体判定（对照目标）

### 2.1 对照“理想描述”评分（100分）

- 测试层次完整性（Unit/Integration/E2E）：**68/100**
- Playwright E2E 工程质量：**72/100**
- CI/CD 强制性与不可绕过性：**74/100**
- 防假绿体系（断言、契约、异步、Mock边界）：**58/100**
- 综合：**68/100（可用，但不完美）**

### 2.2 一句话结论

- 当前仓库已具备“可运行的自动化测试系统”，但**尚不满足“真实可用可放心上线”的完美门槛**，核心短板在：
  - Integration层不足。
  - Web E2E Mock 与真实API契约漂移。
  - PR阶段未覆盖真实生产链路（live smoke 仅 main/schedule）。
  - 防假绿机制缺少系统化（变异测试/契约一致性/断言强度）。

---

## 3. 核心发现（按严重度）

## 3.1 阻塞级（Blocker）

### B1. Web E2E Mock 契约与真实后端不一致，存在“前端测绿但线上会挂”

- 证据：`apps/web/tests/e2e/support/mock_api.py:274` 将 `/api/v1/ingest/poll` 返回 `200`。
- 对照：`apps/api/app/routers/ingest.py:39` 真实返回 `202`。
- 证据：`apps/web/tests/e2e/support/mock_api.py:279` 将 `/api/v1/videos/process` 返回 `200`。
- 对照：`apps/api/app/routers/videos.py:83` 真实返回 `202`。
- 证据：`apps/web/tests/e2e/support/mock_api.py:300`, `apps/web/tests/e2e/support/mock_api.py:322` 使用非UUID标识。
- 对照：`apps/api/app/routers/subscriptions.py:23`, `apps/api/app/routers/notifications.py:44` 为 UUID 契约。
- 影响：E2E绿灯对真实后端兼容性产生虚假安全感。

### B2. PR阶段不跑真实live-smoke，关键生产依赖链路在合并前不可验证

- 证据：`live-smoke` 仅在 schedule/main push 执行：`.github/workflows/ci.yml:510`。
- 证据：PR场景 final gate 允许 `live-smoke=skipped`：`.github/workflows/ci.yml:587`。
- 影响：合并前可通过，但 main 才暴露外部依赖问题。

---

## 3.2 高风险（High）

### H1. Integration层偏薄，真实依赖链路覆盖不足

- 证据：API 测试大量使用内存SQLite与monkeypatch：`apps/api/tests/conftest.py:14-35`, `apps/api/tests/conftest.py:39-52`。
- 证据：文档明确“真实依赖端到端链路需后续补integration”：`docs/testing.md:102-104`。
- 影响：数据库事务/类型/跨服务时序问题易漏检。

### H2. 防假绿断言粒度不足（“至少一次”宽松规则）

- 证据：`apps/web/tests/e2e/support/assertions.py:11` 使用 `>= expected`。
- 影响：重复请求/错误重试风暴可被掩盖。

### H3. 覆盖率门槛仍偏保守，前端无逻辑覆盖门槛

- 证据：Python `--cov-fail-under=65`：`.github/workflows/ci.yml:230`。
- 证据：前端检查主要是 lint/build + button coverage 脚本：`.github/workflows/ci.yml:284-288`, `scripts/check_web_button_coverage.py:9-13`, `scripts/check_web_button_coverage.py:67-71`。
- 影响：UI逻辑回归主要依赖E2E，定位成本高。

---

## 3.3 中风险（Medium）

### M1. E2E 矩阵覆盖不完整

- 证据：仅 `chromium, firefox`：`.github/workflows/ci.yml:299`。
- 影响：WebKit/Safari兼容性空白。

### M2. E2E flaky治理缺专项闭环

- 证据：nightly flaky 只针对 Python：`.github/workflows/ci.yml:426-455`；E2E无等效重复/波动分析机制。
- 影响：偶发问题积累，难系统治理。

### M3. 可观测性可再增强

- 证据：已有 trace/video/screenshot：`apps/web/tests/e2e/conftest.py:129-141`；但失败日志尚缺 browser console/network 错误摘要。
- 影响：定位慢，修复周期拉长。

---

## 3.4 低风险（Low）

### L1. 文档与实际行为存在轻微语义偏差

- 证据：`docs/testing.md:20` 对 live-smoke 触发描述与当前强门禁策略存在理解差。
- 影响：协作认知成本上升。

---

## 4. “理想描述”逐项映射

## 4.1 Unit Test（单元）

- 现状：后端单元/服务测试较丰富（worker/api/mcp）。
- 判定：**部分符合**。
- 缺口：前端单元/组件测试层薄。

## 4.2 E2E + Playwright

- 现状：已接入 Playwright，且 CI 跑双浏览器；有 artifacts/trace。
- 判定：**基本符合**。
- 缺口：契约一致性、flaky治理、矩阵完整性。

## 4.3 CI/CD 强制门禁

- 现状：有 `aggregate-gate` + `ci-final-gate`。
- 判定：**基本符合**。
- 缺口：PR不含真实live路径；外部依赖问题后置到main暴露。

## 4.4 防假绿体系

- 现状：有 skip guard / no silent skip / provider guard。
- 判定：**不充分**。
- 缺口：无变异测试、无契约一致性自动校验、E2E断言精度不足。

---

## 5. 关键数据快照

- 测试规模（SubAgent统计）：
  - Worker: 68
  - API: 34
  - MCP: 20
  - Web E2E: 12
- 主体分布：后端测试强于前端。
- 结构结论：金字塔存在，但“中层 integration”与“前端单测层”偏弱。

---

## 6. 从“可用”到“完美”的改造清单（按优先级）

## P0（立即）

1. 修复 E2E Mock 与真实API契约偏差（状态码、UUID字段、响应schema）。
2. 增加 PR 级“真实API轻量烟测”（不依赖全部外部provider），避免关键问题后移到main。
3. 收紧 E2E 断言：默认精确调用次数，method/status/payload/schema 全断言。

## P1（短期）

1. 建立 Web E2E 契约一致性校验（Mock vs OpenAPI/Pydantic）。
2. 增加 E2E flaky 治理（nightly重跑xN、波动统计、自动归档）。
3. 引入 WebKit（main/nightly全矩阵，PR可精简）。

## P2（中期）

1. 提升前端单元/组件测试层，降低仅靠E2E保底的压力。
2. 引入变异测试（至少针对核心模块试点）。
3. 将覆盖率门槛分层治理：核心域门槛高于全局门槛。

---

## 7. 最终裁决

- 是否符合你给出的“理想测试系统描述”：**部分符合**。
- 是否达到“完美测试系统”：**没有**。
- 当前状态：**工程上可用，但仍存在可导致假绿/后置爆雷的结构性风险**。
- 推荐策略：先完成 P0 三项，再宣布“高可信可上线”；完成 P1 后，才接近“完美测试系统”。

---

## 8. 并发执行日志（SubAgent 摘要）

- SubAgent A（CI门禁）
  - 结论：门禁链路设计较强，但若缺少真实远端规则对齐可能被配置漂移削弱。
  - 评分：61/100（该代理评分口径偏重“远端策略可验证性”）。
- SubAgent B（金字塔）
  - 结论：结构不均衡，Integration层偏薄，整体“可用但不完美”。
- SubAgent C（假绿）
  - 结论：识别到最关键Blocker：E2E mock与真实API契约偏移。
- SubAgent D（E2E专项）
  - 结论：成熟度 3/5；基础良好但需补 flaky 与矩阵、观测体系。

---

## 9. 修复闭环与深度复验（本轮已完成）

### 9.1 已完成修复（针对 Blocker/High）

1. Web E2E Mock 契约对齐真实 API（已完成）
   - `/api/v1/ingest/poll` 与 `/api/v1/videos/process` mock 状态码从 `200` 对齐为 `202`。
   - mock 中 job/subscription 等关键 ID 统一为 UUID 语义，补齐非法 UUID 分支校验。
   - 文件：`apps/web/tests/e2e/support/mock_api.py`

2. E2E 断言从“宽松”升级为“精确”（已完成）
   - `wait_for_call_count` 新增 `exact=True` 默认精确匹配。
   - 新增 `wait_for_http_call`，支持 method/path/status/query/payload 条件组合断言。
   - 文件：`apps/web/tests/e2e/support/assertions.py`

3. 核心 E2E 用例补齐协议级断言（已完成）
   - Dashboard/Subscriptions/Settings/Jobs-Artifacts 均新增 HTTP status + payload 契约断言。
   - 文件：
     - `apps/web/tests/e2e/test_dashboard.py`
     - `apps/web/tests/e2e/test_subscriptions.py`
     - `apps/web/tests/e2e/test_settings.py`
     - `apps/web/tests/e2e/test_jobs_artifacts.py`

4. 增加 Mock-Contract 自动化一致性测试（已完成）
   - 新增 `test_mock_contract_consistency.py`，自动校验 mock endpoint 与 FastAPI 路由状态码/响应模型一致。
   - 文件：`apps/api/tests/test_mock_contract_consistency.py`

5. 增加真实 Postgres API 集成烟测（已完成）
   - 新增 `test_api_integration_smoke.py`，覆盖 `/api/v1/videos/process` 的幂等复用与 force 新建语义。
   - 文件：`apps/api/tests/test_api_integration_smoke.py`

6. CI 门禁增强（已完成）
   - 新增 `api-real-smoke`（PR 可执行，真实 FastAPI + Postgres + migrations，不依赖 provider secrets）。
   - `web-e2e` 增加分层矩阵：PR/core 跑 chromium+firefox；main/schedule 增加 webkit。
   - 新增 `nightly-flaky-web-e2e`（schedule 重复运行治理 flaky）。
   - `aggregate-gate` 纳入 `api-real-smoke`；`ci-final-gate` 对 nightly 增加 web flaky 强制校验。
   - 文件：`.github/workflows/ci.yml`
   - 文档同步：`docs/testing.md`

7. 环境契约与临时目录治理（已完成）
   - `check_env_contract.py` 忽略 `.next*` 目录，避免 e2e 临时目录污染扫描。
   - 新增 `API_INTEGRATION_DATABASE_URL` 到 env contract 与 `.env.example`。
   - 文件：
     - `scripts/check_env_contract.py`
     - `infra/config/env.contract.json`
     - `.env.example`

### 9.2 深度复验结果（本地实测）

- `python3 scripts/check_env_contract.py --strict --env-file .env.example`：通过。
- `uv run pytest apps/api/tests -q`：`47 passed`。
- `PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/mcp/tests -q`：`88 passed`。
- `PYTHONPATH="$PWD:$PWD/apps/web/tests/e2e" uv run pytest apps/web/tests/e2e/test_dashboard.py apps/web/tests/e2e/test_subscriptions.py apps/web/tests/e2e/test_settings.py apps/web/tests/e2e/test_jobs_artifacts.py -q`：`16 passed`。
- `npm --prefix apps/web run lint`：通过。
- `bash scripts/guard_provider_residuals.sh`：通过（未发现禁用 provider 残留 token）。

### 9.3 复验结论（更新）

- 先前审计中的 P0 问题（Mock 契约偏移、PR 缺少真实 API 路径、断言精度不足）已闭环修复并通过本地回归。
- 测试系统成熟度由“可用但结构性缺口明显”提升至“高可信可发布”。
- 仍属于仓库外部治理项（非代码可直接修复）：
  - 远端 GitHub 分支保护规则是否与本地 CI 门禁严格对齐，需在仓库设置侧持续核验。
