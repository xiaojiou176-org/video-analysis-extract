# [🧭] Repo 终局总 Plan

## Plan Meta

- Created: `2026-03-18 20:19:29 America/Los_Angeles`
- Repo: `/Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取`
- Repo Archetype: `hybrid-repo`
- Execution Status: `In Progress`
- Planning Mode: `Single Path / Hard-Cut / Evidence-First`
- Source Of Truth: `本文件`
- Last Updated: `2026-03-18 20:36:00 America/Los_Angeles`
- Current Phase: `Phase-3 WS1 External Blocker Confirmed / Repo-side Truth Convergence Closed`
- Current Workstream: `WS1`

## [一] 3 分钟人话版

这个仓库现在最真实的状态，不是“还很乱”，也不是“已经完美了”，而是：

- **repo-side 已经很强**
- **external 分发链还没闭环**
- **current-truth 聚合面还有时间窗幻觉**

你可以把它理解成一家餐厅：

- 后厨已经很干净，流程卡、配方本、卫生表都齐了，这就是 `repo-side strict + governance-audit + docs control plane`。
- 外卖平台也已经开了账号，订单规则、打包规范、出餐凭证都设计了，这就是 `release-evidence / SBOM / attestation / GHCR workflow`。
- 但外卖骑手那边还没真正接通写权限，所以“店内流程很稳”**不等于**“已经可以稳定外卖配送”。

为什么现在不能继续靠表面成熟度自我感觉良好？

- 因为 `remote-required-checks=pass` 只是“监考名单对齐了”，不是“考试已经全科通过”。
- 因为 `current-state-summary.md` 和 `newcomer-result-proof.json` 这些 current-proof 票据，只要不重拍，就可能把**旧的 clean state**误说成**现在的 clean state**。
- 因为 GHCR external lane 现在还是 `blocked`，这意味着你可以诚实地说“仓库公开了、治理很强”，但**不能诚实地说“安全公开分发也闭环了”**。

改完后会变成什么样？

- `repo-side` 和 `external lane` 的语言边界会更硬，误判空间更小。
- `current-truth` 会变成 fail-close，不会再拿旧票据冒充当前真相。
- GHCR / strict-ci compose image set 这条唯一 external 主红灯会被单独攻克或单独挂账，不再污染整个完成判断。

哪些旧东西会被硬切？

- 任何把 `required-checks pass` 写成 `external closure pass` 的说法。
- 任何把 `source_commit 对齐` 自动当成 `当前 live worktree clean` 的读取方式。
- 任何把 tracked / generated docs 当成 current-state payload 的旧表达。
- 任何“先把 external blocker 先放着，再继续把 repo-side 做得更漂亮”的假进展路线。

为什么必须这么硬？

- 因为现在最贵的问题，已经不是“仓库里没规矩”，而是“规矩很多，容易让人误以为全都已经成立”。
- 这类仓库最怕的不是脏，而是**假成熟**。

## [二] Plan Intake

### 输入材料范围

- 上游 `超级Review` 审计报告
- 上游 `## [十三] 机器可读问题账本` YAML
- 当前 Repo fresh 验证结果：
  - `git status --short --branch`
  - `.runtime-cache/reports/governance/current-state-summary.md`
  - `.runtime-cache/reports/governance/newcomer-result-proof.json`
  - `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
  - `.runtime-cache/reports/governance/remote-platform-truth.json`
  - `.runtime-cache/reports/governance/remote-required-checks.json`
  - `.runtime-cache/reports/governance/external-lane-workflows.json`
  - `.runtime-cache/reports/release/release-evidence-attest-readiness.json`
- 当前 Repo 主线文件：
  - `.github/workflows/ci.yml`
  - `.github/workflows/remote-integrity-audit.yml`
  - `.github/workflows/build-ci-standard-image.yml`
  - `docs/reference/done-model.md`
  - `docs/reference/external-lane-status.md`
  - `docs/generated/ci-topology.md`
  - `config/governance/upstream-compat-matrix.json`
  - `config/governance/runtime-outputs.json`

### 验证范围

- repo structure
- configs
- workflows
- scripts
- docs
- tests
- outputs
- integration surfaces

### 置信边界

- **高置信**
  - GHCR lane 当前仍 blocked
  - remote required checks 当前已 pass
  - current-state/newcomer 当前是 `partial + dirty=true`
  - release-evidence attestation current-head 已 `verified`
  - `strict-ci-compose-image-set` 仍是 blocker 级 pending row
  - `docs/generated/ci-topology.md` 对 GHCR workflow runner 的叙述仍在漂移
- **中置信**
  - 未来 GHCR unblock 后，`strict-ci-compose-image-set` 会不会自动一并转绿；当前倾向认为不会，需要 same-run 重拍
  - platform hardening（如 `enforce_admins` / `required_signatures`）是否受组织级策略限制
- **低置信**
  - 外部 provider 当前时刻的额度 / 账户状态；本轮未重拍全套 provider live chain

### Repo archetype

- `hybrid-repo`

### 当前最真实定位

- `public source-first`
- `limited-maintenance`
- `repo-side strong`
- `external distribution not closed`
- `strong governance repo, not adoption-grade public delivery system yet`

### 最危险误判

- “这个仓库已经很成熟，所以主线应该继续做锦上添花治理”

真实情况是：

- 现在最值钱的动作，已经不是继续堆 repo-side 治理，而是**把 current-truth 读对，把 external blocker 单独打掉**。

### 结构化输入已就位

```xml
<plan_intake>
  <same_repo>true</same_repo>
  <structured_issue_ledger>available</structured_issue_ledger>
  <input_material_types>
    - 超级Review 审计报告（上方输出，含 YAML 账本）
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
    - GHCR external lane 是当前主 blocker
    - current-truth 聚合面仍有假成熟风险
    - docs/CI 很强，但不能替 external lane 补票
    - remote-integrity 未入主链的旧说法可能已过时
  </initial_claims>
  <known_conflicts>
    - 上轮旧说法里“remote-integrity 还没进 merge-relevant required lane”已过时；当前 repo 已证明它已进入 aggregate-gate 与 required checks
    - “pushed head 8f33902 上 current summary and newcomer proof are current and clean”已过时；当前 live workspace 因 tracked `.agents/Plans/*` 改动而再次 dirty
    - release-evidence `ready` 与 remote workflow `verified` 不是同一个层级，不能混写
  </known_conflicts>
  <confidence_boundary>
    - GHCR blocker、summary 幻觉、required-checks 非 terminal closure 为高置信
    - 平台策略进一步收紧是否完全由本仓可控，为中置信
  </confidence_boundary>
</plan_intake>
```

### 统一账本（基于 YAML 初始底稿 + Repo 验证后的裁决）

| Canonical ID | Claim / Issue | Source | Repo Verification | Evidence Strength | Type | Severity | Impact | Root Cause | Final Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ISS-001` | GHCR 标准镜像发布链 blocked | YAML + repo | 已验证 | A | fact | blocker | 阻断 external distribution 可信度 | registry auth / packages write 未闭环 | 采纳 |
| `ISS-002` | current-proof 对 live worktree 有时间窗盲区 | YAML + repo | 已验证 | A | fact | structural | 容易误读 clean state / completion state | freshness 只认 `source_commit`，不认 render 时 worktree snapshot | 采纳 |
| `ISS-003` | generated CI 叙述漂移 | 散文 + repo | 已验证 | A | fact | important | docs/CI 可信度被削弱 | docs generated narrative gate 覆盖不全 | 采纳 |
| `ISS-004` | main branch 平台信任边界偏软 | YAML + repo | 已验证 | B | fact | important | 公开仓供应链信任度不足 | branch protection / actions policy 仍偏宽 | 采纳 |
| `ISS-005` | `strict-ci-compose-image-set` 仍是 blocker 级 pending | YAML + repo | 已验证 | A | fact | important | external upstream 健康无法宣称 fully verified | same-run external proof 未闭合 | 采纳 |
| `ISS-006` | “remote-integrity 尚未进入主链 required lane” | YAML +旧审计 + repo | 被推翻 / 已过时 | A | fact | unknown | 若误保留会让主路线失焦 | 旧审计时间点早于当前 repo 状态 | 不采纳，降级为“保持护栏，不再作为主 blocker” |
| `ILL-001` | `remote-required-checks=pass` 被误读成 terminal closure | YAML + repo | 已验证 | A | risk | structural | 会夸大 CI/external 成熟度 | aggregate integrity 与 terminal closure 混读 | 采纳 |
| `ILL-002` | `current-state-summary` 被误读成 live current truth | YAML + repo | 已验证 | A | risk | structural | 会夸大 clean-state / completion | summary 不是 fail-close current-proof | 采纳 |
| `ILL-003` | upstream inventory 很完整，被误读成 external lanes 都闭环 | YAML + repo | 已验证 | A | risk | important | 会夸大 provider / external 健康度 | inventory 与 verified lane 没被读者强制区分 | 采纳 |
| `OBS-001` | repo-side strict / governance 当前仍是强绿 | repo | 已验证 | A | fact | fact | 决定主线不再浪费在 repo-side 大修 | repo-side 当前不是主战场 | 采纳 |
| `OBS-002` | 当前 live worktree 因 tracked `.agents/Plans/*` 改动再次 dirty | repo | 已验证 | A | fact | fact | current-proof 现在应按 `partial` 读取 | tracked bookkeeping 变更进入 live workspace | 采纳 |

## [三] 统一判断总览表

| 维度 | 当前状态 | 目标状态 | 证据强度 | 是否适用 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 项目定位 | 强工程仓，owner-level 候选 | 保持 source-first 强项目定位，但清除“外部分发也成熟”的误读 | A | 是 | 不走 hosted-product 叙事 |
| 开源边界 | 可安全公开源码，不可宣称安全分发已闭环 | public surface / legal-safe surface 继续稳定，distribution 单独闭环 | A | 是 | MIT/notices/security 已成立 |
| 文档事实源 | control plane + generated + runtime receipts 分层已成立 | current-truth 类页面彻底 fail-close | A | 是 | 最大 seam 在 summary/current-proof |
| CI 主链可信 | trusted boundary / aggregate / final gate 已强 | platform truth 与 generated docs 进一步对齐 | A | 是 | 主链不是空壳 |
| 架构治理 | hybrid repo，边界很清楚 | 继续减少 residual drift | A | 是 | 不需要大改结构 |
| 缓存治理 | `.runtime-cache` 约束已成立 | 保持 root/runtime 单出口，不再引入新噪音 | A | 是 | 当前不是主 blocker |
| 日志治理 | schema / correlation 已有合同 | 补 trace 残缺并保持证据可诊断 | B | 是 | 当前为次要治理项 |
| 根目录治理 | allowlist/budget/zero-unknowns 强 | 继续冻结新增顶级项 | A | 是 | 当前健康 |
| 外部依赖治理 | inventory 完整，部分 verified，1 条 blocker pending | pending row 收敛成 verified 或明确 blocked | A | 是 | 不是 git fork 问题 |
| 外部分发 / 供应链 | GHCR blocked，release evidence verified | current-head distribution verified | A | 是 | 当前头号主战场 |

## [四] 根因与完成幻觉总表

| 根因 / 幻觉 | 表面信号 | 真实问题 | 对应动作 | 防回潮 Gate |
| --- | --- | --- | --- | --- |
| `R1` External distribution 未闭环 | 仓库公开、workflow/SBOM/attestation 都在 | GHCR current-head 仍 blocked，无法诚实对外说“可分发” | `WS1` | GHCR readiness + external workflow current-head verify |
| `R2` Current-truth 聚合面非 fail-close | 有 summary、有 newcomer result proof | 旧票据可以继续冒充 current，尤其在 live dirty worktree 下 | `WS2` | summary/current-proof source_commit + worktree snapshot guard |
| `R3` Docs generated narrative 漂移 | `docs/generated/*.md` 很专业 | 至少一处生成文档已经说错真实 workflow topology | `WS3` | docs governance semantic parity gate |
| `R4` 平台信任边界偏软 | required checks 已对齐 | admin/signature/actions policy 仍偏宽，影响公开供应链说服力 | `WS4` | branch protection / remote platform policy review |
| `R5` External upstream blocker row 未收口 | upstream inventory / compat matrix 很完整 | `strict-ci-compose-image-set` 仍 pending，external 健康度不能宣称 fully verified | `WS5` | same-run compat verification + explicit pending policy |
| `ILL-1` Required checks 幻觉 | `remote-required-checks=status=pass` | 这只是“学校门口签到对齐”，不是“考试已经满分” | `WS2` + `WS3` | done-model/external-lane-status/current-summary reading rules |
| `ILL-2` Current summary 幻觉 | summary 看起来是 current | 只要不重拍，就可能还是上一张“旧照片” | `WS2` | render_newcomer_result_proof + render_current_state_summary fail-close |
| `ILL-3` Inventory 幻觉 | upstream rows 很全 | “登记在册”不等于“本轮已验收通过” | `WS5` | compat freshness + same-run + blocker-row policy |

## [五] 绝不能妥协的红线

- 不再保留任何把 `required-check integrity` 写成 `terminal CI closure` 的文案。
- 不再允许 tracked docs / generated docs 承载 current-state payload，除非它自身带 current-proof fail-close。
- 不再允许 `source_commit 对齐` 自动等同于 `live worktree clean`。
- 不再新增 repo-side runtime 输出根；所有新增输出都必须进入 `.runtime-cache/**` 既有分舱。
- 不再接受“先把 external blocker 放一放，继续做 repo-side 漂亮化”的主路线。
- 不再把 `pending compat row` 写成“基本已完成，只差补票”。
- 不再让旧 summary / old plan / historical example 混入 current verdict。

## [六] Workstreams 总表

| Workstream | 目标 | 关键改造对象 | 删除/禁用对象 | Done Definition | 优先级 |
| --- | --- | --- | --- | --- | --- |
| `WS1` GHCR External Distribution Closure | 关闭唯一 external 主 blocker | GHCR auth path, standard image readiness, build-ci-standard-image receipts | “GHCR 只是 readiness 小问题”的旧说法 | current HEAD 上 GHCR lane `verified` 或明确 fail-close 到不可控平台边界 | P0 |
| `WS2` Current-Truth Fail-Close Convergence | 彻底打掉 clean-state / current-summary 幻觉 | current-state-summary, newcomer-result-proof, external-lane snapshot reading rule | 任何旧 current-like summary 的宽松读取方式 | current-facing 聚合面在 mismatch/dirty 时一律保守降级 | P0 |
| `WS3` Docs / CI Semantic Parity Hardening | 修掉 generated CI 叙述漂移并把 docs truth 收紧 | docs/generated/ci-topology.md, render pipeline, docs governance semantic checks | 旧的“看起来像对的” generated narrative | generated docs 不能再与 workflow topology 说反话 | P1 |
| `WS4` Platform Trust Boundary Hardening | 把“平台侧仍偏软”的问题单独治理，不再和 repo-side 混写 | remote-platform-truth reading rules, branch protection review, actions policy review | “repo-side 很严所以平台也够严”的默认假设 | platform trust posture 被明确记录、校验并进入 public truth | P1 |
| `WS5` External Upstream Verification Closure | 收口 pending compat blocker rows，减少 external 健康度歧义 | upstream-compat-matrix, proof collection, same-run verification | “inventory 完整≈external health 完整”的旧读法 | blocker rows 只允许 `verified / blocked / explicit pending by rule` | P1 |

## [七] 详细 Workstreams

### `WS1` GHCR External Distribution Closure

#### 目标

- 把当前 external distribution 的唯一主 blocker 从“模糊 blocked”压缩成**可闭环通过**，或者**更小、更硬、更不可争辩的单点 blocker**。

#### 为什么它是结构性动作

- 这是当前唯一真正影响“能不能安全公开分发”的 P0。
- 不解决它，所有 release/provenance/SBOM 都只能停留在“仓库很认真”，不能升级成“分发链可信”。

#### 输入

- `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
- `.runtime-cache/reports/governance/external-lane-workflows.json`
- `.github/workflows/build-ci-standard-image.yml`
- `scripts/ci/check_standard_image_publish_readiness.sh`
- `infra/config/strict_ci_contract.json`

#### 输出

- current-head GHCR lane 新鲜判读
- 若通过：`ghcr-standard-image=verified`
- 若失败：失败边界被缩到单一平台真问题，且 public docs/summary 跟进

#### 改造对象

- `scripts/ci/check_standard_image_publish_readiness.sh`
- `.github/workflows/build-ci-standard-image.yml`
- `docs/reference/external-lane-status.md`
- `docs/reference/done-model.md`
- `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
- `.runtime-cache/reports/governance/external-lane-workflows.json`

#### 删除/禁用对象

- 禁止继续保留“GHCR lane 已经差不多，只差最后发一下”的说法
- 禁止把 repo-side readiness 继续包装成 distribution closure

#### 临时兼容桥

- 允许短期保留 `blocked` 状态
- 但只允许一种 blocked 文案：
  - 明确写出 `token_mode`
  - 明确写出 `token_scope_ok`
  - 明确写出 `blob_upload_scope_ok`
  - 明确写出 failed step / current-head run id

#### 兼容桥删除条件与时点

- 一旦 current HEAD GHCR lane `verified`，立刻删除所有“distribution blocked”临时说明页里的旧解释

#### Done Definition

- `scripts/ci/check_standard_image_publish_readiness.sh` 对 current HEAD 输出可判定结论
- `.github/workflows/build-ci-standard-image.yml` 在 current HEAD 上拿到 remote success，或拿到更精确的失败签名
- `current-state-summary.md` 与 `external-lane-status.md` 对 GHCR 的状态与 failed step 一致

#### Fail Fast 检查点

- 若 `standard-image-publish-readiness.json` 仍停在 `no token path with packages write capability detected`
  - 立即停止 repo-side 美化
  - 直接升级为 external/platform blocker
- 若 remote run 不是 current HEAD
  - 不得记为 closure

#### 它会打掉什么幻觉

- “有 GHCR workflow = 能公开分发”
- “SBOM / attestation 已接线 = 分发链已可信”

#### 它会改变哪个上层判断

- 开源就绪
- external lane 健康度
- public 展示可信度

---

### `WS2` Current-Truth Fail-Close Convergence

#### 目标

- 让 `current-state-summary.md`、`newcomer-result-proof.json`、`docs/generated/external-lane-snapshot.md` 的 current-truth 读取彻底 fail-close。

#### 为什么它是结构性动作

- 这是当前最危险的假成熟来源。
- 不解决它，后续任何 audit、plan、README、public truth 都可能用错票据。

#### 输入

- `scripts/governance/render_current_state_summary.py`
- `scripts/governance/render_newcomer_result_proof.py`
- `scripts/governance/check_current_state_summary.py`
- `scripts/governance/check_newcomer_result_proof.py`
- `.runtime-cache/reports/governance/current-state-summary.md`
- `.runtime-cache/reports/governance/newcomer-result-proof.json`

#### 输出

- current-proof 读取规则收紧
- dirty worktree / stale render / mismatched source_commit 时自动降级
- current-facing summary 与底层 receipts 一致

#### 改造对象

- `scripts/governance/render_current_state_summary.py`
- `scripts/governance/render_newcomer_result_proof.py`
- `scripts/governance/check_current_state_summary.py`
- `scripts/governance/check_newcomer_result_proof.py`
- `docs/reference/done-model.md`
- `docs/reference/external-lane-status.md`
- `docs/generated/external-lane-snapshot.md`

#### 删除/禁用对象

- 禁用“只看 `source_commit` 对齐就当 current clean state”的旧读取方式
- 禁用任何没有 dirty-worktree 语义的 current-facing summary 解释

#### 临时兼容桥

- 允许 `current-state-summary.md` 继续存在
- 但必须明确：
  - `current HEAD`
  - `worktree dirty`
  - `reading rule`
  - `stale-summary rule`

#### 兼容桥删除条件与时点

- 当 current-facing summary 都能在 dirty/stale 条件下自动 fail-close 后，删除任何额外的人工“请注意这可能是旧状态”口头补丁

#### Done Definition

- dirty worktree 时，`newcomer-result-proof.status` 必须自动降到 `partial`
- `current-state-summary.md` 必须同步显示 `worktree dirty: true`
- source_commit mismatch 时，任何 green-like lane 都不能继续按 current 读取
- tests / checks 能稳定覆盖至少：
  - clean aligned
  - dirty aligned
  - stale summary
  - historical workflow run

#### Fail Fast 检查点

- 若重渲染后 `current-state-summary` 与 `newcomer-result-proof` 仍会互相打架，停止新增 docs/plan，先补 check

#### 它会打掉什么幻觉

- “current summary 看起来新，所以就是真的 current”
- “repo-side strict 是 pass，所以 live workspace 也 pass”

#### 它会改变哪个上层判断

- docs 可信度
- CI 可信度
- completion proof 可信度
- future audit / plan 的质量

---

### `WS3` Docs / CI Semantic Parity Hardening

#### 目标

- 把当前已证实的 generated-doc 漂移修掉，并让 docs governance 开始检查这类 CI topology 语义点。

#### 为什么它是结构性动作

- 这不是文案修饰，而是“生成式事实页已经开始说错真实执行面”的警报。
- 不修，它会持续腐蚀“facts-driven docs”这块最值钱的品牌资产。

#### 输入

- `docs/generated/ci-topology.md`
- `.github/workflows/build-ci-standard-image.yml`
- `scripts/governance/check_docs_governance.py`
- `scripts/governance/render_docs_governance.py`
- `config/docs/render-manifest.json`

#### 输出

- `docs/generated/ci-topology.md` 不再把 GHCR image publish workflow 说成 self-hosted
- 对应 semantic parity check 入 gate

#### 改造对象

- `docs/generated/ci-topology.md` 的生成逻辑
- `scripts/governance/render_docs_governance.py`
- `scripts/governance/check_docs_governance.py`
- 可能涉及的 `config/docs/*.json` fragment source

#### 删除/禁用对象

- 禁止任何“workflow 名字对了就算 topology 也对了”的弱校验

#### 临时兼容桥

- 无长期桥；这是直接修正型工作流

#### 兼容桥删除条件与时点

- 修完即删，无需保留兼容

#### Done Definition

- `docs/generated/ci-topology.md` 中关于 `build-ci-standard-image` 的 runner / Buildx 叙述与真实 workflow 一致
- `check_docs_governance.py` 或其子校验开始覆盖这一类 semantic parity

#### Fail Fast 检查点

- 如果 render source 无法直接定位，先停在 render manifest / fragment source 层，不要手改 generated file 混过去

#### 它会打掉什么幻觉

- “generated docs 一定比手写 docs 更可信”

#### 它会改变哪个上层判断

- docs 治理成熟度
- CI 事实面可信度

---

### `WS4` Platform Trust Boundary Hardening

#### 目标

- 把“平台侧信任边界仍偏软”的问题明确成一条独立治理线，而不是继续被 repo-side 成熟度盖住。

#### 为什么它是结构性动作

- 公开仓的供应链可信，不只看本地 gate，也看平台规则。
- 当前 `allowed_actions=all`、`sha_pinning_required=false`、`enforce_admins=false`、`required_signatures=false` 会削弱公开仓信任面。

#### 输入

- `.runtime-cache/reports/governance/remote-platform-truth.json`
- `.github/workflows/*.yml`
- `docs/reference/public-repo-readiness.md`
- `docs/reference/external-lane-status.md`

#### 输出

- 一份明确的平台信任边界现状与目标态清单
- 必要时把“平台仍偏软”写入 public boundary docs / governance docs

#### 改造对象

- `docs/reference/public-repo-readiness.md`
- `docs/reference/external-lane-status.md`
- 可能涉及 GitHub branch protection / repo settings（repo 外动作）

#### 删除/禁用对象

- 删除或禁用任何默认把 repo-side 严格性外推成 platform strictness 的表达

#### 临时兼容桥

- 允许短期保留当前平台姿态
- 但必须把它写成：
  - observed fact
  - not yet hardened
  - not equal to repo-side maturity

#### 兼容桥删除条件与时点

- 当 platform settings 达到目标态并被 remote probe 读到时，再删除“偏软边界提醒”

#### Done Definition

- 平台信任边界在 docs / runtime truth 中被单独呈现
- 若 settings 可改，则 remote probe 能读到更硬状态
- 若 settings 暂不可改，则 Plan / public docs 把它诚实挂账，不再模糊处理

#### Fail Fast 检查点

- 若该动作受组织级限制，立即转成 explicit external governance blocker，不要在 repo 内假装能修完

#### 它会打掉什么幻觉

- “required checks 都齐了，所以平台也足够硬”

#### 它会改变哪个上层判断

- 开源 readiness
- public trust
- supply-chain credibility

---

### `WS5` External Upstream Verification Closure

#### 目标

- 把 `strict-ci-compose-image-set` 这条 blocker 级 pending row 收口成**verified**或**explicit blocked by rule**，不再维持模糊 pending。

#### 为什么它是结构性动作

- inventory 已经很强，当前剩的是“最后一条 blocker row 怎么诚实落地”。
- 不收口，external upstream 健康度会长期停在“看起来差一点，但总说不清差哪一点”。

#### 输入

- `config/governance/upstream-compat-matrix.json`
- `.runtime-cache/reports/governance/upstream-compat-report.json`
- `.runtime-cache/reports/governance/external-lane-workflows.json`
- `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
- `scripts/governance/check_upstream_same_run_cohesion.py`
- `scripts/governance/check_upstream_compat_freshness.py`

#### 输出

- compat row 结论更硬
- same-run proof 关系更清楚

#### 改造对象

- `config/governance/upstream-compat-matrix.json`
- `docs/reference/upstream-governance.md`
- `docs/reference/upstream-compatibility-policy.md`
- 相关 governance check / render outputs

#### 删除/禁用对象

- 禁用“pending 但大家都知道其实差不多了”的描述

#### 临时兼容桥

- 允许 `pending`
- 但只在满足以下条件时允许：
  - explicit blocker_type
  - explicit unblock dependency
  - explicit freshness window
  - explicit same-run missing reason

#### 兼容桥删除条件与时点

- 一旦 GHCR lane 转绿并补齐 same-run proof，这条 row 立即升为 `verified`
- 若 GHCR 长期不可解，则改为 `blocked`，不再维持模糊 pending

#### Done Definition

- `strict-ci-compose-image-set` 不再是“语义模糊的 pending”
- compat matrix / docs / runtime summary 对其解释完全一致

#### Fail Fast 检查点

- 若 row 的外部依赖本质就是 GHCR closure，则停止单独空转，把它明确挂到 `WS1` 后置步骤

#### 它会打掉什么幻觉

- “upstream matrix 很全，所以 external health 也很全”

#### 它会改变哪个上层判断

- upstream 健康度
- external lane 可解释性

## [八] 硬切与迁移方案

### 立即废弃项

- 废弃任何把 `remote-required-checks=pass` 当 terminal CI / live-smoke / GHCR closure 的旧说法
- 废弃任何把 `source_commit 对齐` 自动当作 `live workspace clean` 的旧说法
- 废弃 `docs/generated/external-lane-snapshot.md` 承载 current verdict 的旧阅读习惯

### 迁移桥

- `current-state-summary.md` 继续保留，但只作为 runtime-owned pointer + summary，不再允许它越权充当终局完成判决
- `newcomer-result-proof.json` 继续保留，但 dirty/stale 时必须自动降级，不允许人工口头补丁兜底
- `strict-ci-compose-image-set` 允许短期 `pending`，但必须显式写明它挂靠 `WS1`

### 禁写时点

- 一旦 `WS2` 启动，禁止再往 tracked docs 里手写 current-state payload
- 一旦 `WS3` 启动，禁止手工修 generated docs 成果文件而不修 render source

### 只读时点

- `docs/generated/*.md` 在 `WS3` 期间视为 render-only，只能通过 control plane / render pipeline 变更

### 删除时点

- `WS2` 完成后，删除所有旧的“current summary 仅供参考”口头兜底表达
- `WS1` 完成后，删除所有旧的“GHCR blocked 暂存说明”

### 防永久兼容机制

- 所有 pending / blocked / bridge 状态必须具备：
  - owner
  - unblock condition
  - remove condition
  - verification command
- 缺任一项，不允许进入 Plan 主线

## [九] 验证闭环与 Gate

| 维度 | 验证项 | Gate / 命令 / CI / Policy | 通过条件 | 未通过意味着什么 |
| --- | --- | --- | --- | --- |
| README / 项目定位 | public/source-first 叙事与真实能力对齐 | `README.md` + `docs/reference/done-model.md` + `docs/reference/public-repo-readiness.md` 人工核对 + docs governance | 不再把 external lane 误写成已闭环 | 对外定位失真 |
| public surface / secret / provenance | public-safe surface、gitleaks freshness、release evidence 边界一致 | `python3 scripts/governance/check_open_source_audit_freshness.py`; `python3 scripts/governance/check_public_surface_policy.py` | history/worktree gitleaks fresh pass；public surface policy pass | 公开边界不可信 |
| docs 是否是事实源 | generated/reference/control-plane 三层一致 | `python3 scripts/governance/check_docs_governance.py` | render freshness + semantic parity 均 pass | 文档不能当事实源 |
| CI 绿灯是否覆盖关键判断 | required checks、aggregate、final gate 与 external lane 分层清楚 | `.github/workflows/ci.yml`; `python3 scripts/governance/check_remote_required_checks.py` | `required checks pass` 不再被误读成 terminal closure | CI 绿灯解释失真 |
| root allowlist 是否强制 | 顶级路径无未知项 | `python3 scripts/governance/check_root_allowlist.py` | pass | 根目录重新失控 |
| dirty-root / live workspace truth | dirty 时 current-proof 自动降级 | `python3 scripts/governance/render_newcomer_result_proof.py`; `python3 scripts/governance/check_newcomer_result_proof.py` | dirty => `status=partial` | clean-state 幻觉回潮 |
| cache 全删可重建 | `.runtime-cache` 单出口与 rebuild entrypoints 成立 | `python3 scripts/governance/check_runtime_outputs.py`; `python3 scripts/governance/check_runtime_cache_retention.py` | docs/config/live tree 一致 | runtime governance 漂移 |
| 输出路径是否合法 | 新输出不越界 | `config/governance/runtime-outputs.json`; `.gitignore`; root allowlist | 无新非法输出根 | repo-side 噪音回流 |
| 日志 schema / correlation | log contract / trace correlation 成立 | `python3 scripts/governance/check_logging_contract.py`; `python3 scripts/governance/check_log_correlation_completeness.py` | pass | 日志不可诊断 |
| evidence / report 分层 | reports/evidence/run/logs/tmp 分舱一致 | `python3 scripts/governance/check_runtime_outputs.py` | pass | runtime truth surfaces 互相污染 |
| dependency boundary / contract-first | external usage 都经治理登记 | `python3 scripts/governance/check_upstream_governance.py`; `python3 scripts/governance/check_unregistered_upstream_usage.py` | pass | 外部依赖治理失真 |
| upstream inventory / compatibility | blocker rows fresh / same-run / explicit | `python3 scripts/governance/check_upstream_compat_freshness.py`; `python3 scripts/governance/check_upstream_same_run_cohesion.py` | blocker rows 无模糊 pending | external health 判断不可信 |
| GHCR distribution | current-head GHCR lane 能被准确验证 | `./scripts/ci/check_standard_image_publish_readiness.sh`; current-head `build-ci-standard-image.yml` | `verified` 或精确 blocked | external distribution 仍未闭环 |

## [十] 执行时序总表

| 阶段 | 动作 | 前置条件 | 并行性 | 完成标志 | 风险 |
| --- | --- | --- | --- | --- | --- |
| `Phase-0` | 重新确认当前 dirty worktree、summary、newcomer、GHCR、external workflows | 无 | 可并行读取 | 当前账本定稿 | 若不先确认，Plan 会沿用过时判断 |
| `Phase-1` | 执行 `WS2`，先把 current-truth fail-close 做硬 | `Phase-0` | 可与 `WS3` 的只读定位并行，不可与最终 docs 改写并行 | summary/newcomer 读法收敛 | 若跳过，会持续误导后续所有判断 |
| `Phase-2` | 执行 `WS3`，修 generated CI 叙述漂移并补 semantic gate | `WS2` 输出阅读规则稳定 | 可与 `WS4` 文档盘点并行 | docs generated 不再说错 workflow | 若不做，facts-driven docs 品牌被侵蚀 |
| `Phase-3` | 执行 `WS1`，集中攻 GHCR external blocker | `WS2` 完成，避免再被旧 summary 误导 | 与 `WS4/WS5` 只读准备可并行；真正验证须串行 | GHCR lane `verified` 或精确 external blocker 化 | 外部权限可能阻塞推进 |
| `Phase-4` | 执行 `WS5`，收口 `strict-ci-compose-image-set` pending 语义 | `WS1` 有结果 | 串行依赖 `WS1` | compat row 不再模糊 pending | 若 `WS1` 未解，会转为显式 blocked |
| `Phase-5` | 执行 `WS4`，平台 trust boundary 挂账或硬化 | `WS1~WS3` 结论稳定 | 可部分并行 | platform posture 被明确纳入 public truth | 可能受组织级策略限制 |
| `Phase-6` | 全量回归并更新 current truth / docs / plan state | 前述 workstreams 有代码/文档改动 | 串行 | current receipts / docs / workflows 一致 | 若 current receipts 不重拍，会再次产生旧图纸 |

## [十一] 改造动作 -> 上层判断改变 映射表

| 动作 | 改变什么判断 | 为什么 |
| --- | --- | --- |
| 打通 GHCR standard image current-head verified | 开源 readiness / external distribution judgment | 从“可公开源码”升级到“分发链更可信” |
| 让 current summary / newcomer proof fail-close | docs / CI / completion proof judgment | 后续 agent 不再被旧票据带偏 |
| 修复 generated CI topology 漂移 | facts-driven docs judgment | 生成文档重新配得上“事实驱动”这块招牌 |
| 把 platform trust posture 单列治理 | public trust / supply-chain judgment | 公开仓的可信度不再只靠 repo-side gates |
| 收口 pending compat blocker row | upstream 健康度 judgment | external dependency health 说法更诚实 |

## [十二] 如果只允许做 3 件事，先做什么

### 1. `WS1` GHCR External Distribution Closure

- 为什么先做：
  - 这是当前唯一 external 主 blocker
  - 不做它，所有“安全开源 / 可分发”都不能诚实说成立
- 打掉什么幻觉：
  - “有 workflow / attestation / SBOM 就等于可分发”
- 释放什么能力：
  - external distribution 的真实 closure

### 2. `WS2` Current-Truth Fail-Close Convergence

- 为什么第二：
  - 这是所有后续判断的底座
  - 不修它，未来每个 audit / plan / summary 都可能继续说错当前状态
- 打掉什么幻觉：
  - “source_commit 对齐 = 当前 live workspace 可信”
- 释放什么能力：
  - current-proof 能真正为未来执行者服务

### 3. `WS3` Docs / CI Semantic Parity Hardening

- 为什么第三：
  - 这是已被 repo 坐实的当前 drift
  - 成本不高，但能显著提升 docs/CI 的真可信度
- 打掉什么幻觉：
  - “generated docs 一定正确”
- 释放什么能力：
  - facts-driven docs 重新配得上“可当真相层的解释页”

## [十三] 不确定性与落地前核对点

### 高置信事实

- GHCR blocked 仍是真红灯
- `remote-required-checks=pass` 当前已成立
- current live worktree 当前为 dirty，current-proof 应按 `partial` 读取
- `remote-integrity 未入主链` 的旧说法已经过时
- generated `ci-topology.md` 当前仍有一处 runner 叙述漂移

### 中置信反推

- `strict-ci-compose-image-set` 大概率受 `WS1` 结果直接影响，但是否能同轮自动升为 verified，需要执行时再看 same-run proof
- 平台 trust boundary 的进一步收紧，可能部分不受 repo 本身控制

### 落地前要二次核对的点

- `WS1` 开始前再 fresh 读一次：
  - `standard-image-publish-readiness.json`
  - `external-lane-workflows.json`
- `WS2` 开始前再 fresh 读一次：
  - `git status --short`
  - `current-state-summary.md`
  - `newcomer-result-proof.json`
- `WS3` 开始前再核对：
  - `docs/generated/ci-topology.md`
  - `.github/workflows/build-ci-standard-image.yml`

### 但这些不确定性不影响主路线

- 主路线仍然唯一：
  1. 先读对 current truth
  2. 再单点突破 external blocker
  3. 再硬化 docs/CI/platform trust

## [十四] 执行准备状态

### Current Status

- `git status --short --branch` 当前 dirty，原因已不再只是旧 Plan bookkeeping：当前工作树同时包含
  - tracked `.agents/Plans/2026-03-18_16-41-47__repo-ultimate-verified-execution-master-plan.md`
  - tracked WS2/WS3/WS5 改动文件（current-proof scripts/docs/tests、docs governance render/check、upstream compat matrix）
  - untracked 当前执行 Plan `.agents/Plans/2026-03-18_20-19-29__repo-ultimate-single-path-execution-plan.md`
- current HEAD = `8f33902c2a09028c6fe0f4244a0cbbb8f3cafd26`
- `current-state-summary.md` 当前显示：
  - `worktree dirty=true`
  - `current workspace verdict=partial`
  - `fail-close blockers=dirty_worktree`
  - `newcomer-result-proof artifact=partial`
  - `repo-side-strict receipt=pass`
  - `remote-required-checks=pass`
  - `ghcr-standard-image=blocked`
  - `release-evidence-attestation=verified`
- `remote-integrity` 当前已在：
  - `aggregate-gate`
  - remote branch protection required checks
- `docs/generated/ci-topology.md` 已与 GHCR workflow 的真实 runner/buildx 语义重新对齐
- `strict-ci-compose-image-set` 当前在 summary 中已明确显示为 `external; blocked on ghcr-standard-image (registry-auth-failure)`
- 本 Plan 已正式接管上一轮 Plan，成为当前唯一可信执行状态源；旧 Plan 只保留为历史施工记录，不再承载当前状态

### Next Actions

1. 若继续执行，先获取真实 GHCR `write:packages` 能力或远端 secret 修复，再重跑 `WS1`
2. 然后把 `strict-ci-compose-image-set` 从 `pending` 收口为 `verified` 或 `blocked`
3. 最后决定是否进入 `WS4` 的平台 trust boundary 硬化（这是外部设置工作，不是当前 repo-side 主线）

### Decision Log

- 决定**不**再把“remote-integrity 未入主链”保留为主路线，因为 repo 已证明它过时
- 决定把 `current-truth` 放在 GHCR 前面做，是因为它决定后续所有票据能否被正确读取
- 决定维持单一路线，不输出“repo-side 美化优先”这类看起来舒服但错误的支线
- `2026-03-18 20:19 America/Los_Angeles`：正式接管本 Plan 作为唯一可信执行状态源。未选替代方案：继续在上一份 `2026-03-18_16-41-47__repo-ultimate-verified-execution-master-plan.md` 上迭代。原因：上一份 Plan 已被后续 live state 和当前账本部分推翻，继续沿用会把过时判断带回主线。影响：从本条起，一切任务顺序、验证、阻塞、文件清单都只在本文件更新。
- `2026-03-18 20:22 America/Los_Angeles`：已并行派发两个互不重叠的实现工单。`WS2` 工单只允许改 current-state/newcomer render+check、对应 reference docs 与 tests；`WS3` 工单只允许改 docs governance render/check、`ci-topology` 生成逻辑与 tests。未选替代方案：L1 串行自己同时改两组文件。原因：两个 write set 基本不重叠，且都需要 targeted tests。影响：主线程保留给裁决、集成验证、Plan 维护与后续 `WS1` 外部 blocker 分析。
- `2026-03-18 20:26 America/Los_Angeles`：WS3 已在主线程完成真实性复核。子代理实现把 `docs/generated/ci-topology.md` 中 GHCR workflow 叙述从旧的 “self-hosted runners” 改为读取 `.github/workflows/build-ci-standard-image.yml` 的真实 `runs-on`；`check_docs_governance.py` 增加了 semantic parity 校验；主线程复跑 `python3 scripts/governance/check_docs_governance.py` 与 `uv run pytest apps/worker/tests/test_docs_governance_control_plane.py -q` 均通过。未选替代方案：仅手改 generated 文档。影响：WS3 可正式进入 `Verified`。
- `2026-03-18 20:30 America/Los_Angeles`：WS2 已由主线程完成收尾与联合验证。新增 `current_workspace_verdict` / `blocking_conditions` 结构字段，`current-state-summary.md` 现在显式渲染 `current workspace verdict` 与 `fail-close blockers`，并在 dirty worktree 下写出 “只证明 committed snapshot”。同时补上 `apps/worker/tests/test_external_proof_semantics.py` 三个定向测试，主线程联合复跑 docs governance + current-proof checks + 两组 targeted pytest 全部通过。未选替代方案：只补说明文案、不补结构字段和测试。影响：WS2 可正式进入 `Verified`，当前主线切换到 `WS1`。
- `2026-03-18 20:34 America/Los_Angeles`：主线程重跑 `./scripts/ci/check_standard_image_publish_readiness.sh /tmp/ws1-readiness.json` 并再次得到 `registry-auth-failure`；`/tmp/ws1-readiness.json` 显示 `token_mode=gh-cli`, `token_scope_ok=false`, `blob_upload_scope_ok=false`，错误为 `no token path with packages write capability detected`。`gh auth status` 进一步证明当前活动账号 `xiaojiou176` scopes 不含 `write:packages`。未选替代方案：切换用户全局 gh 活动账号做试验。原因：那会改动用户本机全局 GitHub CLI 状态，超出本轮 repo-side 最小必要变更。影响：WS1 当前可诚实收口为 external/platform blocker，不再作为 repo-side 可继续修复项。
- `2026-03-18 20:35 America/Los_Angeles`：补做 `WS5` 的 repo-side truth convergence。`config/governance/upstream-compat-matrix.json` 里 `strict-ci-compose-image-set.failure_signature` 已收紧为显式挂靠 GHCR 写权限边界；`render_current_state_summary.py` 现在把该行渲染成 `external; blocked on ghcr-standard-image (registry-auth-failure)`；并新增一条定向测试保护这层语义。未选替代方案：继续保留模糊的 `external` 注记。影响：WS5 进入 `Partially Completed`，但不会被误读成已闭环。

### Validation Log

- `git status --short --branch` => dirty，旧 tracked Plan 已修改
- `current-state-summary.md` => `worktree dirty=true`
- `newcomer-result-proof.json` => `status=partial`, `strict=pass`, `governance=pass`
- `remote-required-checks.json` => `status=pass`
- `remote-platform-truth.json` => public repo, required checks 已对齐，platform policy 仍偏软
- `standard-image-publish-readiness.json` => `status=blocked`, `blocker_type=registry-auth-failure`
- `external-lane-workflows.json` =>
  - `ghcr-standard-image=blocked` on current head
  - `release-evidence-attestation=verified` on current head
- `docs/generated/ci-topology.md` vs `.github/workflows/build-ci-standard-image.yml` => 已对齐；GHCR workflow 现在按真实 `runs-on: ubuntu-latest` 渲染
- `2026-03-18 20:19 America/Los_Angeles`：复核 `.github/workflows/ci.yml` 证明 `remote-integrity` 已进入 `aggregate-gate` 且远端 required checks 已包含 `remote-integrity`；因此“remote-integrity 尚未进入主链 required lane”已降级为历史问题，不再作为当前主 blocker。
- `2026-03-18 20:22 America/Los_Angeles`：复核 `scripts/governance/common.py` 确认 runtime artifact metadata writer 支持 `extra` 扩展字段，因此 `WS2` 可以走“把 render-time live-worktree 语义写入 artifact metadata/payload”的硬化路线，而不是只能补充说明文案。
- `2026-03-18 20:26 America/Los_Angeles`：主线程复跑 `python3 scripts/governance/check_docs_governance.py` => pass；`uv run pytest apps/worker/tests/test_docs_governance_control_plane.py -q` => `9 passed, 2 warnings`。说明 WS3 的 render/check/test 三面已经重新对齐。`reruns/reruns_delay` warning 属既有 pytest 配置噪音，本轮不作为 blocker。
- `2026-03-18 20:30 America/Los_Angeles`：主线程顺序执行 `python3 scripts/governance/render_docs_governance.py`、`python3 scripts/governance/render_newcomer_result_proof.py`、`python3 scripts/governance/render_current_state_summary.py`、`python3 scripts/governance/check_docs_governance.py`、`python3 scripts/governance/check_newcomer_result_proof.py`、`python3 scripts/governance/check_current_state_summary.py`、`uv run pytest apps/worker/tests/test_docs_governance_control_plane.py -q`、`uv run pytest apps/worker/tests/test_external_proof_semantics.py -q`，全部通过。当前 summary 首屏已明确显示 `current workspace verdict=partial`、`fail-close blockers=dirty_worktree`。
- `2026-03-18 20:34 America/Los_Angeles`：主线程执行 `./scripts/ci/check_standard_image_publish_readiness.sh /tmp/ws1-readiness.json` => fail；随后读取 `/tmp/ws1-readiness.json` 与 `gh auth status`，共同证明当前活动凭证路径缺少 `packages write` 能力。
- `2026-03-18 20:35 America/Los_Angeles`：主线程执行 `python3 scripts/governance/render_current_state_summary.py`、`python3 scripts/governance/check_current_state_summary.py`、`uv run pytest apps/worker/tests/test_external_proof_semantics.py -q`，全部通过；当前 summary 中 `strict-ci-compose-image-set` 已显示为 `external; blocked on ghcr-standard-image (registry-auth-failure)`，定向 pytest 为 `11 passed, 2 warnings`。

### Risk / Blocker Log

- `P0`: GHCR `registry-auth-failure`
- `P1`: platform trust boundary still soft
- `P1`: `strict-ci-compose-image-set` 仍 pending，且已确认挂靠 GHCR blocker
- `P1`: pytest 仍有既有 `reruns/reruns_delay` config warning，但本轮未引入新失败

### Files Changed Log

- `scripts/governance/render_newcomer_result_proof.py`
  - 新增 `current_workspace_verdict` / `blocking_conditions` fail-close 结构
- `scripts/governance/check_newcomer_result_proof.py`
  - 强制校验 dirty/stale/missing 条件必须落到 blocker 列表
- `scripts/governance/render_current_state_summary.py`
  - summary 显式渲染 `current workspace verdict`、`fail-close blockers`
  - `strict-ci-compose-image-set` 现在会把 GHCR 当前 blocker 挂出来
- `scripts/governance/check_current_state_summary.py`
  - 强制 summary 与 newcomer fail-close 语义对齐
- `docs/reference/done-model.md`
  - 明确 `current_workspace_verdict` 是 repo-side 当前工作区总闸判词
- `docs/reference/external-lane-status.md`
  - 明确 dirty/partial current summary 必须 fail-close 读取
- `scripts/governance/render_docs_governance.py`
  - GHCR workflow runner/buildx 文案改为从真实 workflow 解析
- `scripts/governance/check_docs_governance.py`
  - 增加 GHCR workflow runner/buildx 语义 parity 检查
- `docs/generated/ci-topology.md`
  - 现已与 `.github/workflows/build-ci-standard-image.yml` 的 `ubuntu-latest` runner 对齐
- `apps/worker/tests/test_docs_governance_control_plane.py`
  - 新增 WS3 语义回归保护
- `apps/worker/tests/test_external_proof_semantics.py`
  - 新增 WS2 fail-close 测试与 WS5 pending-row 说明测试
- `config/governance/upstream-compat-matrix.json`
  - 将 `strict-ci-compose-image-set.failure_signature` 改为明确挂靠 GHCR 写权限边界

### Files Planned To Change

- 若继续执行 WS1：远端 GHCR secret / 平台 write 权限相关外部配置（repo 外）
- 若继续执行 WS4：GitHub 平台 settings（repo 外）
- 若继续执行 WS5：可能继续更新 `config/governance/upstream-compat-matrix.json` 的 row 状态

## Workstreams 状态表

| Workstream | 状态 | 优先级 | 负责人 | 最近动作 | 下一步 | 验证状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `WS1` GHCR External Distribution Closure | `Blocked` | `P0` | `L1 Coordinator + L2 validator/debugger` | 已在当前工作树再次复跑本地 readiness；`/tmp/ws1-readiness.json` 与 current-head workflow 同时指向 `registry-auth-failure` / 无 `packages write` 能力 | 等待真实 GHCR write-capable token / remote secret 修复后再重跑 | `standard-image-publish-readiness.json=blocked; external-lane-workflows current-head=blocked` |
| `WS2` Current-Truth Fail-Close Convergence | `Verified` | `P0` | `L1 Coordinator + L2 implementer` | 已新增 `current_workspace_verdict` / `blocking_conditions` 结构字段，并让 summary 显式消费这些 fail-close 语义；主线程已完成联合 render/check/pytest 复核 | 后续只做只读回归 | `check_newcomer_result_proof.py=pass; check_current_state_summary.py=pass; test_external_proof_semantics.py=10 passed` |
| `WS3` Docs / CI Semantic Parity Hardening | `Verified` | `P1` | `L1 Coordinator + L2 implementer` | 已完成 render/check/test 三面收口：`ci-topology` 现在按 workflow 真实 `runs-on` 渲染，docs governance 已增加 semantic parity 校验 | 不再继续扩散；后续只在 WS3 回归时复跑 docs governance | `check_docs_governance.py=pass; test_docs_governance_control_plane.py=9 passed` |
| `WS4` Platform Trust Boundary Hardening | `Blocked` | `P1` | `L1 Coordinator + L2 validator` | 已确认最值得先硬化的是 `allowed_actions=all` / `sha_pinning_required=false` 与 `required_signatures=false` / `enforce_admins=false`，但这属于外部平台设置变更 | 等待用户明确授权或外部平台治理窗口 | `remote-platform-truth.json` 已读；repo-side docs 已足够诚实 |
| `WS5` External Upstream Verification Closure | `Partially Completed` | `P1` | `L1 Coordinator + L2 validator` | 已把 `strict-ci-compose-image-set` 的 current pending 原因从泛化 external 收口为显式 GHCR 依赖；summary 与 matrix 已对齐 | 待 `WS1` 成功后把该 row 升为 verified；若 WS1 长期 blocked，则改为 explicit blocked | `current-state-summary row=GHCR-dependent pending; test_external_proof_semantics.py=11 passed` |
