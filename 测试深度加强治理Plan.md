# 测试深度加强治理 Plan

## 1) 文档目的与愿景

### 1.1 目的
把当前“测试可运行、门禁较完整”的状态，升级为“**可证明真绿（Provable True Green）**”体系：
- 任何一次 `green` 都能回答三件事：
  1. 测到了真实契约吗？
  2. 能拦住回归吗？
  3. 能在 PR 前暴露高风险故障吗？

### 1.2 “完美”定义（本计划目标态）
“完美”不等于 100% 覆盖率，而是满足以下四条同时成立：
- `真实性`：关键链路在 PR 前有真实依赖验证（不只 mock 路径）。
- `反脆弱`：断言强度、突变测试、契约校验可持续压制假绿。
- `可追责`：每条门禁失败可定位到责任层（代码/环境/外部依赖）。
- `可运营`：PR/main/nightly/release 分层门禁明确，成本可控、并发可扩展。

---

## 2) 当前基线总览（做到了什么）

### 2.1 治理骨架已到位
- 已有统一质量门禁脚本，覆盖 pre-commit / pre-push 两种模式：`scripts/quality_gate.sh:30-37`, `scripts/quality_gate.sh:784-962`。
- 已实现“先短测后长测 + heartbeat”执行模式：`scripts/quality_gate.sh:895-920`, `scripts/quality_gate.sh:467-492`。
- Git Hooks 已接入质量门禁与 commitlint：`.githooks/pre-commit:8-11`, `.githooks/pre-push:8-14`, `.githooks/commit-msg:45-49`。

### 2.2 CI 分层和聚合门禁成熟
- `aggregate-gate` 聚合关键 job，按改动范围条件化判定：`.github/workflows/ci.yml:955-1083`。
- `ci-final-gate` 对 main/schedule 强制 live-smoke，对 nightly 强制 flaky 子集：`.github/workflows/ci.yml:1282-1340`。
- Python 测试具备总覆盖率（>=80）+ 核心覆盖率（>=95）双阈值：`.github/workflows/ci.yml:385-420`。

### 2.3 假绿防线已具备初版
- 安慰剂断言拦截脚本已落地，并进入 quality gate：`scripts/check_test_assertions.py:34-71`, `scripts/quality_gate.sh:798-803`, `scripts/quality_gate.sh:861-863`。
- 变异测试门禁已在 pre-push 与 weekly workflow 生效：
  - `scripts/quality_gate.sh:354-420`, `scripts/quality_gate.sh:943-951`
  - `.github/workflows/mutation-weekly.yml:44-75`

### 2.4 E2E 契约治理取得实质进展
- Mock vs API 契约一致性测试已新增：`apps/api/tests/test_mock_contract_consistency.py:224-237`。
- Web E2E 断言升级支持 method/path/status/payload 组合匹配：`apps/web/tests/e2e/support/assertions.py:94-137`。
- 历史 Blocker 已修复并留档：`docs/Repo测试系统审计.md:209-246`。

---

## 3) 关键缺口（没做到什么）

### G1. PR 阶段仍允许关键真实链路跳过（高风险）
- PR 下 `live-smoke` 不执行：`.github/workflows/ci.yml:1232-1234`。
- PR 下 `aggregate-gate` 允许多个关键 job `skipped`：`.github/workflows/ci.yml:1032-1035`, `.github/workflows/ci.yml:1058-1069`。
- 文档口径也明确 PR 场景允许跳过：`docs/testing.md:179`。

### G2. Web E2E 仍以 mock API 为默认主路径（真实性不足）
- `web-e2e` 默认 mock API，不访问真实外部：`docs/testing.md:32`, `docs/testing.md:74`。
- E2E 启动时将前端 API 指向 mock server：`apps/web/tests/e2e/conftest.py:132`。

### G3. 前端“逻辑质量门禁”仍偏弱（Coverage 结构不均衡）
- Web 单测执行了 coverage，但缺少“核心模块最低阈值”门禁策略：`.github/workflows/ci.yml:706-707`。
- 当前额外门禁偏向按钮文本映射，不等价于业务逻辑覆盖：`.github/workflows/ci.yml:712-713`, `scripts/check_web_button_coverage.py:9-13`, `scripts/check_web_button_coverage.py:84-103`。

### G4. 变异测试覆盖范围过窄（防假绿纵深不足）
- `mutmut` 当前仅针对单文件：`pyproject.toml:94-98`。
- pre-push mutation gate 目标同样固定在该文件：`scripts/quality_gate.sh:356-357`。

### G5. 假绿检测仍缺“异步/条件断言”规则级防护
- 现有脚本覆盖字面量自证、self-assert、toBeDefined 等：`scripts/check_test_assertions.py:34-71`。
- 但尚无 Jest/Vitest 规则级 `no-conditional-expect`/`valid-expect-in-promise` 类门禁（需补 ESLint/Jest 规则层）。

### G6. 集成烟测存在可跳过路径（环境不满足时 skip）
- `test_api_integration_smoke` 在驱动或 DB 建库失败时 `pytest.skip`：`apps/api/tests/test_api_integration_smoke.py:40`, `apps/api/tests/test_api_integration_smoke.py:57`。
- 这在本地是合理降级，但 release 场景应转为强制失败策略。

---

## 4) 证据索引（文件+行号）

| 证据ID | 证据路径 | 证明点 |
|---|---|---|
| E-01 | `scripts/quality_gate.sh:784-836` | pre-commit 并行门禁完整执行 |
| E-02 | `scripts/quality_gate.sh:839-953` | pre-push 分阶段（短测/长测/覆盖/mutation） |
| E-03 | `scripts/quality_gate.sh:467-492` | 长任务 heartbeat 机制 |
| E-04 | `.githooks/pre-commit:8-11` | 本地 pre-commit 强制 quality gate |
| E-05 | `.githooks/pre-push:8-14` | 本地 pre-push 强制 mutation+heartbeat |
| E-06 | `.githooks/commit-msg:45-49` | Conventional Commits 门禁 |
| E-07 | `.github/workflows/ci.yml:385-420` | Python 总覆盖+核心覆盖双阈值 |
| E-08 | `.github/workflows/ci.yml:955-1083` | aggregate-gate 条件化验收逻辑 |
| E-09 | `.github/workflows/ci.yml:1282-1340` | final-gate 对 live-smoke/nightly-flaky 的硬约束 |
| E-10 | `.github/workflows/ci.yml:1232-1234` | live-smoke 仅 main/schedule |
| E-11 | `.github/workflows/ci.yml:1032-1035` | PR 场景允许 required=0 时 skipped |
| E-12 | `docs/testing.md:179-181` | PR/main/nightly 差异化放行规则 |
| E-13 | `docs/testing.md:32`, `docs/testing.md:74` | web-e2e 默认 mock API |
| E-14 | `apps/web/tests/e2e/conftest.py:132` | E2E 环境强制注入 mock base URL |
| E-15 | `apps/api/tests/test_mock_contract_consistency.py:224-237` | mock 契约自动对齐路由状态码/模型 |
| E-16 | `apps/web/tests/e2e/support/assertions.py:21-35`, `apps/web/tests/e2e/support/assertions.py:94-137` | E2E 断言精度能力 |
| E-17 | `scripts/check_test_assertions.py:34-71` | 安慰剂断言规则集合 |
| E-18 | `scripts/quality_gate.sh:354-420` | mutation gate 实施细节 |
| E-19 | `pyproject.toml:94-98` | mutmut 仅覆盖单一目标文件 |
| E-20 | `.github/workflows/mutation-weekly.yml:44-75` | weekly mutation 强制 survived=0 |
| E-21 | `.github/workflows/ci.yml:706-707` | Web 单测执行 coverage |
| E-22 | `.github/workflows/ci.yml:712-713` | Web button coverage gate |
| E-23 | `scripts/check_web_button_coverage.py:84-103` | button 覆盖算法本质 |
| E-24 | `apps/api/tests/test_api_integration_smoke.py:40`, `apps/api/tests/test_api_integration_smoke.py:57` | 集成烟测存在 skip 分支 |
| E-25 | `docs/Repo测试系统审计.md:7`, `docs/Repo测试系统审计.md:45-49`, `docs/Repo测试系统审计.md:209-246` | 本轮审计结论与已修复闭环 |

---

## 5) 差距评估（当前 vs 愿景）

评分口径：0-10（10 为完美）。

| 维度 | 当前 | 目标 | 差距 | 说明 |
|---|---:|---:|---:|---|
| PR 前真实链路可验证性 | 6 | 10 | 4 | live-smoke 仅 main/schedule，PR 允许跳过高风险链路 |
| 假绿防护深度 | 7 | 10 | 3 | 有断言守卫+mutation，但 mutation 范围过窄 |
| 前端测试分层平衡（Unit/Comp/E2E） | 6 | 9 | 3 | Web 逻辑覆盖阈值体系不够强，E2E 仍偏重 mock |
| 契约一致性自动化 | 8 | 10 | 2 | 已有 mock-contract 测试，需扩展到 schema diff/变更审计 |
| 门禁分层治理（PR/main/nightly/release） | 8 | 10 | 2 | 分层结构清晰，但 release 级“硬失败策略”仍可增强 |
| Flaky 治理与可观测 | 7 | 9 | 2 | nightly 已有重复跑，缺趋势报表与自动归因 |
| 变异测试覆盖广度 | 4 | 9 | 5 | 当前仅单文件，无法代表核心业务整体质量 |
| 可证明真绿（证据链完整度） | 7 | 10 | 3 | 证据已形成，但还缺“失败归因+SLO”统一报表 |

**综合评分：6.6 / 10（可用，未达可证明真绿）**。

---

## 6) 分阶段治理路线图（Phase 0~5）

### Phase 0（第 0-7 天）- 基线固化与止血

#### 目标
- 锁定当前门禁行为，避免继续“规则漂移”。

#### 任务清单
- T0-1：建立测试治理清单文件（`docs/testing-governance-baseline.md`），固化当前 gate 与阈值映射。
- T0-2：补充 CI 报告归档脚本：汇总 `aggregate-gate` / `ci-final-gate` / mutation 结果到 `.runtime-cache/testing-governance-summary.json`。
- T0-3：把 PR 放行矩阵显式化（job->required/skipped 条件表）并纳入文档自动校验（脚本校验 `ci.yml` 与 `docs/testing.md` 一致性）。
- T0-4：对 `test_api_integration_smoke` 增加“release 模式禁止 skip”开关（例如 `STRICT_INTEGRATION_SMOKE=1`）。

#### 依赖与风险
- 依赖：CI 权限、工作流可修改权限。
- 风险：规则收紧后短期红灯增多。

#### 产出物
- `docs/testing-governance-baseline.md`
- `scripts/report_testing_governance.py`
- `scripts/check_ci_docs_parity.py`

#### 成功标准（KPI）
- KPI-0.1：PR 中 governance 证据产物上传率 100%。
- KPI-0.2：文档与 workflow 漂移告警时间 < 1 次/周。

---

### Phase 1（第 2-3 周）- PR 真实链路前移

#### 目标
- 把“main 才暴雷”的高风险链路尽量前移到 PR。

#### 任务清单
- T1-1：将 `live-smoke` 扩展为全部 PR 必跑（真实 API + 真实 DB + 受控外部探针）。
- T1-2：对 `pr-llm-real-smoke` 由 optional 改为“命中关键路径时 required”。
- T1-3：引入关键路径标签（如 `paths-filter` + 路由映射）判定是否强制真实链路。
- T1-4：`aggregate-gate` 增加“关键路径变更时不允许 skipped”规则。

#### 依赖与风险
- 依赖：Secrets 最小集管理策略。
- 风险：PR 时长上升，需并发优化和缓存。

#### 产出物
- `.github/workflows/ci.yml`（新增/调整 job）
- `scripts/critical_path_detector.py`

#### 成功标准（KPI）
- KPI-1.1：关键路径 PR 的真实链路覆盖率 >= 95%。
- KPI-1.2：main 分支因外部依赖首暴故障数量环比下降 >= 60%。

---

### Phase 2（第 3-5 周）- 假绿深度治理

#### 目标
- 从“有断言”升级为“高强度断言 + 可证伪测试”。

#### 任务清单
- T2-1：前端引入 `eslint-plugin-jest`/Vitest 等价规则，强制：
  - `expect-expect`
  - `no-conditional-expect`
  - `valid-expect-in-promise`
- T2-2：在 `scripts/check_test_assertions.py` 增加异步漏 await 与条件断言模式检测。
- T2-3：把 mutation 目标从单文件扩展为核心域清单（worker pipeline + api services）。
- T2-4：将 weekly mutation 的结果接入趋势报表（survived/killed 趋势图）。

#### 依赖与风险
- 依赖：前端 lint 规则改造与团队接受度。
- 风险：短期需要批量修复历史测试。

#### 产出物
- `apps/web/.eslintrc*` 或 `eslint.config.*` 更新
- `scripts/check_test_assertions.py` 增强
- `pyproject.toml` 的 `[tool.mutmut]` 扩展配置

#### 成功标准（KPI）
- KPI-2.1：前端假绿规则命中后修复闭环率 100%。
- KPI-2.2：核心模块 mutation score >= 0.75（30 天）。
- KPI-2.3：survived mutants 数量 4 周持续下降。

---

### Phase 3（第 2 个月）- 前端测试金字塔补强

#### 目标
- 降低对 E2E+mock 的单点依赖，补齐 Unit/Component 层。

#### 任务清单
- T3-1：定义 Web 核心模块清单（状态管理、关键表单、数据转换层）。
- T3-2：每个核心模块补齐 unit/component tests（React Testing Library + Vitest）。
- T3-3：增加 Web 覆盖率硬阈值（全局 + 核心目录双阈值）。
- T3-4：将 `button coverage` 从主门禁降级为辅助指标（不单独代表质量）。

#### 依赖与风险
- 依赖：前端代码可测性重构（必要时拆函数）。
- 风险：初期改动面较大，需分波次推进。

#### 产出物
- `apps/web/tests/unit/**`
- `apps/web/tests/component/**`
- Web coverage gate 脚本（例如 `scripts/check_web_coverage_threshold.py`）

#### 成功标准（KPI）
- KPI-3.1：Web 核心模块行覆盖 >= 90%，分支覆盖 >= 80%。
- KPI-3.2：E2E 用例总时长降低 >= 25%（将可下沉断言下沉到 unit/component）。

---

### Phase 4（第 2-3 个月）- 契约与集成体系产品化

#### 目标
- 构建“接口契约变更即感知、即阻断”的体系。

#### 任务清单
- T4-1：扩展 `test_mock_contract_consistency` 到 OpenAPI / Pydantic Schema 差异检测。
- T4-2：新增 `contract-diff` workflow：PR 自动对比 base/head 接口契约变化。
- T4-3：集成 smoke 在 release 模式强制“不可 skip”。
- T4-4：新增“兼容性预算”规则（允许新增字段，不允许破坏字段语义）。

#### 依赖与风险
- 依赖：接口 schema 导出能力。
- 风险：历史接口不规范导致一次性修复成本高。

#### 产出物
- `scripts/export_api_contract.py`
- `scripts/check_contract_diff.py`
- `.github/workflows/contract-diff.yml`

#### 成功标准（KPI）
- KPI-4.1：契约变更漏检率 0。
- KPI-4.2：由接口兼容性导致的线上回滚次数下降 >= 80%。

---

### Phase 5（第 3 个月）- “可证明真绿”运营化闭环

#### 目标
- 形成长期稳定运行、可审计、可对外汇报的测试治理系统。

#### 任务清单
- T5-1：建立测试 SLO 仪表盘：
  - PR 首次通过率
  - flaky 率
  - mutation score
  - skipped job 风险比
- T5-2：建立失败归因分类标准：`code_logic_error` / `env_timeout` / `external_dependency`。
- T5-3：引入 release readiness 报告（自动生成，作为发布门禁输入）。
- T5-4：建立季度治理例行审查（对照本 Plan 的 Definition of Perfect）。

#### 依赖与风险
- 依赖：CI artifact 可持续保留策略。
- 风险：没有 owner 会导致运营化指标失效。

#### 产出物
- `docs/testing-slo.md`
- `scripts/build_release_readiness_report.py`
- `reports/release-readiness/*.md`

#### 成功标准（KPI）
- KPI-5.1：关键测试 SLO 连续 4 周达标。
- KPI-5.2：发布前测试风险评估人工介入时间下降 >= 50%。

---

## 7) 并发执行编排（SubAgent 批次模型）

### 7.1 已定批次模型
- **Batch A（并发上限 6）**：门禁与契约
  - A1：CI workflow 规则收紧（PR/main/nightly）
  - A2：quality_gate.sh 扩展与参数治理
  - A3：contract-diff 脚本
  - A4：check_test_assertions 增强
  - A5：文档同步（docs/testing.md + README）
  - A6：报告聚合脚本（SLO/ready 报告）

- **Batch B（并发上限 6）**：测试资产补强
  - B1：Web unit/component 覆盖补齐
  - B2：E2E 用例去 mock 化（关键路径）
  - B3：API 集成 smoke 严格化（禁止 skip 模式）
  - B4：mutation 扩面（worker+api）
  - B5：nightly flaky 统计与可视化
  - B6：release gate 文档与验收脚本

### 7.2 并发安全约束
- 同文件写入任务不可并发（如 `.github/workflows/ci.yml`、`scripts/quality_gate.sh`）。
- 可并发任务：测试新增、文档更新、独立脚本开发、报表生成。
- 每批次结束必须统一跑：`quality gate + targeted smoke + regression subset`。

---

## 8) 门禁与验收体系（PR/main/nightly/release）

### 8.1 PR Gate（快速但不失真）
- 必须：`preflight`、`python-tests`、`web-test-build`、`web-e2e`、`api-real-smoke`、`live-smoke` 全部通过。
- 必须：PR 场景不允许 `live-smoke`、`integration smoke`、`web-e2e`、`api-real-smoke` 为 `skipped`。
- 已定策略：PR 默认执行全量 real API E2E，mock 仅允许本地开发调试，且不可作为 CI 主路径。

### 8.2 Main Gate（防后置爆雷）
- 必须：`aggregate-gate=success`、`live-smoke=success`（已实现，见 `.github/workflows/ci.yml:1328-1333`）。
- 必须：`quality-gate-pre-push` 与 `external-playwright-smoke` success（见 `.github/workflows/ci.yml:1058-1064`）。

### 8.3 Nightly Gate（波动探测）
- 必须：`nightly-flaky-python` success + `nightly-flaky-web-e2e` success（见 `.github/workflows/ci.yml:1318-1325`）。
- 必须：mutation 阈值按 0.85 收敛并进入趋势报表，不仅看单次 pass/fail。

### 8.4 Release Gate（发布前硬门禁）
- 必须：
  - 全量质量门禁通过；
  - 集成烟测不允许 skip（PR/main/release 全禁 skip）；
  - mutation 达到 release 阈值；
  - release-readiness 报告为 `green`。
- 已定策略：新增 `release-candidate` workflow，统一串行执行并输出单一报告。

---

## 9) “完美状态”定义（Definition of Perfect）与最终验收清单

### 9.1 Definition of Perfect
满足以下 12 条即视为“测试体系完美态”：
1. PR 对关键路径具备真实链路验证且不可跳过。
2. mock 契约与真实 API 自动一致性校验常态化。
3. 前端存在稳定 unit/component 层，不依赖 E2E 兜底。
4. E2E 默认断言为精确断言，并覆盖关键协议字段。
5. 全局覆盖率与核心覆盖率双阈值长期达标。
6. mutation 不局限单文件，覆盖核心业务域。
7. 假绿规则覆盖同步/异步/条件断言三类风险。
8. flaky 发现、归因、修复有闭环并可量化。
9. PR/main/nightly/release gate 边界清晰且文档与实现一致。
10. 所有长测具备 heartbeat，失败有分类诊断。
11. release 前可自动生成 readiness 报告。
12. 近 30 天无“测试全绿但上线爆雷”重大事件。

### 9.2 最终验收清单
- [ ] `critical-path PR` 真实链路覆盖率 >= 95%
- [ ] `mutation score (core)` >= 0.80
- [ ] `web core branch coverage` >= 80%
- [ ] `nightly flaky rate` 连续 4 周下降
- [ ] `release gate` 连续 3 次无人工豁免通过
- [ ] `docs/testing.md` 与 `ci.yml` 无漂移告警

---

## 10) 决策点清单（已拍板，口径冻结）

### D1. 全部 PR 强制 live-smoke（已定策略）
- 已定策略：所有 PR 必须执行 `live-smoke`，不再仅关键路径触发。
- 执行口径：PR/main/nightly/release 均按“真实链路优先”执行，禁止以 `skipped` 通过关键验证。
- 影响：PR 时长上升，但可显著降低 main 首暴风险。

### D2. Mutation 门禁阈值 = 0.85（已定策略）
- 已定策略：pre-push、main、nightly 的 mutation 阈值统一收敛到 `0.85`。
- 执行口径：允许迁移窗口，但窗口内必须有按周收敛计划与失败归因。
- 影响：短期红灯增多，长期可提升假绿拦截能力。

### D3. Web 覆盖率硬门禁（已定策略）
- 已定策略：Web 覆盖率硬门禁统一为 `全局>=80` + `核心>=90`。
- 执行口径：button coverage 仅保留为辅助指标，不可替代业务逻辑覆盖门禁。
- 影响：需要补齐 unit/component 测试资产，E2E 压力可逐步回落。

### D4. 集成 smoke 全禁 skip（已定策略）
- 已定策略：PR/main/release 的集成 smoke 一律禁 `skip`，环境不足视为失败而非跳过。
- 执行口径：本地开发可单独使用 debug profile，但不得进入 CI 主路径。
- 影响：对环境稳定性与依赖可用性提出更高要求。

### D5. E2E 默认全量 real API（已定策略）
- 已定策略：CI 中 E2E 默认全量 real API，mock 仅用于开发本地调试。
- 执行口径：PR/main/release 的主路径不得依赖 mock server 作为真实性证明。
- 影响：外部波动可见性上升，需配套重试、隔离与归因机制。

---

## 11) 30/60/90 天执行计划

### Day 0-30
- 完成 Phase 0 + Phase 1。
- 目标：关键路径 PR 不再“可跳过后置爆雷”。
- 里程碑：
  - M1：`live-smoke` 在全部 PR 强制上线（禁 skip）
  - M2：aggregate-gate 关键路径强制规则落地

### Day 31-60
- 完成 Phase 2 + Phase 3（前半）。
- 目标：假绿压制与前端测试分层成型。
- 里程碑：
  - M3：mutation 扩面到多核心模块
  - M4：web coverage 双阈值门禁上线

### Day 61-90
- 完成 Phase 3（后半）+ Phase 4 + Phase 5。
- 目标：形成可运营“可证明真绿”体系。
- 里程碑：
  - M5：contract-diff + release-readiness 全量接入
  - M6：测试 SLO 仪表盘持续运行并纳入发布流程

---

## 12) 附录：优先级队列（P0/P1/P2）+ 快速启动命令

### 12.1 优先级队列

#### P0（立即）
1. 全部 PR 强制真实链路 `live-smoke`（禁 skip）。
2. aggregate-gate 对关键路径禁 `skipped`。
3. PR/main/release 集成 smoke 全禁 `skip`。
4. mutation 目标从单文件扩展到核心域并统一阈值 0.85。

#### P1（短期）
1. Web 覆盖率双阈值门禁。
2. 假绿规则扩展到异步/条件断言。
3. mock-contract 扩展到 schema diff。
4. flaky 趋势报表与归因自动化。

#### P2（中期）
1. release-readiness 自动报告。
2. 测试 SLO 仪表盘。
3. E2E 全量 real API 主路径稳定化（mock 仅保留本地调试）。

### 12.2 快速启动命令（建议按顺序）

```bash
# 1) 本地全量质量门禁（短+长+mutation）
./scripts/quality_gate.sh --mode pre-push --profile ci --profile live-smoke --heartbeat-seconds 25 --mutation-min-score 0.85

# 2) 假断言扫描
python3 scripts/check_test_assertions.py --path .

# 3) 后端核心测试 + 覆盖
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q -rA \
  --cov=apps/worker/worker --cov=apps/api --cov=apps/mcp --cov-fail-under=80

# 4) Web 单测 + 覆盖
npm --prefix apps/web run test -- --coverage

# 5) Web E2E（指定浏览器）
uv run --with pytest --with playwright pytest apps/web/tests/e2e -q --web-e2e-browser chromium

# 6) API 真实集成烟测
uv run pytest apps/api/tests/test_api_integration_smoke.py -q -rA

# 7) Mock 合同一致性
uv run pytest apps/api/tests/test_mock_contract_consistency.py -q -rA

# 8) 手工执行 live smoke（本地）
scripts/smoke_llm_real_local.sh --api-base-url "http://127.0.0.1:18081" --heartbeat-seconds 30

# 9) 最终治理总检查（profile -> pre-commit -> pre-push）
bash scripts/env/final_governance_check.sh

# 10) 运行 weekly mutation 同口径命令
uv run --extra dev --with mutmut mutmut run && uv run --extra dev --with mutmut mutmut export-cicd-stats
```

---

## 本周可立即启动的前 10 个任务

1. 在 `ci.yml` 调整为“全部 PR 强制 `live-smoke`”，并接入 `aggregate-gate` required 逻辑。
2. 修改 `aggregate-gate`：关键路径改动时禁止 `python-tests/api-real-smoke/web-e2e` 为 `skipped`。
3. 为 `test_api_integration_smoke.py` 增加 CI 主路径（PR/main/release）全禁 `skip` 策略。
4. 扩展 `pyproject.toml` 的 `tool.mutmut.paths_to_mutate` 到 API/Worker 核心服务模块，并统一阈值 0.85。
5. 在 `scripts/check_test_assertions.py` 增加异步 promise/await 漏检规则。
6. 在 Web lint 增加 Jest/Vitest 断言质量规则（条件断言、Promise 断言有效性）。
7. 新增 `scripts/check_contract_diff.py` 并在 PR workflow 调用。
8. 将 `check_web_button_coverage.py` 调整为辅指标，新增 `全局>=80 + 核心>=90` 业务逻辑覆盖率 gate。
9. 新增 nightly flaky 趋势汇总脚本并上传 artifact。
10. 产出 `docs/testing-governance-baseline.md`，固化当前门禁矩阵与目标阈值。

---

## 13) 深化附录（执行版）

### 13.1 执行摘要（3个关键结论）
1. 测试体系从“分层可用”升级为“真实性优先”，核心变化是 PR/main/release 全链路强制 real smoke + real API E2E。
2. 质量门禁从“推荐收敛”升级为“硬阈值收敛”，核心阈值固定为 mutation=0.85、Web 覆盖率全局>=80/核心>=90、集成 smoke 禁 skip。
3. 治理重点从“补规则”转为“运营闭环”，必须按周产出 Gate 通过率、flaky 率、mutation 趋势与失败归因，确保不是一次性运动。

### 13.2 范围与非范围
- In Scope：
  - `scripts/quality_gate.sh`、`.github/workflows/ci.yml`、`.github/workflows/mutation-weekly.yml` 门禁策略收敛。
  - `apps/web/tests/e2e/**` 从 CI 主路径 mock 切换到 real API 主路径。
  - `apps/api/tests/test_api_integration_smoke.py` 的 skip 策略改为 PR/main/release 全禁。
  - 覆盖率与 mutation 阈值在 PR/main/nightly/release 统一可审计。
- Out of Scope：
  - 业务功能重构、数据库 schema 设计变更、非测试相关性能优化。
  - 把“外部服务 100% 可用”作为承诺目标（不可数学保证，只能做工程缓解）。

### 13.3 术语表
- True Green：测试通过且可证明覆盖了真实契约和关键故障模式。
- Live Smoke：真实依赖（真实 API/DB/外部服务）最小闭环烟测。
- Hard Gate：失败即阻断合并/发布的门禁。
- Soft Check：失败不阻断，但需进入治理报表并跟踪。
- Flaky：同一提交重复执行结果不稳定。
- Mutation Score：测试杀死变异体比例，用于衡量断言强度。
- Core Coverage：核心目录覆盖率，独立于全局覆盖率统计。
- Skip Debt：关键作业通过 `skipped` 逃逸形成的质量债。

### 13.4 现状架构图（文字版）
1. 开发者提交 PR。
2. CI 触发 `preflight` -> `python-tests` -> `web-test-build` -> `web-e2e(real API)` -> `api-real-smoke` -> `live-smoke`。
3. `aggregate-gate` 聚合所有 required jobs，不接受关键链路 `skipped`。
4. main/release 再次执行完整长测与最终 gate，nightly 执行波动探测与 mutation 收敛。
5. 结果进入 artifact 与周报，形成“失败归因 -> 修复 -> 指标回升”的治理闭环。

### 13.5 Phase 子任务分解表（输入/输出/角色/前置/工时/风险/回滚）
| Phase | 子任务 | 输入 | 输出 | 角色 | 前置 | 工时 | 风险 | 回滚 |
|---|---|---|---|---|---|---|---|---|
| P0 | 规则冻结 | `ci.yml`, `quality_gate.sh` 现状 | 基线文档+脚本参数清单 | QA Owner | 无 | 0.5d | 口径漂移 | 回滚到上个 workflow commit |
| P1 | PR 强制 live-smoke | workflow 依赖图 | PR required jobs 更新 | CI Owner | P0 | 1d | PR 时长上升 | 恢复 required 映射（临时） |
| P1 | 禁 skip 改造 | smoke 测试代码 | PR/main/release skip->fail | API Owner | P0 | 1d | 环境波动增红 | 启用重试+隔离队列 |
| P2 | Mutation=0.85 | mutmut 配置与历史分数 | 统一阈值策略与迁移窗口 | Test Owner | P1 | 1.5d | 大量红灯 | 分模块分周收敛 |
| P2 | Web 覆盖硬门禁 | web 测试覆盖数据 | 全局>=80/核心>=90 门禁 | Web Owner | P1 | 2d | 补测压力 | 暂时冻结非核心目录增量 |
| P3 | E2E real API 主路径 | e2e 配置 | mock 退到本地调试 | Web+API | P2 | 2d | 外部服务不稳 | 增加心跳/重试/归因 |

### 13.6 AC->测试->Gate->Artifact 可追溯矩阵
| AC | 测试/检查 | Gate | Artifact |
|---|---|---|---|
| AC-01: PR 必跑 live-smoke | `scripts/smoke_llm_real_local.sh`/CI job | `aggregate-gate` | `artifacts/live-smoke-report.json` |
| AC-02: mutation>=0.85 | `mutmut run` + `export-cicd-stats` | pre-push/main/nightly | `mutation-results.json` |
| AC-03: Web 覆盖双阈值 | `npm --prefix apps/web run test -- --coverage` | web coverage gate | `coverage-summary.json` |
| AC-04: 集成 smoke 禁 skip | `pytest apps/api/tests/test_api_integration_smoke.py -q -rA` | PR/main/release | `integration-smoke.xml` |
| AC-05: E2E real API 主路径 | `pytest apps/web/tests/e2e -q` | PR/main/release | `playwright-report/` |

### 13.7 KPI 详表（定义/公式/数据源/阈值/告警）
| KPI | 定义 | 公式 | 数据源 | 阈值 | 告警 |
|---|---|---|---|---|---|
| PR 真实链路通过率 | PR required real jobs 首次通过比例 | 首次通过PR数/总PR数 | GitHub Actions runs | >=90% | 连续2天<85% 触发 |
| Mutation 收敛率 | mutation score 达标率 | score>=0.85 的流水线数/总流水线数 | mutmut stats | >=95% | 任一主分支<0.85 |
| Web 核心覆盖率 | 核心目录覆盖达标 | core_coverage>=90 | coverage summary | >=90% | 任一PR低于90阻断 |
| Skip Debt | 关键 gate 被 skip 比例 | skipped_required_jobs/required_jobs | workflow summary | =0 | 任意非0即P1事件 |
| Flaky 率 | 同提交重复执行结果不一致 | flaky_cases/total_cases | nightly rerun reports | <=5% | >8% 连续3天 |
边界说明：以上 KPI 不能“数学保证线上 0 故障”；它们只能提升缺陷提前暴露概率，受外部依赖可用性和测试数据真实性影响。

### 13.8 风险登记册（至少12条）
| 风险ID | 风险描述 | 触发信号 | 影响 | 缓解 |
|---|---|---|---|---|
| R01 | PR 时长显著上升 | P95 持续上升 | 合并效率下降 | 并发执行+缓存预热 |
| R02 | 外部 API 抖动导致误红 | timeout 增多 | 信任下降 | 指数退避重试+分级告警 |
| R03 | 测试数据污染 | 同用例随机失败 | 假 flaky | 数据隔离与清理 |
| R04 | mutation 一次性红灯过多 | score 突降 | 团队阻塞 | 迁移窗口+模块化提升 |
| R05 | 覆盖率“刷数不测质” | 无效断言增加 | 假绿 | 断言规则+反事实检查 |
| R06 | workflow 规则漂移 | 文档与实现不一致 | 决策失效 | parity 检查脚本 |
| R07 | 环境依赖短缺 | 资源准备失败 | 全线失败 | 预检脚本+资源配额 |
| R08 | 本地/CI口径不一致 | 本地绿 CI 红 | 返工 | 标准化命令入口 |
| R09 | 并发改同文件冲突 | merge conflict 高发 | 进度拖慢 | 冲突矩阵与分批 |
| R10 | 关键 job 被绕过 | skipped 变多 | 漏检风险 | required 强制校验 |
| R11 | 发布前手工豁免常态化 | waiver 增多 | 质量下滑 | 豁免审批与到期机制 |
| R12 | 指标无 owner | 周报停更 | 运营失效 | KPI owner 绑定值班 |

### 13.9 并发作战手册（可并发池/冲突矩阵/批次节奏/SubAgent模板）
- 可并发池：
  - Pool-A：`apps/web/tests/**` 覆盖补测。
  - Pool-B：`apps/api/tests/**` smoke 严格化。
  - Pool-C：`scripts/*.py` 报表与校验脚本。
  - Pool-D：`docs/*.md` 口径同步。
- 冲突矩阵：
  - `.github/workflows/ci.yml` 与 `scripts/quality_gate.sh` 禁并发写。
  - `pyproject.toml` 与 mutation workflow 同批只允许 1 人落盘。
- 批次节奏：
  - 批次1（2天）：策略硬化（workflow+gate）。
  - 批次2（3天）：测试资产补齐（web/api）。
  - 批次3（2天）：报表、验收、回归。
- SubAgent 模板（执行提示）：
```text
目标: 收敛到已定策略，不改业务功能。
输入: 指定文件 + AC 列表。
输出: 最小可审计 diff + 验证命令结果。
约束: 禁止新增“可选/推荐”口径；关键 gate 不可 skip。
验收命令:
1) ./scripts/quality_gate.sh --mode pre-push --mutation-min-score 0.85
2) npm --prefix apps/web run test -- --coverage
3) uv run pytest apps/api/tests/test_api_integration_smoke.py -q -rA
```

### 13.10 变更沟通机制（周会模板/升级路径）
- 周会模板：
  - 本周 gate 数据：通过率、耗时、skip debt、flaky、mutation。
  - 本周故障 Top3：症状、根因、修复、预防。
  - 下周计划：必须完成项/风险项/owner。
- 升级路径：
  - P2（局部红）：模块 owner 当日修复。
  - P1（主链路红>1天）：通知 QA/CI 双 owner + 技术负责人。
  - P0（发布阻断或关键漏检）：启动应急会议，冻结非必要合并。

### 13.11 决策点展开（每个选项后果）
- D1 全部 PR 强制 live-smoke：
  - 后果：时长增加但前置暴露能力明显提升；若回退到关键路径触发，将重新引入“未命中映射导致漏检”风险。
- D2 mutation=0.85：
  - 后果：短期修复成本增加；若保持低阈值，假绿率难以下降。
- D3 Web 覆盖硬门禁：
  - 后果：补测压力上升；若不硬化，E2E 将长期承担不合理回归负担。
- D4 集成 smoke 全禁 skip：
  - 后果：环境建设成本上升；若允许 skip，发布可信度不可证明。
- D5 E2E 全量 real API：
  - 后果：受外部波动影响更大；若继续 CI 依赖 mock，真实性不足问题持续。

### 13.12 第一周 Day1-Day7 落地表
| Day | 目标 | 主要动作 | 验收命令 |
|---|---|---|---|
| Day1 | 冻结口径 | 更新 plan/workflow 参数清单 | `python3 scripts/check_ci_docs_parity.py` |
| Day2 | PR 强制 live-smoke | 改 `ci.yml` required 逻辑 | `gh workflow run` 或 PR 试跑 |
| Day3 | 禁 skip | 改 smoke 测试跳过逻辑 | `uv run pytest apps/api/tests/test_api_integration_smoke.py -q -rA` |
| Day4 | mutation 收敛 | 改 gate 阈值至 0.85 | `uv run --extra dev --with mutmut mutmut run` |
| Day5 | Web 覆盖硬门禁 | 加全局/核心双阈值检查 | `npm --prefix apps/web run test -- --coverage` |
| Day6 | E2E real API 切换 | 调整 e2e 配置与主路径 | `uv run pytest apps/web/tests/e2e -q` |
| Day7 | 回归与周报 | 汇总 KPI 与风险处置 | `python3 scripts/report_testing_governance.py` |

### 13.13 失败案例预演（至少5个）
1. 案例A：PR 因外部 API 波动连红。处置：标记 `external_dependency`，启用限次重试和隔离重跑，不放松 hard gate。
2. 案例B：mutation 从 0.83 回退到 0.71。处置：按模块定位 survived mutant，优先修核心目录断言。
3. 案例C：Web 覆盖过线但核心分支覆盖不达标。处置：阻断合并，强制补 core tests，不接受“全局掩盖核心”。
4. 案例D：集成 smoke 因资源缺失被迫 skip。处置：在 CI 主路径视为失败，触发环境修复任务，不允许豁免。
5. 案例E：E2E 使用 mock 在 CI 通过但线上失败。处置：追责为流程违规，要求恢复 real API 主路径并复盘。
边界说明：失败预演用于降低未知风险，但无法覆盖所有黑天鹅事件；因此需保持“持续观测+快速回滚”。

---

## 14) 已拍板决策（强制执行）

### 14.1 生效日期
- 生效时间：**即日起**。
- 执行原则：本节口径高于本文历史“推荐/可选”描述，冲突项一律按已拍板决策执行。

### 14.2 对 CI 配置的直接影响（必须改动）
1. `.github/workflows/ci.yml`
   - PR 事件下将 `live-smoke` 设为 required，禁止关键链路 `skipped`。
   - `web-e2e` 主路径切为 real API；mock 路径仅保留本地开发 profile。
   - `integration smoke` 在 PR/main/release 禁 skip（环境不足即 fail）。
2. `.github/workflows/mutation-weekly.yml`
   - 阈值口径统一为 `0.85`，并输出按模块趋势 artifact。
3. `scripts/quality_gate.sh`
   - `--mutation-min-score` 默认值提升到 `0.85`。
   - pre-push/main/nightly 使用统一阈值逻辑，不再分裂。
4. Web 覆盖率检查脚本（新增或改造）
   - 实施 `全局>=80 + 核心>=90` 硬门禁。
5. `apps/web/tests/e2e/conftest.py` 与相关启动脚本
   - CI 默认不注入 mock base URL，改为 real API endpoint。
6. `apps/api/tests/test_api_integration_smoke.py`
   - CI 主路径下 skip 分支改为 fail 分支，并给出失败原因标签。

### 14.3 风险与缓解（CI 时长、外部波动）
- 风险1：CI 总时长上升。
  - 缓解：并发拆分 job、缓存依赖、仅对变更子集执行全量回归。
- 风险2：外部依赖波动导致误红。
  - 缓解：有限重试（最多2次）、隔离重跑队列、失败归因标记 `external_dependency`。
- 风险3：短期红灯多影响吞吐。
  - 缓解：设置 2-4 周迁移窗口，按模块排期补测并固定 owner。
- 风险4：开发体验下降。
  - 缓解：保留本地 mock 调试入口，但明确禁止进入 CI 主路径。
- 非100%保证边界：该策略显著降低假绿和后置爆雷，但不能保证“零红灯/零线上故障”，尤其在第三方服务不稳定时。

### 14.4 验收标准（1周/2周/4周）
- 1周验收：
  - PR `live-smoke` required 覆盖率 = 100%。
  - CI 主路径 `integration smoke skip` = 0。
  - mutation 门禁已统一到 0.85（允许过渡性失败但需有归因记录）。
- 2周验收：
  - Web 覆盖率硬门禁稳定生效（全局>=80，核心>=90）。
  - E2E CI 主路径 real API 执行占比 = 100%。
  - `aggregate-gate` 关键链路 `skipped` = 0。
- 4周验收：
  - mutation score 达标流水线占比 >=95%。
  - 关键路径 PR 首次通过率 >=90%，且 main 首暴问题较变更前下降 >=50%。
  - 发布前 gate 连续 3 次无人工豁免通过。
