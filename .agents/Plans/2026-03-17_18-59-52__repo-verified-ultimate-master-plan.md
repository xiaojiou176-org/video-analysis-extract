# [🧭] Repo 终局总 Plan

## [一] 3 分钟人话版

现在这个仓库最危险的地方，不是它不成熟，而是它**已经足够成熟到会制造错觉**。

说得像生活一点：这像一家工厂，车间内部已经非常规整，巡检单、消防通道、出入库制度都做得很像样；但你不能因为厂内整洁，就说它“已经完成全国发货、售后通道、质检备案全部闭环”。本仓库现在就是这个状态：

- **Repo-side 很强**：治理总闸、required checks 对账、文档控制面、runtime truth、repo-side strict 收据都已经很硬。
- **当前最真实的问题不是 repo-side 坏掉，而是 current-proof 只到 `partial`**：因为工作树是 dirty，commit 级收据不等于“当前这一份未提交工作树也 fully proved”。
- **external/public 还没闭环**：GHCR 标准镜像发布仍被 packages write 权限卡住。
- **平台安全能力也没闭环**：`private vulnerability reporting` 还是 `unverified`，`security_and_analysis` 仍有 disabled 项。

所以这份 Plan 的唯一主路线不是“再补几个漂亮功能”，而是：

1. **先把 current-proof 从 partial 拉到真正 current**。
2. **再把 GHCR external lane 从 blocked 拉到 verified**。
3. **再把平台安全能力从 posture 变成 live-proof**。
4. **同时把 docs/CI/current-truth 的语义硬切成 fail-close，杜绝完成幻觉回潮**。
5. **最后只在真正改变判断的地方做 architecture hard cut，不做装饰性收口。**

改完以后，仓库会从“强治理但容易被误读”，变成“repo-side、external、public、安全、语义边界都分层闭环”的 Final-Form 候选。

必须这么硬的原因也很简单：

- 不硬切，旧绿灯会继续冒充 current truth。
- 不硬切，`ready` 会继续被误读成 `verified`。
- 不硬切，public repo 会继续被误读成 public distribution ready。
- 不硬切，下一位 Agent 还会重复走错路。

## [二] Plan Intake

```xml
<plan_intake>
  <same_repo>true</same_repo>
  <structured_issue_ledger>available</structured_issue_ledger>
  <input_material_types>
    - 超级Review 审计报告（上方输出，含 YAML 账本）
    - 当前 Repo tracked docs / workflows / configs / scripts
    - 当前 Repo runtime-owned fresh reports
    - 现有 .agents/Plans 中的前序执行计划
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
    - repo-side 很强，但 external/public/security 仍未闭环
    - docs/CI 成熟，但语义上仍有完成幻觉窗口
    - 当前最贵问题不是“代码能不能跑”，而是“当前判断能不能被诚实复述”
  </initial_claims>
  <known_conflicts>
    - 旧材料曾把 repo-side strict 视作当前唯一已闭环；fresh 验证显示 strict receipt 已存在，但 newcomer 总状态仍是 partial，因为 worktree dirty
    - 旧材料容易把 release readiness 与 release verified 混成一件事；fresh 当前态证明两者必须继续分层
    - 旧材料容易把 SECURITY.md 的存在误读成 private vulnerability reporting 已启用；Repo 当前不支持此说法
    - archetype 旧材料与前序计划都用 hybrid-repo；fresh 复核后维持该判断，但必须说明它不是“胶水仓”
  </known_conflicts>
  <confidence_boundary>
    - 高置信：fresh 命令直接证明的 repo-side / external / security / current-proof 状态
    - 中置信：外部 glue locality 剩余哪些收口还值得继续做
    - 中低置信：平台安全能力启用后的具体组织级审批路径
  </confidence_boundary>
</plan_intake>
```

### 输入材料范围

- 上方超级 Review 审计报告与 YAML 账本
- 当前 Repo 内以下事实源：
  - `README.md`
  - `docs/start-here.md`
  - `docs/reference/done-model.md`
  - `docs/reference/external-lane-status.md`
  - `docs/reference/public-repo-readiness.md`
  - `config/docs/*.json`
  - `.github/workflows/*.yml`
  - `.runtime-cache/reports/governance/*`
  - `config/governance/active-upstreams.json`
  - `config/governance/upstream-compat-matrix.json`

### 验证范围

- Repo 结构与 archetype
- current-proof / newcomer / external lane runtime artifacts
- docs control plane 与 generated docs 的接线关系
- CI 主链 / branch protection / required checks 对齐
- platform security capability 当前态
- external distribution 当前 blocker
- architecture hard-cut 是否还值得继续推进

### Repo archetype

- **结论：`hybrid-repo`**
- **解释**：
  - 不是纯 glue-repo，因为核心业务复杂度与控制面都在 repo 内。
  - 也不是纯 native-repo，因为外部 provider、binary、image、reader stack、release evidence 对系统可信度构成一等公民影响。
  - 正确说法是：**repo-owned core + governed external integration surfaces 的 hybrid-repo**。

### 当前最真实定位

- `public source-first + limited-maintenance + dual completion lanes`
- 强工程型 applied AI mini-system
- owner-level candidate
- 不是 adoption-grade 镜像优先产品

### 最危险误判

- 把 `governance-audit PASS`、`repo_side_strict_receipt=pass`、仓库 public、release evidence ready/verified 等信号叠加后，误判成“整个仓库已经 Final Form”。

### Phase 1 统一账本（由上游 YAML + Repo 验证归并）

| Canonical ID | Claim / Issue | Source | Repo Verification | Evidence Strength | Type | Severity | Impact | Root Cause | Final Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ISS-001` | GHCR external lane 被 packages write 能力阻断 | 上游 YAML + Repo fresh 命令 | 已验证 | A | fact | blocker | 决定 external/public 是否能闭环 | 平台权限未闭环 | 采纳 |
| `ISS-002` | live workspace 只有 partial proof，不应冒充 fully proved | 上游 YAML + `newcomer-result-proof.json` | 已验证 | A | fact | structural | 决定 current-state 是否可信 | dirty worktree 与 commit-proof 被分层 | 采纳并升级为 WS1 |
| `ISS-003` | PVR / security_and_analysis 仍未形成 current-proof | 上游 YAML + `remote-platform-truth.json` | 已验证 | A | fact | structural | 决定开源安全边界成熟度 | 平台能力未启用或未被 live probe 证实 | 采纳并升级为 WS3 |
| `ISS-004` | docs/CI/current-truth 语义仍易误读 | 上游 YAML + docs/governance scripts | 已验证 | A | inference | important | 决定完成幻觉是否持续回潮 | 控制面已强，但语义 fail-close 覆盖仍不均匀 | 采纳 |
| `ISS-005` | 治理面规模大，维护税高 | 上游 YAML + Repo 面观察 | 部分验证 | B | risk | important | 决定长期维护成本 | 规则与解释层很多 | 部分采纳 |
| `ISS-006` | strongest signal 是工程治理而非 adoption-grade 产品交付 | 上游 YAML + positioning docs | 已验证 | A | inference | important | 决定对外叙事与招聘信号 | public posture 主动做了降承诺 | 采纳 |
| `NEW-001` | repo-side strict 当前不是红灯，而是已绿但被 dirty-worktree 总状态盖成 partial | fresh Repo runtime proof | 已验证 | A | fact | structural | 纠正主路线优先级 | 旧说法已过时 | 新增并替换旧“strict reclosure”叙事 |
| `NEW-002` | repo-level upstream/fork 路线图不适用；适用的是 integration-upstream governance | fresh Repo topology | 已验证 | A | fact | enhancement | 防止错误规划 merge/rebase 路线 | upstream 是兼容治理，不是 fork 漂移 | 新增并硬切错误议题 |

## [三] 统一判断总览表

| 维度 | 当前状态 | 目标状态 | 证据强度 | 是否适用 | 备注 |
| --- | --- | --- | --- | --- | --- |
| Repo archetype | `hybrid-repo` | 保持 | A | 是 | 不翻案，但要讲清不是胶水仓 |
| Repo-side governance | green | 保持 green | A | 是 | `./bin/governance-audit --mode audit` fresh PASS |
| Repo-side strict current receipt | green | 保持 green | A | 是 | 当前是 pass，不再把它当 blocker |
| Newcomer / current-proof 总状态 | `partial` | `pass` | A | 是 | 核心缺口是 dirty worktree |
| GHCR external lane | blocked | verified | A | 是 | 当前最硬 blocker |
| Release evidence lane | readiness=READY, remote=current-head verified | 继续分层但不混淆 | A | 是 | 不是 blocker，但语义必须继续硬切 |
| Public posture | source-first / limited-maintenance | 保持但更 current-proof | A | 是 | 不能升格成 adoption-grade |
| Platform security capability | `unverified` + 部分 disabled | explicit current-proof | A | 是 | WS3 主对象 |
| Docs control plane | strong | semantic fail-close | A | 是 | freshness 已有，语义还要再收紧 |
| CI governance | strong | 保持并减少误读 | A | 是 | required checks 对账 fresh PASS |
| External glue locality | 部分完成 | freeze + selective hard cut | B | 是 | 只在能改变判断时继续做 |
| Repo-level upstream/fork | N/A | N/A | A | 否 | 不引入伪议题 |

## [四] 根因与完成幻觉总表

| 根因 / 幻觉 | 表面信号 | 真实问题 | 对应动作 | 防回潮 Gate |
| --- | --- | --- | --- | --- |
| `RC1` Commit-proof 与 live workspace proof 被混读 | 有 strict PASS、current-proof alignment PASS | newcomer 总状态仍 partial，当前未提交工作树未 fully proved | WS1 Current-Proof Closure | `render_newcomer_result_proof.py` + `check_newcomer_result_proof.py` |
| `RC2` External/public 的最终可信度受平台能力控制 | 仓库 public、workflow 存在、release readiness READY | GHCR write 权限未闭环，public distribution 不可信 | WS2 GHCR Closure | `check_standard_image_publish_readiness.sh` + external workflow proof |
| `RC3` 平台安全能力只写了 policy，没拿到 live-proof | SECURITY.md、public docs 齐全 | PVR 仍 unverified，security_and_analysis 部分 disabled | WS3 Platform Security Proof | `probe_remote_platform_truth.py` + security freshness receipts |
| `RC4` docs/CI/current-truth 虽强，但语义仍可能混层 | generated docs 很齐、runtime reports 很多 | ready/verified、repo-side/external、pointer/current verdict 仍可能被误读 | WS4 Semantic Fail-Close | `check_docs_governance.py` + current-state rendering tests |
| `RC6` current-proof contract 仍把关键 external/current artifacts 设成 optional | current-state summary 已经很诚实 | 缺关键 external/current-proof artifact 时仍可能只降级展示，而不是 fail-close | WS4 扩 current-proof contract 语义 | `config/governance/current-proof-contract.json` + current-proof checks |
| `RC5` 架构 hard-cut 已有成果，但继续切错地方会变成美化工程 | integrations/providers 已经开始收口 | 剩余 low-value glue 再切不一定改变成熟判断 | WS5 Freeze + Selective Hard Cut | `check_dependency_boundaries.py` |
| `IL1` Governance PASS = Done | `governance-audit PASS` | 只证明控制面站稳 | WS4 强化 done-model / newcomer proof 语义 | `done-model.md` + `check_newcomer_result_proof.py` |
| `IL2` Ready = Verified | readiness 文件存在 | workflow verified 与 readiness ready 不是一回事 | WS4 继续拆语义 | `external-lane-status.md` + current-state summary tests |
| `IL3` Public repo = public distribution ready | repo 已 public | GHCR blocked, external lane 未闭环 | WS2 | GHCR readiness gate |
| `IL4` SECURITY.md = private intake 已可用 | SECURITY.md 在仓 | PVR 仍 unverified | WS3 | `remote-platform-truth.json` |
| `IL5` repo-side strict wrapper = release-grade strict | `bin/repo-side-strict-ci` 有 PASS | 它是 repo-side lane wrapper，不是 external release proof | WS4 | docs semantics + current-state rules |

## [五] 绝不能妥协的红线

- 不再允许把 `governance-audit PASS` 写成 repo-side done。
- 不再允许把 `repo_side_strict_receipt=pass` 写成“当前 live workspace 已 fully proved”。
- 不再允许把 `ready` 写成 `verified`。
- 不再允许 tracked docs 继续承载 current external verdict。
- 不再允许因为 `SECURITY.md` 存在就默认 private vulnerability reporting 已启用。
- 不再允许外部 provider / binary / platform glue 新增在 `apps/*` 内部实现里。
- 不再允许为 GHCR/public/security 问题引入长期兼容层。
- 不再允许把 `.agents/Plans/*` 这类 planning artifact 的 dirty-state 语义静默抹掉。
- 不再允许把 repo-level upstream/fork merge/rebase 议题带回主路线。

## [六] Workstreams 总表

| Workstream | 目标 | 关键改造对象 | 删除/禁用对象 | Done Definition | 优先级 |
| --- | --- | --- | --- | --- | --- |
| `WS1` Current-Proof Closure | 把 live workspace 从 `partial` 拉到真正 current-proof | `newcomer-result-proof`, `current-state-summary`, current-proof runbook, worktree-proof discipline | 禁用 partial 冒充 pass 的所有叙事 | clean worktree + fresh repo-side strict + newcomer top-level `pass` | `P0` |
| `WS2` GHCR External Distribution Closure | 把 GHCR lane 从 blocked 推到 current-head verified | GHCR readiness script, image publish workflow, external-lane summary, strict contract image lane | 禁用 public repo=distribution ready 的旧口径 | local readiness PASS + remote current-head workflow verified + lane=verified | `P0` |
| `WS3` Platform Security Proof Closure | 把平台安全边界从文档姿态变成 live-proof | remote platform probe, SECURITY/public docs, open-source freshness receipts, env-governance | 禁用 unverified capability 被写成 enabled | PVR / security features current-proof 化 | `P0` |
| `WS4` Docs / CI / Current-Truth Semantic Hard Cut | 让 docs/CI/current-truth 语义 fail-close | docs control plane, generated docs, semantic guards, lane rendering tests | 禁用 tracked docs 承载 current verdict / ready-verified 混读 | docs semantic assertions green，误读入口收敛 | `P1` |
| `WS5` External Glue Locality Freeze + Selective Hard Cut | 只在能改变治理判断的边界继续收口 | `apps/worker/**`, `integrations/providers/**`, architecture docs, dependency boundary guards | 禁用装饰性收口、禁用继续扩大战线 | no new direct glue in apps；仅高价值 residual slice 被处理 | `P2` |

## [七] 详细 Workstreams

### `WS1` Current-Proof Closure

**目标**

- 把当前 `newcomer-result-proof.status=partial` 拉到 `pass`。
- 让“当前 live workspace 已证明”这句话第一次可以被诚实说出口。

**为什么它是结构性动作**

- 这一步不做，所有 repo-side 绿灯都只能证明 commit-level history，不足以证明当前工作状态。
- 它直接决定“我们现在是在说当前状态，还是在拿历史收据说现在”。

**输入**

- `.runtime-cache/reports/governance/newcomer-result-proof.json`
- `.runtime-cache/reports/governance/current-state-summary.md`
- `.runtime-cache/reports/governance/current-proof-commit-alignment.json`
- `git status --short`
- `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`

**输出**

- clean worktree proof receipt
- fresh `newcomer-result-proof.json` top-level `status=pass`
- fresh `current-state-summary.md` no dirty-worktree caveat

**改哪些目录 / 文件 / 配置 / gate**

- `scripts/governance/render_newcomer_result_proof.py`
- `scripts/governance/check_newcomer_result_proof.py`
- `scripts/governance/render_current_state_summary.py`
- `docs/reference/newcomer-result-proof.md`
- `docs/reference/done-model.md`
- 运行 gate：
  - `python3 scripts/governance/check_current_proof_commit_alignment.py`
  - `python3 scripts/governance/check_docs_governance.py`
  - `./bin/governance-audit --mode audit`
  - `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`

**删除 / 禁用对象**

- 禁止任何地方把 `partial` 继续包装成“差不多 done”。
- 禁止 current-state summary 在 dirty-worktree 仍为真时省略 dirty note。

**迁移桥**

- 短期允许 `partial` 继续存在，但只作为 planning / in-flight execution 状态。
- 不允许把它当完成态对外复述。

**兼容桥删除条件**

- 当 worktree clean 且 newcomer top-level 为 `pass` 后，关于“当前工作树未 fully proved”的解释可以从 summary 主体中降级为历史注记。

**Done Definition**

- `git status --short` 只剩明确允许的状态，且不再触发 dirty-worktree 语义。
- `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` fresh PASS。
- `python3 scripts/governance/render_newcomer_result_proof.py && python3 scripts/governance/check_newcomer_result_proof.py` fresh PASS。
- `newcomer-result-proof.json.status == "pass"`。

**Fail Fast 检查点**

- 任何新的 untracked / unrelated modified path 再次出现，就停止宣传 current-proof closure。
- strict 任何长测或 dependency gate 再红，WS1 回退为“repo-side strict 再次失守”，不得跳过。

**它会打掉什么幻觉**

- `IL1`、`IL5`

**它会改变哪个上层判断**

- 从“repo-side 很强，但当前 live workspace 还没 fully proved”
- 变成“当前 live workspace 也已经拿到 repo-side current-proof”

---

### `WS2` GHCR External Distribution Closure

**目标**

- 把 GHCR 标准镜像 external lane 从 `blocked` 推到 `verified`。

**为什么它是结构性动作**

- 这是当前 external/public 可信度最硬的一块红灯。
- 不关掉这盏红灯，public repo 只能是 source-first，可审阅，但不能高信心主张 distribution closure。

**输入**

- `scripts/ci/check_standard_image_publish_readiness.sh`
- `.github/workflows/build-ci-standard-image.yml`
- `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
- `.runtime-cache/reports/governance/external-lane-workflows.json`
- `.runtime-cache/reports/governance/current-state-summary.md`
- `infra/config/strict_ci_contract.json`

**输出**

- local readiness PASS
- remote current-head build-ci-standard-image workflow verified
- GHCR lane in current-state summary = verified
- upstream/external image row 不再是 pending/blocked

**改哪些目录 / 文件 / 配置 / gate**

- `scripts/ci/check_standard_image_publish_readiness.sh`
- `.github/workflows/build-ci-standard-image.yml`
- `docs/reference/external-lane-status.md`
- `docs/start-here.md`
- `docs/runbook-local.md`
- `README.md`
- `ENVIRONMENT.md`
- `scripts/governance/probe_external_lane_workflows.py`
- `scripts/governance/render_current_state_summary.py`

**删除 / 禁用对象**

- 禁止把“package API 可见”当成“blob write 可用”。
- 禁止把本机 GH auth 成功读仓库信息，写成 GHCR packages write 已闭环。
- 禁止本地 readiness 与 remote current-head workflow 失败层级混成一条模糊状态。

**迁移桥**

- 在 GHCR 仍 blocked 期间，保留双层状态：
  - `local readiness`
  - `remote workflow result`
- 但 bridge 只用于解释失败层级，不用于降级成功标准。

**兼容桥删除条件**

- 一旦 local readiness PASS 且 remote current-head workflow verified，删除 blocked/ready 过渡叙事，直接以 `verified` 为唯一有效状态。

**Done Definition**

- `./scripts/ci/check_standard_image_publish_readiness.sh` fresh PASS。
- GHCR blob upload preflight 返回 success 语义。
- `build-ci-standard-image.yml` 对当前 HEAD 成功完成并产出可信 artifact。
- `current-state-summary.md` 中 `ghcr-standard-image = verified`。

**Fail Fast 检查点**

- 如果失败仍是 `packages write` / `blob HEAD 403`，停止 repo 内继续重构，直接转平台权限处置。
- 如果 workflow 不是 current HEAD，禁止把成功 run 升级为 current verified。

**它会打掉什么幻觉**

- `IL2`、`IL3`

**它会改变哪个上层判断**

- 从“public source-first engineering repo”
- 变成“public repo + external image distribution current-head verified”

---

### `WS3` Platform Security Proof Closure

**目标**

- 让平台安全边界从“文档姿态”升级为“live probe 证明过的当前状态”。

**为什么它是结构性动作**

- 这是 open-source readiness 的关键一票。
- 现在的风险不是“没有 SECURITY.md”，而是“有 SECURITY.md 却还无法证明平台私密报告能力当前可用”。

**输入**

- `.runtime-cache/reports/governance/remote-platform-truth.json`
- `.runtime-cache/reports/governance/open-source-audit-freshness.json`
- `SECURITY.md`
- `docs/reference/public-repo-readiness.md`
- `docs/reference/public-rights-and-provenance.md`
- `.github/workflows/env-governance.yml`
- `scripts/governance/probe_remote_platform_truth.py`
- `scripts/governance/check_open_source_audit_freshness.py`

**输出**

- 平台安全能力 current-proof
- PVR 状态明确且可重复 probe
- open-source audit receipts 对齐当前 HEAD

**改哪些目录 / 文件 / 配置 / gate**

- `scripts/governance/probe_remote_platform_truth.py`
- `scripts/governance/check_open_source_audit_freshness.py`
- `SECURITY.md`
- `docs/reference/public-repo-readiness.md`
- `docs/reference/public-rights-and-provenance.md`
- `docs/reference/public-privacy-and-data-boundary.md`
- `.github/workflows/env-governance.yml`

**删除 / 禁用对象**

- 禁止把 `unverified` 写成 `enabled`。
- 禁止复用旧 commit 的 gitleaks / security receipts 当 current-head proof。

**迁移桥**

- 若组织侧暂时不能启用 PVR，允许状态为 `disabled`，但必须是 live-proved `disabled`，不是 `unverified`。
- `unverified` 只允许短暂存在于“probe 尚未拿到明确结果”的窗口，不允许作为长期公开叙事。

**兼容桥删除条件**

- 当 PVR 与关键 security_and_analysis feature 拿到明确 current-proof 后，删除 `unverified` 叙事与占位提醒。

**Done Definition**

- `probe_remote_platform_truth.py` fresh 运行后，PVR 变为显式 `enabled` 或显式 `disabled`。
- `open-source-audit-freshness.json` 全部对齐当前 HEAD。
- public/security 文档不再需要靠“如果最新 probe 这样那样”来兜底当前缺证状态。

**Fail Fast 检查点**

- 只要 probe 仍返回 `unverified`，就不能升级 public security claim。
- 只要 open-source freshness 不对齐当前 HEAD，就不能宣称 current security proof。

**它会打掉什么幻觉**

- `IL4`

**它会改变哪个上层判断**

- 从“可谨慎公开”
- 变成“更安全、更诚实、平台能力被 current-proof 化的公开仓”

---

### `WS4` Docs / CI / Current-Truth Semantic Hard Cut

**目标**

- 把 docs / CI / current-truth 的语义从“freshness 正确”升级成“语义误读也会失败”。

**为什么它是结构性动作**

- 这个仓库不缺文档，也不缺 gate。
- 它真正缺的是：**让错误解释也自动撞墙**。

**输入**

- `config/docs/boundary-policy.json`
- `config/docs/render-manifest.json`
- `config/docs/change-contract.json`
- `config/governance/current-proof-contract.json`
- `scripts/governance/check_docs_governance.py`
- `scripts/governance/render_docs_governance.py`
- `scripts/governance/check_remote_required_checks.py`
- `scripts/governance/render_current_state_summary.py`
- `docs/generated/*.md`
- `.github/workflows/ci.yml`
- `.runtime-cache/reports/governance/remote-required-checks.json`

**输出**

- docs semantic assertions 更强
- CI/required-checks/summary 读法不再靠人脑记忆
- lane semantics 不再混层

**改哪些目录 / 文件 / 配置 / gate**

- `config/governance/current-proof-contract.json`
- `scripts/governance/check_docs_governance.py`
- `scripts/governance/render_docs_governance.py`
- `scripts/governance/check_remote_required_checks.py`
- `scripts/governance/render_current_state_summary.py`
- `docs/generated/ci-topology.md`
- `docs/generated/required-checks.md`
- `docs/generated/release-evidence.md`
- `docs/reference/external-lane-status.md`
- `docs/reference/done-model.md`
- `docs/reference/newcomer-result-proof.md`
- 必要时补 tests 到：
  - `apps/worker/tests/test_external_proof_semantics.py`
  - `apps/worker/tests/test_docs_governance_control_plane.py`
  - `apps/worker/tests/test_ci_workflow_strictness.py`

**删除 / 禁用对象**

- 禁止 tracked docs 承载 current external verdict。
- 禁止 `ready`/`verified` 同词不同义。
- 禁止 `repo-side wrapper` 被写成 external/release-grade evidence。
- 禁止把 `remote-required-checks PASS` 误读成 terminal CI current closure。
- 禁止 current-proof contract 对关键 external/current artifact 长期保持“缺了也只是 optional”的宽松语义。

**迁移桥**

- 允许保留 pointer 文档。
- 但 pointer 文档只能解释读法，不能重复承载 current payload。
- `remote-required-checks` 允许继续只覆盖 aggregate-required-check integrity，但在迁移期必须明确写出“它不证明 `ci-final-gate/live-smoke/nightly terminal closure`”。
- current-proof contract 在迁移期允许保留少量 optional artifact，但必须把关键 external/current verdict surfaces 升成 blocker-classified required set。

**兼容桥删除条件**

- 所有高漂移 current-state 内容都移出 tracked docs 后，删除任何历史遗留 current payload 片段。

**Done Definition**

- `python3 scripts/governance/check_docs_governance.py` fresh PASS。
- `python3 scripts/governance/check_remote_required_checks.py` 仍 PASS，且解释面不再把它等同于 terminal CI closure。
- `config/governance/current-proof-contract.json` 对关键 external/current verdict artifact 的 required/blocker 语义已经升级。
- 关键 generated docs 与 runtime summary 的语义断言测试 fresh PASS。
- 入口文档没有会把 repo-side / external / current-proof 混为一谈的句子。

**Fail Fast 检查点**

- 只要当前态还能被 tracked docs 直接承载，WS4 不算 done。
- 只要 summary 还能写出模糊 blocked 描述而不分 local vs remote 层级，WS4 不算 done。
- 只要 `remote-required-checks PASS` 仍会被人误读成 terminal CI closure，WS4 不算 done。
- 只要 current-proof contract 还允许关键 external/current artifact 缺席而不触发 fail-close/blocker 语义，WS4 不算 done。

**它会打掉什么幻觉**

- `IL1`、`IL2`、`IL5`

**它会改变哪个上层判断**

- 从“文档很多、规则很多”
- 变成“错误读法也会被机器打回”

---

### `WS5` External Glue Locality Freeze + Selective Hard Cut

**目标**

- 不再为了好看继续大扫除。
- 只在“能显著改变架构成熟判断”的 residual slice 上继续 hard cut。

**为什么它是结构性动作**

- 到这一步，继续无差别收口很容易变成美化工程。
- 真正值钱的是：守住“所有新 external glue 都必须进 integrations”，并只补剩余高价值违规面。

**输入**

- `docs/reference/architecture-governance.md`
- `config/governance/module-ownership.json`
- `scripts/governance/check_dependency_boundaries.py`
- `scripts/governance/check_contract_locality.py`
- 当前 `apps/worker/**` 与 `integrations/providers/**` 的 residual direct glue

**输出**

- no-new-glue discipline
- selective residual hard cut
- architecture docs 与 code reality 持续一致

**改哪些目录 / 文件 / 配置 / gate**

- `apps/worker/**`
- `integrations/providers/**`
- `docs/reference/architecture-governance.md`
- `scripts/governance/check_dependency_boundaries.py`
- `scripts/governance/check_contract_locality.py`

**删除 / 禁用对象**

- 禁止继续在 `apps/*` 增加新的 direct external API/binary/platform glue。
- 禁止为了“全都收口到 integrations”而切动 orchestration 主体。

**迁移桥**

- 对已经存在、但价值低且 blast radius 高的旧薄封装，允许暂留，只要 boundary gate 不再放新债。

**兼容桥删除条件**

- 只在某 residual slice 同时满足“高价值 + 低 blast-radius + 会改变成熟判断”时，才把它列入下一轮实施。

**Done Definition**

- `check_dependency_boundaries.py` 与 `check_contract_locality.py` 持续 PASS。
- 新增功能不再把 external glue 散落回 apps 层。
- 剩余 residual slice 有明确 freeze 决策，而不是模糊悬而不决。

**Fail Fast 检查点**

- 若下一刀收口不能改变上层判断，只能列为 enhancement，禁止进入主路线。

**它会打掉什么幻觉**

- “目录更整齐 = 更成熟”

**它会改变哪个上层判断**

- 从“架构治理很强但还可能回流”
- 变成“边界已经制度化，剩余收口不是主风险”

## [八] 硬切与迁移方案

### 立即废弃项

- 把 `partial` 说成“差不多 done”的所有叙事。
- 把 `ready` 说成 `verified` 的所有叙事。
- 把 public repo 说成 public distribution ready 的所有叙事。
- 把 `SECURITY.md` 说成 private reporting 已启用的所有叙事。
- 任何新的 `apps/*` direct external glue。

### 迁移桥

- `partial` 状态可以作为 planning / in-flight 执行中的诚实状态继续存在，但不能升级成完成态。
- GHCR external lane 在本机 readiness 与远端 workflow 双层状态都未 verified 前，允许保留“local readiness / remote workflow”双层表述。
- 平台安全能力在未拿到明确 `enabled|disabled` 前，允许短期维持 `unverified`，但只在 probe 视角里出现，不进入对外能力陈述。

### 禁写时点

- 从下一轮执行开始，禁止再往 `apps/*` 增加新的 provider/binary/platform glue。
- 从 WS4 启动开始，禁止再把 current external verdict 写进 tracked docs。
- 从 WS1 启动开始，禁止再用 dirty-worktree 下的 receipts 升级 current-proof 口径。

### 删除时点

- WS1 done 后，删除所有“当前工作树未 fully proved”的过渡性强调语句，只在历史记录中保留。
- WS2 done 后，删除 GHCR blocked 过渡口径与 blob-403 解释。
- WS3 done 后，删除 `unverified` 安全能力占位叙事。
- WS4 done 后，删除 tracked docs 中所有 current payload 遗留片段。

### 防永久兼容机制

- 每个 bridge 都必须绑定删除条件。
- 每个 current-state 解释都必须绑定 runtime artifact，而不是 docs 文案。
- 每个 external/public/security claim 都必须要求 current-head same-run evidence。

## [九] 验证闭环与 Gate

| 维度 | 验证项 | Gate / 命令 / CI / Policy | 通过条件 | 未通过意味着什么 |
| --- | --- | --- | --- | --- |
| README / 项目定位 | 公开姿态与真实能力对齐 | `python3 scripts/governance/check_docs_governance.py` + 人工 spot check `README.md` / `project-positioning.md` | 不再混淆 source-first 与 adoption-grade | 叙事仍在制造含金量/公开成熟幻觉 |
| current-proof | newcomer 总状态从 partial 变 pass | `python3 scripts/governance/render_newcomer_result_proof.py && python3 scripts/governance/check_newcomer_result_proof.py` | top-level `status=pass` | 当前 live workspace 仍未 fully proved |
| repo-side strict | deepest repo-side gate 继续为绿 | `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` | fresh PASS | repo-side 重新失守，主路线必须回退 |
| docs 是事实源而非宣传册 | control plane / render / pointer 语义分层成立 | `python3 scripts/governance/check_docs_governance.py` | render freshness + semantic assertions 同时通过 | docs 仍会制造 current-truth 幻觉 |
| CI 绿灯可信 | required checks 与 branch protection 一致 | `python3 scripts/governance/check_remote_required_checks.py` | expected=actual 且 no missing | CI 绿灯覆盖关键判断不完整 |
| root allowlist | 根目录无未知项 | `./bin/governance-audit --mode audit` | root allowlist / layout budget / zero unknowns PASS | root cleanliness 只是表面整齐 |
| dirty-root / dirty-worktree | 当前 proof 是否真的 current | `git status --short` + newcomer/current-state artifacts | clean or explicitly partial | current-proof 仍不可升级 |
| cache 全删可重建 | runtime cache 不是事实源 | `./bin/governance-audit --mode audit` + runtime-cache retention/freshness 子 gate | freshness/retention green | 旧 artifact 仍可能冒充 current truth |
| 输出路径合法 | runtime outputs 不污染源码树 | `./bin/governance-audit --mode audit` | runtime-outputs/source-runtime-residue PASS | 运行时噪音治理失守 |
| 日志 schema / correlation | 日志能诊断不是摆设 | `./bin/governance-audit --mode audit` | logging-contract/log-correlation PASS | logger 只是存在，不可诊断 |
| evidence/report 分层 | tracked docs 不承载 current payload | docs semantic checks + `render_current_state_summary.py` tests | pointer / current runtime 分层清楚 | ready/verified/current 混读 |
| dependency boundary / contract-first | external glue 不再回流 apps | `python3 scripts/governance/check_dependency_boundaries.py` + `check_contract_locality.py` | PASS | 架构 hard-cut 只是口号 |
| GHCR external lane | standard image 当前 HEAD verified | `./scripts/ci/check_standard_image_publish_readiness.sh` + remote workflow current-head success | readiness PASS + workflow verified | public distribution 仍 blocked |
| platform security capability | PVR/security features current-proof | `python3 scripts/governance/probe_remote_platform_truth.py` + `check_open_source_audit_freshness.py` | explicit status + fresh receipts | 公开安全能力仍靠猜 |
| upstream inventory / compatibility | third-party governance current and bounded | `./bin/governance-audit --mode audit` + upstream sub-gates | freshness/same-run/current semantics all green | 上游兼容治理只停留在台账存在 |

## [十] 执行时序总表

| 阶段 | 动作 | 前置条件 | 并行性 | 完成标志 | 风险 |
| --- | --- | --- | --- | --- | --- |
| `Phase-A` | 冻结主路线语义，确认 WS1/WS2/WS3 为唯一前三优先级 | 本 Plan 落盘 | 低 | 决策日志固定 | 若继续争论 archetype 或旧 blocker，会拖慢主路线 |
| `Phase-B` | 执行 WS1：clean worktree + fresh repo-side current-proof | 不新增无关改动 | 可与 WS4 部分并行 | newcomer top-level `pass` | planning artifacts / in-flight edits 继续制造 dirty 状态 |
| `Phase-C` | 执行 WS2：GHCR auth/ACL/write path closure | WS1 不必全完，但 repo-side strict 必须继续为绿 | 仅平台处置与 repo-side preflight 可并行 | GHCR lane current-head verified | 若平台权限未补齐，repo 内继续改不会有收益 |
| `Phase-D` | 执行 WS3：platform security proof closure | WS1 已明确 current-proof discipline；WS2 可并行推进 | 可并行 | PVR/security features current-proof 化 | 组织/平台策略可能拖慢 |
| `Phase-E` | 执行 WS4：semantic fail-close | WS1/WS2/WS3 的真实语义已基本稳定 | 可并行但以 WS1-3 真相为输入 | docs/CI/current-truth 语义 hard cut 成立 | 若前 3 条线还在漂，语义 hard-cut 会写死错话 |
| `Phase-F` | 执行 WS5：freeze residual glue / selective hard cut | 前 4 条线已稳定 | 串行、低优先 | no new glue discipline 成立 | 若太早做，会变成装饰性工程 |

## [十一] 改造动作 -> 上层判断改变 映射表

| 动作 | 改变什么判断 | 为什么 |
| --- | --- | --- |
| WS1 把 newcomer 从 partial 拉到 pass | “当前 live workspace 是否真的被证明” | 这直接消灭 commit-proof 与 live-proof 混读 |
| WS2 关闭 GHCR blocked | “仓库能不能安全对外分发标准镜像” | external/public 最硬 blocker 被打掉 |
| WS3 让 PVR/security features current-proof 化 | “开源是否安全” | 有 SECURITY.md 不再只是姿态，而是平台能力被证明 |
| WS4 把 docs/CI/current-state 语义 fail-close | “文档与 CI 是否可信” | 错误读法也会失败，可信度显著上升 |
| WS5 冻结 residual glue 扩张 | “架构治理是否达标” | 边界从倡议变成纪律 |

## [十二] 如果只允许做 3 件事，先做什么

### 1. 先做 `WS1` Current-Proof Closure

- **为什么是第 1 件**
  - 不先解决 partial，任何“当前状态很好”的说法都不够诚实。
- **打掉什么幻觉**
  - 打掉“有 repo-side receipt 就等于当前工作树已 fully proved”。
- **释放什么能力**
  - 释放后续 WS2/WS3 的复述可信度。

### 2. 再做 `WS2` GHCR External Distribution Closure

- **为什么是第 2 件**
  - 这是 external/public 最大 blocker，且不是再写几份文档能解决的。
- **打掉什么幻觉**
  - 打掉“public repo = public distribution ready”。
- **释放什么能力**
  - 释放 external lane verified，改变公开成熟判断。

### 3. 再做 `WS3` Platform Security Proof Closure

- **为什么是第 3 件**
  - 安全能力如果只停留在文档姿态，开源 readiness 永远有缺口。
- **打掉什么幻觉**
  - 打掉“有 SECURITY.md = private intake 已可用”。
- **释放什么能力**
  - 释放更强的 open-source / public-safety 判断。

## [十三] 不确定性与落地前核对点

### 高置信事实

- `./bin/governance-audit --mode audit` fresh PASS
- `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 当前已有 pass receipt
- `newcomer-result-proof.json` 当前 top-level 为 `partial`
- `check_standard_image_publish_readiness.sh` 当前 fresh FAIL
- `remote-platform-truth.json` 当前 PVR 为 `unverified`

### 中置信反推

- residual external glue 再继续大面积 hard cut 的收益已经低于前三条主路线
- docs semantic hard-cut 会显著降低维护税与误读成本

### 落地前要二次核对的点

- WS1 执行时，dirty paths 里哪些是 intentional in-flight edits，哪些是 planning artifacts，哪些是真正应清理的 residue
- WS2 执行时，组织级 GHCR package ownership / ACL 的实际权限变更入口
- WS3 执行时，PVR/security_and_analysis 能否由当前 actor 直接启用，还是需要更高权限

### 但不因此逃避的设计结论

- 主路线依然唯一：`WS1 -> WS2 -> WS3 -> WS4 -> WS5`
- 不确定性只影响具体执行细节，不影响主路线顺序

## [十四] 执行准备状态

### Current Status

- Repo archetype：`hybrid-repo`
- Repo positioning：`public source-first + limited-maintenance + owner-level candidate`
- Repo-side governance：green
- Repo-side strict receipt：green
- newcomer overall：`partial`
- GHCR external lane：blocked
- release evidence lane：ready + current-head verified
- platform security capability：`unverified` / partial disabled

### Next Actions

1. 先把 dirty-worktree / partial current-proof 关掉
2. 再直攻 GHCR packages write / blob upload / current-head workflow verified
3. 再把平台安全能力与 open-source freshness current-proof 化

### Decision Log

- 维持 `hybrid-repo` 判断，但明确不是胶水仓
- 放弃 repo-level upstream/fork 路线图
- 维持 source-first posture，不升格成 adoption-grade 叙事
- 把前三优先级固定为：`WS1, WS2, WS3`
- 把 architecture locality 收口降为第 5 优先级，只做 selective hard cut

### Validation Log

- `git status --short --branch` 显示当前工作树 dirty
- `python3 scripts/governance/check_current_proof_commit_alignment.py` -> PASS
- `./bin/governance-audit --mode audit` -> PASS
- `python3 scripts/governance/check_remote_required_checks.py` -> PASS
- `python3 scripts/release/check_release_evidence_attest_readiness.py --release-tag v0.1.0` -> READY
- `./scripts/ci/check_standard_image_publish_readiness.sh` -> FAIL (`no token path with packages write capability detected`)

### Risk / Blocker Log

- `RB-01`: current-proof 仍 partial
- `RB-02`: GHCR packages write / blob upload 权限未闭环
- `RB-03`: PVR / security_and_analysis 当前未形成 current-proof
- `RB-04`: docs/CI/current-state 语义若不继续 hard-cut，完成幻觉会回潮

### Files Planned To Change

- `scripts/governance/render_newcomer_result_proof.py`
- `scripts/governance/check_newcomer_result_proof.py`
- `scripts/governance/render_current_state_summary.py`
- `scripts/ci/check_standard_image_publish_readiness.sh`
- `.github/workflows/build-ci-standard-image.yml`
- `scripts/governance/probe_remote_platform_truth.py`
- `scripts/governance/check_open_source_audit_freshness.py`
- `scripts/governance/check_docs_governance.py`
- `scripts/governance/render_docs_governance.py`
- `docs/reference/done-model.md`
- `docs/reference/external-lane-status.md`
- `docs/reference/public-repo-readiness.md`
- `SECURITY.md`
- `README.md`
- `docs/start-here.md`
- `docs/runbook-local.md`
- `docs/generated/ci-topology.md`
- `docs/generated/release-evidence.md`
- `apps/worker/tests/test_external_proof_semantics.py`
- `apps/worker/tests/test_docs_governance_control_plane.py`
- `apps/worker/tests/test_ci_workflow_strictness.py`
