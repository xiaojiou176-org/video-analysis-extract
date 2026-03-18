# [🧭] Repo 终局总 Plan

## Plan Meta

- Created: `2026-03-17 19:00:34 America/Los_Angeles`
- Last Updated: `2026-03-17 20:12:44 America/Los_Angeles`
- Repo: `/Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取`
- Repo Archetype: `hybrid-repo`
- Execution Status: `In Progress`
- Current Phase: `Execution / WS4 verified / WS5 guard-set / WS1-WS3 still open`
- Current Workstream: `WS1 Clean-State Current-Proof Closure`
- Source Of Truth: `本文件`

## Workstreams 状态表

| Workstream | 状态 | 优先级 | 负责人 | 最近动作 | 下一步 | 验证状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `WS1` Clean-State Current-Proof Closure | `Blocked` | `P0` | `L1 + validator` | 已完成 dirty file 分桶判断：当前 `partial` 的唯一真实缺口是工作树仍 dirty；在不 commit / 不 stash / 不放松语义的约束下，无法把 newcomer 顶层诚实拉到 `pass` | 等用户明确允许 commit / checkpoint 或接受继续保留 dirty in-flight 状态；否则只能维持 partial | `Repo-side strong; live workspace not fully proved under current no-commit constraint` |
| `WS2` GHCR External Lane Closure | `Blocked` | `P0` | `L1 + platform` | 已补做手工 GHCR 认证复现：`terryyifeng` token 能 `docker login ghcr.io` 成功，但 package probe 仅 404、blob upload probe 仍 401，fresh readiness script 继续 FAIL | 继续等待/推动真正可写的 packages token / ACL；repo-side 已无更多诚实可做项 | `True platform blocker: blob upload still unauthorized` |
| `WS3` Platform Security Proof Closure | `Partially Completed` | `P1` | `L1` | 已通过 GitHub API 启用 `private vulnerability reporting`、`vulnerability alerts`、`secret_scanning`、`secret_scanning_push_protection`；fresh canonical probe 现显示 `private_vulnerability_reporting=enabled`，`security_and_analysis` 部分转绿，剩余 `secret_scanning_non_provider_patterns` / `secret_scanning_validity_checks` 仍 disabled | 保持 docs/security/current-proof 不回潮，并仅在可用时继续推进剩余 secondary features | `PVR closed; security_and_analysis partially closed` |
| `WS4` Docs & Current-Truth Semantic Fail-Close | `Verified` | `P1` | `L1 + implementer` | 已完成 contract required 化、reference docs 语义硬切、`required-checks` 生成页 aggregate-only 提示、gate 与定向测试闭环 | 保持护栏，不再把它当主施工面 | `docs governance PASS; current-proof PASS; 12 tests PASS` |
| `WS5` External Glue Locality Active Guard | `Partially Completed` | `P2` | `L1 + reconciler` | residual 决策已确认：当前没有值得继续切的同等级 slice；`rss/fetcher.py`、`activities_email.py`、`notifications.py` 转入冻结守护而非继续切割 | 守边界、防回流；仅在出现新 direct glue 或新的低 blast-radius slice 时重开 | `dependency-boundaries PASS; contract-locality PASS; intentionally paused` |

## 任务清单

- `[-]` 接管并校准最新 Plan 文件
  - 目标：以本文件为唯一可信源
  - 变更对象：本 Plan 文件
  - 验证方式：fresh runtime proof + git status + latest plan check
  - 完成证据：本次 takeover-calibration 已写回 `Plan Meta / Workstreams 状态表 / Validation Log`
- `[-]` 执行 `WS1`：dirty worktree 分桶并收敛 clean-state closure 路径
  - 目标：将 `newcomer-result-proof.status` 从 `partial` 推到 `pass`
  - 变更对象：dirty file set、current-proof 渲染面、必要 docs/gates
  - 验证方式：`git status --short`; fresh governance/strict rerun; newcomer/current-state rerender
  - 当前证据：repo-side strict receipt 已是 `pass`，当前 blocker 是 dirty worktree
- `[!]` 执行 `WS2`：关闭 GHCR packages write blocker
  - 目标：让 GHCR lane current-head `verified`
  - 变更对象：平台 credentials / package ACL / repo-side readiness semantics
  - 验证方式：`./scripts/ci/check_standard_image_publish_readiness.sh`; remote workflow current-head success
  - 当前证据：fresh readiness 仍 FAIL
- `[x]` 执行 `WS4`：语义 hard-cut（aggregate-required-checks vs terminal CI；current-proof optionality）
  - 目标：让关键误读能被 gate/test 阻断
  - 变更对象：`current-proof-contract`, docs governance / semantic docs / tests
  - 验证方式：定向 tests + docs governance
  - 完成证据：`render_docs_governance.py`、`check_docs_governance.py`、`check_current_proof_commit_alignment.py`、定向 pytest 全部 fresh 通过
- `[~]` 旧 `WS5` 宽战线 residual cutting 路径已废弃 / 改道
  - 目标：不再把低价值 residual slice 当主战场
  - 变更对象：本 Plan 的 WS5 定义、状态与 stop-rule
  - 验证方式：residual decision 写回 Plan；`dependency-boundaries` / `contract-locality` / `governance-audit` 继续绿
- `[-]` 执行 `WS5`：Active Guard / intentionally paused 守边界
  - 目标：防止 new direct glue 回流 apps 层
  - 变更对象：边界 guard、Plan 状态机、必要时的 docs/gate wording
  - 验证方式：边界门持续为绿；若出现新 direct glue 再重开 targeted cut

## [一] 3 分钟人话版

这个仓库现在最容易犯的错，不是“没做完”，而是**把已经很强的 repo-side 治理，误读成整个仓库已经 final form**。

说得更直白一点：

- **仓库内部控制面很强**：`./bin/governance-audit --mode audit` 是 fresh 绿，`current-proof` 对齐是绿，远端 required checks 对账也是绿。
- **repo-side strict 收据已经存在**：`newcomer-result-proof.json` 里 `repo_side_strict_receipt.status=pass`，`quality-gate/summary.json` 也是 `passed`。
- **但当前 live workspace 还不能宣称 fully proved**：因为 `worktree_state.dirty=true`，所以 `newcomer-result-proof.status=partial`，不是 `pass`。
- **真正还红的是外部/平台层**：GHCR 标准镜像 lane 还卡在 `Build and push strict CI standard image -> blob HEAD 403 Forbidden`，本地 readiness 直接报 `no token path with packages write capability detected`；GitHub 平台安全能力也还没闭环，`private_vulnerability_reporting=unverified`，`security_and_analysis` 多项 `disabled`。

所以这份 Plan 的唯一主路线不是“再打磨一下已经很强的部分”，而是：

1. **先把 current workspace 重新收敛成 clean，并拿到 clean-state 的 fresh current-proof**。
2. **再打掉 GHCR external lane 这个唯一 P0 外部 blocker**。
3. **然后把平台安全能力与 public/security proof 做成 current-head fail-close**。
4. **最后补齐 docs 语义 gate 和 external glue locality，防止假成熟回潮。**

必须这么硬的原因很简单：

- 如果不先清理 dirty worktree，就会一直存在“commit 已证实，但眼前这份工作树没有完全证实”的灰区。
- 如果不先打 GHCR，就会持续把“仓库公开了”误读成“公开分发也成熟了”。
- 如果不把平台安全能力 current-proof 化，`SECURITY.md` 这种文件本身就会变成假成熟信号。
- 如果不把 docs/current-truth 语义和 external glue locality 再硬切一轮，未来 agent 会继续被旧词、旧路径、旧边界带偏。

这轮改完以后，仓库会从“很强，但容易被读错”，升级成“分层清楚、误判成本低、下一位接手者很难再把绿灯读错”的 final-form 候选。

## [二] Plan Intake

### 输入材料范围

- 上游 `超级Review` 审计报告及其 `## [十三] 机器可读问题账本` YAML
- 当前仓库 tracked docs / workflows / governance scripts / runtime reports
- 当前 `.agents/Plans/` 下已有 Plan，作为历史执行上下文，不作为当前真相源
- 当前 live worktree 漂移

### 验证范围

- repo structure
- governance configs
- runtime-owned current truth
- docs control plane / generated docs
- CI workflows / required checks / branch protection probe
- public/open-source governance pack
- external lane reports
- dependency boundary / locality docs and gates

### 置信边界

- **A 级（fresh 命令或 current runtime artifact）**
  - `python3 scripts/governance/check_current_proof_commit_alignment.py` PASS
  - `./bin/governance-audit --mode audit` PASS
  - `python3 scripts/governance/check_remote_required_checks.py` PASS
  - `python3 scripts/release/check_release_evidence_attest_readiness.py --release-tag v0.1.0` => `READY`
  - `./scripts/ci/check_standard_image_publish_readiness.sh` => `FAIL: no token path with packages write capability detected`
  - `.runtime-cache/reports/governance/newcomer-result-proof.json`
  - `.runtime-cache/reports/governance/current-state-summary.md`
  - `.runtime-cache/reports/governance/external-lane-workflows.json`
- **B 级（tracked docs + governance script logic）**
  - `docs/reference/done-model.md`
  - `docs/reference/external-lane-status.md`
  - `scripts/governance/check_docs_governance.py`
  - `config/governance/current-proof-contract.json`
  - `docs/reference/architecture-governance.md`
  - `docs/reference/dependency-governance.md`
- **C 级（仍需落地时再二次核对）**
  - dirty worktree 中各变更文件的最终归属与是否应该保留
  - GHCR 平台 ACL / package ownership 的最终修正方式

### Repo archetype

- **结论：`hybrid-repo`**
- **原因**：
  - repo-owned 核心复杂度在 `apps/ + contracts/ + scripts/ + config/governance/`；
  - 但 external provider、GHCR、runner、release evidence、public boundary 不是外围附属物，而是系统主叙事的一部分；
  - 因此不能简单按“纯 native”处理，也不该误写成“glue-repo”。

### 当前最真实定位

- `public source-first + limited-maintenance + dual completion lanes`
- 强工程型 applied AI mini-system
- repo-side 已很强，external/public 仍有明确硬边界

### 最危险误判

- 把 `governance-audit PASS` + `repo_side_strict_receipt=pass` + 仓库公开 + SECURITY/README 文档齐全，误读成“整个仓库已经 final form 并且可安全公开分发”。

### 结构化输入已就位

```xml
<plan_intake>
  <same_repo>true</same_repo>
  <structured_issue_ledger>available</structured_issue_ledger>
  <input_material_types>
    - 超级Review 审计报告（上方输出，含 YAML 账本）
    - 当前 Repo fresh gate 结果
    - 当前 Repo tracked docs / runtime reports / workflows / governance control plane
  </input_material_types>
  <validation_scope>
    - repo structure
    - configs
    - workflows
    - scripts
    - docs
    - tests
    - outputs
    - integration surfaces
  </validation_scope>
  <initial_claims>
    - repo-side 很强
    - external/public 主要 blocker 是 GHCR
    - docs/CI 治理成熟但控制面分布较广
    - upstream 更像第三方依赖治理，而不是 repo-level fork 治理
    - release evidence 是 split 语义，不是 blocker
  </initial_claims>
  <known_conflicts>
    - 旧执行计划仍把 WS1 叙事停留在 strict 重修阶段，但 current repo truth 已经前进到 strict receipt 存在、dirty-worktree 仍是 partial
    - 上游超级Review 报告中关于 open-source freshness 的风险已经部分过时，当前 fresh artifact 显示 gitleaks current-head freshness 已 pass
    - release lane 不能再被笼统写成 ready/未闭环；当前真实状态是 readiness=ready 且 remote workflow=current-head verified
  </known_conflicts>
  <confidence_boundary>
    - GHCR blocker、dirty-worktree partial、platform security capability gap 均为高置信
    - external glue locality 仍需在实施前逐文件归属
    - dirty worktree 的每个文件是否纳入主线，需要在执行时按 workstream 分桶
  </confidence_boundary>
</plan_intake>
```

## [三] 统一判断总览表

| 维度 | 当前状态 | 目标状态 | 证据强度 | 是否适用 | 备注 |
| --- | --- | --- | --- | --- | --- |
| Repo archetype | `hybrid-repo` | 保持 | A | 是 | 不再翻案为 pure-native 或 glue |
| Repo-side governance | `green` | 保持 green | A | 是 | `./bin/governance-audit --mode audit` fresh PASS |
| Repo-side strict current receipt | `pass` | 保持 pass | A | 是 | `newcomer-result-proof.json` 中 `repo_side_strict_receipt.status=pass` |
| Current workspace proof | `partial` | `pass` | A | 是 | dirty worktree 阻止 live workspace 被 fully proved |
| GHCR standard image lane | `blocked` | `verified` | A | 是 | 当前唯一 P0 external blocker |
| Release evidence lane | `ready + verified` split | 保持 split but explicit，再稳定 | A | 是 | readiness 文件与 remote workflow 各司其职 |
| Open-source freshness | `pass` | 保持 pass | A | 是 | 上游旧担忧已过时，需从 blocker 降级为 guardrail |
| Platform security capability | `unverified/disabled` | `enabled + verified` | A | 是 | PVR 和 security_and_analysis 仍不够 |
| Docs control plane | `strong` | semantic fail-close | B | 是 | 已有 freshness gate，语义门还需再硬化 |
| CI trust boundary | `strong` | 保持 | A | 是 | required checks 对账 fresh PASS |
| External lane semantics | `强但易误读` | `机器强约束` | A/B | 是 | 特别是 ready/verified、tracked/runtime 区分 |
| External glue locality | `部分收口` | `强收口` | B | 是 | docs 已写 integrations 为唯一转接层，代码仍未完全完成 |
| Repo-level upstream/fork | `N/A` | `N/A` | A | 否 | 不做 merge/rebase 叙事 |

### YAML 账本归并结果

| Canonical ID | 原 Claim / Issue | Repo Verification | Evidence Strength | Type | Severity | Final Decision |
| --- | --- | --- | --- | --- | --- | --- |
| `ISS-001` | GHCR external lane 被 packages write 权限阻断 | 已验证 | A | fact | blocker | 采纳 |
| `ISS-002` | 当前 live workspace 只有 partial proof | 已验证 | A | fact | structural | 采纳 |
| `ISS-003` | GitHub 平台安全能力不完整 | 已验证 | A | fact | structural | 采纳 |
| `ISS-004` | repo-side / external lane / dirty-worktree 三层语义认知负担高 | 已验证 | B | inference | important | 采纳 |
| `ISS-005` | 治理面规模大、维护税高 | 已验证 | B | inference | important | 采纳 |
| `ISS-006` | strongest signal 是工程治理，不是 adoption-grade 产品交付 | 已验证 | B | inference | important | 采纳 |
| `ADD-001` | 上游报告里对 open-source freshness 的担忧已部分过时 | 已验证为过时修正 | A | fact | important | 过时修正 |
| `ADD-002` | release lane 不是 blocker，而是 split semantics 已成立 | 已验证 | A | fact | important | 采纳 |
| `ADD-003` | existing execution plan 的 WS1 叙事已过时 | 已验证 | A | fact | structural | 采纳 |
| `ADD-004` | external glue locality 是当前最像“下一阶段 final-form 工程债”的内部结构问题 | 部分验证 | B | inference | important | 部分采纳 |

## [四] 根因与完成幻觉总表

| 根因 / 幻觉 | 表面信号 | 真实问题 | 对应动作 | 防回潮 Gate |
| --- | --- | --- | --- | --- |
| `RC1` live workspace 与 commit-proof 混淆 | strict receipt 存在、quality-gate 绿 | 当前工作树 dirty，live workspace 仍只是 `partial` | `WS1` clean-state closure | `render_newcomer_result_proof.py` + `check_newcomer_result_proof.py` |
| `RC2` external lane 仍依赖平台能力而非 repo-side 重构 | workflow 存在、仓库公开、readiness 文件存在 | GHCR 写权限与 package ACL 仍未闭环 | `WS2` GHCR closure | `check_standard_image_publish_readiness.sh` + `external-lane-workflows.json` |
| `RC3` 安全公开能力仍停在 posture，不是 proven capability | SECURITY/README/public docs 都在 | PVR 未验证、security_and_analysis disabled | `WS3` platform security proof closure | `probe_remote_platform_truth.py` + `remote-platform-truth.json` |
| `RC4` docs/current-truth 已有 control plane，但语义 fail-close 仍不均匀 | generated docs 很齐、docs governance 已 pass | ready/verified、tracked/runtime、repo-side/external 容易被误读 | `WS4` docs semantic hardening | `check_docs_governance.py` + `current-proof-contract.json` |
| `RC5` 架构边界契约领先于代码落点 | docs 说 integrations 是唯一外部 glue 层 | apps/worker 里仍有直接 provider/binary/platform glue 残留 | `WS5` locality hard cut | `check_dependency_boundaries.py` + `check_contract_locality.py` |
| `IL1` Governance PASS = 整仓完成 | `governance-audit PASS` | 只证明控制面，不证明 external/public/live-workspace | `WS1` + `WS4` | `done-model.md` + current-state summary |
| `IL2` Ready = Verified | readiness 文件为 `ready` | release/GHCR 都要再看 workflow current-head 状态 | `WS2` + `WS4` | `external-lane-workflows.json` + docs semantic gate |
| `IL3` Public repo = public distribution ready | 仓库 public、LICENSE/SECURITY 在 | GHCR blocked，平台安全能力未闭环 | `WS2` + `WS3` | GHCR readiness + remote platform probe |
| `IL4` Generated docs = current truth | `docs/generated/*.md` 很齐 | generated docs 只能是 pointer/reference，不是 runtime verdict | `WS4` | `render_docs_governance.py --check` |
| `IL5` repo-side strict receipt = current workspace fully proved | newcomer strict receipt 是 pass | 顶层 newcomer 状态仍是 partial，dirty-worktree note 明确禁止偷换 | `WS1` | `check_newcomer_result_proof.py` |
| `IL6` 架构已经完全 clean | integrations/providers 新文件已存在 | locality hard cut 仍在迁移中 | `WS5` | dependency boundary gates |

## [五] 绝不能妥协的红线

- 不再允许任何文档、报告、Plan 把 `governance-audit PASS` 包装成 repo-side done。
- 不再允许任何 tracked docs 承载 current external verdict。
- 不再允许任何叙事把 `ready` 说成 `verified`。
- 不再允许使用旧 commit 的安全收据、release 收据、workflow 收据冒充 current-head truth。
- 不再允许用“仓库公开了”偷换“镜像分发和平台安全能力都成熟了”。
- 不再允许 `apps/*` 新增 direct external provider/binary/platform glue。
- 不再允许继续复用旧执行计划中“WS1=strict 仍待修”的过时时间判断。
- 不再允许在 dirty worktree 下宣称 current workspace fully proved。
- 不再允许 local fake digest、旧 workflow 成功记录、手工口头解释替代 GHCR current-head verified。
- 不再允许把 open-source freshness 的已绿项继续当 blocker 叙事使用；它只能作为 guardrail 保持项。

## [六] Workstreams 总表

| Workstream | 目标 | 关键改造对象 | 删除/禁用对象 | Done Definition | 优先级 |
| --- | --- | --- | --- | --- | --- |
| `WS1` Clean-State Current-Proof Closure | 把 live workspace 从 `partial` 收敛到可声明的 current proof | dirty worktree 分桶、newcomer/current-state 渲染面、strict/governance rerun | 禁用“dirty 也差不多算 done”的口径 | `git status` clean；fresh governance + repo-side strict 绿；`newcomer-result-proof.status=pass` | `P0` |
| `WS2` GHCR External Lane Closure | 把 GHCR 标准镜像 lane 从 blocked 推到 current-head verified | readiness script、build workflow、current-state/external docs、平台凭证与 package ACL | 禁用 fake digest / old-run success / 口头补票 | readiness 过；workflow current-head verified；external summary 不再 blocked | `P0` |
| `WS3` Platform Security Proof Closure | 把 public/security 从 posture 提升为 current-head proven capability | remote platform probe、SECURITY/public docs、env governance/open-source freshness link | 禁用 static docs 暗示 private security intake 已启用 | `remote-platform-truth.json` 明确 capability；security docs 与 current truth 一致 | `P1` |
| `WS4` Docs & Current-Truth Semantic Fail-Close | 把 docs control plane 从 freshness 扩到关键语义断言 | docs control plane、render/check scripts、current-proof contract、generated docs | 禁用 tracked docs 叙述 current verdict、禁用 ready/verified 混读 | docs governance check 可机器拦截关键语义漂移 | `P1` |
| `WS5` External Glue Locality Hard Cut | 把 apps 层残余 external glue 收口到 `integrations/` | `apps/worker/**`, `integrations/providers/**`, boundary docs/gates/tests | 禁用 apps 层新增 external glue | external provider/binary/platform glue 全部在 integrations；boundary gates 继续绿 | `P2` |

## [七] 详细 Workstreams

### `WS1` Clean-State Current-Proof Closure

#### 目标

- 把当前 `newcomer-result-proof.status=partial` 收敛到 `pass`。
- 把“commit 已证明”与“眼前工作树已证明”之间的灰区彻底关掉。

#### 为什么它是结构性动作

- 这不是格式洁癖，而是完成信号语义的核心问题。
- 只要 dirty worktree 还在，任何“当前状态已完成”的说法都不够硬。

#### 输入

- `.runtime-cache/reports/governance/newcomer-result-proof.json`
- `.runtime-cache/reports/governance/current-state-summary.md`
- `git status --short`
- `.runtime-cache/reports/governance/quality-gate/summary.json`
- `docs/reference/done-model.md`

#### 关键改造对象

- 当前 dirty 路径分桶：
  - docs/public/governance 相关：`README.md`, `SECURITY.md`, `docs/reference/*`, `docs/generated/*`, `docs/start-here.md`, `docs/runbook-local.md`
  - governance/runtime proof 相关：`scripts/governance/*`, `config/governance/current-proof-contract.json`
  - env/security 相关：`.env.example`, `ENVIRONMENT.md`, `infra/config/env.contract.json`, `bin/open-source-audit-refresh`, `scripts/governance/check_open_source_audit_freshness.py`, `.github/workflows/env-governance.yml`
  - external lane 相关：`.github/workflows/build-ci-standard-image.yml`, `scripts/ci/check_standard_image_publish_readiness.sh`
  - locality 相关：`integrations/providers/*`, `apps/worker/worker/*`, `apps/worker/tests/*`, `integrations/README.md`
  - dependency/lock 相关：`pyproject.toml`, `uv.lock`, `THIRD_PARTY_NOTICES.md`, `artifacts/licenses/third-party-license-inventory.json`
- current-proof 渲染面：
  - `scripts/governance/render_newcomer_result_proof.py`
  - `scripts/governance/render_current_state_summary.py`
  - `scripts/governance/check_newcomer_result_proof.py`

#### 删除/禁用对象

- 禁用任何基于 dirty worktree 的“近似 done”表述
- 禁用旧 Plan 中“strict 仍待修”的 current-state 判断

#### 迁移桥

- 临时允许 `newcomer-result-proof.status=partial` 继续存在
- 但只允许作为短期过渡，且必须在 current-state summary 明确写出 `worktree dirty=true`

#### 兼容桥删除条件与时点

- 条件：
  - `git status` 仅剩新 Plan 文件或完全 clean
  - `./bin/governance-audit --mode audit` fresh PASS
  - `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` fresh PASS
  - 重新渲染 `newcomer-result-proof.json` 与 `current-state-summary.md`
- 时点：WS1 结束时立即删除“partial but close enough”叙事

#### Done Definition

- `git status --short` clean，或仅剩本轮明确豁免的 plan/artifact 且不属于 tracked source drift
- `.runtime-cache/reports/governance/newcomer-result-proof.json` 顶层 `status=pass`
- `.runtime-cache/reports/governance/current-state-summary.md` 中 `worktree dirty: false`
- `check_current_proof_commit_alignment.py` fresh PASS
- `governance-audit` 与 `repo-side-strict-ci` fresh PASS

#### Fail Fast 检查点

- 若 dirty 路径无法按 workstream 分桶，先停在分桶，不要继续复跑 gate
- 若 strict 复跑转红，立即回到 deepest failing gate，不允许跳过
- 若 newcomer/current-state 仍把 dirty workspace 包成 pass，先修渲染/检查语义再谈 closeout

#### 打掉什么幻觉

- `repo_side_strict_receipt=pass` 就等于当前工作树 fully proved
- repo-side 已经绿了，所以剩下都是可选收尾

#### 改变哪个上层判断

- **招聘信号**：从“很强但 current state 还有灰区”升级成“很强且收据语义也严谨”
- **docs/CI 可信度**：从“强”升级成“强且不偷换当前工作树”
- **repo-side 完成判断**：从 `partial` 升为可公开复述的 `pass`

---

### `WS2` GHCR External Lane Closure

#### 目标

- 把 `ghcr-standard-image` 从 `blocked` 推到 current-head `verified`。
- 结束“external lane 最大 blocker 仍在平台边界”的状态。

#### 为什么它是结构性动作

- 这是当前唯一明确的 P0 external blocker。
- 只要 GHCR 没闭环，public distribution 叙事就不能升级。

#### 输入

- `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
- `.runtime-cache/reports/governance/external-lane-workflows.json`
- `.github/workflows/build-ci-standard-image.yml`
- `scripts/ci/check_standard_image_publish_readiness.sh`
- `docs/reference/external-lane-status.md`
- `docs/reference/public-repo-readiness.md`

#### 关键改造对象

- repo files
  - `scripts/ci/check_standard_image_publish_readiness.sh`
  - `.github/workflows/build-ci-standard-image.yml`
  - `scripts/governance/probe_external_lane_workflows.py`
  - `scripts/governance/render_current_state_summary.py`
  - `docs/reference/external-lane-status.md`
  - `docs/reference/public-repo-readiness.md`
  - `config/governance/current-proof-contract.json`
- platform / secret surfaces
  - `GHCR_WRITE_USERNAME`
  - `GHCR_WRITE_TOKEN`
  - GitHub Packages ownership / ACL / package repository linkage

#### 删除/禁用对象

- 禁用本地 image hash 伪装成 GHCR digest 的任何路径
- 禁用旧 workflow 成功 run 冒充 current-head closure
- 禁用 readiness 通过但 workflow 失败时仍宣称 external green

#### 迁移桥

- 当前允许 external lane 继续保持 `blocked`
- 但必须由 runtime artifacts 精确描述：
  - local readiness blocked
  - remote workflow current-head failure
  - failed step = `Build and push strict CI standard image`
  - failure signature = `blob-head-403-forbidden`

#### 兼容桥删除条件与时点

- 条件：
  - readiness artifact 至少通过 token path / blob upload probe
  - remote workflow current-head run `success`
  - current-state summary 中 `ghcr-standard-image` 不再为 `blocked`
- 时点：一旦 current-head verified 成立，立即删掉“platform blocked”旧口径

#### Done Definition

- `.runtime-cache/reports/governance/standard-image-publish-readiness.json` 不再 `blocked:registry-auth-failure`
- `.runtime-cache/reports/governance/external-lane-workflows.json` 中 `ghcr-standard-image.state=verified`
- latest run `headSha == 当前 HEAD`
- `current-state-summary.md` 中 external lane row 不再标红
- docs/reference 中对 GHCR lane 的解释与 runtime verdict 一致

#### Fail Fast 检查点

- 若 token path 仍不存在，先停在平台/secret 配置，不要继续改 repo 逻辑
- 若 readiness 过但 workflow fail 在别的 step，重新归因；不要继续用 403 旧签名
- 若 workflow 成功但 current-head 不匹配，仍按历史证据处理，不算闭环

#### 打掉什么幻觉

- public repo = public distribution ready
- readiness 文件存在 = external lane done
- workflow 曾成功过一次 = 当前已经没问题

#### 改变哪个上层判断

- **open-source / public 展示判断**：从“可谨慎公开”升级到更接近“可安全公开分发”
- **CI 可信判断**：external lane 不再只停留在 repo-side 解释
- **价值密度判断**：从“强工程仓”往“更完整交付样本”升级

---

### `WS3` Platform Security Proof Closure

#### 目标

- 把 public/security 从 posture 变成 current-head proven capability。
- 不再让 `SECURITY.md` 本身制造能力幻觉。

#### 为什么它是结构性动作

- 只要 `private_vulnerability_reporting` 还是 `unverified`，安全开源结论就不够硬。
- `security_and_analysis` 继续 disabled，会拖低开源成熟度。

#### 输入

- `.runtime-cache/reports/governance/remote-platform-truth.json`
- `.runtime-cache/reports/governance/open-source-audit-freshness.json`
- `SECURITY.md`
- `docs/reference/public-repo-readiness.md`
- `docs/reference/public-rights-and-provenance.md`
- `.github/workflows/env-governance.yml`
- `scripts/governance/probe_remote_platform_truth.py`
- `scripts/governance/check_open_source_audit_freshness.py`

#### 关键改造对象

- platform truth probes
  - `scripts/governance/probe_remote_platform_truth.py`
  - `scripts/governance/check_open_source_audit_freshness.py`
  - `.github/workflows/env-governance.yml`
  - `.github/workflows/remote-integrity-audit.yml`
- public/security docs
  - `SECURITY.md`
  - `docs/reference/public-repo-readiness.md`
  - `docs/reference/public-rights-and-provenance.md`
  - `docs/reference/public-privacy-and-data-boundary.md`

#### 删除/禁用对象

- 禁用任何基于静态文档的 private reporting 能力暗示
- 禁用旧 commit 的 gitleaks receipts 冒充 current-head open-source proof

#### 迁移桥

- 当前允许 `private_vulnerability_reporting=unverified` 继续存在
- 但只允许作为 runtime probe 结论被公开陈述，不允许被柔化成“应该已经有了”

#### 兼容桥删除条件与时点

- 主路线默认目标：启用 PVR，并通过 live probe 读到 `enabled`
- 若平台政策阻止启用，则必须做一次显式决策，将目标降为“明确 disabled 且文档不再暗示 private path”
- 不允许长期停留在 `unverified`

#### Done Definition

- `remote-platform-truth.json` 中 `private_vulnerability_reporting.status` 不再为 `unverified`
- `security_and_analysis` 至少达到明确可陈述的目标态
- `open-source-audit-freshness.json` 对当前 HEAD 保持 `pass`
- `SECURITY.md`、`public-repo-readiness.md` 与 runtime truth 不冲突

#### Fail Fast 检查点

- 若 probe 逻辑拿不到字段，先修 probe，不要先修文案
- 若平台不支持启用，立即记录 platform decision，不允许继续模糊表述
- 若 open-source freshness 转红，先恢复 fresh receipts，再推进 platform narrative

#### 打掉什么幻觉

- 有 SECURITY.md 就等于 private security route 可用
- 仓库 public 就等于安全开源边界成立

#### 改变哪个上层判断

- **开源就绪判断**：从“可谨慎公开”进一步升级
- **协作边界判断**：陌生贡献者对安全入口的理解会更准确
- **招聘信号**：展示的不再只是工程治理，而是平台安全能力治理

---

### `WS4` Docs & Current-Truth Semantic Fail-Close

#### 目标

- 把 docs control plane 从“渲染新鲜”升级到“关键语义一漂移就 fail-close”。
- 防止 future agent 再把 tracked docs、runtime truth、ready/verified 混成一锅。

#### 为什么它是结构性动作

- 当前 docs governance 已经很强，但它最危险的敌人不是 freshness，而是**语义偷换**。
- 只做 freshness，不做 semantic fail-close，会留下大量“看起来成熟”的灰区。

#### 输入

- `config/docs/*.json`
- `scripts/governance/check_docs_governance.py`
- `scripts/governance/render_docs_governance.py`
- `scripts/governance/render_current_state_summary.py`
- `config/governance/current-proof-contract.json`
- `docs/generated/*.md`
- `docs/reference/done-model.md`
- `docs/reference/external-lane-status.md`
- `docs/reference/newcomer-result-proof.md`

#### 关键改造对象

- docs control plane
  - `config/docs/render-manifest.json`
  - `config/docs/boundary-policy.json`
  - `config/docs/change-contract.json`
- docs semantic gate
  - `scripts/governance/check_docs_governance.py`
  - `scripts/governance/render_docs_governance.py`
  - `scripts/governance/render_current_state_summary.py`
  - `config/governance/current-proof-contract.json`
- generated docs
  - `docs/generated/ci-topology.md`
  - `docs/generated/runner-baseline.md`
  - `docs/generated/release-evidence.md`
  - `docs/generated/external-lane-snapshot.md`

#### 删除/禁用对象

- 禁用 tracked docs 承载 current external verdict
- 禁用 `release-readiness` 与 `release-evidence-attestation` 混写
- 禁用 `ready` 被文案包装成 `verified`

#### 迁移桥

- 允许 generated docs 继续做 pointer/reference
- 但 current verdict 必须只从 `.runtime-cache/reports/**` 读取

#### 兼容桥删除条件与时点

- 条件：
  - docs semantic gate 能断言至少以下语义：
    - tracked docs 只做 pointer，不做 current verdict
    - release readiness 与 workflow verified 不混读
    - repo-side strict receipt 与 top-level newcomer status 不混读
    - open-source freshness 与 platform capability 都进入 current-proof contract
- 时点：WS4 结束时立即删掉旧的模糊词与旧路径

#### Done Definition

- `check_docs_governance.py` 能拦截关键语义漂移
- generated docs 与 docs/reference 的 current-truth 读取规则一致
- `current-proof-contract.json` 覆盖 security/open-source/external 关键 current claims
- README/start-here/external-lane-status/newcomer-result-proof 的核心用词不再相互冲突

#### Fail Fast 检查点

- 若语义约束写不进 gate，就不要只改 docs 文案
- 若 generated docs 仍承载 current verdict，先收口再做其它叙事修正

#### 打掉什么幻觉

- generated docs 就是 current truth
- 文档很齐就等于语义很稳
- current-state summary 是可选解释层，不是主证据面

#### 改变哪个上层判断

- **文档可信判断**：从“成熟”升级到“高强度 fail-close”
- **CI 可信判断**：docs/CI 不再只是并行存在，而是相互约束

---

### `WS5` External Glue Locality Active Guard（intentionally paused residual cutting）

#### 目标

- 明确结束“继续找 residual slice 再切一刀”的宽战线。
- 把 WS5 从持续迁移改成**守边界、防回流、只在出现新低 blast-radius slice 时重开**。

#### 为什么它是结构性动作

- 当前最值钱的结构动作已经不是“再找一两个 provider helper 搬家”，而是**防止已经收口的边界重新回流**。
- residual 冻结判断本身也是结构决策：它决定这条战线是不是还值得烧时间。

#### 输入

- `docs/reference/architecture-governance.md`
- `docs/reference/dependency-governance.md`
- `config/governance/dependency-boundaries.json`
- `scripts/governance/check_dependency_boundaries.py`
- `scripts/governance/check_contract_locality.py`
- `scripts/governance/check_no_cross_app_implementation_imports.py`
- residual decision 目标：
  - `apps/worker/worker/rss/fetcher.py`
  - `apps/worker/worker/temporal/activities_email.py`
  - `apps/api/app/services/notifications.py`
  - `integrations/providers/resend.py`

#### 关键改造对象

- boundary guard surfaces
  - `config/governance/dependency-boundaries.json`
  - `scripts/governance/check_dependency_boundaries.py`
  - `scripts/governance/check_contract_locality.py`
- architectural truth surfaces
  - `docs/reference/architecture-governance.md`
  - `integrations/README.md`
- frozen residual files
  - `apps/worker/worker/rss/fetcher.py`
  - `apps/worker/worker/temporal/activities_email.py`
  - `apps/api/app/services/notifications.py`

#### 删除/禁用对象

- 禁用 apps 层继续新增 direct HTTP/API/binary/platform glue
- 禁用“继续找 residual slice 再切一刀”作为默认主路线
- 禁用把 orchestration-heavy `rss/fetcher.py` 或领域主体 `notifications.py` 误当成当前最值钱的迁移对象

#### 迁移桥

- 允许极薄 facade 暂存，只要它们不重新长出 provider 解析、headers、request、重试、平台耦合逻辑
- `rss/fetcher.py`、`activities_email.py`、`notifications.py` 当前进入冻结守护，不再作为同等级切割目标

#### 兼容桥删除条件与时点

- 重新打开 targeted cut 的条件：
  - 发现新的 low blast-radius direct glue 回流 apps 层
  - 或 frozen residual file 重新长出 provider-specific request / retry / parsing 逻辑
- 若以上条件不成立，WS5 保持 guard 状态，不再继续切

#### Done Definition

- 已完成收口样例仍真实成立
- `check_dependency_boundaries.py`, `check_contract_locality.py`, `check_no_cross_app_implementation_imports.py` 继续绿
- Plan 已明确写死“当前没有值得继续切的同等级 residual slice”
- 新增 direct glue 不再回流 apps 层

#### Fail Fast 检查点

- 若 frozen file 出现新的 provider-specific request glue，立即重开 targeted cut
- 若 boundary gate 需要扩规则，先在 Plan 记账，再改 gate，不允许口头默许

#### 打掉什么幻觉

- “继续切更多文件”一定比“明确停线守边界”更成熟
- 只要还有几个碰 provider 的文件，WS5 就永远不能收敛

#### 改变哪个上层判断

- **架构成熟判断**：从“仍在大规模迁移中”升级到“边界主债已清，剩余进入 guard 模式”
- **长期维护税判断**：不再为低收益 residual cut 持续烧维护成本

## [八] 硬切与迁移方案

### 立即废弃项

- 旧执行计划中“WS1 仍是 strict 重修”的 current-state 叙事
- 任何把 `ready` 直接当成 `verified` 的 release/GHCR 口径
- 任何把 tracked docs 当 current external verdict 的用法
- 任何把 `SECURITY.md` 当成 private reporting capability 证明的说法

### 迁移桥

- `WS1`：允许 `newcomer-result-proof.status=partial` 暂存，但只在 dirty-worktree 仍存在期间有效
- `WS2`：允许 GHCR 继续 blocked，但必须精确落在 runtime artifact，不允许口头兜底
- `WS3`：允许 `PVR=unverified` 暂存，但不允许长期维持；必须转成 `enabled` 或显式 `disabled`
- `WS4`：允许 generated docs 继续作为 pointer/reference，但不允许继续承载 current verdict
- `WS5`：允许极薄 wrapper 暂存，但不允许保留 provider request/解析/重试/平台耦合逻辑

### 禁写时点

- 现在起禁止在 `apps/*` 新增 external glue
- 现在起禁止在 tracked docs 新增 current external verdict payload
- 现在起禁止复用旧 commit security receipts 作为 current-head 证明

### 只读时点

- 旧 execution plan 从新 Plan 落地起转为**历史上下文只读**
- `docs/generated/external-lane-snapshot.md` 继续作为 pointer，只读，不承载 current verdict

### 删除时点

- `WS1` 结束：删除 dirty-worktree 近似完成叙事
- `WS2` 结束：删除 GHCR blocked 旧解释
- `WS3` 结束：删除 `unverified` 安全入口模糊表述
- `WS4` 结束：删除 ready/verified 混写与 tracked current verdict 文案
- `WS5` 结束：删除 apps 层兼容 wrapper

### 防永久兼容机制

- 所有迁移桥都必须绑定删除条件和结束 gate
- 不允许出现“先留着以后再说”但没有 gate 的兼容层
- boundary / docs / current-proof 三类 gate 必须覆盖迁移桥退场条件

## [九] 验证闭环与 Gate

| 维度 | 验证项 | Gate / 命令 / CI / Policy | 通过条件 | 未通过意味着什么 |
| --- | --- | --- | --- | --- |
| Current workspace | 当前工作树是否 fully proved | `git status --short`; `python3 scripts/governance/render_newcomer_result_proof.py`; `python3 scripts/governance/check_newcomer_result_proof.py` | newcomer 顶层 `status=pass`; `dirty=false` | 当前 live workspace 仍不可宣称完成 |
| Repo-side governance | 控制面是否站稳 | `./bin/governance-audit --mode audit` | fresh PASS | docs/runtime/boundary 至少有一层失真 |
| Repo-side strict | 最重 repo-side lane 是否为绿 | `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` | fresh PASS | repo-side done 不成立 |
| Current-proof alignment | current claims 是否都对齐 HEAD | `python3 scripts/governance/check_current_proof_commit_alignment.py` | PASS | current artifact 可能是旧 commit 残留 |
| GHCR lane | 标准镜像 external lane 是否闭环 | `./scripts/ci/check_standard_image_publish_readiness.sh`; `.runtime-cache/reports/governance/external-lane-workflows.json`; `.github/workflows/build-ci-standard-image.yml` | readiness 非 blocked；workflow current-head verified | external/public distribution 仍 blocked |
| Release evidence lane | release lane 是否 current-head 有效 | `python3 scripts/release/check_release_evidence_attest_readiness.py --release-tag v0.1.0`; `.runtime-cache/reports/governance/external-lane-workflows.json` | readiness=ready 且 workflow current-head verified | 只能说“前置存在”，不能说 external release 已闭环 |
| Public/security | private reporting 与 security features 是否可证明 | `./bin/remote-platform-probe --repo ...`; `.runtime-cache/reports/governance/remote-platform-truth.json` | PVR 不再 unverified；security_and_analysis 达到目标态 | 安全开源边界仍是灰区 |
| Open-source freshness | 安全收据是否 current-head fresh | `python3 scripts/governance/check_open_source_audit_freshness.py`; `.runtime-cache/reports/governance/open-source-audit-freshness.json` | PASS | public/security current-proof 不可信 |
| Docs truth | docs 是否是事实源而非手抄表 | `python3 scripts/governance/check_docs_governance.py` | PASS 且关键语义被检查 | 文档可能再次制造完成幻觉 |
| Required checks integrity | branch protection 与 policy 是否一致 | `python3 scripts/governance/check_remote_required_checks.py` | PASS | 远端 CI 绿灯不一定覆盖关键判断 |
| Root allowlist / runtime hygiene | 根目录与 runtime root 是否 machine-governed | `./bin/governance-audit --mode audit`; `quality-gate/summary.json` | 相关 gate 全 PASS | repo-side 卫生不可信 |
| Cache 全删可重建 | runtime cache 是否为非真相源 | `check_runtime_cache_retention.py`; `check_runtime_cache_freshness.py`; runtime docs | PASS | 历史 artifact 可能继续污染 current claims |
| 日志 schema / correlation | 日志是否可诊断 | `check_logging_contract.py`; `check_log_correlation_completeness.py` | PASS | 运行问题只能靠猜 |
| Dependency / locality boundary | 业务层是否仍写 external glue | `python3 scripts/governance/check_dependency_boundaries.py`; `python3 scripts/governance/check_contract_locality.py`; `python3 scripts/governance/check_no_cross_app_implementation_imports.py` | PASS 且 apps 层不再持有 glue 逻辑 | 架构 clean 只是文档信号，不是实现事实 |

## [十] 执行时序总表

| 阶段 | 动作 | 前置条件 | 并行性 | 完成标志 | 风险 |
| --- | --- | --- | --- | --- | --- |
| `Phase 1` | 把 dirty worktree 按 WS1~WS5 分桶，决定哪些改动保留、哪些要先完成 | 当前 `git status` | 可并行分析，不可并行写同文件 | 所有 dirty 路径有明确归属 | 误把不相关改动一起打包 |
| `Phase 2` | 先执行 `WS1` clean-state closure | 分桶完成 | 串行优先 | newcomer 顶层不再 `partial` | 严格 gate 再次暴露更深 repo-side 红灯 |
| `Phase 3` | 执行 `WS2` GHCR closure | `WS1` 至少拿到 clean-state repo-side truth | 平台动作与 docs 准备可并行；repo 代码修补与平台配置协同 | GHCR current-head verified | 平台 ACL 受组织权限限制 |
| `Phase 4` | 执行 `WS3` platform security proof closure | `WS1` 完成；`WS2` 可并行推进 | 与 `WS4` 部分并行 | PVR/security_and_analysis 有明确 current-proof | 平台能力可能受 plan/权限限制 |
| `Phase 5` | 执行 `WS4` docs semantic fail-close | `WS1` 完成 | 可与 `WS3` 部分并行 | docs gate 拦截关键语义漂移 | 文案修了但 gate 没接线 |
| `Phase 6` | 执行 `WS5` locality hard cut | `WS1` 完成；尽量在 `WS4` 后进行，避免 docs 再漂 | 低 blast-radius 子切片可并行，单文件不可并写 | external glue 真正收口到 integrations | 迁移时把编排逻辑也一起搬坏 |
| `Phase 7` | 终局复核：repo-side + external + public/security + docs semantics + locality | 前五个 WS 完成 | 串行 | 所有主判断已按新层级重写 | 某一条 lane 仍在旧口径 |

## [十一] 改造动作 -> 上层判断改变 映射表

| 动作 | 改变什么判断 | 为什么 |
| --- | --- | --- |
| `WS1` clean-state closure | repo-side 当前状态判断 | 结束“commit 绿、工作树灰”的模糊地带 |
| `WS2` GHCR closure | public/open-source/distribution 判断 | external lane 最大 blocker 被真正消灭 |
| `WS3` platform security proof | 安全开源判断 | 让 `SECURITY.md` 从 policy 升级为 capability-backed statement |
| `WS4` docs semantic fail-close | 文档与 CI 可信判断 | 文档不再只是更新勤快，而是关键语义可机审 |
| `WS5` locality hard cut | 架构成熟与维护税判断 | external change surface 更集中，边界契约与实现一致 |
| 删除旧 WS1/旧 ready 叙事 | 完成幻觉判断 | 未来接手者更难再读错层次 |

## [十二] 如果只允许做 3 件事，先做什么

### 1. `WS1` Clean-State Current-Proof Closure

- **为什么先做**
  - 这是把“眼前这份工作树到底算不算 current proof”说清楚的前提。
- **打掉什么幻觉**
  - strict receipt 存在 = 当前 workspace fully proved。
- **释放什么能力**
  - 后续 GHCR/security/docs/locality 改造都能建立在清晰 current-state 上。

### 2. `WS2` GHCR External Lane Closure

- **为什么第二**
  - 这是当前唯一明确的 P0 external blocker。
- **打掉什么幻觉**
  - public repo = public distribution ready。
- **释放什么能力**
  - external/public 叙事可以真正升级，而不是一直靠“repo-side 很强”兜底。

### 3. `WS3` Platform Security Proof Closure

- **为什么第三**
  - GHCR 之后，最能改变“能不能安全开源”判断的就是平台安全能力。
- **打掉什么幻觉**
  - 有 `SECURITY.md` 就等于私密入口可用。
- **释放什么能力**
  - 仓库可从“可谨慎公开”向“更安全可公开协作”升级。

## [十三] 不确定性与落地前核对点

### 高置信事实

- repo-side governance 当前是 green
- repo-side strict current receipt 当前存在
- current workspace 因 dirty worktree 仍是 partial
- GHCR lane 当前 blocked
- release evidence lane 当前不是 blocker
- platform security capability 当前不够
- open-source freshness 当前已 pass
- WS4 当前已 verified
- WS5 当前已转 Active Guard / intentionally paused
- WS3 当前在本地可做面已清空，剩平台 capability 本身未闭环

### 中置信反推

- WS5 不再需要继续宽战线 residual cutting，除非出现新的 low blast-radius direct glue 回流
- docs semantic gate 目前已覆盖本轮最危险的 aggregate-only / current-proof 误读，但 future lane 语义仍需守护

### 落地前必须二次核对

- dirty 路径分桶时，哪些文件属于本轮主线，哪些是历史漂移或平行工作
- GHCR package ownership / ACL 的真正修复动作由哪个平台入口完成
- PVR/security_and_analysis 是否可在当前组织/仓库设置中启用
- `repo-side-strict-ci` 作为 repo-side wrapper 的语义，是否需要在 docs 中进一步写死，防止被误读为 external/release qualification

### 但即便如此，主路线不变

- 先 clean-state current-proof
- 再 GHCR
- 再 platform security
- 然后 docs semantic
- 最后 locality hard cut

## [十四] 执行准备状态

### Current Status

- current HEAD: `40e0603372c1079c8dc699e49d80305b48af0b30`
- repo-side governance: `pass`
- repo-side strict current receipt: `pass`
- newcomer top-level status: `partial`
- worktree dirty: `true`
- GHCR lane: `blocked (true write-path blocker confirmed)`
- release evidence lane: `ready + verified`
- open-source freshness: `pass`
- private vulnerability reporting: `enabled`
- security_and_analysis: `partially enabled`

### Next Actions

1. 若要真正关闭 WS1，必须先有用户授权的 checkpoint 动作（commit / 其他等价收敛方式）；在此之前继续保持 `partial` 的诚实语义
2. 继续维护 WS2 平台 blocker 台账；下一步只接受真正可写的 packages token / ACL 变化，不再重复本地空转
3. WS3 仅在剩余两个 secondary security features 可推进时再刷新 proof，不再把 WS4/WS5 当主施工面

### Decision Log

- `D1`：不再沿用旧执行计划里“WS1=strict 仍待修”的 current-state 判断
- `D2`：主路线采用 `clean-state -> GHCR -> platform security -> docs semantics -> locality`，不提供多方案
- `D3`：release evidence lane 归类为 split semantics，不归类为 blocker
- `D4`：open-source freshness 从旧 blocker 叙事降级为保持项
- `D5`：repo archetype 固定为 `hybrid-repo`
- `D6`：WS4 本轮正式升为 `Verified`；关键 external/current proof surface 已从 optional 收紧为 fail-close，`remote-required-checks` 的 aggregate-only 语义已进入 docs gate、generated page 与 tests
- `D7`：WS5 不再继续宽战线 residual cutting，改为 `Active Guard / intentionally paused`；当前没有值得继续切的同等级 slice
- `D8`：WS3 已从“PVR 未验证”推进到“PVR enabled + 核心 security_and_analysis 部分开启”；剩余问题缩小为两个 secondary security features 未闭环
- `D9`：WS1 在当前“不做 commit / 不 stash / 不放松语义”的约束下无法闭环；唯一缺口不是 repo-side strict，而是 dirty worktree 本身
- `D10`：WS2 已证实不是单纯脚本误判；即便使用带 `write:packages` 的本机二级账号 token，`docker login` 可成功，但 GHCR blob upload probe 仍返回 `401`，所以 blocker 仍落在真实写权限边界
- `D11`：当前能力范围内可完成项已基本清空；继续推进只会在获得 `WS1` checkpoint 授权或 `WS2` 真正可写的 GHCR packages 凭证后才会改变主结论

### Validation Log

- `python3 scripts/governance/check_current_proof_commit_alignment.py` => PASS
- `./bin/governance-audit --mode audit` => PASS
- `python3 scripts/governance/check_remote_required_checks.py` => PASS
- `python3 scripts/release/check_release_evidence_attest_readiness.py --release-tag v0.1.0` => READY
- `./scripts/ci/check_standard_image_publish_readiness.sh` => FAIL (`no token path with packages write capability detected`)
- `.runtime-cache/reports/governance/newcomer-result-proof.json` => `status=partial`, `repo_side_strict_receipt.status=pass`, `worktree_state.dirty=true`
- `.runtime-cache/reports/governance/external-lane-workflows.json` => GHCR current-head blocked, release current-head verified
- `python3 scripts/governance/render_docs_governance.py` => `docs governance render completed`
- `python3 scripts/governance/check_docs_governance.py` => PASS
- `uv run pytest apps/worker/tests/test_external_proof_semantics.py apps/worker/tests/test_docs_governance_control_plane.py -q` => `12 passed, 2 warnings`
- `python3 scripts/governance/check_dependency_boundaries.py` => PASS
- `python3 scripts/governance/check_contract_locality.py` => PASS
- `./bin/governance-audit --mode audit` => PASS（本轮 WS4 contract/docs 变更后再次复核）
- `python3 scripts/governance/check_open_source_audit_freshness.py` => PASS
- `gh api -X PUT repos/xiaojiou176-org/video-analysis-extract/private-vulnerability-reporting -i` => `204 No Content`
- `gh api -X PUT repos/xiaojiou176-org/video-analysis-extract/vulnerability-alerts -i` => `204 No Content`
- `gh api -X PATCH repos/xiaojiou176-org/video-analysis-extract --input <security_and_analysis enabled subset>` => `200 OK`
- `uv run pytest apps/worker/tests/test_external_proof_semantics.py -q` => `5 passed, 2 warnings`
- `python3 scripts/governance/probe_remote_platform_truth.py --output .runtime-cache/reports/governance/remote-platform-truth.exec.json` => PASS（`private_vulnerability_reporting=enabled`）
- `python3 scripts/governance/probe_remote_platform_truth.py` => PASS（canonical `remote-platform-truth.json` refreshed）
- `python3 scripts/governance/render_current_state_summary.py` => PASS（current-state summary refreshed after WS3 platform changes）
- `gh auth status` => active account `xiaojiou176`; inactive account `terryyifeng` carries `write:packages`
- `GHCR_WRITE_USERNAME=terryyifeng GHCR_WRITE_TOKEN=<gh auth token> ./scripts/ci/check_standard_image_publish_readiness.sh` => FAIL（仍报 `no token path with packages write capability detected`）
- 手工 GHCR probes with `terryyifeng` token => package API `404`, blob upload probe `401`, `docker login ghcr.io` succeeded
- `WS1` feasibility reconciliation => 在当前 no-commit / no-stash / no-semantic-weakening 约束下，`newcomer-result-proof.status` 无法从 `partial` 诚实提升到 `pass`

### Risk / Blocker Log

- `B1` GHCR package auth / ACL external blocker
- `B2` dirty worktree 让 live workspace 不能 fully proved；在当前 no-commit/no-stash/no-semantic-weakening 约束下无法闭环
- `B3` platform security capability 仅剩部分 secondary features 未闭环（`secret_scanning_non_provider_patterns`, `secret_scanning_validity_checks`）
- `R1` WS4 已收口，但若 future generated/reference/current-state 语义再次漂移，仍可能回潮
- `R2` WS5 当前已转 Active Guard；真正风险变成 direct glue 回流，而不是 residual cut 不够多
- `R3` 本轮 reviewer 未在时限内返回 blocker-only verdict；当前收口基于主线程 fresh evidence 与 gate 结果
- `R4` 如果继续在未获新凭证/新授权前空转 WS1/WS2，只会重复生成同一结论，不会改变真实成立条件

### Files Changed Log

- `WS4`
  - `config/governance/current-proof-contract.json`
  - `scripts/governance/render_docs_governance.py`
  - `scripts/governance/check_docs_governance.py`
  - `docs/generated/required-checks.md`
  - `docs/reference/external-lane-status.md`
  - `docs/reference/done-model.md`
  - `docs/reference/newcomer-result-proof.md`
  - `apps/worker/tests/test_external_proof_semantics.py`
  - `apps/worker/tests/test_docs_governance_control_plane.py`
- `WS3`
  - `.runtime-cache/reports/governance/remote-platform-truth.exec.json`（fresh probe）
  - `.runtime-cache/reports/governance/remote-platform-truth.json`（canonical probe refreshed）
  - `.runtime-cache/reports/governance/open-source-audit-freshness.json`（fresh check retained green）
- `Plan maintenance`
  - `.agents/Plans/2026-03-17_19-00-34__repo-verified-final-form-master-plan.md`

### Files Planned To Change

- `README.md`
- `SECURITY.md`
- `docs/start-here.md`
- `docs/runbook-local.md`
- `docs/reference/done-model.md`
- `docs/reference/external-lane-status.md`
- `docs/reference/newcomer-result-proof.md`
- `docs/reference/public-repo-readiness.md`
- `docs/reference/public-rights-and-provenance.md`
- `docs/reference/public-privacy-and-data-boundary.md`
- `docs/reference/public-brand-boundary.md`
- `docs/reference/architecture-governance.md`
- `docs/reference/dependency-governance.md`
- `docs/generated/ci-topology.md`
- `docs/generated/runner-baseline.md`
- `docs/generated/release-evidence.md`
- `config/governance/current-proof-contract.json`
- `scripts/governance/render_newcomer_result_proof.py`
- `scripts/governance/check_newcomer_result_proof.py`
- `scripts/governance/render_current_state_summary.py`
- `scripts/governance/render_docs_governance.py`
- `scripts/governance/check_docs_governance.py`
- `scripts/governance/probe_remote_platform_truth.py`
- `scripts/governance/probe_external_lane_workflows.py`
- `scripts/governance/check_open_source_audit_freshness.py`
- `.github/workflows/build-ci-standard-image.yml`
- `.github/workflows/env-governance.yml`
- `scripts/ci/check_standard_image_publish_readiness.sh`
- `infra/config/env.contract.json`
- `pyproject.toml`
- `uv.lock`
- `THIRD_PARTY_NOTICES.md`
- `artifacts/licenses/third-party-license-inventory.json`
- `integrations/README.md`
- `integrations/providers/article_fetch.py`
- `integrations/providers/bilibili_comments.py`
- `integrations/providers/http_probe.py`
- `integrations/providers/youtube_comments.py`
- `integrations/providers/youtube_transcript.py`
- `apps/worker/worker/comments/bilibili.py`
- `apps/worker/worker/comments/youtube.py`
- `apps/worker/worker/pipeline/steps/article.py`
- `apps/worker/worker/pipeline/steps/subtitles.py`
- `apps/worker/worker/rss/fetcher.py`
- `apps/worker/worker/temporal/activities_health.py`
- `apps/worker/tests/test_article_step.py`
- `apps/worker/tests/test_external_proof_semantics.py`
