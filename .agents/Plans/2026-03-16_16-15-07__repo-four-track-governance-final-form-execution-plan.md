# Repo Four-Track Governance Final Form Execution Plan

## Header

- Plan ID: `2026-03-16_16-15-07__repo-four-track-governance-final-form-execution-plan`
- Repo: `📺视频分析提取`
- Status: `IN_PROGRESS`
- Source of Truth: `本文件是本次改造执行的唯一可信状态源`
- Execution Mode: `hard-cut / single-route / no-illusion / no-permanent-compat`

## Objective

把 Repo 从“repo-side 高成熟但 external/adoption 闭环未完成、且仍存在完成幻觉”的当前状态，推进到“外层闭环更真、public 叙事更稳、runtime/cache 单出口更硬、结果证明与 newcomer 证明进入主链”的下一阶段正确形态。

## Score Targets / Target State

| 维度 | 当前状态 | 目标状态 |
| --- | --- | --- |
| 项目含金量 / 招聘信号 | 强工程项目，但结果证明弱于治理证明 | 结果证明进入主链，能稳定讲“价值 + 证据 + owner-level 判断” |
| 开源就绪度 | 可 public，但只适合 limited-maintenance source-first 叙事 | 权利、隐私、品牌、public surface 集中说明；外部分发边界不再误导 |
| 文档治理 | 高成熟，但存在 manual sync tax 与 external status 语义缝 | 高漂移事实 render-only，状态语义单一、不可误读 |
| CI 治理 | 高成熟，但 external verified 未钉死到 same-HEAD same-run | 所有完成性状态都被主链持续验证 |
| 架构治理 | 高成熟，但 glue 面未完全显式化 | bridges inventory 成为强制控制面 |
| 缓存治理 | `.runtime-cache` 为主出口，但 `cache/.cache` 仍有制度后门 | repo-side 运行噪音唯一出口只有 `.runtime-cache/**` |
| 日志治理 | 高成熟，但 helper / 直写、jsonl / plain 并存 | 结构化主写入面统一，辅助日志降级为次级面 |
| 根目录治理 | 高成熟但预算贴边 | 新增 root 项冻结，root 预算留缓冲区 |
| 上游治理 | 台账强，但 standard image / compose image external lane 未闭环 | external lane current-proof 与 image lane 同轮次 verified |

## Current Status

- 当前工作树非干净快照，已存在一批未提交的治理改动。
- 已完成第一轮 hard cut：
  - external truth / same-HEAD current-proof 已接线，并 fresh 通过 targeted gate 与 `./bin/governance-audit --mode audit`
  - runtime/cache 单出口已切掉 repo 根 `cache/` 与 `.cache` 白名单后门，并 fresh 通过 targeted gate 与 `./bin/governance-audit --mode audit`
  - public rights / privacy / brand 三个边界面已收口为受治理 reference 事实源，并接入 README / nav / change-contract / public-entrypoints 控制面
- 当前仍未关闭的主要剩余项：
  - `ghcr-standard-image` external lane 仍 blocked
  - newcomer / result proof truth pack 已进入主链，但 `repo-side-strict-ci` fresh PASS 收据与 full newcomer receipt 仍缺
  - historical release artifact truth 已接 gate，但是否要进一步迁出当前路径仍可继续推进
- 当前禁止：
  - 继续保留宽松 `verified`
  - 继续允许 repo-side root `cache/` / `.cache/`
  - 继续把历史样例写成像当前官方证明

## Workstream Table

| WS | 名称 | 目标 | 优先级 | 状态 |
| --- | --- | --- | --- | --- |
| WS1 | Repo 定位与 public 叙事真相重构 | README / positioning / readiness / done-model 同口径 | P0 | completed |
| WS2 | External proof 与标准镜像链硬切 | `verified` 只对应 same-HEAD same-run，外层 image lane 闭环 | P0 | in_progress |
| WS3 | Runtime/cache 单出口硬切 | repo-side 运行噪音唯一合法出口收口到 `.runtime-cache/**` | P0 | completed |
| WS4 | Historical artifact truth 收口 | 历史样例不再冒充当前 release / proof | P1 | completed |
| WS5 | Docs facts-source / render-only 收口 | 高漂移 facts render-only，manual docs 只讲解释层 | P1 | in_progress |
| WS6 | Bridge inventory / glue 面显式化 | 所有桥接面进控制面并受 gate 约束 | P1 | completed |
| WS7 | Rights / privacy / trademark 边界集中说明 | public-safe surface 对外边界集中化 | P1 | completed |
| WS8 | Newcomer / result proof 主链化 | newcomer receipt 与 result proof 变成 gate 输入 | P0 | in_progress |
| WS9 | Logging 主写入面统一 | 统一结构化主写入，降低双轨维护税 | P2 | pending |
| WS10 | Root budget 缓冲与冻结 | 防止 root 再次长歪 | P2 | pending |

## Task Checklist

- [x] 创建本次执行 Plan 并开始持续维护
- [x] 读取现有执行痕迹，确认当前树已进行到哪一步
- [x] 审核并修正 external proof / status word / same-HEAD 逻辑
- [x] 审核并修正 standard image / compose image external lane 相关控制面
- [x] 审核并修正 runtime/cache 单出口控制面与 cleanup prefix
- [x] 审核并修正 historical artifact truth 与 current proof 的边界
- [x] 审核并修正 README / public positioning / done-model / external status 对外口径
- [x] 建立或补齐 bridge inventory 与 gate
- [x] 建立 rights / privacy / trademark 集中边界事实源并接线控制面
- [x] 建立 newcomer / result proof truth pack 与 gate
- [x] 运行关键验证并记录结果
- [x] 更新 Plan 为本轮最终一致状态

## Decision Log

- `2026-03-16 16:15:07 America/Los_Angeles`
  - 决策：采用单一路线 hard-cut 执行，不做 A/B 方案。
  - 原因：当前仓库的主要风险不是缺方案，而是旧幻觉与旧语义继续存活。
  - 未选方案：不采用“先补展示层再慢慢收口控制面”的路线，因为这会继续制造假成熟。
- `2026-03-16 16:15:07 America/Los_Angeles`
  - 决策：先接手当前 dirty worktree，而不是假装回到干净起点。
  - 原因：当前树已经有结构性治理改动，回避它只会重复劳动或制造冲突。
- `2026-03-16 16:40:00 America/Los_Angeles`
  - 决策：external remote workflow 的 `verified` 只允许由 same-HEAD 成功 run 升级。
  - 原因：旧 commit 成功被 current snapshot 消费，是当前最大完成幻觉源头。
  - 未选方案：不继续允许 renderer 直接用“最近一次 success”覆盖 canonical readiness 状态。
- `2026-03-16 16:46:00 America/Los_Angeles`
  - 决策：repo-side cleanup 不再允许 root `cache/` 与 `.cache/`。
  - 原因：如果保留根级后门，`.runtime-cache/**` 就永远不是真单出口。
  - 未选方案：不保留长期兼容白名单。
- `2026-03-16 17:02:00 America/Los_Angeles`
  - 决策：rights/privacy/brand 边界说明进入 `docs/reference/`，并接入 public/docs 控制面。
  - 原因：root budget 已贴边，不能为了补边界说明继续向根目录塞文档。
  - 未选方案：不新增根级 `RIGHTS.md` / `PRIVACY.md` / `TRADEMARK.md`。
- `2026-03-16 17:18:00 America/Los_Angeles`
  - 决策：先把 standard-image external blocker 收敛成更诚实的 current artifact，再决定是否继续深挖 buildx。
  - 原因：当前最需要的是 truthful blocker，不是模糊的“某条 lane 超时”。
  - 未选方案：不在未确认 builder 健康模型前盲目扩大战术修补范围。
- `2026-03-16 17:48:00 America/Los_Angeles`
  - 决策：bridge inventory 只登记长期显式桥接面，不把所有脚本都塞进桥接台账。
  - 原因：桥接台账的目标是解释长期存在的 repo/runtime/external bridge，而不是制造新的噪音目录。
  - 未选方案：不把 every wrapper 都登记成 bridge。
- `2026-03-16 17:57:00 America/Los_Angeles`
  - 决策：newcomer/result proof 先主链化为 truthful proof pack，再把缺失的 strict/full newcomer 收据显式保留为缺口。
  - 原因：当前最大的结构问题是“没有统一 truth pack”，不是“缺一个完美终局收据”。
  - 未选方案：不把 missing strict receipt 包装成通过，也不让这条线继续只活在聊天里。

## Validation Log

| 验证项 | 状态 | 验证方法 | 结果 | 备注 |
| --- | --- | --- | --- | --- |
| Plan 已落盘 | pass | 文件创建 | 本文件已创建 | 后续持续维护 |
| external same-HEAD proof | pass | `python3 scripts/governance/probe_external_lane_workflows.py`; `python3 scripts/governance/check_current_proof_commit_alignment.py`; `python3 scripts/governance/render_docs_governance.py` | fresh PASS；release evidence 舊成功已降为 `historical` | WS2 |
| runtime/cache 单出口 | pass | `bash -n scripts/runtime/start_ops_workflows.sh`; `python3 scripts/governance/check_root_policy_alignment.py`; `python3 scripts/governance/check_runtime_outputs.py` | fresh PASS | WS3 |
| public narrative consistency | pass | `python3 scripts/governance/check_public_entrypoint_references.py`; `python3 scripts/governance/check_docs_governance.py`; `./bin/governance-audit --mode audit` | fresh PASS | WS1 |
| rights/privacy/brand boundary pack | pass | docs/nav/change-contract/public-entrypoints 接线 + `./bin/governance-audit --mode audit` | fresh PASS | WS7 |
| repo-side governance total gate | pass | `./bin/governance-audit --mode audit` | 已 fresh 连续 PASS 两轮 | WS1/WS2/WS3/WS7 |
| standard image readiness | blocked | `bash scripts/ci/check_standard_image_publish_readiness.sh` | 仍 blocked，当前 artifact 诚实记录 buildx runtime preparation failure | WS2 |
| historical artifact truth | pass | `python3 scripts/governance/check_historical_release_examples.py`; `./bin/governance-audit --mode audit` | fresh PASS | WS4 |
| bridge inventory | pass | `python3 scripts/governance/check_governance_schema_references_exist.py`; `[bridge-expiry]`; `./bin/governance-audit --mode audit` | fresh PASS（4 bridges tracked） | WS6 |
| validate-profile newcomer preflight | pass | `./bin/validate-profile --profile local` | fresh PASS | WS8 |
| repo-side strict receipt | partial | `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` | 已启动并产生新 run manifests，但本轮未拿到 fresh exit 收据 | WS8 |
| newcomer / result proof 主链化 | pass-with-open-gap | `python3 scripts/governance/render_newcomer_result_proof.py`; `python3 scripts/governance/check_newcomer_result_proof.py`; `./bin/governance-audit --mode audit` | truth pack 已进入主链；strict receipt 仍诚实标记为 `missing_current_receipt` | WS8 |

## Risk / Blocker Log

| 时间 | 类型 | 内容 | 影响 | 当前处理 |
| --- | --- | --- | --- | --- |
| 2026-03-16 16:15:07 | workspace drift | 当前工作树已有未提交治理改动 | 需要避免覆盖与反向回滚 | 先读取现有痕迹，再顺势推进 |
| 2026-03-16 16:54:00 | external blocker | `ghcr-standard-image` readiness 仍 blocked | 影响 external lane 完整闭环 | 已收敛成 current artifact；继续判断是否可在仓内修复 |
| 2026-03-16 17:06:00 | root budget | root docs 已贴边，不能通过新增根级边界文档解决开源边界问题 | 影响 WS7 落盘位置 | 已改为 `docs/reference/` 收口 |
| 2026-03-16 17:32:00 | receipt boundary | `repo-side-strict-ci` 本轮已启动并持续写 run manifest，但未拿到 fresh exit 收据 | 影响 WS8 是否可宣布完成 | 保留为本轮剩余项，不能包装成通过 |
| 2026-03-16 17:50:00 | external runtime blocker | `docker buildx ls`、`docker buildx inspect --bootstrap`、`docker info` 都表现出 daemon/builder 健康异常或长时间无响应 | 说明 standard-image lane 当前主要阻塞落在 Docker/Buildx runtime preparation 层 | 保持为 truthful external blocker，不再误归因到 docs/CI 语义层 |

## Files Changed Log

| 时间 | 文件 | 动作 | 说明 |
| --- | --- | --- | --- |
| 2026-03-16 16:15:07 | `.agents/Plans/2026-03-16_16-15-07__repo-four-track-governance-final-form-execution-plan.md` | created | 创建本轮执行唯一可信状态源 |
| 2026-03-16 16:40:00 | `config/governance/external-lane-contract.json` | modified | 为 remote workflow lane 显式声明 `verified_requires_current_head` |
| 2026-03-16 16:40:00 | `scripts/governance/check_external_lane_contract.py` | modified | 强制 remote workflow lane 声明 current-head 语义 |
| 2026-03-16 16:40:00 | `scripts/governance/probe_external_lane_workflows.py` | modified | 旧 commit success 不再冒充当前 `verified`，新增 `latest_run_matches_current_head` |
| 2026-03-16 16:40:00 | `scripts/governance/check_current_proof_commit_alignment.py` | modified | 新增 external workflow nested same-HEAD 校验 |
| 2026-03-16 16:40:00 | `scripts/governance/render_docs_governance.py` | modified | generated external snapshot 只在 current HEAD 时消费 remote workflow verified/blocker 状态 |
| 2026-03-16 16:40:00 | `docs/reference/external-lane-status.md` | modified | 把 old-head success 降格为历史证据 |
| 2026-03-16 16:40:00 | `docs/reference/done-model.md` | modified | 写入 same-HEAD external done 硬规则 |
| 2026-03-16 16:46:00 | `scripts/runtime/start_ops_workflows.sh` | modified | 移除 repo 根 `cache/.cache` cleanup 白名单 |
| 2026-03-16 16:46:00 | `docs/reference/cache.md` | modified | 明确 worker workspace cache 是 operator-side，而不是 repo 根合法出口 |
| 2026-03-16 16:46:00 | `docs/runbook-local.md` | modified | 收紧 cleanup 目录白名单，与单出口原则对齐 |
| 2026-03-16 17:02:00 | `docs/reference/public-rights-and-provenance.md` | created | 新增权利与来源边界事实源 |
| 2026-03-16 17:02:00 | `docs/reference/public-privacy-and-data-boundary.md` | created | 新增数据/隐私边界事实源 |
| 2026-03-16 17:02:00 | `docs/reference/public-brand-boundary.md` | created | 新增品牌/affiliation 边界事实源 |
| 2026-03-16 17:02:00 | `README.md` | modified | 把 public boundary pack 接入前门 |
| 2026-03-16 17:02:00 | `docs/reference/public-repo-readiness.md` | modified | 将 rights/privacy/brand pack 纳入 public governance pack |
| 2026-03-16 17:02:00 | `docs/index.md` | modified | 将边界事实源与 value proof 纳入索引 |
| 2026-03-16 17:02:00 | `config/docs/nav-registry.json` | modified | 将边界事实源与 value proof 接入导航 |
| 2026-03-16 17:02:00 | `config/docs/change-contract.json` | modified | 将 public boundary pack 与 value proof 纳入 docs drift contract |
| 2026-03-16 17:02:00 | `config/governance/public-entrypoints.json` | modified | 将边界事实源纳入 public entrypoint reference surfaces |
| 2026-03-16 17:18:00 | `scripts/ci/check_standard_image_publish_readiness.sh` | modified | 增强 standard-image readiness 的 buildx runtime 诊断面 |
| 2026-03-16 17:24:00 | `.agents/Plans/2026-03-16_16-15-07__repo-four-track-governance-final-form-execution-plan.md` | modified | 回写第一轮 hard cut、gate 结果与剩余项 |
| 2026-03-16 17:48:00 | `config/governance/bridges.json` | modified | 新增 4 个受治理 bridge surface |
| 2026-03-16 17:48:00 | `scripts/governance/check_historical_release_examples.py` | created | 为 tracked historical release manifests 增加 truth gate |
| 2026-03-16 17:48:00 | `artifacts/releases/v0.1.0/manifest.json` | modified | 将 tracked historical manifest 的 `evidence_scope` 收紧为 `historical-example` |
| 2026-03-16 17:48:00 | `artifacts/releases/README.md` | modified | 强化 historical example 与 canonical verdict 的边界说明 |
| 2026-03-16 17:48:00 | `docs/reference/public-artifact-exposure.md` | modified | 将 tracked historical manifest truth 规则写入 public artifact 边界 |
| 2026-03-16 17:48:00 | `docs/reference/dependency-governance.md` | modified | 将 `bridges.json` 提升为显式桥接面真相源 |
| 2026-03-16 17:48:00 | `integrations/README.md` | modified | 解释 integration layer 与 bridges inventory 的边界关系 |
| 2026-03-16 17:48:00 | `scripts/governance/gate.sh` | modified | 将 historical truth gate 与 newcomer/result proof gate 接入治理主链 |
| 2026-03-16 17:57:00 | `scripts/governance/render_newcomer_result_proof.py` | created | 生成 newcomer/result proof 当前真相包 |
| 2026-03-16 17:57:00 | `scripts/governance/check_newcomer_result_proof.py` | created | 校验 newcomer/result proof truth pack 结构与 current-commit 对齐 |
| 2026-03-16 17:57:00 | `docs/reference/newcomer-result-proof.md` | created | 解释 newcomer/result proof 的 reading rule |
| 2026-03-16 17:57:00 | `config/docs/nav-registry.json` | modified | 将 newcomer/result proof 页面接入 reference 导航 |
| 2026-03-16 17:57:00 | `config/docs/change-contract.json` | modified | 将 newcomer/result proof 页面纳入高信号 drift contract |
| 2026-03-16 17:57:00 | `docs/index.md` | modified | 将 newcomer/result proof 页面接入索引 |

## Next Actions

1. 下一轮优先关闭 external standard-image lane：先解决 Docker/Buildx daemon/builder 健康，再重试 readiness / publish 路径。
2. 下一轮优先继续推 WS8：拿到 fresh `repo-side-strict-ci` 完整 PASS 收据，并把 full-stack newcomer receipt 也纳入 truth pack。
3. 若要继续降低误读风险，再评估是否把 historical release examples 进一步迁出当前 `artifacts/releases/*` 路径。

## Final Completion Summary

- 状态：`PARTIAL_COMPLETE`
- 当前原因：本轮所有可无歧义落地的 repo-side P0/P1 结构性动作已完成并 fresh 过总闸；剩余未完成项已收敛为 external standard-image lane blocked，以及 newcomer truth pack 中 strict/full newcomer 收据仍缺。
- 退出条件：
  - 所有可完成的 P0/P1 结构性动作已落地
  - 关键 gate 已接线并 fresh 验证
  - 兼容桥已删除或处于短期受控状态
  - 本文件与 Repo 实际状态一致
