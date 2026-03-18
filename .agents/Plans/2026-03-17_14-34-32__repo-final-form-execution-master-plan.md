# [🧭] Repo 终局总 Plan

## Plan Meta

- Created: `2026-03-17 14:34:32 America/Los_Angeles`
- Last Updated: `2026-03-17 18:31:00 America/Los_Angeles`
- Repo: `/Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取`
- Repo Archetype: `hybrid-repo`
- Execution Status: `In Progress`
- Current Phase: `Execution / WS2 GHCR Repo-side Fail-Close + Platform Blocker Isolation`
- Current Workstream: `WS2`
- Source Of Truth: `本文件`

## Workstreams 状态表

| Workstream | 状态 | 优先级 | 负责人 | 最近动作 | 下一步 | 验证状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `WS1` Repo-side Strict Reclosure | `Verified` | `P0` | `L1 + implementer` | canonical `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 已 fresh PASS；随后 newcomer proof / current-state summary / current-proof alignment 也已 fresh 通过 | 保持 repo-side strict 绿灯，不再把旧 debug-build 或 Docker 阻塞口径当 current truth | `Verified (overall newcomer status remains partial because worktree dirty)` |
| `WS2` GHCR / External Distribution Closure | `In Progress` | `P0` | `L1` | external blocker 仍稳定指向 GHCR blob HEAD `403 Forbidden`；repo-side 现已补强 readiness preflight：新增 blob upload probe，并把 `GHCR_WRITE_*` / `GHCR_*` / `gh auth` 三层凭证优先级对齐到脚本、workflow 与文档 | 平台侧修 package ownership / ACL / write 权限；repo 内只保留 preflight/文档/current-state 的诚实强化 | `Repo-side fail-close strengthened; external unblock still platform-blocked` |
| `WS3` Open-source Security Proof Freshness | `Partially Completed` | `P1` | `L1 + implementer` | PVR explicit status、gitleaks freshness gate、env-governance 接线和文档收紧已落地，且本轮 fresh `check_open_source_audit_freshness.py`、`check_remote_required_checks.py`、`probe_remote_platform_truth.py` 全部通过 | 等远端 env-governance workflow / 平台能力仍可继续补强后，再决定是否将 WS3 提升为 Verified | `Partially Verified` |
| `WS4` Docs / Current-Truth Semantic Fail-Close | `Partially Completed` | `P1` | `L1` | 已修正生成脚本里的旧 `release-readiness` 混写，并把 dirty-worktree 语义补进 newcomer proof 与 current-state-summary，相关 gate fresh PASS | 继续扩 semantic assertions，避免类似旧路径再次回潮 | `Partially Verified` |
| `WS5` External Glue Locality Hard Cut | `Partially Completed` | `P2` | `L1 + implementer` | article fetch、RSS feed protocol helper、YouTube comments API glue、Bilibili comments API glue、provider health HTTP probe、YouTube transcript fallback helper 都已迁入 `integrations/providers/`；第六刀后 `check_dependency_boundaries.py`、`check_contract_locality.py`、`governance-audit` 继续 PASS | 低 blast-radius 六刀已完成；剩余要么是 orchestration 主体，要么是低价值薄封装，不再继续扩大战线 | `Low-blast-radius slice set verified; broader WS5 intentionally paused` |

## 任务清单

- `[-]` 接管上一轮 Plan 并校准 Repo 当前状态
  - 目标：确认本文件与 Repo current truth 一致
  - 变更对象：本 Plan 文件
  - 验证方式：`git status --short`、fresh gate、关键 artifact 复核
  - 完成证据：已确认 canonical strict red、GHCR blocked、release ready/verified split
- `[-]` 执行 `WS1`：修复 `pyasn1` 导致的 canonical strict 红灯
  - 目标：恢复 repo-side strict current PASS
  - 变更对象：`pyproject.toml`, `uv.lock`, 可能的依赖治理文档
  - 验证方式：`./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`
  - 完成证据：strict PASS + newcomer strict receipt PASS
  - 当前进度：已完成约束落地、锁文件升级、依赖治理文档联动、public docs 联动、third-party notices freshness 刷新、Docker 恢复、short-check blockers 修复；fresh canonical strict 已 PASS，并已刷新 newcomer/current-state/current-proof 收据
- `[-]` 执行 `WS3`：补 security/current-proof 的 repo 可做面
  - 目标：把 PVR/gitleaks 口径从姿态化推进到 current-proof 化
  - 变更对象：安全探针、security docs、freshness gate
  - 验证方式：fresh probe + fresh audit receipt
  - 当前进度：核心脚本、workflow、security/public docs 已落地，待与主线一起跑 fresh gate
- `[-]` 执行 `WS4`
  - 目标：把 docs/current-truth 的已知路径漂移从生成脚本层硬切掉
  - 变更对象：`scripts/governance/render_docs_governance.py` 及其产出的 `docs/generated/*`
  - 验证方式：`python3 scripts/governance/render_docs_governance.py` + `python3 scripts/governance/check_docs_governance.py`
  - 当前进度：release-readiness / release-evidence 路径混写已修，generated docs 已 fresh 重生并通过 gate
- `[-]` 执行 `WS2`：推进 GHCR/public distribution 闭环
  - 目标：把 GHCR lane 从 blocked 推到 verified
  - 变更对象：GHCR readiness script、workflow、平台配置说明
  - 验证方式：readiness PASS + workflow current-head verified
  - 当前进度：repo-side preflight 已补强 blob upload probe，但 external unblock 仍卡平台侧 package ownership / ACL / write 权限
- `[-]` 执行 `WS5`
  - 目标：把最后一个同等级低 blast-radius transcript fallback helper 收口到 `integrations/providers/`
  - 变更对象：`apps/worker/worker/pipeline/steps/subtitles.py`, `integrations/providers/youtube_transcript.py`
  - 验证方式：定向 pytest + orchestrator/runner contract tests + `ruff check`
  - 当前进度：helper 已迁入 provider，`subtitles.py` 保留编排并通过 fresh 定向验证；待和主线门禁一起完成总复核

## [一] 3 分钟人话版

现在这仓库最危险的地方，不是“它不成熟”，而是**它已经足够成熟，容易把人骗成以为全都闭环了**。

说得更直白一点：

- **Repo-side 治理很强**：`./bin/governance-audit --mode audit`、`current-proof` 对齐、远端 required checks 对账，这些都是真绿。
- **现在 canonical repo-side strict 已经 fresh 绿了**：`./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 已完整 PASS，但 `newcomer-result-proof` 仍保持 `partial`，因为当前工作树依然 dirty。
- **external/public 也还没闭环**：GHCR 标准镜像发布仍然 blocked，签名是 `no token path with packages write capability detected`。
- **开源安全证明也还不够 current-head**：`private vulnerability reporting` 没有被平台探针证实，`gitleaks` 两份 meta 还指向旧 commit。

所以这份 Plan 的唯一主路线不是“继续润色强项”，而是：

1. **先承认 repo-side strict 已回绿，但不要把 dirty-worktree 下的 `partial` 误读成 global done。**
2. **再打 GHCR/public distribution**，因为 external 最硬的门还卡在平台侧 blob write 权限。
3. **继续把安全证明和 current-truth 语义面做成 fail-close**，彻底拆掉假成熟。
4. **把外部 glue locality 收口停在高价值边界**，不为“看起来更整齐”继续扩大战线。

改完以后，仓库会从“强治理但有错觉窗口”，变成“repo-side、external、public、安全、语义 gate 都按层闭环，别人不容易再读错”。

必须这么硬的原因很简单：如果不硬切，旧的绿灯、旧的 ready、旧的 tracked docs、旧的安全口径，会一直把未来 Agent 和人类带回错误判断。

## [二] Plan Intake

结构化输入已就位：上游 `超级Review` 报告的 `## [十三、] 机器可读问题账本` YAML 账本已在上方上下文中。下方 `<structured_issue_ledger>` 已声明 `available`，并直接以该 YAML 中的 `issues` / `completion_illusions` / `top_3_priorities` 作为 Phase 1 账本的初始底稿，再用 Repo fresh 验证做增删改判。

```xml
<plan_intake>
  <same_repo>true</same_repo>
  <structured_issue_ledger>available</structured_issue_ledger>
  <input_material_types>
    - 超级Review 审计报告（上方输出，含 YAML 账本）
    - 当前 Repo fresh gate 结果
    - 当前 Repo tracked docs / runtime reports / workflows / governance control plane
    - 相关共享记忆（已用，但已用 fresh 本地证据重新校正）
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
    - runtime-owned current truth
  </validation_scope>
  <initial_claims>
    - repo-side 很强
    - external/public 主要 blocker 是 GHCR
    - docs/CI 治理成熟但控制面分布较广
    - upstream 更像第三方依赖治理，而不是 repo-level fork 治理
    - release evidence 存在 ready/verified 语义分裂
  </initial_claims>
  <known_conflicts>
    - 旧审计与旧记忆曾把 repo-side strict 视为 current green；fresh 复核一度证明 canonical strict red at `pip-audit(pyasn1/CVE-2026-30922)`，但本轮已重新闭环到 fresh PASS
    - 旧说法曾把 release evidence 读成只有 ready；fresh 复核显示 readiness 仍是 ready，但 remote workflow 对当前 HEAD 已 verified
    - 旧说法曾默认 SECURITY.md 链接代表 private vulnerability reporting 已启用；Repo 当前证据不支持
    - docs/generated 某些页仍引用旧 release-readiness 路径，而 current release truth 已转到 .runtime-cache/reports/release/
  </known_conflicts>
  <confidence_boundary>
    - 高置信 fresh：governance-audit PASS、current-proof alignment PASS、remote-required-checks PASS、release readiness READY、GHCR readiness FAIL、repo-side strict PASS
    - 中高置信 read-based：docs semantic gate coverage 不均、lane semantics 易误读、external glue locality 未完全收口到 integrations
    - 中置信推断：upstream row-level current-head alignment 仍不够 fail-close，需要通过 gate 扩展固化
  </confidence_boundary>
</plan_intake>
```

**Repo archetype**

- 结论：**`hybrid-repo`**
- 解释：业务内核是 repo-owned 的 `apps/ + contracts/ + infra/`，同时外部依赖治理、current-proof、runtime reports、docs control plane 也都已经进入主控制面，而不是附属物。

**当前最真实定位**

- `public source-first + limited-maintenance + dual completion lanes`
- 强工程型 applied AI mini-system
- 不是 adoption-grade 镜像优先产品

**最危险误判**

- 把 `governance-audit PASS`、`newcomer-result-proof pass`、公开仓库状态、release readiness 文件存在，一起误读成“repo-side + external/public 都闭环了”。

## [三] 统一判断总览表

| 维度 | 当前状态 | 目标状态 | 证据强度 | 是否适用 | 备注 |
| --- | --- | --- | --- | --- | --- |
| Repo archetype | `hybrid-repo` | 保持 | A | 是 | 不做 archetype 翻案，做边界硬化 |
| Repo-side governance | green | 保持 green | A | 是 | `./bin/governance-audit --mode audit` fresh PASS |
| Canonical repo-side strict | green | 保持 green | A | 是 | fresh canonical strict 已 PASS；但 dirty worktree 让 newcomer 总状态仍为 `partial` |
| Current-proof alignment | green | 更广覆盖 | A | 是 | 当前 5 个 artifact 对齐 HEAD，安全/open-source 还没纳入 |
| GHCR external lane | blocked | verified | A | 是 | 当前主 external blocker |
| Release evidence lane | split | split but explicit / then stable | A | 是 | `readiness=READY`，workflow=current HEAD verified |
| Public/open-source posture | 可谨慎公开 | current-proof 化 | A | 是 | posture 成立，证明还不够硬 |
| Private vulnerability reporting | unverified | explicit enabled/disabled/unverified | A | 是 | 当前不能默认已启用 |
| gitleaks security receipts | stale-current | current-head fresh | A | 是 | meta 指向旧 commit |
| Docs control plane | strong | semantic fail-close | A | 是 | control plane 成立，语义 gate 还不均匀 |
| CI governance | strong | 保持并减少误读 | A | 是 | required checks 远端对账已绿 |
| Upstream governance | strong but not row-level current-head fail-close | stronger | B | 是 | freshness/same-run 已有，row-level current-head 还需补 |
| Repo-level upstream/fork 审计 | N/A | N/A | A | 否 | 不应该再引入 merge/rebase 叙事 |
| Architecture locality | 部分成立 | 代码真相收口 | B | 是 | worker 里仍有 external glue |

## [四] 根因与完成幻觉总表

| 根因 / 幻觉 | 表面信号 | 真实问题 | 对应动作 | 防回潮 Gate |
| --- | --- | --- | --- | --- |
| `RC1` Repo-side strict 仍可能被新供应链/联动门再次打断 | 旧 strict 收据是绿的 | canonical strict 曾 fresh 红在 `pip-audit`，说明 repo-side 仍需持续靠 deepest gate 说话 | WS1 升级 `pyasn1` 并重建 strict receipt | `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` |
| `RC2` External/public 依赖平台能力闭环 | 仓库已公开，workflow 也存在 | GHCR package auth 没闭环，PVR 未验证 | WS2 修 GHCR，WS3 补平台安全 truth | `check_standard_image_publish_readiness.sh` + `probe_remote_platform_truth.py` |
| `RC3` Current-truth 覆盖还不够 fail-close | current-proof alignment PASS | open-source audit、部分 generated docs、upstream row 仍有 stale/语义歧义 | WS3 + WS4 扩 current-proof / semantic gate | `check_current_proof_commit_alignment.py` + `check_docs_governance.py` + upstream gates |
| `RC4` 架构边界文字契约快于代码落点 | docs 写着 external glue 要进 integrations | worker 里还保留直接外部接线 | WS5 做 locality hard cut | `check_dependency_boundaries.py` 扩规则 |
| `IL1` Governance PASS = Done | `governance-audit PASS` | 只证明控制面站稳 | 文档与 gate 双重硬切 | `done-model.md` + `check_newcomer_result_proof.py` |
| `IL2` Ready = Verified | readiness 文件是 `ready` | workflow verified 与 readiness ready 是两回事 | release/GHCR 语义拆开 | `external-lane-status.md` + `render_current_state_summary.py` |
| `IL3` Generated docs = current truth | `docs/generated/*.md` 很齐 | 它们只是 pointer/reference，不是 runtime verdict | 当前态一律下沉 `.runtime-cache/reports/**` | `check_docs_governance.py` + `check_current_proof_commit_alignment.py` |
| `IL4` Public repo = public distribution ready | 仓库公开、LICENSE/SECURITY 都在 | GHCR blocked，安全证明不够 fresh | 先修 GHCR，再修 security proof | GHCR readiness + security freshness gate |
| `IL5` Repo-level upstream/fork 需要 merge/rebase 路线图 | 名字里有 upstream | 这个 repo 当前适用的是 third-party upstream governance | 删除 fork 叙事 | `upstream-governance.md` + `.git/config` |
| `IL6` repo-side strict wrapper = release-grade strict | `repo-side-strict-ci` 有 PASS 收据 | 它是 repo-side lane wrapper，不是 external/release qualification | 强化 lane semantics | `check_newcomer_result_proof.py` + README/start-here wording |

## [五] 绝不能妥协的红线

- 不能再保留“`governance-audit PASS` 就等于 repo-side done”的旧说法。
- 不能再保留“`ready` 可以被当成 `verified`”的旧说法。
- 不能再保留“仓库公开了，所以 public distribution 也差不多了”的旧说法。
- 不能再保留“有 `SECURITY.md` 链接，所以 private vulnerability reporting 已启用”的旧说法。
- 不能再复用旧 `gitleaks` meta 继续冒充 current-head 安全证明。
- 不能让 tracked docs 承载 current external verdict；current verdict 只允许在 `.runtime-cache/reports/**`。
- 不能新增未登记顶级输出路径。
- 不能让 `apps/*` 继续新增 direct external provider/binary/platform glue。
- 不能为了追求“看起来闭环”引入长期兼容层。
- 不能在 WS1 未绿之前，把 WS2/WS3 的完成包装成“仓库已 final form”。

## [六] Workstreams 总表

| Workstream | 目标 | 关键改造对象 | 删除/禁用对象 | Done Definition | 优先级 |
| --- | --- | --- | --- | --- | --- |
| `WS1` Repo-side Strict Reclosure | 把 canonical repo-side strict 拉回绿 | `pyproject.toml`, `uv.lock`, `scripts/governance/quality_gate.sh`, `docs/reference/dependency-governance.md`, `newcomer-result-proof` surfaces | 禁用旧 strict 绿收据继续冒充 current truth | fresh strict PASS + fresh newcomer strict receipt PASS | `P0` |
| `WS2` GHCR / External Distribution Closure | 把 GHCR lane 从 blocked 推到 current HEAD verified | `scripts/ci/check_standard_image_publish_readiness.sh`, `.github/workflows/build-ci-standard-image.yml`, `infra/config/strict_ci_contract.json`, external lane reports/docs | 禁用任何“public repo = public distribution ready”旧口径 | current HEAD GHCR verified | `P0` |
| `WS3` Open-source Security Proof Freshness | 把安全边界从 posture 变 current-head proof | `probe_remote_platform_truth.py`, `SECURITY.md`, public readiness docs, open-source audit receipts, env governance workflow | 禁用 legacy gitleaks / 未验证 PVR 叙事 | PVR 明确状态 + gitleaks current-head fresh | `P1` |
| `WS4` Docs / Current-Truth Semantic Fail-Close | 把分布式控制面从 freshness 升级到 semantic fail-close | `check_docs_governance.py`, `render_docs_governance.py`, `render_current_state_summary.py`, `render-manifest.json`, `change-contract.json`, generated docs | 禁用 tracked docs 承载 current verdict、禁用 ready/verified 混读 | generated docs 关键页语义受机器约束 | `P1` |
| `WS5` External Glue Locality Hard Cut | 把 external glue 从业务层收口回 integrations | `apps/worker/**`, `integrations/providers/**`, `dependency-boundaries` rules, architecture docs | 禁用 apps 层新增 direct external glue | worker 只保留编排，external glue 进入 integrations | `P2` |

## [七] 详细 Workstreams

### `WS1` Repo-side Strict Reclosure

**目标**

- 先把 canonical repo-side strict 拉回绿。
- 不解决这个红灯，后面的 GHCR/public/security work 都不能被包装成“只剩 external blocker”。

**为什么它是结构性动作**

- 它不是一条普通依赖告警，而是 canonical repo-side strict 的 fresh 红灯。
- 它直接决定 repo-side done 这层是否还成立。

**输入**

- fresh 命令：`./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`
- 当前失败签名：`pip-audit -> pyasn1 0.6.2 -> CVE-2026-30922 -> fix 0.6.3`
- 当前 HEAD：`40e0603372c1079c8dc699e49d80305b48af0b30`

**输出**

- 更新后的 Python 依赖锁
- fresh strict PASS 收据
- 刷新的 newcomer result proof
- 如果依赖升级影响 docs 契约，则同步更新 `docs/reference/dependency-governance.md`

**改哪些目录 / 文件 / 配置 / gate**

- `pyproject.toml`
- `uv.lock`
- `scripts/governance/quality_gate.sh`
- `scripts/ci/strict_entry.sh`
- `docs/reference/dependency-governance.md`
- `.runtime-cache/reports/governance/newcomer-result-proof.json`

**具体动作**

1. 确认 `pyasn1` 的引入链，明确是 direct 还是 transitive。
2. 如果是 transitive，升级拥有者包或加显式上界/下界约束，目标是锁到 `pyasn1>=0.6.3`。
3. 重建 `uv.lock`，确保不会引入新的 vulnerability 回归。
4. 重跑 canonical strict。
5. 重渲染 newcomer result proof，并复核 strict receipt 已指向当前 HEAD 的 fresh PASS。
6. 若依赖策略发生变化，补写 `docs/reference/dependency-governance.md`。

**删除哪些旧结构**

- 删除任何继续引用旧 strict 绿收据的叙事。

**迁移桥**

- 无长期兼容桥。
- 允许短期保留“旧收据 = historical only”的说明，但不得再作为 current truth 被引用。

**兼容桥删除条件与时点**

- 一旦 fresh strict PASS 和 newcomer result proof 重渲染完成，旧 strict 绿收据只保留历史价值，立即停止在任何当前总结中引用。

**Done Definition**

- `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` fresh PASS
- `python3 scripts/governance/render_newcomer_result_proof.py && python3 scripts/governance/check_newcomer_result_proof.py` PASS
- `newcomer-result-proof.json` 中 `repo_side_strict_receipt.status=pass`
- 没有新增 repo-side blocker

**Fail Fast 检查点**

- 若 `pyasn1` 升级引发大面积 API break，则先冻结 WS2-WS5，实现最小化依赖闭环后再继续。
- 若 strict 过了 `pip-audit` 但红到别的 gate，主路线仍停留在 WS1，不允许直接跳去 external。

**它会打掉什么幻觉**

- `IL1 governance PASS = done`
- `IL6 repo-side strict wrapper = release-grade strict`

**它会改变哪个上层判断**

- 把“repo-side strict 当前不可信”改回“repo-side strict fresh 可证”。

### `WS2` GHCR / External Distribution Closure

**目标**

- 把 `ghcr-standard-image` 从 `blocked(registry-auth-failure)` 推到 current HEAD `verified`。

**为什么它是结构性动作**

- 它是 external/public 最硬的真实 blocker。
- 它不闭环，public/open-source 叙事永远只能停在“可谨慎公开”，不能再往 adoption-ready 推。

**输入**

- `scripts/ci/check_standard_image_publish_readiness.sh`
- `.github/workflows/build-ci-standard-image.yml`
- `config/governance/external-lane-contract.json`
- `current-state-summary.md`

**输出**

- current HEAD GHCR workflow verified
- current HEAD GHCR readiness artifact not blocked
- current-state-summary 与 external lane docs 同步反映 verified，而不是 blocked

**改哪些目录 / 文件 / 配置 / gate**

- `scripts/ci/check_standard_image_publish_readiness.sh`
- `.github/workflows/build-ci-standard-image.yml`
- `infra/config/strict_ci_contract.json`
- `scripts/governance/probe_external_lane_workflows.py`
- `scripts/governance/render_current_state_summary.py`
- `docs/reference/external-lane-status.md`

**具体动作**

1. 明确标准镜像发布的唯一 auth 路径：`GHCR_WRITE_USERNAME` / `GHCR_WRITE_TOKEN` 或明确受支持的 fallback。
2. 在 readiness script 里把失败分类固化为：
   - token missing
   - token lacks `write:packages`
   - package ownership mismatch
   - buildx/runtime preparation failure
3. 在 workflow 中明确 GHCR login 的用户名、token 来源、失败日志。
4. 完成 GitHub 平台侧动作：
   - 修正 repo secrets
   - 修正 package ownership / package ACL
   - 确认当前 repo/actor 对目标 GHCR package 具备写权限
5. 在任何远端 GHCR rerun 前，先执行并通过本地 full pre-push 入口：
   - `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`
   - 若此命令仍红，先本地复现并修复，不允许直接重跑远端 workflow 碰运气。
6. 触发 current HEAD 的 `build-ci-standard-image.yml`。
7. 重跑 external lane workflow probe。
8. 重渲染 `current-state-summary.md`。

**删除哪些旧结构**

- 删除任何未在 `strict_ci_contract.json` 声明的替代 GHCR 仓库名、临时 tag、临时镜像叙事。

**迁移桥**

- 允许短期保留 `blocked(platform)` 状态。
- 不允许引入“先发布到别的临时 registry，再假装 GHCR 已闭环”的兼容桥。

**兼容桥删除条件与时点**

- GHCR current HEAD `verified` 后，删除所有临时 blocked workaround 叙事。

**Done Definition**

- `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 在 GHCR 修复后本地可通过
- `./scripts/ci/check_standard_image_publish_readiness.sh` 不再报 `registry-auth-failure`
- `.runtime-cache/reports/governance/external-lane-workflows.json` 中 `ghcr-standard-image.state=verified`
- `latest_run_head_sha == current HEAD`
- `current-state-summary.md` 的 GHCR lane 为 `verified`

**Fail Fast 检查点**

- 若本地 `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 未绿，禁止触发下一次远端 GHCR 验证性运行。
- 如果 readiness 仍报 `no token path with packages write capability detected`，立即停止 repo 内空转，改做平台 secret/ACL 修复。
- 如果 workflow 成功但 `headSha != current HEAD`，不得升级叙事。

**它会打掉什么幻觉**

- `IL2 ready = verified`
- `IL4 public repo = public distribution ready`

**它会改变哪个上层判断**

- 把“external/public blocked at GHCR”改成“distribution lane current-head verified”。

### `WS3` Open-source Security Proof Freshness

**目标**

- 把 public/open-source 安全边界从“姿态完整”推进到“current-head 真有 fresh proof”。

**为什么它是结构性动作**

- 现在最容易被误读的不是 license，而是“安全口径是否被平台和 fresh receipt 证明过”。

**输入**

- `SECURITY.md`
- `docs/reference/public-repo-readiness.md`
- `probe_remote_platform_truth.py`
- `.runtime-cache/reports/open-source-audit/*.meta.json`
- `.github/workflows/env-governance.yml`

**输出**

- PVR 状态成为显式字段：`enabled|disabled|unverified`
- gitleaks history/worktree 两份 meta 指向当前 HEAD
- public docs 只说 probe 证实过的能力

**改哪些目录 / 文件 / 配置 / gate**

- `scripts/governance/probe_remote_platform_truth.py`
- `SECURITY.md`
- `docs/reference/public-repo-readiness.md`
- `docs/reference/public-rights-and-provenance.md`
- `.github/workflows/env-governance.yml`
- 新增：`scripts/governance/check_open_source_audit_freshness.py`
- 新增：`bin/open-source-audit-refresh`

**具体动作**

1. 扩展 `probe_remote_platform_truth.py`，显式写出 private vulnerability reporting 状态，不允许默默缺项。
2. 新增 `check_open_source_audit_freshness.py`，验证：
   - `gitleaks-history.json.meta.json.source_commit == current HEAD`
   - `gitleaks-working-tree.json.meta.json.source_commit == current HEAD`
3. 新增 `bin/open-source-audit-refresh`，统一刷新 history + working-tree gitleaks receipts。
4. 把 env/security workflow 接上 open-source freshness check。
5. 收紧 `SECURITY.md` 和 public readiness wording：如果 probe 不支持，就明确写 `unverified`，不能写成“已可用”。

**删除哪些旧结构**

- 删除“legacy gitleaks receipt 仍可代表 current-head”的默契。
- 删除“有 security 链接就默认 private vulnerability reporting 已启用”的暗示。

**迁移桥**

- 允许短期文案使用 `unverified`。
- 不允许用模糊表述替代明确状态。

**兼容桥删除条件与时点**

- 一旦 PVR 被证实启用或明确禁用，对应文档立即改成确定状态，不再保留模糊措辞。

**Done Definition**

- `probe_remote_platform_truth.py` 产物出现 PVR 显式状态
- 两份 gitleaks meta 指向当前 HEAD
- `check_open_source_audit_freshness.py` PASS
- `SECURITY.md` / `public-repo-readiness.md` 无未证实能力叙事

**Fail Fast 检查点**

- 若 GitHub API 无法提供 PVR 能力信息，则状态必须写 `unverified`，不得自作主张升级为 `enabled`。
- 若 gitleaks 只能继续复用旧 receipt，则 public/security readiness 不得升级。

**它会打掉什么幻觉**

- `IL4 public repo = public distribution ready`
- `IL5 security docs 存在 = security capability verified`

**它会改变哪个上层判断**

- 把“公开但安全证明偏姿态化”改成“公开且安全口径 current-proof 化”。

### `WS4` Docs / Current-Truth Semantic Fail-Close

**目标**

- 把现在已经很强的 docs control plane，再往前推进一层，变成 semantic fail-close，而不是 freshness-only。

**为什么它是结构性动作**

- 当前最大维护税，不是没控制面，而是控制面分布广、语义覆盖不均匀。

**输入**

- `config/docs/render-manifest.json`
- `config/docs/change-contract.json`
- `scripts/governance/check_docs_governance.py`
- `scripts/governance/render_docs_governance.py`
- `scripts/governance/render_current_state_summary.py`
- `docs/generated/*.md`

**输出**

- `required-checks`、`runner-baseline`、`external-lane-snapshot` 的关键语义也受 gate 保护
- release/current truth 路径漂移消失
- repo-side/external/release/workflow 语义不再容易混读

**改哪些目录 / 文件 / 配置 / gate**

- `scripts/governance/check_docs_governance.py`
- `scripts/governance/render_docs_governance.py`
- `scripts/governance/render_current_state_summary.py`
- `config/docs/render-manifest.json`
- `config/docs/change-contract.json`
- `docs/generated/ci-topology.md`
- `docs/generated/runner-baseline.md`
- `docs/generated/required-checks.md`
- `docs/generated/external-lane-snapshot.md`
- `README.md`
- `docs/start-here.md`
- `docs/reference/done-model.md`
- `docs/reference/external-lane-status.md`

**具体动作**

1. 为关键 generated 页增加 semantic assertions，不只检查文件存在和 marker 新鲜。
2. 统一 current truth 路径：
   - current external verdict -> `.runtime-cache/reports/**`
   - tracked generated 页 -> pointer / explanation / reading rule
3. 修正 `ci-topology` / `runner-baseline` 里对旧 `release-readiness` 路径的残留。
4. 强化 newcomer / repo-side strict wrapper 的 lane semantics 说明：
   - repo-side receipt 可以是 repo-side canonical
   - 但不得被引用成 external/release-grade completion evidence
5. 如有必要，扩展 `check_newcomer_result_proof.py` 的 lane semantics 校验。

**删除哪些旧结构**

- 删除 tracked docs 中任何 current verdict payload。
- 删除 ready/verified 混写、repo-side/external 混写。

**迁移桥**

- `docs/generated/external-lane-snapshot.md` 保留为 pointer。
- `current-state-summary.md` 保留为 runtime-owned current summary。

**兼容桥删除条件与时点**

- 无需删除 pointer 机制；要删除的是 pointer 被当 current verdict 读的旧习惯。

**Done Definition**

- `check_docs_governance.py` 对关键 generated 页的语义断言通过
- generated docs 不再引用错误的 current-state 路径
- README/start-here/done-model 对 repo-side、external、ready、verified 的解释不再可混读

**Fail Fast 检查点**

- 任何 generated 页语义仍然能把 ready 说成 verified，则 WS4 未完成。
- 任何 tracked docs 仍承载 current external verdict，则 WS4 未完成。

**它会打掉什么幻觉**

- `IL2 ready = verified`
- `IL3 generated docs = current truth`

**它会改变哪个上层判断**

- 把“控制面很强但易误读”改成“控制面强且不易误读”。

### `WS5` External Glue Locality Hard Cut

**目标**

- 把 external provider/binary/platform glue 从 `apps/worker` 等业务层收口回 `integrations/`。

**为什么它是结构性动作**

- 这是“文档契约比代码落点更先进”的典型尾巴。
- 不收口，未来每次 provider 变更都更容易重新扩散到业务层。

**输入**

- `docs/reference/architecture-governance.md`
- `config/governance/dependency-boundaries.json`
- `apps/worker/worker/rss/fetcher.py`
- `apps/worker/worker/comments/youtube.py`
- `apps/worker/worker/comments/bilibili.py`
- `apps/worker/worker/pipeline/steps/article.py`
- `apps/worker/worker/temporal/activities_health.py`
- `integrations/providers/*.py`

**输出**

- `apps/*` 主要保留编排 / 领域逻辑
- `integrations/` 成为 external glue 唯一落点
- dependency boundary gate 对 direct external glue 更严格

**改哪些目录 / 文件 / 配置 / gate**

- `apps/worker/worker/rss/**`
- `apps/worker/worker/comments/**`
- `apps/worker/worker/pipeline/steps/article.py`
- `apps/worker/worker/temporal/activities_health.py`
- `integrations/providers/**`
- `config/governance/dependency-boundaries.json`
- `scripts/governance/check_dependency_boundaries.py`
- `docs/reference/architecture-governance.md`

**具体动作**

1. 逐类列出 direct external glue：
   - RSSHub
   - YouTube comments / platform fetch
   - Bilibili comments / platform fetch
   - article fetch / webpage fetch
   - provider health probes
2. 对每类 glue 新建或扩展 `integrations/providers/*`。
3. 业务层改成调用 adapter，而不是直接 `httpx` / `urlopen` / 组装外部 URL。
4. 扩 `check_dependency_boundaries.py`：
   - 在 `apps/worker` 中阻断新 direct external glue
5. 更新 architecture docs。

**删除哪些旧结构**

- 删除 `apps/worker` 中 direct provider/platform HTTP glue。

**迁移桥**

- 允许极短期 adapter pass-through。
- 不允许长期双写：旧逻辑和新 adapter 共存超过一个执行波次。

**兼容桥删除条件与时点**

- 一旦 adapter 接好并验证，旧 direct calls 立即删。

**Done Definition**

- 指定 external glue 已迁入 `integrations/`
- `apps/worker` 只依赖 adapter 层
- dependency boundary gate 能阻止新 direct glue 回流

**Fail Fast 检查点**

- 如果迁移需要改 public contract 或跨 app 共享 contract，先停在 contract 审查，不做无边界扩散。

**它会打掉什么幻觉**

- “boundary gate 绿了，就代表 external glue 已收口”

**它会改变哪个上层判断**

- 把“架构文字契约先进于代码”改成“架构文字契约和代码落点一致”。

## [八] 硬切与迁移方案

### 立即废弃项

- 废弃“repo-side strict green and only external blockers remain”的当前叙事。
- 废弃“release evidence 只有 ready”这类单层叙事。
- 废弃“private vulnerability reporting 默认已启用”。
- 废弃 legacy `gitleaks` current-proof 口径。
- 废弃 repo-level upstream/fork merge/rebase 叙事。

### 迁移桥

- `docs/generated/external-lane-snapshot.md` 继续保留，但只做 pointer。
- `current-state-summary.md` 继续作为 runtime-owned current summary。
- `repo-side-strict-ci` 继续保留为 repo-side lane wrapper，但必须在文档和 gate 中明确其不是 external/release-grade receipt。

### 禁写时点

- 从 WS4 开始，tracked docs 禁止再写 current external verdict payload。
- 从 WS5 开始，`apps/worker` 禁止新增 direct external glue。

### 只读时点

- WS1 完成后，旧 strict 绿收据只读，不再参与 current verdict。
- WS3 完成后，legacy gitleaks receipt 只读，只保留历史参考。

### 删除时点

- WS1 完成后，停止引用旧 strict current 叙事。
- WS3 完成后，停止引用 legacy gitleaks current 叙事。
- WS5 完成后，删除 `apps/worker` 中对应 direct external glue 实现。

### 防永久兼容机制

- 每个 bridge 都要有删除触发条件，且写入对应 Workstream 的 Done Definition。
- 不允许“先迁一半再长期共存”。
- 若需要暂时保留双路径，必须在同一 Workstream 内写明删除时间点和删除 gate。

## [九] 验证闭环与 Gate

| 维度 | 验证项 | Gate / 命令 / CI / Policy | 通过条件 | 未通过意味着什么 |
| --- | --- | --- | --- | --- |
| Repo-side governance | 控制面总闸 | `./bin/governance-audit --mode audit` | PASS | repo-side 基础治理未站稳 |
| Repo-side strict | canonical strict receipt | `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` | PASS | repo-side done 不成立 |
| Newcomer/current strict receipt | strict 收据渲染与语义 | `python3 scripts/governance/render_newcomer_result_proof.py && python3 scripts/governance/check_newcomer_result_proof.py` | PASS 且 `repo_side_strict_receipt=pass` | current receipt 不可信或 lane semantics 有误 |
| Current-proof alignment | current artifact 是否对齐 HEAD | `python3 scripts/governance/check_current_proof_commit_alignment.py` | PASS | current-state 可能在消费旧 artifact |
| Remote required checks | 远端 branch protection 对账 | `python3 scripts/governance/check_remote_required_checks.py` | PASS | CI contract 与 GitHub 平台态不一致 |
| GHCR readiness | 外部分发前置 | `./scripts/ci/check_standard_image_publish_readiness.sh` | 非 blocked，最终 verified | GHCR external lane 未闭环 |
| Release evidence readiness | release bundle 前置 | `python3 scripts/release/check_release_evidence_attest_readiness.py --release-tag v0.1.0` | READY | release evidence 还缺基础输入 |
| Release external verification | workflow current-head verified | `python3 scripts/governance/probe_external_lane_workflows.py` | `release-evidence-attestation=verified` on current HEAD | ready 还没升级成 verified |
| Public security truth | PVR + gitleaks current-head | 新增 `python3 scripts/governance/check_open_source_audit_freshness.py` + `probe_remote_platform_truth.py` | PVR 显式状态 + gitleaks meta 指向 current HEAD | 安全边界仍是姿态化，不是 current-proof |
| Docs truth | docs control plane + semantic assertions | `python3 scripts/governance/check_docs_governance.py` | PASS 且关键 generated 页语义正确 | docs 仍可能制造假成熟 |
| Root allowlist | 根目录洁净 | `python3 scripts/governance/check_root_allowlist.py --strict-local-private` | PASS | 顶层门厅污染或治理资产漂移 |
| Runtime outputs | 输出路径合法 | `python3 scripts/governance/check_runtime_outputs.py` | PASS | 运行态泄漏到源码树或非法位置 |
| Logging schema | 日志 contract | `python3 scripts/governance/check_logging_contract.py` | PASS | 关键链路不可诊断 |
| Upstream governance | 第三方依赖治理完整性 | `python3 scripts/governance/check_upstream_governance.py` | PASS | third-party upstream 台账不完整或 drift |
| Upstream freshness | verified rows freshness | `python3 scripts/governance/check_upstream_compat_freshness.py` | PASS | upstream verified 证据过期 |
| Upstream same-run | blocker rows same-run cohesion | `python3 scripts/governance/check_upstream_same_run_cohesion.py` | PASS | upstream blocker rows 证据不成束 |
| External glue locality | boundary not bypassed | `python3 scripts/governance/check_dependency_boundaries.py`（扩展后） | PASS 且 apps 层无新 direct external glue | architecture locality 仍未闭环 |

## [十] 执行时序总表

| 阶段 | 动作 | 前置条件 | 并行性 | 完成标志 | 风险 |
| --- | --- | --- | --- | --- | --- |
| `S0` | 冻结旧口径，固定当前事实源 | 无 | 串行 | 本 Plan 成为唯一当前 authority | 若不冻结，后续会被旧结论干扰 |
| `S1` | 执行 WS1：修 canonical repo-side strict | `S0` | 串行 | strict fresh PASS | 若 strict 未绿，后面一切 current 结论都降级 |
| `S2` | 重渲染 newcomer/current-proof，更新 repo-side truth | `S1` | 串行 | newcomer result proof PASS | 若不重渲染，repo-side current truth 仍旧 |
| `S3` | 执行 WS2：修 GHCR repo 内准备 + 平台 auth/ACL | `S1` | 可与 WS3 并行一部分 | GHCR readiness 不再 blocked，且远端 rerun 前本地 full pre-push 已绿 | 最大风险在 GitHub 平台，不在 repo |
| `S4` | 执行 WS3：补 public/security current-proof | `S1` | 可与 WS2 并行一部分 | PVR 显式状态 + gitleaks fresh | 若 API 不支持，只能降级为 unverified |
| `S5` | 执行 WS4：docs/current-truth semantic hard cut | `S3` + `S4` 关键结果明确 | 串行 | generated docs 不再能制造错读 | 若提前做，可能二次返工 |
| `S6` | 执行 WS5：external glue locality 收口 | `S5` | 分 provider 小波次并行 | apps 层 direct glue 收口 | 若提前做，容易在语义面未稳定时返工 |
| `S7` | 总复核 | `S1`-`S6` | 串行 | repo-side/external/public/security/docs/architecture 全部分层可读 | 若跳过总复核，旧错读会回潮 |

## [十一] 改造动作 -> 上层判断改变 映射表

| 动作 | 改变什么判断 | 为什么 |
| --- | --- | --- |
| WS1 修复 `pyasn1` / strict red | 改变 repo-side current verdict | canonical strict 是 repo-side done 的必要条件 |
| WS2 打通 GHCR | 改变 external/public distribution 判断 | GHCR 是 external/public 最硬 blocker |
| WS3 补 PVR + gitleaks current-proof | 改变 open-source/security 判断 | 安全边界从 posture 变 evidence |
| WS4 强化 docs semantic gate | 改变 docs/CI 可信判断 | 从“控制面强”升级到“不易读错” |
| WS5 收口 external glue locality | 改变 architecture maturity 判断 | 文字契约和代码落点一致 |

## [十二] 如果只允许做 3 件事，先做什么

### 1. 先做 `WS1` Repo-side Strict Reclosure

- 为什么是第 1：当前 fresh 红灯已经在 canonical strict，而不是只在 external。
- 它打掉的幻觉：`repo-side 已绿，只剩 external blocker`
- 它释放的能力：恢复 repo-side done 的可信性

### 2. 再做 `WS2` GHCR / External Distribution Closure

- 为什么是第 2：这是 external/public 最硬 blocker。
- 它打掉的幻觉：`public repo = public distribution ready`
- 它释放的能力：第一次把 external/public 分发真正拉进闭环

### 3. 然后做 `WS3` Open-source Security Proof Freshness

- 为什么是第 3：即使 GHCR 好了，没有 current-head 安全证明也不能把 public/security 说满。
- 它打掉的幻觉：`SECURITY.md 在，就等于安全入口已验证`
- 它释放的能力：让公开边界从“姿态完整”变成“current-proof 完整”

## [十三] 不确定性与落地前核对点

**高置信事实**

- governance audit 当前 fresh PASS
- current-proof alignment 当前 fresh PASS
- remote-required-checks 当前 fresh PASS
- release readiness 当前 fresh READY
- GHCR readiness 当前 fresh FAIL
- canonical repo-side strict 当前 fresh FAIL at `pyasn1`

**中置信反推**

- docs semantic gate coverage 不均衡是结构性问题，但具体要不要新增脚本还是扩旧脚本，落地时可二选一
- upstream row-level current-head alignment 仍需补强，但可以优先扩现有 freshness/cohesion gate，而不是另起一套框架

**落地前要二次核对**

- `pyasn1` 的具体引入链和最小升级面
- GHCR package ownership / secret 命名 / token 权限的当前 GitHub 平台配置
- GitHub API 是否能稳定提供 PVR 能力状态
- `apps/worker` 中每条 external glue 的最终 adapter 切分边界

**但这些不确定性不影响主路线**

- 主路线仍然唯一：`WS1 -> WS2 -> WS3 -> WS4 -> WS5`

## [十四] 执行准备状态

### Current Status

- Repo-side governance: green
- Canonical repo-side strict: fresh PASS
- GHCR external lane: blocked
- Release lane: `readiness=READY`, remote workflow semantics previously/currently split to verified on current HEAD
- Public/security proof: repo-side current-proof strengthened；仍缺 external/public platform closure

### Next Actions

1. 平台侧修复 GHCR package ownership / ACL / write 权限，并核实 `GHCR_WRITE_USERNAME` / `GHCR_WRITE_TOKEN` 是否真实具备 blob write 能力。
2. repo 内维持 WS2 的 fail-close：保留 blob upload probe、`GHCR_WRITE_* -> GHCR_* -> gh auth` 凭证优先级、外部 lane 文档和 current-state summary 的诚实语义；不要在 strict 前置条件之外重跑远端 GHCR。
3. 若平台权限修好，再触发 current HEAD GHCR lane 验证，并重刷 external lane workflows / current-state summary。

### Decision Log

- `2026-03-17 14:39 PDT`：确认上一轮“只剩 external blocker”的旧结论已失效，执行顺序固定为 `WS1 -> WS2 -> WS3 -> WS4 -> WS5`，因为 fresh canonical strict 当前红在 `pip-audit`。
- `2026-03-17 14:39 PDT`：为最小 blast radius，先采用直接安全约束方式在 `pyproject.toml` 中显式钉住 `pyasn1>=0.6.3,<1`，再由 `uv lock` 统一回收传递依赖，而不是先做大范围依赖升级。
- `2026-03-17 14:42 PDT`：fresh strict 复跑后，`pip-audit` 已不再是最深红灯；当前最深红灯前移到 `documentation drift gate (push range)`，要求同步更新 `docs/reference/dependency-governance.md`。已立即补写文档，再次准备复跑 strict。
- `2026-03-17 14:47 PDT`：并行 WS3 子任务已在授权范围内落地到工作树，且 second strict 证明这些改动又触发了 `public_governance_pack` 的 change-contract 联动；决定立即将并行结果并回主线，并把相关 public 文档一次性补齐，而不是继续让 strict 在 change-contract 上兜圈。
- `2026-03-17 14:49 PDT`：WS3 的 repo 面已经拿到 fresh 局部验证：open-source audit freshness PASS、public contact points PASS、remote platform probe PASS 且 `private_vulnerability_reporting=unverified`。因此 WS3 不再是“只有实现没有验证”，而是进入 `Partially Verified`。
- `2026-03-17 14:52 PDT`：第三次 canonical strict 已完整越过前面的依赖/文档联动红灯，并把新的最深 blocker 收敛到 `third-party-notices` stale：`artifacts/licenses/third-party-license-inventory.json` 与 `THIRD_PARTY_NOTICES.md` 需要重生成。这说明 WS1 仍在推进，但下一刀已从依赖/文档联动转到权利账本 freshness。
- `2026-03-17 14:53 PDT`：已运行 `python3 scripts/governance/render_third_party_notices.py` 刷新第三方权利账本 freshness。虽然工作树未新增 tracked diff，但该动作直接改变了 terminal governance 对 stale generated file 的判断前提，因此必须作为正式执行进度记账。
- `2026-03-17 15:02 PDT`：第四次 canonical strict 已明确穿过 `short-checks`、`long-tests`、`web coverage threshold`、`coverage-core-gates`，并进入 `mutation gate`；但长时间未产出 fresh final verdict。按照执行纪律，这一轮不能被口头视为 PASS，因此将其降级记录为“未决中的重验证”，并继续推进不依赖 mutation 结果的 repo-side 可做项。
- `2026-03-17 15:12 PDT`：`WS4` 的已知确定性 repo-side 漂移已被修复：`render_docs_governance.py` 不再把 release-evidence attestation readiness 混写到旧 `.runtime-cache/reports/release-readiness/` 路径；相关 generated docs 已重渲染且 docs governance gate fresh PASS。
- `2026-03-17 15:18 PDT`：将 dirty-worktree 语义纳入 newcomer proof：`render_newcomer_result_proof.py` 现在会显式记录 `worktree_state.dirty`，并在 dirty worktree 上把总体状态降级为 `partial`；`check_newcomer_result_proof.py` 已按该语义 fresh PASS。此举直接封堵了“未提交改动下仍复用旧 pass 收据”的假成熟窗口。
- `2026-03-17 15:24 PDT`：进一步把 dirty-worktree 语义下沉到 `current-state-summary`，并补齐 WS2 的远端 failure 证据：GHCR workflow 的 preflight 已过，真正失败发生在 `Build and push strict CI standard image`，对 GHCR blob 的 `HEAD` 请求返回 `403 Forbidden`。
- `2026-03-17 15:29 PDT`：已将 WS2 的 GHCR failure 细节真正写回 runtime artifacts：`probe_external_lane_workflows.py` fresh 产物现在携带 `failure_details` 与 `failure_signature`，`current-state-summary.md` 也已显示“preflight passed; blocked at Build and push strict CI standard image; GHCR blob HEAD returned 403 Forbidden”。这使 WS2 的 repo-side 取证链达到 `Partially Verified` 水平。
- `2026-03-17 15:31 PDT`：已将 `open-source-audit-freshness.json` 纳入 `current-proof-contract.json`，并 fresh 通过 `check_current_proof_commit_alignment.py`（6 artifacts）与 `./bin/governance-audit --mode audit`。这说明 WS3 的 current-proof 接线已经从“独立脚本”升级为“正式主链票据”。
- `2026-03-17 15:36 PDT`：继续压实 WS2 平台边界：本地 `gh` 身份对组织 container package 及其 versions API 都返回 `403 need read:packages`，而仓库同时确实配置了 `GHCR_WRITE_USERNAME` / `GHCR_WRITE_TOKEN` secrets。结论：WS2 后续必须围绕 workflow secret 路径、org/package ACL 与 package ownership 来修，不能再把本地 CLI 身份当最终 auth 事实。
- `2026-03-17 15:50 PDT`：WS5 第一刀已完成并 fresh 验证：`article` step 的 direct external HTTP/trafilatura glue 已从 worker step 收口到 `integrations/providers/article_fetch.py`，且 `apps/worker/tests/test_article_step.py` fresh `11 passed`。这说明 WS5 已从“只存在计划”进入 `Partially Verified`。
- `2026-03-17 15:50 PDT`：WS5 第一刀已落地并经 fresh 测试验证：`article` step 的 direct external HTTP/trafilatura glue 已从 `apps/worker/worker/pipeline/steps/article.py` 收口到 `integrations/providers/article_fetch.py`；`apps/worker/tests/test_article_step.py` fresh `11 passed`。这使 WS5 首次从“只存在计划”进入 `Partially Verified`。
- `2026-03-17 15:56 PDT`：WS5 第二刀已完成并 fresh 验证：`RSSHubFetcher` 中 feed 解析与 risk-control helper 已从 worker/rss/fetcher 收口到 `integrations/providers/rsshub.py`；`apps/worker/tests/test_rss_fetcher.py apps/worker/tests/test_rss_fetcher_bilibili_fallback.py` fresh `15 passed`。这说明 WS5 已经拿下第二个低 blast-radius provider slice。
- `2026-03-17 16:04 PDT`：`run_mutmut.sh` 已自然完成并导出全量 stats，随后又补上了 fresh runtime metadata，并把 repo 内历史 `tmp/mutation` 与 `tmp/third-party-license-uv` 清出 `.runtime-cache/tmp`。此后 fresh `./bin/governance-audit --mode audit` 已再次 PASS，说明 mutation sidecar 与 tmp budget 两条派生问题都被收回 repo-side 基线内。
- `2026-03-17 16:10 PDT`：WS5 第三刀已完成并 fresh 验证：YouTube comments 的 direct external API glue 已从 `worker.comments.youtube` 收口到 `integrations/providers/youtube_comments.py`；定向测试 fresh `13 passed`。这说明 WS5 已经拿下第三个 low blast-radius provider slice。
- `2026-03-17 16:12 PDT`：WS5 第四刀已完成并 fresh 验证：Bilibili comments 的 direct external API glue 已从 `worker.comments.bilibili` 收口到 `integrations/providers/bilibili_comments.py`；定向测试 fresh `17 passed`。这说明评论链两侧都已经开始按 provider 收口。
- `2026-03-17 16:18 PDT`：WS5 第五刀已完成并 fresh 验证：provider health 的 raw HTTP probe 已从 `apps/worker/worker/temporal/activities_health.py` 收口到 `integrations/providers/http_probe.py`；`apps/worker/tests/test_temporal_helpers_coverage.py` fresh `6 passed`，随后 `check_dependency_boundaries.py`、`check_contract_locality.py`、`governance-audit` 继续 PASS。说明这条 health probe slice 也属于低 blast-radius 且已稳定落地的收口面。
- `2026-03-17 16:32 PDT`：只读协调收口结论已经确认：在当前工作树上，还剩 1 个同等级、低 blast-radius 的 provider/locality slice 候选，即 `subtitles.py` 中的 YouTube transcript fallback helper；除此之外，剩余 direct external glue 要么已经是 orchestration 主体（如 `rss/fetcher.py`），要么只是低价值薄 facade，不值得继续在本轮扩大战线。
- `2026-03-17 17:32 PDT`：本机 Docker daemon 已恢复可用，`docker version` / `docker info` 都能返回 server 侧信息；因此 WS1 的主阻塞不再是本机容器引擎 availability，而是 fresh canonical strict 的真实 repo-side 门禁结果。
- `2026-03-17 17:34 PDT`：Docker 恢复后首次 fresh canonical strict 已重新跑到 `short-checks`，并把最深红灯收敛到两处具体 repo-side 问题：`env.contract` 新增 `MUTATION_WORKDIR_ROOT` 后未同步 `.env.example` / `ENVIRONMENT.md`，以及 comments provider locality 收口后 `apps/worker/worker/comments/{bilibili,youtube}.py` 不再包含 critical-path `logger.*` 调用。决定立即做最小硬修，而不是再次把 repo-side 红灯误判成环境问题。
- `2026-03-17 17:38 PDT`：WS5 第六刀已完成并 fresh 验证：YouTube transcript fallback helper 已从 `apps/worker/worker/pipeline/steps/subtitles.py` 收口到 `integrations/providers/youtube_transcript.py`，`subtitles.py` 保留编排语义与模块级 re-export；定向验证 `21 passed`，orchestrator 合同测试 `1 passed`，`ruff check` PASS。结论：WS5 在“低 blast-radius provider slice”层面已完成第六刀收口。
- `2026-03-17 17:40 PDT`：针对 fresh strict 的两个 short-check blocker 已完成硬修并定向复验：`bash scripts/governance/ci_or_local_gate_doc_drift.sh --scope push` PASS，`python3 scripts/governance/check_structured_logs.py` PASS，comments 定向测试 fresh `25 passed`。结论：WS1 当前重新回到“等待 fresh canonical strict 最终收据”的状态，不再被已知 short-check 缺口卡住。
- `2026-03-17 18:00 PDT`：fresh canonical `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 已完整 PASS，依次通过 short-checks、long-tests、web coverage threshold、core coverage、mutation、api real smoke local 与 final root dirtiness。结论：WS1 主目标已经从 `In Progress` 升级为 `Verified`。
- `2026-03-17 18:02 PDT`：在 canonical strict PASS 后已立刻重渲染 runtime receipts：`render_newcomer_result_proof.py` / `check_newcomer_result_proof.py` PASS，`render_current_state_summary.py` PASS，`check_current_proof_commit_alignment.py` PASS。说明“strict 通过”不只存在于终端，也已进入机器账本；但 newcomer 总状态仍为 `partial`，因为 dirty worktree 语义仍然成立。
- `2026-03-17 18:06 PDT`：WS2 的 repo-side fail-close 已进一步增强：`check_standard_image_publish_readiness.sh` 新增 GHCR blob upload probe，显式把“package API 可见但 blob write 403”的情形纳入 preflight 语义；`docs/reference/external-lane-status.md` 也同步解释了 `202`/`401`/`403` 的读法。结论：WS2 现在更清楚地分出“repo-side 已做到哪”与“平台真正卡在哪”。 
- `2026-03-17 18:08 PDT`：最新 fresh 复核再次确认：`check_dependency_boundaries.py` PASS、`check_contract_locality.py` PASS、`./bin/governance-audit --mode audit` PASS。说明 WS5 第六刀与 WS2 preflight 补强都没有破坏治理总闸或架构边界。
- `2026-03-17 18:15 PDT`：WS3 本轮又补了一轮 fresh 平台/安全票：`check_open_source_audit_freshness.py` PASS、`check_remote_required_checks.py` PASS、`probe_remote_platform_truth.py` PASS 且 `private_vulnerability_reporting=unverified`。结论：WS3 仍未 external-closed，但它现在不是“旧票撑门面”，而是今天也新刷过的部分验证态。
- `2026-03-17 18:20 PDT`：进一步修正 GHCR current-state 语义：`render_current_state_summary.py` 现在会同时写出“本机 local readiness artifact blocked:registry-auth-failure”和“latest remote current-head workflow preflight passed but later hit blob HEAD 403”。结论：WS2 的 current-state summary 不再把本机 readiness 与远端 workflow 的失败层级混成一句模糊描述。
- `2026-03-17 18:24 PDT`：为防止 WS2 语义回潮，新增 `test_render_current_state_summary_distinguishes_local_readiness_from_remote_push_failure`，并 fresh 通过 `apps/worker/tests/test_external_proof_semantics.py`；随后 `./bin/governance-audit --mode audit` 再次 PASS。结论：GHCR 双层状态描述现在既有实现，又有测试和总闸复核。
- `2026-03-17 18:31 PDT`：继续把 GHCR 预检的凭证来源对齐到底：`check_standard_image_publish_readiness.sh` 现在优先读取 workflow 对齐的 `GHCR_WRITE_USERNAME/GHCR_WRITE_TOKEN`，其次才是本地 `GHCR_USERNAME/GHCR_TOKEN`，最后才退回 `gh auth`；workflow preflight env、README、start-here、runbook、testing、ENVIRONMENT 已同步改写，随后 `doc-drift`、`check_docs_governance.py`、`governance-audit` 全部 fresh PASS。结论：WS2 的 repo-side fail-close 现在不只逻辑更诚实，连变量命名和操作文档也对齐了。
- `2026-03-17 16:04 PDT`：已完成 mutation 结果收口与 scratch 预算修复：`bash scripts/ci/run_mutmut.sh` 自然跑完并导出 stats，`check_mutation_stats.py` PASS；随后为 `mutmut-cicd-stats.json` 写入 fresh runtime metadata，并把 repo 内历史 `tmp/mutation` 与 `tmp/third-party-license-uv` 清理出 `.runtime-cache/tmp`，使 governance 总闸重新回绿。结论：WS1 当前剩余的唯一硬阻塞已收敛为 Docker daemon availability，而不是 mutation 自身失败。
- `2026-03-17 15:58 PDT`：WS5 当前两刀已经过治理侧复核：`python3 scripts/governance/check_dependency_boundaries.py` PASS，`python3 scripts/governance/check_contract_locality.py` PASS。结论：article/rss 两刀不只局部测试通过，也没有破坏当前架构边界门。
- 决定把旧“先 GHCR”主路线下调到第 2 优先级。
- 决定不做 repo-level upstream/fork 路线图。
- 决定保持 `hybrid-repo` 判断，不再争论 `native vs hybrid` 表层标签。
- 决定用 fail-close 方式扩现有 gate，而不是另起第二套治理体系。

### Validation Log

- `2026-03-17 14:38 PDT`：`uv lock` -> `exit 0`；结果：`pyasn1 v0.6.2 -> v0.6.3`；结论：WS1 的第一刀已真实落到锁文件，不再停留在计划层。
- `2026-03-17 14:41 PDT`：`./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` -> 中途定位到新的最深 blocker：`documentation drift gate (push range)`；结论：`pip-audit` 已不再是最浅红灯，当前应先完成 `docs/reference/dependency-governance.md` 联动。
- `2026-03-17 14:46 PDT`：第二次 `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` -> 再次在 `documentation drift gate (push range)` 提前失败；这次最深 blocker 前移到 `public_governance_pack` 联动缺口：`README.md`、`docs/reference/done-model.md`、`docs/reference/public-artifact-exposure.md`、`docs/reference/public-rights-and-provenance.md`、`docs/reference/public-privacy-and-data-boundary.md`、`docs/reference/public-brand-boundary.md`。结论：WS3 并行改动是有效的，但必须被正式并回主线并补齐 change-contract。
- `2026-03-17 14:49 PDT`：`python3 scripts/governance/check_open_source_audit_freshness.py` -> PASS；`python3 scripts/governance/check_public_contact_points.py` -> PASS；`python3 scripts/governance/probe_remote_platform_truth.py --output .runtime-cache/reports/governance/remote-platform-truth.exec.json` -> PASS，并显式输出 `private_vulnerability_reporting=unverified`。结论：WS3 的 repo 可做面已经拿到 fresh 局部验证。
- `2026-03-17 14:51 PDT`：第三次 `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` -> `exit 1`；结果：short-checks 基本全部通过，terminal governance gate 报 `third-party-notices` stale，需运行 `python3 scripts/governance/render_third_party_notices.py`；结论：当前最深 repo-side blocker 已更新。
- `2026-03-17 14:53 PDT`：`python3 scripts/governance/render_third_party_notices.py` -> `exit 0`；结果：`[third-party-notices] rendered`；结论：WS1 当前最深 blocker 继续向下推进，准备第四次 strict 复核。
- `2026-03-17 15:01 PDT`：第四次 `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 未在可接受时间内形成 final receipt；但从 `quality-gate.jsonl` 可验证已通过 `terminal governance gate`、`long-tests`、`web coverage threshold gate`、`worker/api core coverage gates`，并进入 `mutation gate`。结论：当前 repo-side 主阻塞已从确定失败转为“mutation final verdict 未决”。
- `2026-03-17 15:11 PDT`：`python3 scripts/governance/render_docs_governance.py` -> `exit 0`；`python3 scripts/governance/check_docs_governance.py` -> `exit 0`；结论：`docs/generated/ci-topology.md`、`docs/generated/runner-baseline.md`、`docs/generated/release-evidence.md` 已按新的真实路径语义重生，WS4 第一刀有效。
- `2026-03-17 15:17 PDT`：`python3 scripts/governance/render_newcomer_result_proof.py && python3 scripts/governance/check_newcomer_result_proof.py` -> `exit 0`；结果：当前 dirty worktree 下 `newcomer-result-proof.status=partial`，并显式记录 `worktree_state.dirty=true`；结论：current-truth 语义更诚实，WS4 第二刀有效。
- `2026-03-17 15:23 PDT`：`python3 scripts/governance/render_current_state_summary.py` -> `exit 0`；结果：`current-state-summary.md` 已显式显示 `worktree dirty: true` 与 dirty-worktree note；结论：runtime-owned 当前态也不再默认把 dirty worktree 包装成干净快照。
- `2026-03-17 15:23 PDT`：`gh run view 23195742795 --repo xiaojiou176-org/video-analysis-extract --log-failed` -> `exit 0`；结果：GHCR workflow 失败发生在 `Build and push strict CI standard image`，具体为 GHCR blob `HEAD` 请求 `403 Forbidden`；结论：WS2 当前更像 package ownership / ACL / blob write 权限问题，而不是 preflight 或 buildx 未准备。
- `2026-03-17 15:24 PDT`：`./bin/governance-audit --mode audit` -> `exit 0`；结果：本轮 WS3/WS4 语义修复后，governance 总闸仍 fresh 绿，且 `newcomer-result-proof-check` PASS。
- `2026-03-17 15:28 PDT`：`python3 scripts/governance/probe_external_lane_workflows.py` -> `exit 0`；`python3 scripts/governance/render_current_state_summary.py` -> `exit 0`；结果：GHCR lane 的 failed step / failure signature 已落入 runtime artifact 与 current-state summary。结论：WS2 的 repo-side failure classification 已完成当前能力范围内的收口。
- `2026-03-17 15:30 PDT`：`python3 scripts/governance/check_current_proof_commit_alignment.py` -> `exit 0 (6 artifacts)`；`./bin/governance-audit --mode audit` -> `exit 0`。结论：WS3 新增的 open-source audit freshness 已成功接入 current-proof 主链，且本轮所有 repo-side 语义修复未破坏 governance 总闸。
- `2026-03-17 15:35 PDT`：`gh api orgs/xiaojiou176-org/packages/container/video-analysis-extract-ci-standard` -> `exit 1 (HTTP 403 need read:packages)`；`gh api 'orgs/xiaojiou176-org/packages/container/video-analysis-extract-ci-standard/versions?per_page=5'` -> `exit 1 (HTTP 403 need read:packages)`；`gh api repos/xiaojiou176-org/video-analysis-extract/actions/secrets --jq '.secrets[].name'` -> `exit 0` 且包含 `GHCR_WRITE_USERNAME` / `GHCR_WRITE_TOKEN`。结论：本地 CLI 身份与 workflow secret 路径必须分开读。
- `2026-03-17 15:49 PDT`：`UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_article_step.py -q` -> `exit 0 (11 passed)`；结论：WS5 第一刀保持行为不变，article fetch external glue 收口有效。
- `2026-03-17 15:49 PDT`：`UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_article_step.py -q` -> `exit 0 (11 passed)`；结论：WS5 第一刀保持行为不变，article fetch external glue 收口有效。
- `2026-03-17 15:56 PDT`：`UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_rss_fetcher.py apps/worker/tests/test_rss_fetcher_bilibili_fallback.py -q` -> `exit 0 (15 passed)`；结论：WS5 第二刀保持 RSS feed 解析 / fallback 行为不变，RSSHub provider 协议细节收口有效。
- `2026-03-17 16:03 PDT`：`bash scripts/ci/run_mutmut.sh` 自然完成；结果：`mutmut-cicd-stats.json` fresh 导出，`killed=5567, survived=232, total=5998`。随后 `python3 scripts/governance/check_mutation_stats.py ... 0.64 0.27 0.72` -> `exit 0`，说明 mutation gate 阈值本身是通过的。
- `2026-03-17 16:04 PDT`：手动为 `.runtime-cache/reports/mutation/mutmut-cicd-stats.json` 写入 fresh runtime metadata 后，`du -sh .runtime-cache/tmp/*` 复核并清理掉历史 `tmp/mutation` 与 `tmp/third-party-license-uv`；随后 `./bin/governance-audit --mode audit` -> `exit 0`。结论：mutation long-run 与 tmp budget 两个派生问题都已被收口。
- `2026-03-17 15:58 PDT`：`python3 scripts/governance/check_dependency_boundaries.py` -> `exit 0`；`python3 scripts/governance/check_contract_locality.py` -> `exit 0`。结论：WS5 当前两刀没有破坏依赖边界与 contract locality。
- `2026-03-17 16:09 PDT`：`UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_youtube_comments.py apps/worker/tests/test_youtube_comments_coverage_extra.py apps/worker/tests/test_worker_step_branches.py -q` -> `exit 0 (13 passed)`。结论：WS5 第三刀保持 YouTube comments 行为不变，YouTube provider glue 收口有效。
- `2026-03-17 16:12 PDT`：`UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_bilibili_comments_collector.py apps/worker/tests/test_bilibili_comments_collector_extra_coverage.py apps/worker/tests/test_worker_step_branches.py -q` -> `exit 0 (17 passed)`；`python3 scripts/governance/check_dependency_boundaries.py && python3 scripts/governance/check_contract_locality.py` -> `exit 0`。结论：WS5 第四刀保持 Bilibili comments 行为不变，且未破坏边界门。
- `2026-03-17 16:18 PDT`：`UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_temporal_helpers_coverage.py -q` -> `exit 0 (6 passed)`；`python3 scripts/governance/check_dependency_boundaries.py && python3 scripts/governance/check_contract_locality.py` -> `exit 0`；`./bin/governance-audit --mode audit` -> `exit 0`。结论：WS5 第五刀保持 provider health probe 行为不变，且未破坏边界门与总闸。
- `2026-03-17 17:32 PDT`：`docker version` -> `exit 0`；`docker info` -> `exit 0`。结果：Docker Desktop server 侧恢复可访问，`desktop-linux` context 与 `~/.docker/run/docker.sock` 均可用。结论：本机 Docker daemon availability 不再是 WS1 blocker。
- `2026-03-17 17:34 PDT`：`./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` -> `exit 1`；结果：fresh red 已推进到 `documentation drift gate (push range)` 与 `structured log critical-path guard`，具体缺口分别为 `MUTATION_WORKDIR_ROOT` 文档联动未完成，以及 `apps/worker/worker/comments/bilibili.py` / `apps/worker/worker/comments/youtube.py` 没有 `logger.*` critical-path 调用。结论：repo-side 当前红灯已从环境问题收敛为两个精确、可施工的治理缺口。
- `2026-03-17 17:38 PDT`：`UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_subtitles_step_coverage_extra.py apps/worker/tests/test_runner_fallbacks.py apps/worker/tests/test_runner_app_prefix.py -q` -> `exit 0 (21 passed)`；`UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_orchestrator_step_contract.py -q -k default_handlers_delegate_expected_collaborators` -> `exit 0 (1 passed, 75 deselected)`；`UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" uv run ruff check apps/worker/worker/pipeline/steps/subtitles.py integrations/providers/youtube_transcript.py apps/worker/tests/test_subtitles_step_coverage_extra.py` -> `exit 0`。结论：WS5 第六刀 transcript fallback 收口已 fresh 验证。
- `2026-03-17 17:40 PDT`：`bash scripts/governance/ci_or_local_gate_doc_drift.sh --scope push` -> `exit 0`；`python3 scripts/governance/check_structured_logs.py` -> `exit 0`；`UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_youtube_comments.py apps/worker/tests/test_youtube_comments_coverage_extra.py apps/worker/tests/test_bilibili_comments_collector.py apps/worker/tests/test_bilibili_comments_collector_extra_coverage.py apps/worker/tests/test_worker_step_branches.py -q` -> `exit 0 (25 passed)`。结论：刚暴露出的两个 short-check blocker 已被定向修复并 fresh 复验。
- `2026-03-17 18:00 PDT`：`./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` -> `exit 0`。结果：short-checks、long-tests、web coverage threshold、worker/api core coverage、mutation gate、api real smoke local、root dirtiness 全部 fresh PASS。结论：WS1 的 canonical repo-side strict 已真实闭环。
- `2026-03-17 18:02 PDT`：`python3 scripts/governance/render_newcomer_result_proof.py && python3 scripts/governance/check_newcomer_result_proof.py` -> `exit 0`；`python3 scripts/governance/render_current_state_summary.py && python3 scripts/governance/check_current_proof_commit_alignment.py` -> `exit 0`。结果：runtime-owned current truth 已刷新为最新 strict 通过后的状态；`newcomer-result-proof.status=partial` 仍保留 dirty-worktree 降级语义，`repo_side_strict_receipt=pass`。结论：repo-side 绿灯与 dirty-worktree 警告现在并存且语义诚实。
- `2026-03-17 18:05 PDT`：`bash -n scripts/ci/check_standard_image_publish_readiness.sh` -> `exit 0`；`./scripts/ci/check_standard_image_publish_readiness.sh /tmp/standard-image-publish-readiness.test.json` -> `exit 1`（预期 blocked，本机仍无 packages-write token 路径）；`uv run pytest apps/worker/tests/test_external_proof_semantics.py -q` -> `exit 0 (2 passed)`。结果：WS2 新增的 blob upload probe 语义未破坏现有 external proof 读法。
- `2026-03-17 18:06 PDT`：`./scripts/ci/check_standard_image_publish_readiness.sh` -> `exit 1`；artifact 显示 `status=blocked`、`blocker_type=registry-auth-failure`、`token_mode=gh-cli`、`token_scope_ok=false`、`blob_upload_scope_ok=false`。结论：在当前本机无写包 token 的前提下，repo-side preflight 仍诚实 blocked；真正的 external unblock 依然不在仓库内部。
- `2026-03-17 18:08 PDT`：`python3 scripts/governance/check_dependency_boundaries.py && python3 scripts/governance/check_contract_locality.py` -> `exit 0`；`./bin/governance-audit --mode audit` -> `exit 0`。结论：WS5 第六刀与 WS2 preflight 补强都没有引入新的治理回归。
- `2026-03-17 18:15 PDT`：`python3 scripts/governance/check_open_source_audit_freshness.py` -> `exit 0`；`python3 scripts/governance/check_remote_required_checks.py` -> `exit 0 (17 checks)`；`python3 scripts/governance/probe_remote_platform_truth.py` -> `exit 0` 且 `private_vulnerability_reporting=unverified`；随后 `python3 scripts/governance/render_current_state_summary.py && python3 scripts/governance/check_current_proof_commit_alignment.py` -> `exit 0`。结论：WS3 的 repo-side current-proof 与 remote platform truth 在本轮已 fresh 重刷并继续保持一致。
- `2026-03-17 18:20 PDT`：`python3 scripts/governance/render_current_state_summary.py && python3 scripts/governance/check_current_proof_commit_alignment.py` -> `exit 0`；最新 `current-state-summary.md` 中 GHCR lane 已显示：`local readiness artifact=blocked:registry-auth-failure; latest remote current-head workflow preflight passed; blocked at Build and push strict CI standard image; GHCR blob HEAD returned 403 Forbidden`。结论：WS2 的 runtime-owned 汇总页现在能同时表达本机 preflight 状态和远端失败层级，减少误读。
- `2026-03-17 18:24 PDT`：`UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_external_proof_semantics.py -q` -> `exit 0 (3 passed)`；`./bin/governance-audit --mode audit` -> `exit 0`；`python3 scripts/governance/render_current_state_summary.py && python3 scripts/governance/check_current_proof_commit_alignment.py` -> `exit 0`。结论：WS2 的 GHCR 双层语义补丁已被测试锁住，并且没有破坏治理总闸。
- `2026-03-17 18:31 PDT`：`bash -n scripts/ci/check_standard_image_publish_readiness.sh` -> `exit 0`；`./scripts/ci/check_standard_image_publish_readiness.sh /tmp/standard-image-publish-readiness.test2.json` -> `exit 0` with expected blocked output；`uv run pytest apps/worker/tests/test_external_proof_semantics.py -q` -> `exit 0 (3 passed)`；`bash scripts/governance/ci_or_local_gate_doc_drift.sh --scope push` -> `exit 0`；`python3 scripts/governance/check_docs_governance.py` -> `exit 0`；`./bin/governance-audit --mode audit` -> `exit 0`。结论：GHCR 凭证优先级对齐、文档联动、以及最终治理总闸都已 fresh 通过。
- `./bin/governance-audit --mode audit` PASS
- `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` PASS
- `python3 scripts/governance/check_current_proof_commit_alignment.py` PASS
- `python3 scripts/governance/check_remote_required_checks.py` PASS
- `python3 scripts/release/check_release_evidence_attest_readiness.py --release-tag v0.1.0` READY
- `./scripts/ci/check_standard_image_publish_readiness.sh` FAIL
- `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` FAIL（旧 fresh 失败点：`pyasn1 0.6.2`；已修复，待最新 strict 复核）

### Risk / Blocker Log

- `B2` GHCR package auth not closed
- `B2a` GHCR blocked 已压到 `Build and push strict CI standard image` / blob HEAD `403 Forbidden`；当前更像 package ownership / ACL / blob write 权限边界
- `B2b` 当前本地 `gh` 身份本身缺 `read:packages`，因此不能单凭本地 package API 读取结果替代 workflow secret 路径的最终判定
- `B2c` repo-side readiness 现在已能区分 package API 可见性与 blob upload 预检，但真正解除 blocked 仍需要平台侧 token / package ACL / ownership 修复
- `B3` PVR unverified
- `B4` gitleaks stale-current receipt 已通过本地 refresh + freshness gate 修正，待与全局 strict 一起再确认
- `B5` generated docs / current-truth semantic gate 仍不均匀，但旧 `release-readiness` 路径混写、dirty-worktree newcomer 误读窗口、dirty-worktree current-state-summary 误读窗口已修正
- `B6` WS5 已完成 article / rss helper / youtube comments / bilibili comments / health probe / youtube transcript 六刀；剩余可见 direct external glue 主要集中在 RSSHub fetcher 的候选排序 / circuit-breaker / fallback orchestration，以及 `activities_email.py` 这类低价值薄封装，不再属于与前六刀同等级的低 blast-radius slice

### Files Changed Log

- Repo-side strict / dependency closure：
  `pyproject.toml`, `uv.lock`, `docs/reference/dependency-governance.md`, `scripts/ci/run_mutmut.sh`, `artifacts/licenses/third-party-license-inventory.json`, `THIRD_PARTY_NOTICES.md`
- Security / current-proof / public readiness：
  `.github/workflows/env-governance.yml`, `config/governance/current-proof-contract.json`, `scripts/governance/check_open_source_audit_freshness.py`, `scripts/governance/probe_remote_platform_truth.py`, `bin/open-source-audit-refresh`, `SECURITY.md`, `docs/reference/public-repo-readiness.md`
- Docs / current-truth semantics：
  `scripts/governance/check_docs_governance.py`, `scripts/governance/check_newcomer_result_proof.py`, `scripts/governance/render_current_state_summary.py`, `scripts/governance/render_docs_governance.py`, `scripts/governance/render_newcomer_result_proof.py`, `docs/reference/newcomer-result-proof.md`, `docs/reference/done-model.md`, `docs/generated/ci-topology.md`, `docs/generated/release-evidence.md`, `docs/generated/runner-baseline.md`
- WS5 locality 六刀：
  `integrations/providers/article_fetch.py`, `integrations/providers/rsshub.py`, `integrations/providers/youtube_comments.py`, `integrations/providers/bilibili_comments.py`, `integrations/providers/http_probe.py`, `integrations/providers/youtube_transcript.py`, `apps/worker/worker/pipeline/steps/article.py`, `apps/worker/worker/rss/fetcher.py`, `apps/worker/worker/comments/youtube.py`, `apps/worker/worker/comments/bilibili.py`, `apps/worker/worker/temporal/activities_health.py`, `apps/worker/worker/pipeline/steps/subtitles.py`
- WS1 文档/日志联动收口：
  `.env.example`, `ENVIRONMENT.md`, `apps/worker/worker/comments/youtube.py`, `apps/worker/worker/comments/bilibili.py`
- WS2 fail-close 强化：
  `scripts/ci/check_standard_image_publish_readiness.sh`, `docs/reference/external-lane-status.md`
- WS2 current-state / anti-regression：
  `scripts/governance/render_current_state_summary.py`, `apps/worker/tests/test_external_proof_semantics.py`
- WS2 凭证来源与操作文档对齐：
  `.github/workflows/build-ci-standard-image.yml`, `README.md`, `docs/start-here.md`, `docs/runbook-local.md`, `docs/testing.md`, `ENVIRONMENT.md`

### Files Planned To Change

- `pyproject.toml`
- `uv.lock`
- `docs/reference/dependency-governance.md`
- `README.md`
- `docs/reference/done-model.md`
- `docs/reference/public-artifact-exposure.md`
- `docs/reference/public-rights-and-provenance.md`
- `docs/reference/public-privacy-and-data-boundary.md`
- `docs/reference/public-brand-boundary.md`
- `scripts/ci/check_standard_image_publish_readiness.sh`
- `.github/workflows/build-ci-standard-image.yml`
- `scripts/governance/probe_remote_platform_truth.py`
- `SECURITY.md`
- `docs/reference/public-repo-readiness.md`
- `.github/workflows/env-governance.yml`
- `.env.example`
- `ENVIRONMENT.md`
- `apps/worker/worker/comments/bilibili.py`
- `apps/worker/worker/comments/youtube.py`
- `scripts/governance/check_open_source_audit_freshness.py`
- `bin/open-source-audit-refresh`
- `config/governance/current-proof-contract.json`
- `scripts/governance/check_docs_governance.py`
- `scripts/governance/render_docs_governance.py`
- `scripts/governance/render_current_state_summary.py`
- `scripts/ci/check_standard_image_publish_readiness.sh`
- `docs/reference/external-lane-status.md`
- `apps/worker/worker/pipeline/steps/subtitles.py`
- `integrations/providers/youtube_transcript.py`
- `config/docs/render-manifest.json`
- `config/docs/change-contract.json`
- `config/governance/dependency-boundaries.json`
- `scripts/governance/check_dependency_boundaries.py`
- `apps/worker/worker/rss/fetcher.py`
- `apps/worker/worker/comments/youtube.py`
- `apps/worker/worker/comments/bilibili.py`
- `apps/worker/worker/pipeline/steps/article.py`
- `apps/worker/worker/temporal/activities_health.py`
- `integrations/providers/*`

## Execution Delta

- `2026-03-17 14:38 PDT`
  - changed: `pyproject.toml`
  - changed: `uv.lock`
  - effect: 将 canonical strict 当前红灯的已知漏洞入口从 `pyasn1 0.6.2` 推进到 `0.6.3`
  - next verification: `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`
- `2026-03-17 14:42 PDT`
  - changed: `docs/reference/dependency-governance.md`
  - effect: 补齐 `dependency_policy` 的 change-contract 联动，消除 fresh strict 当前暴露出的 doc-drift blocker
  - next verification: `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`
- `2026-03-17 14:47 PDT`
  - changed: `scripts/governance/probe_remote_platform_truth.py`
  - changed: `SECURITY.md`
  - changed: `docs/reference/public-repo-readiness.md`
  - changed: `.github/workflows/env-governance.yml`
  - changed: `scripts/governance/check_open_source_audit_freshness.py`
  - changed: `bin/open-source-audit-refresh`
  - changed: `README.md`
  - changed: `docs/reference/done-model.md`
  - changed: `docs/reference/public-artifact-exposure.md`
  - changed: `docs/reference/public-rights-and-provenance.md`
  - changed: `docs/reference/public-privacy-and-data-boundary.md`
  - changed: `docs/reference/public-brand-boundary.md`
  - effect: 将 WS3 的 repo 可做面正式并回主线，并补齐 `public_governance_pack` 触发的文档联动
  - next verification: 先跑 `check_open_source_audit_freshness.py` / `check_public_contact_points.py`，再回到 canonical strict
- `2026-03-17 14:49 PDT`
  - changed: `.runtime-cache/reports/governance/remote-platform-truth.exec.json`
  - effect: fresh probe 已显式确认 `private_vulnerability_reporting=unverified`
  - next verification: 回到 canonical strict，看 WS1/WS3 联动后是否还存在新的最深 blocker
- `2026-03-17 14:53 PDT`
  - changed: `THIRD_PARTY_NOTICES.md` freshness surface
  - changed: `artifacts/licenses/third-party-license-inventory.json` freshness surface
  - effect: 清理 terminal governance 当前暴露出的 stale generated file blocker
  - next verification: `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`
- `2026-03-17 15:11 PDT`
  - changed: `scripts/governance/render_docs_governance.py`
  - changed: `docs/generated/ci-topology.md`
  - changed: `docs/generated/runner-baseline.md`
  - changed: `docs/generated/release-evidence.md`
  - effect: 将 release-readiness / release-evidence current-truth 混写拆成两类真实路径语义
  - next verification: `python3 scripts/governance/check_docs_governance.py`，随后再重发 canonical strict
- `2026-03-17 15:17 PDT`
  - changed: `scripts/governance/render_newcomer_result_proof.py`
  - changed: `scripts/governance/check_newcomer_result_proof.py`
  - changed: `docs/reference/done-model.md`
  - effect: dirty worktree 不再自动继承旧的 commit-aligned `pass` 语义；newcomer proof 现在会显式降级并暴露 dirty 状态
  - next verification: `python3 scripts/governance/render_newcomer_result_proof.py && python3 scripts/governance/check_newcomer_result_proof.py`
- `2026-03-17 15:23 PDT`
  - changed: `scripts/governance/render_current_state_summary.py`
  - changed: `.runtime-cache/reports/governance/current-state-summary.md`
  - effect: runtime-owned 当前状态页现在会显式暴露 dirty-worktree 状态，并可显示 GHCR failed step / failure signature
  - next verification: `python3 scripts/governance/render_current_state_summary.py`
- `2026-03-17 15:30 PDT`
  - changed: `config/governance/current-proof-contract.json`
  - effect: `open-source-audit-freshness.json` 已被正式纳入 current-proof 合同，不再只是独立脚本输出
  - next verification: `python3 scripts/governance/check_current_proof_commit_alignment.py`
- `2026-03-17 15:49 PDT`
  - changed: `apps/worker/worker/pipeline/steps/article.py`
  - changed: `integrations/providers/article_fetch.py`
  - changed: `apps/worker/tests/test_article_step.py`
  - effect: article fetch 的 direct external HTTP/trafilatura glue 已收口到 `integrations/providers`
  - next verification: `UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_article_step.py -q`
- `2026-03-17 15:56 PDT`
  - changed: `integrations/providers/rsshub.py`
  - changed: `apps/worker/worker/rss/fetcher.py`
  - effect: RSS feed 解析与 risk-control helper 已从 worker/rss/fetcher 收口到 `integrations/providers/rsshub.py`
  - next verification: `UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_rss_fetcher.py apps/worker/tests/test_rss_fetcher_bilibili_fallback.py -q`
- `2026-03-17 16:04 PDT`
  - changed: `scripts/ci/run_mutmut.sh`
  - changed: `.runtime-cache/reports/mutation/mutmut-cicd-stats.json.meta.json`
  - effect: mutation stats 现在可生成 fresh runtime metadata，且重型 mutation scratch 已迁到 `/tmp`；repo 内旧 scratch 已清理
  - next verification: `python3 scripts/governance/check_mutation_stats.py .runtime-cache/reports/mutation/mutmut-cicd-stats.json 0.64 0.27 0.72` 与 `./bin/governance-audit --mode audit`
- `2026-03-17 15:49 PDT`
  - changed: `apps/worker/worker/pipeline/steps/article.py`
  - changed: `integrations/providers/article_fetch.py`
  - changed: `apps/worker/tests/test_article_step.py`
  - effect: article fetch 的 direct external HTTP/trafilatura glue 已收口到 `integrations/providers`
  - next verification: `UV_PROJECT_ENVIRONMENT=\"$HOME/.cache/video-digestor/project-venv\" PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_article_step.py -q`
- `2026-03-17 15:30 PDT`
  - changed: `config/governance/current-proof-contract.json`
  - effect: `open-source-audit-freshness.json` 已被正式纳入 current-proof 合同，不再只是独立脚本输出
  - next verification: `python3 scripts/governance/check_current_proof_commit_alignment.py`
- `2026-03-17 15:23 PDT`
  - changed: `scripts/governance/render_current_state_summary.py`
  - changed: `.runtime-cache/reports/governance/current-state-summary.md`
  - effect: runtime-owned 当前状态页现在会显式暴露 dirty-worktree 状态，减少 current-truth 误读
  - next verification: `python3 scripts/governance/render_current_state_summary.py`
