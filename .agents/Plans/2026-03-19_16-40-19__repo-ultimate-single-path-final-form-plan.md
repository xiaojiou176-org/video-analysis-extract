# [🧭] Repo 终局总 Plan

## Plan Meta

- Created: `2026-03-19 16:40:19 America/Los_Angeles`
- Last Updated: `2026-03-20 00:34:00 America/Los_Angeles`
- Repo: `/Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取`
- Repo Archetype: `hybrid-repo`
- Execution Status: `Blocked`
- Current Phase: `Execution Closeout`
- Current Workstream: `WS4 External Platform Closure`
- Current Status Summary: `当前能力范围内可落地的主线改造已全部完成并完成新鲜复验：WS1/WS2/WS3/WS5/WS6 已 Verified，WS2 的最后一刀也已落地——内部 prompt/control 文本回到 English-first，product-output locale allowlist 收紧到真正的终端用户输出面；WS4 已把 GHCR 压实到 current-head hosted preflight failure + manifest unknown + package-path/ownership unresolved，并进一步追加到 registry upload boundary denied；确认剩余唯一未闭环主项是仓库外平台侧 external closure，而不是本地代码或治理面继续欠账`
- Authoritative Plan: `this file is the only execution source of truth for the current run`
- Current Workspace Note: `committed snapshot receipts remain green, but the current dirty worktree now fail-closes to partial；WS1 已封住 PR self-hosted 侧门，WS3 已切除 docs control plane 双账本并修复 pre-commit IaC guard 路径，WS5 已把 worker/MCP 首批相关性、MCP \`upstream_operation\` 语义与行为级测试真实接线并跑通 Gate/测试；当前唯一主阻塞已收敛到 WS4 的平台闭环`

## [一] 3 分钟人话版

这个仓库现在最真实的状态，可以先这样理解：

- **不是 demo**，而是一个已经有 API、Worker、MCP、Web、契约层、治理层、运行收据层的真系统。
- **不是 Final Form**，因为还有几处“看起来很成熟、实际上还差最后一把锁”的地方。
- **不是不能继续用**，而是不能再靠“文件很多、规则很多、报告很多”来自我感觉良好。

说得更直白一点：

- 现在它像一家已经把后厨、仓库、巡检表、监控屏都搭好的餐厅。
- 但有几扇侧门还没锁死，有些对外告示牌还没统一口径，部分后厨操作说明仍然只有中文。
- 所以它**内部运转已经很像样**，但**对外协作、外部信任、长期维护税**还没完全压平。

为什么不能继续靠表面成熟度自我感觉良好？

因为这个 Repo 最容易产生一种错觉：

> **“治理面很强，所以整体成熟度已经同样强。”**

但 Repo 交叉验证后的真实情况是：

1. **repo-side 当前态已经 fresh pass。**
   也就是说，仓库内部当前这张“成绩单”已经站住了。
2. **external lane 还没有 current-head verified。**
   尤其 GHCR 标准镜像分发现在已经被压实到 `current-head hosted preflight failure + manifest unknown + package-path/ownership unresolved`，不是一句模糊的“外部没通”。
3. **CI trusted boundary 的本地硬切已经完成。**
   也就是说，之前那条 self-hosted 侧门已经被封住，不再是当前本地欠账。
4. **开源健康文件和 rights / English-first 第一阶段边界已经落地。**
   现在剩下的不是“有没有边界”，而是产品输出层 locale allowlist 要不要继续收紧。
5. **docs control plane 的双账本/路径漂移已经在当前工作树中切掉并通过门禁。**
   当前真正没闭环的主项已经收敛成平台侧 external closure，而不是 docs/CI 继续欠账。

改完后，Repo 应该变成：

- **内部 current truth、外部 current truth、历史样例**三者不再混读。
- **任何 self-hosted PR workflow 都有同一套信任边界，不留侧门。**
- **贡献者看得见的深水区 surface 全部 English-first。**
- **docs control plane 只保留一个 render-only 真相源。**
- **runtime/logging/cache 的合法出口、生命周期、相关性都有机器门禁。**
- **外部分发闭环是否成立，能一眼从 current artifact 看懂，不用靠人脑拼图。**

哪些旧东西会被硬切：

- 旧说法：`governance-audit PASS = repo done`
- 旧说法：`remote-required-checks PASS = terminal closure`
- 旧结构：`boundary-policy.render_only_paths` 与 `render-manifest.generated_docs` 双账本并存
- 旧入口：`.pre-commit-config.yaml` 中错误的 `scripts/check_iac_entrypoint.sh`
- 旧习惯：在 contributor-facing / runtime-facing / governance-facing surface 中继续写中文
- 旧漏洞：任何直接在 `pull_request` 上跑 self-hosted 且不经 trusted boundary 的 workflow

为什么必须这么硬？

- 不硬切，**完成幻觉会回潮**。
- 不硬切，**新加入的人会继续被“强工程外观”误导**。
- 不硬切，**外部信任无法和内部治理对齐**。
- 不硬切，**每次再做一轮治理，都会继续交维护税**。

---

## [二] Plan Intake

### 输入材料范围

- 上游 `超级Review` 审计报告
- 上游 `## [十三] 机器可读问题账本` YAML
- 当前 Repo fresh runtime artifacts / workflows / governance control plane
- 当前 tracked docs / configs / scripts / hooks
- `.agents/Plans/` 下历史 Plan（仅作时间线参考，不作为本轮真相源）

### 验证范围

- repo structure
- configs
- workflows
- scripts
- docs
- outputs
- runtime receipts
- integration surfaces
- public/open-source boundary

### 置信边界

- **高置信**
  - 当前 `HEAD == origin/main == 7113d86f2294f594aad6f5914a6e3e4ab9a3181d`
  - 当前 worktree 为**有意保持未提交的 dirty 施工态**；因此 current workspace verdict 会 fail-close 为 `partial`
  - `[newcomer-result-proof.json](../../.runtime-cache/reports/governance/newcomer-result-proof.json)` 的 committed snapshot 当前为 `pass`
  - `[current-state-summary.md](../../.runtime-cache/reports/governance/current-state-summary.md)` 当前 repo-side verdict 为 `pass`，workspace verdict 因 dirty worktree 为 `partial`
  - `ghcr-standard-image` 当前仍未 external verified，且 local readiness 为 `blocked: registry-auth-failure`
  - `release-evidence-attestation` 当前仍是 old-head `historical`
  - self-hosted PR 侧 workflow 的 trusted boundary hard cut 已在当前工作树落地，且 `check_ci_workflow_strictness.py` 通过
  - `boundary-policy.json` 与 `render-manifest.json` 的 render-only 双账本已在当前工作树切除，且 docs governance 通过
  - `.pre-commit-config.yaml` 的 IaC guard 路径漂移已在当前工作树修复
  - `codex-test@example.com` 高频出现于提交作者统计，rights chain 需单独治理
  - deep-water 中文残留已被压缩到显式 product-output allowlist；contributor/runtime/governance surface 的第一阶段 hard cut 与 gate 已成立
- **中置信**
  - GHCR 卡点最终需要 repo policy、org policy、package policy 哪一层调整，仍需执行期二次定位
  - 现有权利链条是否可通过单页授权声明补足，还是需要更正式的 DCO/CLA 流程，需落地时再选具体形式
- **低置信**
  - 任何 external provider/live lane 的瞬时状态

### Repo archetype

- `hybrid-repo`

### 当前最真实定位

- `public source-first`
- `limited-maintenance engineering repo`
- `repo-side strong`
- `external distribution not closed`
- `strong governance repo, not adoption-grade OSS product`

### 最危险误判

> **把“内部治理强、当前 repo-side pass、文件齐全”误判成“外部分发可信、全球协作友好、开源边界已经终局成立”。**

### 结构化输入已就位

> **结构化输入已就位：** 上游 `超级Review` 报告的 `## [十三、] 机器可读问题账本` YAML 账本已在上方上下文中。请在下方 `<structured_issue_ledger>` 字段中声明 `available`，并直接以该 YAML 中的 `issues` / `completion_illusions` / `top_3_priorities` 作为 Phase 1 账本的初始底稿。

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
    - CI 主链可信但存在 self-hosted 侧门
    - 开源健康文件齐全但 rights chain 和英文化未闭环
    - docs control plane 已成型但仍有双账本
    - external lane 仍未闭环
    - 项目强于 demo，但治理强于结果证明
  </initial_claims>
  <known_conflicts>
    - 上游审计里“repo_side_strict_missing_current_receipt”已被当前 fresh runtime proof 推翻
    - upstream/fork 漂移风险在本轮验证中不适用
    - 一些看似开源 blocker 的表述，Repo 中已被定位为 public-safe / historical-example 边界问题，而非全部都是法律 blocker
  </known_conflicts>
  <confidence_boundary>
    - repo-side 当前态、CI side-door、render-only 双账本、pre-commit 路径漂移、deep-water 中文残留为高置信
    - external GHCR 最终需改 repo 还是 org/package policy 为中置信
    - provider/live 即时状态不纳入本轮设计判定
  </confidence_boundary>
</plan_intake>
```

### 统一账本裁决表

| Canonical ID | Claim / Issue | Source | Repo Verification | Evidence Strength | Type | Severity | Impact | Root Cause | Final Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ISS-001` | self-hosted PR workflow 存在 trusted boundary 侧门 | 上游 YAML + Repo workflows | **已验证** | A | fact | blocker | 直接伤害 CI 信任边界 | trusted boundary 只在主 `ci.yml` 统一落地，旁路 workflow 未复用 | 采纳 |
| `ISS-002` | rights chain 不够硬 | 上游 YAML + `git shortlog -sne --all` | **已验证** | A | fact | blocker | 阻断“可安全开源”叙事 | 高频 `codex-test@example.com` 提交缺少配套授权模型 | 采纳 |
| `ISS-003` | 深水区英文化未完成 | 上游 YAML + `rg '[\\p{Han}]'` | **已验证** | A | fact | structural | 阻断全球协作与外部排障 | 中文仍进入 runtime/governance/contributor-facing surface | 采纳 |
| `ISS-004` | render-only SSOT 双账本 | 上游 YAML + Repo configs | **已验证** | A | fact | structural | 增加文档治理维护税 | `boundary-policy.render_only_paths` 与 `render-manifest.generated_docs` 并存且不一致 | 采纳 |
| `ISS-005` | pre-commit IaC guard 路径漂移 | 上游 YAML + `.pre-commit-config.yaml` | **已验证** | A | fact | important | 可选 hook 路径不可信 | 脚本迁移后配置未同步 | 采纳 |
| `ISS-006` | API/worker/MCP 日志诊断能力不均匀 | 上游 YAML + logging/docs/code抽检 | **部分验证** | B | inference | important | 影响排障和后续运维 | API 侧更强，异步链路统一关联证据不足 | 采纳 |
| `ISS-007` | `.runtime-cache` 体量与残留偏重 | 上游 YAML + `du -sh` | **已验证** | A | fact | important | 增加维护税与局部假象 | 生命周期与保留策略更多依赖保养流程 | 采纳 |
| `ISS-008` | 公共结果证明弱于治理证明 | 上游 YAML + `value-proof/public docs/current state` | **已验证** | B | inference | important | 影响招聘信号与公开叙事真实性 | evidence surface 更擅长证明制度而非当前结果 | 采纳 |
| `ISS-009` | GHCR / external lane 未 current-head verified | 上游 YAML + fresh runtime artifacts | **已验证** | A | fact | structural | 阻断 external done | readiness 仍 `blocked: registry-auth-failure`，remote workflow 仍 `queued` / `historical` | 采纳 |
| `ISS-010` | repo-side strict receipt 缺失 | 上游 YAML | **被推翻 / 已过时** | A | fact | n/a | 若保留会让主路线失焦 | 当前 `[newcomer-result-proof.json](../../.runtime-cache/reports/governance/newcomer-result-proof.json)` 已 `pass` | 不采纳为当前 blocker |
| `ISS-011` | upstream/fork 偏移风险 | 上游散文维度 + Repo 验证 | **不适用** | A | fact | n/a | 若误判会引入无效工作 | 当前无真实 upstream/fork/vendored 偏移拓扑 | 不采纳为主路线 |

### 输入材料 -> 当前状态 归一化

| 输入材料说法 | 当前 Repo 状态 | 最终处理 |
| --- | --- | --- |
| `repo_side_strict_missing_current_receipt` | **已过时**，当前 repo-side 为 `pass` | 从主路线移除，改为“已验证关闭” |
| `CI trust boundary 有侧门` | **成立** | 升为 `P0 blocker` |
| `render-only SSOT 双账本` | **成立** | 保留为 `P1 structural` |
| `open-source 不安全` | **部分成立** | 精确改写为“可公开看，但 rights chain + English-first + external distribution 未闭环” |
| `项目结果证据不够强` | **成立** | 纳入叙事真实性与 value-proof workstream |
| `upstream 漂移风险` | **不适用** | 从主路线剔除 |

---

## [三] 统一判断总览表

| 维度 | 当前状态 | 目标状态 | 证据强度 | 是否适用 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 项目定位 / 含金量 | 强工程仓，强于 demo | 强工程仓 + 结果证明密度与治理证明密度更平衡 | B | 是 | 不改定位，改证据结构 |
| 开源边界 / public surface | 可公开审阅 | 可公开审阅 + 权利链清楚 + 全球协作可接手 | A | 是 | 不是单纯补文件 |
| 文档事实源 | control plane 已成型 | 单一 render-only SSOT，无双账本 | A | 是 | 重点是收敛而非扩张 |
| CI 主链可信度 | 主链强，旁链有洞 | 所有 self-hosted PR workflow 同一信任边界 | A | 是 | 当前最硬 blocker |
| 架构治理 | 强 | 保持强，不做无关重构 | A | 是 | 只做必要治理硬切 |
| 缓存治理 | 合法出口明确 | 更强预算、TTL、自动收口 | A | 是 | 不是第一刀 |
| 日志治理 | 契约强但不均匀 | API/worker/MCP 关联模型统一 | B | 是 | 先做 contributor-facing English 边界 |
| 根目录洁净 | 好 | 冻结新增顶级项 | A | 是 | 当前非主风险 |
| 外部依赖集成治理 | inventory 强 | current-head external verified 真实闭环 | A | 是 | 以 GHCR lane 为先 |
| upstream/fork | 当前不适用 | 继续保持不适用/显式治理预案 | A | 否 | 不进入主路线 |

---

## [四] 根因与完成幻觉总表

### 底层根因

| 根因 / 幻觉 | 表面信号 | 真实问题 | 对应动作 | 防回潮 Gate |
| --- | --- | --- | --- | --- |
| `R1` 证据语义未被所有表面统一执行 | 当前 reports / docs / workflows 很全 | repo-side、external、historical 仍可能被读者混读 | `WS4` | current-state gate + wording guard |
| `R2` privileged runner trust boundary 未 fleet-wide 收口 | `ci.yml` 有 trusted boundary | 旁路 workflow 仍能在 PR 上直接进入 self-hosted | `WS1` | self-hosted workflow boundary audit |
| `R3` public/open-source boundary 只完成了“文件包”，没完成“协作包” | LICENSE/SECURITY/CONTRIBUTING 都在 | rights chain 与 English-first contributor surface 仍未闭环 | `WS2` | rights policy + governance language gate |
| `R4` docs control plane 仍有残余双账本与路径漂移 | render-only 系统看起来已成熟 | 真实真相源不够唯一，hook/guard 仍有老路径 | `WS3` | docs control plane parity gate |
| `R5` runtime治理更多靠保养，不够天然自收口 | `.runtime-cache/**` 合法出口已定义 | 体积、日志、关联链、清理策略仍需进一步硬化 | `WS5` | runtime budget / log schema / retention gate |

### 完成幻觉

| 根因 / 幻觉 | 表面信号 | 真实问题 | 对应动作 | 防回潮 Gate |
| --- | --- | --- | --- | --- |
| `ILL-001` CI 可信幻觉 | 主 CI 很严、required checks 很全 | 不是所有 self-hosted workflow 都受 trusted boundary 保护 | `WS1` | CI workflow strictness + PR trust boundary audit |
| `ILL-002` 开源 readiness 幻觉 | public repo + MIT + SECURITY + notices | 这证明“能公开看”，不证明“能安全开源 + 全球可协作” | `WS2` | rights policy + English-first gate + public-surface audit |
| `ILL-003` docs 成熟幻觉 | generated docs / control plane / snapshots 很齐 | render-only 真相源仍有双账本，co-change 思维仍残留 | `WS3` | render-manifest single source gate |
| `ILL-004` external closure 幻觉 | remote-required-checks pass、lane 有状态页 | current-head GHCR / release evidence 仍未 verified | `WS4` | external-lane current-head proof gate |
| `ILL-005` 架构治理终局幻觉 | runtime/logging/cache 路径都写得很清楚 | 诊断链和生命周期仍需更均匀、可预算、可自动收口 | `WS5` | runtime budget + log correlation gate |

---

## [五] 绝不能妥协的红线

- 不再保留任何把 `governance-audit PASS` 等同于 repo-side done 的文案或脚本逻辑。
- 不再允许任何 `pull_request` 事件在未经 trusted boundary 的情况下进入 self-hosted runner。
- 不再允许在 contributor-facing / runtime-facing / governance-facing 深水区继续新增中文。
- 不再让 `boundary-policy.json` 和 `render-manifest.json` 同时维护同一类 render-only 真相。
- 不再让 `.pre-commit-config.yaml` 指向已经搬迁的旧脚本路径。
- 不再把 `ready / queued / historical` 包装成 `verified`。
- 不再在 tracked docs 中承载 current-state payload。
- 不再新增 repo 根级运行时输出路径；所有新输出必须进入 `.runtime-cache/{run,logs,reports,evidence,tmp}`。
- 不再用“先补文档、先整理表达”来替代真正改变成立条件的结构动作。

---

## [六] Workstreams 总表

| Workstream | 目标 | 关键改造对象 | 删除/禁用对象 | Done Definition | 优先级 |
| --- | --- | --- | --- | --- | --- |
| `WS1` Self-hosted PR Trust Boundary Hard Cut | 封死所有 self-hosted PR 侧门 | `.github/workflows/ci.yml`, `.github/workflows/pre-commit.yml`, `.github/workflows/contract-diff.yml`, `.github/workflows/env-governance.yml`, `.github/workflows/vendor-governance.yml`, 可复用 trusted-boundary workflow/action | 任何未经 trusted boundary 的 self-hosted PR workflow 路径 | 所有 PR self-hosted workflow 都要先过同一 trusted boundary，fork/untrusted PR 无法进入 privileged runner | `P0` |
| `WS2` Open-source Rights + Deep-Water English Hard Cut | 让“可公开看”进化为“协作边界清楚” | rights policy docs、`.github` 社区文件、`scripts/governance/check_governance_language.py`, `scripts/ci/e2e_live_smoke.sh`, `apps/worker/worker/pipeline/*`, `apps/worker/templates/*`, `docs/reference/public-*.md` | contributor/runtime/governance 深水区中文残留；模糊 rights chain 叙事 | 贡献授权模型明确、English-first 深水区边界落地、语言 gate 可自动阻断回潮 | `P0` |
| `WS3` Docs Control Plane Single-Source Hard Cut | 把 docs control plane 压成唯一 render-only 真相源 | `config/docs/render-manifest.json`, `config/docs/boundary-policy.json`, `config/docs/change-contract.json`, `.pre-commit-config.yaml`, `scripts/governance/check_docs_governance.py`, `scripts/governance/render_docs_governance.py` | render-only 双账本；错误 IaC hook 路径；把 generated docs 当 required hand-maintained artifact 的残留思维 | docs render-only 只有一份列表真相源，相关 hooks/gates 路径全对齐 | `P1` |
| `WS4` External Lane Truth Compression | 让 external lane “一眼可读、一眼不误读”，并推动 current-head verified 收口 | `.runtime-cache/reports/governance/current-state-summary.md` 生成逻辑、`docs/reference/external-lane-status.md`, `scripts/ci/check_standard_image_publish_readiness.sh`, GHCR workflow/readiness surfaces, `config/governance/upstream-compat-matrix.json` | old-head historical 冒充 current proof 的解释面；含糊的 ready/queued 文案 | external lane 每一行都有 current-head 语义、失败层级、依赖解释；GHCR row 可继续独立追踪到 verified | `P1` |
| `WS5` Runtime / Logging / Cache Normalization | 让运行输出更均匀、更可预算、更少靠保养 | `docs/reference/cache.md`, `docs/reference/logging.md`, `scripts/governance/check_structured_logs.py`, runtime retention/budget guards, worker/MCP logging surfaces | 依赖人工保养才能维持的 runtime residue 幻觉 | runtime budget、log schema、correlation、retention 在 API/worker/MCP 上更均匀落地 | `P2` |
| `WS6` Public Value Proof Realignment | 让结果证明密度追上治理证明密度 | `docs/reference/value-proof.md`, `docs/proofs/task-result-proof-pack.md`, public-safe sample policy | “治理很强=结果很强”的表达 | 对外可复核的 current-safe result proof 与边界注释齐备 | `P2` |

### Workstreams 状态表

| Workstream | 状态 | 优先级 | 负责人 | 最近动作 | 下一步 | 验证状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `WS1` | `Verified` | `P0` | `L1 Coordinator` | 已新增共享 `_trusted-pr-boundary.yml`，并把 `pre-commit.yml`、`contract-diff.yml`、`env-governance.yml`、`vendor-governance.yml` 全接上同一门禁；`check_ci_workflow_strictness.py` 已扩展旁路 fleet 检查 | 仅保留 remote/required-checks 对账收尾，不再作为主施工项 | `Passed: strictness gate + reviewer APPROVE` |
| `WS2` | `Verified` | `P0` | `L1 + 并行 implementer` | 已落地 contributor rights model、public/open-source 边界升级、English-first 第一阶段 gate，并继续把 `llm_prompts.py` 这类内部 prompt/control 中文切回英文；product-output locale allowlist 已从“worker prompts + rendering”收紧到真正终端用户输出层 | 转入只读维护态；后续若再新增 locale 例外，必须以新 allowlist 决策显式记账，而不是默认豁免 | `Passed: governance-language + docs governance + reviewer APPROVE + allowlist tightening` |
| `WS3` | `Verified` | `P1` | `L1 Coordinator` | 已移除 `boundary-policy.render_only_paths`、收敛 `change-contract.json` 对 generated docs 的手工陪跑要求、修复 `.pre-commit-config.yaml` IaC guard 路径并重渲染 docs governance | 如无 reviewer blocker，则转入只读维护态 | `Passed: docs governance + strictness + path parity` |
| `WS4` | `Partially Completed` | `P1` | `L1 Coordinator` | 已把 GHCR 双层读法和 current-head external verification 语义压进 `external-lane-status.md` 与 `current-state-summary` 生成逻辑；mixed reviewer 已给 `APPROVE`；runtime-owned workflow probe 已刷新到 current-head hosted failure，并继续压实到 `preflight 401 + manifest unknown + package-path unresolved`；本轮又依据 GitHub 官方 container-registry 文档，为标准镜像构建链补上了 `org.opencontainers.image.source` repo-link label，并用 targeted tests 守住这条接线 | 下一步不再是继续猜 repo-side naming drift，而是等待/推动 current-head hosted publish 在修正后重新验证 package creation/linkage/visibility | `Passed: current-state-summary + docs governance + reviewer APPROVE + live workflow probe + repo-link label targeted tests` |
| `WS5` | `Verified` | `P2` | `L1 Coordinator + 并行 implementer` | 已清理过期 runtime artifacts、拉绿 retention/freshness/log retention、启用 `.githooks`，并为 worker/MCP 落下首批结构化关联日志；本轮又把 MCP upstream request 压成稳定 `upstream_operation` 语义并补齐 targeted tests；logging contract、sample generation、correlation gate 与 targeted tests 已通过，且未发现继续本地改代码就能显著改变诊断成立条件的残余缺口 | 转入只读维护态；更深层 everywhere correlation 视后续真实故障证据再开新波次，而不是在本轮继续空转扩写 | `Passed: retention + freshness + hooks activation + logging contract/sample/correlation gates + worker/MCP targeted tests + final fresh rerun` |
| `WS6` | `Verified` | `P2` | `L1 Coordinator` | 已补充 current-safe reading rule，并把 representative proof pack 与 current truth 的边界写得更清楚；独立 render-only pointer/page `docs/generated/public-value-proof.md` 已存在且 fresh 可读 | 转入只读维护态 | `Passed: docs governance + public-value-proof pointer` |

### 任务清单

- `[x] WS1.A` 为 self-hosted PR workflows 设计统一 trusted boundary 入口
- `[x] WS1.B` 将 `pre-commit.yml` / `contract-diff.yml` / `env-governance.yml` / `vendor-governance.yml` 接入统一 boundary
- `[x] WS1.C` 扩展 `check_ci_workflow_strictness.py`，让旁路 workflow 侧门可被自动阻断
- `[x] WS1.D` 同步 `docs/testing.md` 中 CI trust boundary 口径
- `[x] WS3.A` 确认 render-only 真相源与边界策略的职责切分
- `[x] WS3.B` 移除 `boundary-policy.render_only_paths` 双账本地位，统一到 `render-manifest.generated_docs`
- `[x] WS3.C` 修正 `.pre-commit-config.yaml` 的 IaC guard 路径
- `[x] WS3.D` 更新 docs governance 相关脚本以适配单一 source
- `[x] WS2.A` 起草 contributor rights model 与 agent-generated contribution policy
- `[x] WS2.B` 收口 public/open-source 文档口径
- `[x] WS2.C` 扩展 `check_governance_language.py` 为 English-first deep-water gate
- `[x] WS2.D` 运行允许范围内的文档/语言 gate 验证
- `[x] WS2.E` 将 `scripts/ci/e2e_live_smoke.sh`、`scripts/ci/autofix.py`、`scripts/deploy/recreate_gce_instance.sh` 收口到 English-first 深水区
- `[x] WS2.F` 将内部 prompt/control 中文从 allowlist 中移出，只保留真正终端用户输出层中文
- `[x] WS4.A` 在 `docs/reference/external-lane-status.md` 写明 GHCR 双层读法
- `[x] WS4.B` 更新 `render_current_state_summary.py`，让 queued/ready 不再听起来像 verified
- `[x] WS4.C` 运行 current-state/docs 相关 gate 验证
- `[x] WS5.A` 清理过期 runtime manifests / stale test report 并拉绿 retention gate
- `[x] WS5.B` 复核 runtime freshness / log retention 通过
- `[x] WS5.C` 在当前 clone 启用 `.githooks`，把本地 enforcement 从“存在”推进到“启用”
- `[x] WS5.D` 为 worker CLI 与 MCP upstream request 落下首批结构化关联日志
- `[x] WS5.E` 为 MCP upstream request 落下稳定 `upstream_operation` 分类，并用 targeted tests 证明不是文档摆设
- `[x] WS6.C` 生成独立 public-safe value proof pointer/page 并接入 docs control plane

---

## [七] 详细 Workstreams

### `WS1` Self-hosted PR Trust Boundary Hard Cut

#### 目标

把所有 `pull_request` 触发、且使用 `[self-hosted, video-analysis-extract]` 的 workflow，统一纳入 **同一套 trusted internal PR boundary**。

#### 为什么它是结构性动作

这是整个主路线里**最硬的安全问题**。  
现在主 `ci.yml` 已经有门禁，但旁路 workflow 还有侧门。  
这就像商场正门安检很严，员工通道却不查证件。

#### 输入

- `[ci.yml](../../.github/workflows/ci.yml)`
- `[pre-commit.yml](../../.github/workflows/pre-commit.yml)`
- `[contract-diff.yml](../../.github/workflows/contract-diff.yml)`
- `[env-governance.yml](../../.github/workflows/env-governance.yml)`
- `[vendor-governance.yml](../../.github/workflows/vendor-governance.yml)`
- `[boundary-policy.json](../../config/docs/boundary-policy.json)`

#### 输出

- 可复用的 trusted boundary 入口
- 所有 self-hosted PR workflow 的统一前置条件
- PR 信任边界一致性 gate
- 文档口径与 workflow 真实行为完全一致

#### 改哪些目录 / 文件 / 配置 / task / workflow / gate

- `.github/workflows/ci.yml`
- `.github/workflows/pre-commit.yml`
- `.github/workflows/contract-diff.yml`
- `.github/workflows/env-governance.yml`
- `.github/workflows/vendor-governance.yml`
- 新增可复用 workflow 或 action：
  - 建议：`.github/workflows/_trusted-pr-boundary.yml`
  - 或：`.github/actions/enforce-trusted-pr-boundary/`
- `scripts/governance/check_ci_workflow_strictness.py`
- `docs/testing.md`
- `docs/runbook-local.md`
- `docs/start-here.md`
- `docs/generated/ci-topology.md` 的生成逻辑来源

#### 删除哪些旧结构

- 每个 workflow 各自“裸跑 self-hosted”的逻辑
- 对 trusted boundary 的隐式假设

#### 迁移哪些旧路径

- 如果采用 reusable workflow：
  - 旧路径：各 workflow 自己直接 `runs-on: [self-hosted,...]`
  - 新路径：先 `needs: trusted-pr-boundary`，再进 self-hosted jobs
- 如果采用 composite action：
  - 旧路径：workflow 内分散写条件
  - 新路径：统一 action + 统一 `if`

#### 哪些兼容桥可临时存在

- 允许在过渡期保留主 `ci.yml` 原 trusted-boundary job 名称，避免 branch protection 立即漂移

#### 兼容桥删除条件与时点

- 当所有 self-hosted PR workflow 都已走统一入口，且 remote-required-checks / branch protection 对齐后，删除旧的重复 boundary 逻辑

#### Done Definition

- 所有 `pull_request` + `self-hosted` workflow 都共享同一 trusted boundary 策略
- fork/untrusted PR 无法进入任何 privileged self-hosted path
- CI strictness check 会断言这条规则
- docs 中“trusted internal PR only”的说法与真实 workflow 一致

#### Fail Fast 检查点

- 任一 self-hosted PR workflow 还能在无 boundary 的前提下执行 -> 立即失败
- reusable boundary 落地后 branch protection 漂移 -> 立即停下先修 required checks

#### 它会打掉什么幻觉

- `ILL-001` CI 可信幻觉

#### 它会改变哪个上层判断

- “CI 主链很强，但有侧门” -> “CI trust boundary fleet-wide 成立”

---

### `WS2` Open-source Rights + Deep-Water English Hard Cut

#### 目标

把开源边界从“文件齐了”推进到“协作边界清楚”。

这条工作流不是做门面，而是做**真正能让陌生开发者参与和法务看得懂的基础设施**。

#### 为什么它是结构性动作

开源不是把仓库设成 public。  
更像是开一家对外营业的店：  
不只要挂营业执照，还要保证菜单、规章、投诉入口、责任归属都让外人看得懂。

#### 输入

- `git shortlog -sne --all`
- `[public-repo-readiness.md](../../docs/reference/public-repo-readiness.md)`
- `[public-rights-and-provenance.md](../../docs/reference/public-rights-and-provenance.md)`
- `[public-surface-policy.json](../../config/governance/public-surface-policy.json)`
- `[THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)`
- `[check_governance_language.py](../../scripts/governance/check_governance_language.py)`
- 中文残留扫描结果

#### 输出

- 明确的贡献授权模型
- English-first 深水区边界规范
- 自动化语言 gate
- public/open-source 文档口径升级

#### 改哪些目录 / 文件 / 配置 / task / workflow / gate

- `CONTRIBUTING.md`
- `SECURITY.md`
- `SUPPORT.md`
- `README.md`
- `docs/reference/public-repo-readiness.md`
- `docs/reference/public-rights-and-provenance.md`
- 新增：
  - `docs/reference/contributor-rights-model.md`
  - 若采用 DCO：`docs/reference/dco-policy.md`
  - 若采用 CLA：`docs/reference/cla-policy.md`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/ISSUE_TEMPLATE/*`
- `scripts/governance/check_governance_language.py`
- `scripts/governance/render_third_party_notices.py`
- `scripts/ci/e2e_live_smoke.sh`
- `scripts/ci/autofix.py`
- `scripts/deploy/recreate_gce_instance.sh`
- `apps/worker/worker/pipeline/steps/artifacts.py`
- `apps/worker/worker/pipeline/runner_rendering.py`
- `apps/worker/templates/digest.md.mustache`

#### 删除哪些旧结构

- 所有 contributor/runtime/governance 深水区中文提示
- 任何含糊的 “public = safe open source” 叙事

#### 迁移哪些旧路径

- 允许保留面向最终内容消费者的中文生成内容，但必须从 contributor-facing/runtime-facing/gate-facing surface 中剥离
- 建立 allowlist：
  - 允许：产品内容、localized UI、业务生成物
  - 禁止：gate、workflow、error、runbook、governance、contributor docs、PR flow

#### 哪些兼容桥可临时存在

- 允许短期在 docs 中保留双语解释，但**英文必须先行且完整**
- 允许对历史 commit message 保持历史存在，但新提交 policy 必须 English-first

#### 兼容桥删除条件与时点

- 当语言 gate 已区分 allowlist/denylist，并且全仓 contributor/runtime/governance 深水区扫描通过后，移除“迁移期保留”豁免词

#### Done Definition

- 贡献授权模型明确，并在公开文档中可定位
- governance/runtime/contributor-facing surface 的中文残留被压缩到 allowlist 内
- `check_governance_language.py` 可阻断回潮
- public readiness 文档不再只讲 public-safe，而能清楚讲 rights / collaboration / external distribution boundary

#### Fail Fast 检查点

- 若语言整改试图顺手把产品 UI 全部去中文 -> 立刻停下，说明边界切错了
- 若权利链条只写一段空话、不形成可执行 policy -> 立刻停下，不能冒充完成

#### 它会打掉什么幻觉

- `ILL-002` 开源 readiness 幻觉

#### 它会改变哪个上层判断

- “可公开看，但不能安全开源” -> “至少可以诚实宣称：rights/collaboration boundary 已明确”

---

### `WS3` Docs Control Plane Single-Source Hard Cut

#### 目标

把 docs control plane 收敛成**一个 render-only 真相源**，并修掉 hook 路径漂移。

#### 为什么它是结构性动作

文档治理最怕“双账本”。  
双账本就像两个老师各记一本成绩册，平时都说自己是准的，期末一定打架。

#### 输入

- `[render-manifest.json](../../config/docs/render-manifest.json)`
- `[boundary-policy.json](../../config/docs/boundary-policy.json)`
- `[change-contract.json](../../config/docs/change-contract.json)`
- `[check_docs_governance.py](../../scripts/governance/check_docs_governance.py)`
- `[render_docs_governance.py](../../scripts/governance/render_docs_governance.py)`
- `[.pre-commit-config.yaml](../../.pre-commit-config.yaml)`

#### 输出

- 唯一 render-only source list
- docs governance gate 的职责边界更单一
- pre-commit hook 路径完全对齐

#### 改哪些目录 / 文件 / 配置 / task / workflow / gate

- `config/docs/render-manifest.json`
- `config/docs/boundary-policy.json`
- `config/docs/change-contract.json`
- `scripts/governance/check_docs_governance.py`
- `scripts/governance/render_docs_governance.py`
- `.pre-commit-config.yaml`
- `scripts/governance/check_ci_workflow_strictness.py`
- `docs/start-here.md`
- `docs/testing.md`

#### 删除哪些旧结构

- `boundary-policy.render_only_paths` 这类与 render-manifest 重复且不完整的字段
- `.pre-commit-config.yaml` 中错误脚本路径

#### 迁移哪些旧路径

- render-only 列表：
  - 统一迁移到 `render-manifest.generated_docs`
- 边界策略：
  - `boundary-policy.json` 只保留 trust boundary / manual docs purpose / marker policy
- IaC hook：
  - 从 `scripts/check_iac_entrypoint.sh` 硬切到 `scripts/governance/check_iac_entrypoint.sh`

#### 哪些兼容桥可临时存在

- `check_docs_governance.py` 可在过渡期同时兼容旧字段和新字段，但必须发 warning

#### 兼容桥删除条件与时点

- 当所有调用面只读新字段且历史配置已迁移后，删除旧字段兼容代码

#### Done Definition

- render-only 列表只有一个真相源
- docs gate 不再依赖重复清单
- pre-commit IaC guard 路径与实际脚本一致
- change-contract 不再把 generated docs 当手工陪跑对象

#### Fail Fast 检查点

- 一旦修改 control plane 导致 generated docs render/check 整体失配，先停下修控制面，不继续叠加动作

#### 它会打掉什么幻觉

- `ILL-003` docs 成熟幻觉

#### 它会改变哪个上层判断

- “docs control plane 很强，但略重” -> “docs control plane 真正单一、可审计、低漂移”

---

### `WS4` External Lane Truth Compression

#### 目标

把 external lane 从“得靠人解释”变成“artifact 自解释”，并把 current-head external closure 的路径压缩清楚。

#### 为什么它是结构性动作

现在 external lane 不是没做，而是**做了很多解释，但读起来仍容易误会**。  
这条工作流的重点，不是伪造 external verified，而是让每个 lane 的真实状态更不可误读。

#### 输入

- `[current-state-summary.md](../../.runtime-cache/reports/governance/current-state-summary.md)`
- `[external-lane-workflows.json](../../.runtime-cache/reports/governance/external-lane-workflows.json)`
- `[standard-image-publish-readiness.json](../../.runtime-cache/reports/governance/standard-image-publish-readiness.json)`
- `[external-lane-status.md](../../docs/reference/external-lane-status.md)`
- `[upstream-compat-report.json](../../.runtime-cache/reports/governance/upstream-compat-report.json)`
- `config/governance/upstream-compat-matrix.json`

#### 输出

- external lane 语义表更清楚
- GHCR lane 的失败分层更清楚
- current-head verified / historical / ready / queued 四层语义被统一

#### 改哪些目录 / 文件 / 配置 / task / workflow / gate

- `docs/reference/external-lane-status.md`
- `docs/generated/external-lane-snapshot.md` 的说明生成逻辑
- `scripts/ci/check_standard_image_publish_readiness.sh`
- `scripts/governance/render_current_state_summary.py` 或等价 summary 生成逻辑
- `config/governance/external-lane-contract.json`
- `config/governance/upstream-compat-matrix.json`

#### 删除哪些旧结构

- 任何把 `ready/queued` 贴得像“差不多通过了”的表述

#### 迁移哪些旧路径

- external lane 的 current payload 继续只存在于 runtime-owned artifacts
- tracked docs 保留 reading rule，但不再夹带 current verdict 片段

#### 哪些兼容桥可临时存在

- 允许短期保留现有 lane 名称，避免破坏旧 artifacts 的读取路径

#### 兼容桥删除条件与时点

- 当 summary/render logic 已统一 current-head semantics 后，删掉旧 wording fallback

#### Done Definition

- `current-state-summary.md` 中每个 external lane 的语义一眼可读
- GHCR lane 明确区分 local readiness blocked、remote queued、remote verified 三层
- `upstream-compat-matrix` 中 external 相关 row 有清晰升级路径

#### Fail Fast 检查点

- 如果试图为了好看把 `queued` / `historical` 改写成正面状态 -> 立即回退

#### 它会打掉什么幻觉

- `ILL-004` external closure 幻觉

#### 它会改变哪个上层判断

- “external lane 存在但不好读” -> “external lane 真实成熟度可被直接复核”

---

### `WS5` Runtime / Logging / Cache Normalization

#### 目标

让 runtime 输出、日志相关性、缓存生命周期不再主要依赖“保养得好”。

#### 为什么它是结构性动作

现在 `.runtime-cache/**` 是合法出口，这点方向正确。  
但方向正确不代表维护税低。

#### 输入

- `.runtime-cache` 当前体量与文件数量
- `[cache.md](../../docs/reference/cache.md)`
- `[logging.md](../../docs/reference/logging.md)`
- `scripts/governance/check_structured_logs.py`
- worker / MCP 运行面现状

#### 输出

- runtime budget
- 更均匀的 log correlation model
- 更可自动化的 retention/budget policy

#### 改哪些目录 / 文件 / 配置 / task / workflow / gate

- `docs/reference/cache.md`
- `docs/reference/logging.md`
- `scripts/governance/check_structured_logs.py`
- `scripts/governance/check_runtime_cache_retention.py`
- `scripts/governance/check_log_retention.py`
- `apps/worker/worker/main.py`
- `apps/mcp/server.py`
- runtime metadata builders / log writers

#### 删除哪些旧结构

- worker/MCP 上过多依赖 stdout 的弱结构运行输出

#### 迁移哪些旧路径

- 统一把 worker/MCP 的关键运行面纳入 `.runtime-cache/logs/**` 与 `.runtime-cache/reports/**`

#### 哪些兼容桥可临时存在

- 允许 stdout 仍保留开发者体验层输出，但必须同步结构化落盘

#### 兼容桥删除条件与时点

- 当关键路径 correlation 字段在 API/worker/MCP 三侧都能被 gate 断言后，再收紧 stdout-only 容忍度

#### Done Definition

- `.runtime-cache` 预算与 retention 有更硬的自动检查
- worker/MCP 关键路径具备与 API 同级别的 correlation 证据
- runtime residue 更可预测

#### Fail Fast 检查点

- 如果 runtime 路径调整引发 docs/strict gate 大面积失配，先止损，不与 WS1-WS4 并行硬推

#### 它会打掉什么幻觉

- `ILL-005` 架构治理终局幻觉

#### 它会改变哪个上层判断

- “运行治理制度强，但有维护税” -> “运行治理制度与结构优势同步成立”

---

### `WS6` Public Value Proof Realignment

#### 目标

让对外能看到的“结果证明”，不再明显弱于“治理证明”。

#### 为什么它是结构性动作

招聘信号和 public signal 不是靠夸出来的，而是靠**让陌生人一眼能看到：这个仓库不只会立规矩，还真能产出有价值结果**。

#### 输入

- `[value-proof.md](../../docs/reference/value-proof.md)`
- `docs/proofs/task-result-proof-pack.md`
- public-safe sample policy
- current runtime result surfaces

#### 输出

- 更强的 current-safe result proof 入口
- 更少误解的 representative case pack

#### 改哪些目录 / 文件 / 配置 / task / workflow / gate

- `docs/reference/value-proof.md`
- `docs/proofs/task-result-proof-pack.md`
- `config/governance/public-surface-policy.json`
- 如有必要：新增 `docs/generated/public-value-proof.md` 作为 render-only pointer page

#### 删除哪些旧结构

- “治理强=结果强”的暗示性表达

#### 迁移哪些旧路径

- historical example 继续保留，但必须更强地标注与 current proof 的边界

#### 哪些兼容桥可临时存在

- 允许先通过 docs/proofs 强化，不强制第一轮就引入新的 generated page

#### 兼容桥删除条件与时点

- 当 current-safe result proof 已可稳定被引用，再决定是否把入口进一步产品化

#### Done Definition

- README / value-proof / task-result-proof-pack 之间的叙事完全一致
- 陌生读者能在 3 分钟内分清：系统强在哪里、当前还没闭环什么

#### Fail Fast 检查点

- 如果 value-proof 变成宣传稿，而不是证据页，立刻回退

#### 它会打掉什么幻觉

- “强治理外观 = 强结果密度”

#### 它会改变哪个上层判断

- “强工程仓但结果信号偏弱” -> “强工程仓且价值证明更直观”

---

## [八] 硬切与迁移方案

### 立即废弃项

- `governance-audit PASS = repo-side done` 相关说法
- `remote-required-checks PASS = terminal closure` 相关说法
- `.pre-commit-config.yaml` 中 `scripts/check_iac_entrypoint.sh`
- 任何新的 self-hosted PR workflow 若不带 trusted boundary
- 任何新的深水区中文 contributor/runtime/governance 文本

### 迁移桥

| 对象 | 迁移桥 | 允许多久 | 删除条件 |
| --- | --- | --- | --- |
| trusted boundary | 允许保留主 `ci.yml` 现有 job 名称作为 branch protection 兼容桥 | 短期 | 所有 workflow 已复用同一 trusted boundary 模式 |
| render-only control plane | `check_docs_governance.py` 可短期兼容旧字段与新字段 | 短期 | 所有 render-only 读取面切到单一 source |
| language boundary | 对产品内容层允许中文保留 | 长期允许 | 仅在 contributor/runtime/governance 深水区移除，不要求产品内容层清零 |
| stdout logging | worker/MCP 允许保留 stdout DX | 中期 | 结构化落盘与 correlation gate 成立后再收紧 |

### 禁写时点

- **立即**：禁止新增未受 trusted boundary 保护的 self-hosted PR workflow
- **立即**：禁止新增 render-only 双账本字段
- **立即**：禁止在深水区 surface 新增中文
- **立即**：禁止在 tracked docs 重新写 current-state payload

### 只读时点

- `boundary-policy.render_only_paths` 在迁移开始后进入只读，不再新增项
- `.pre-commit-config.yaml` 中旧 IaC 路径视为只读待删

### 删除时点

- WS3 通过后：删除 `boundary-policy.render_only_paths`
- WS3 通过后：删除 `.pre-commit-config.yaml` 中旧 IaC 路径引用
- WS1 通过后：删除重复 boundary 逻辑

### 防永久兼容机制

- 给兼容桥加明确 TODO-free exit gate，不允许“迁移期保留”长期存在
- 在 docs governance / CI strictness / language gate 中加入对旧结构的阻断式检查

---

## [九] 验证闭环与 Gate

| 维度 | 验证项 | Gate / 命令 / CI / Policy | 通过条件 | 未通过意味着什么 |
| --- | --- | --- | --- | --- |
| README / 项目定位 | source-first、limited-maintenance、repo-side vs external 语义一致 | `README.md` + `docs/reference/public-repo-readiness.md` + `docs/reference/done-model.md` 人工审查 + docs governance checks | 三处口径一致 | public 叙事仍在制造误读 |
| public surface / secret / license / provenance | 社区文件齐全、secrets fresh、rights policy 明确 | `python3 scripts/governance/check_open_source_audit_freshness.py` + public surface policy + 新增 rights policy gate | security proof fresh，rights model 可定位 | 不能诚实宣称安全开源 |
| docs 是否事实源 | render-only 单一列表 | `scripts/governance/check_docs_governance.py` + `render_docs_governance.py --check` | render-only 只有单一 source，generated docs 全对齐 | docs 仍有双账本漂移 |
| CI 绿灯是否覆盖关键判断 | 所有 self-hosted PR workflow 都经 trusted boundary | `check_ci_workflow_strictness.py` + workflow fleet audit | 无 PR self-hosted 侧门 | CI 信任边界不可信 |
| root allowlist / dirty-root | 根目录无新噪音，workspace verdict fail-close 正常 | `./bin/governance-audit --mode audit` | root/allowlist/current-proof 全绿 | 根目录或 current-proof 被污染 |
| cache 全删可重建 | runtime residue 不冒充真相 | `check_runtime_cache_retention.py`, `check_runtime_cache_freshness.py`, `prune_runtime_cache.py --assert-clean` | stale artifacts 不影响 current verdict | runtime proof 可能被旧 artifacts 污染 |
| 输出路径是否合法 | 新输出都进 `.runtime-cache/**` | root/runtime output governance checks | 无非法输出路径 | 路径治理失效 |
| 日志 schema / correlation | API/worker/MCP 关键路径具备 run_id/trace_id/request_id 等相关性 | `check_structured_logs.py` + 新增 worker/MCP correlation gate | 三侧关键路径都可关联 | 端到端诊断仍不可信 |
| evidence / report 分层 | tracked docs 不承载 current-state payload | docs governance + summary rendering checks | current payload 只存在 runtime-owned artifact | historical/current 混读回潮 |
| dependency boundary / contract-first | 跨 app 与 contracts 边界不漂移 | `check_contract_locality.py`, `check_no_cross_app_implementation_imports.py`, `check_dependency_boundaries.py` | 责任分层稳定 | 架构边界回潮 |
| upstream inventory / compatibility | current external/ provider rows 语义清楚 | `check_upstream_governance.py`, `upstream-compat-report`, external lane wording checks | verified/pending/historical 各自语义清楚 | external truth 继续靠人脑解释 |

---

## [十] 执行时序总表

| 阶段 | 动作 | 前置条件 | 并行性 | 完成标志 | 风险 |
| --- | --- | --- | --- | --- | --- |
| `Phase 1` | 落实 `WS1`：统一 trusted boundary 到所有 self-hosted PR workflow | 无 | 可与 WS3 文档设计并行，但实现最好串行 | 所有 PR self-hosted workflow 都有统一 trusted boundary | branch protection / required checks 漂移 |
| `Phase 2` | 落实 `WS3`：合并 docs control plane、修正 pre-commit IaC guard | 已锁定 WS1 方案，不再新增新 workflow 入口 | 可与 WS2 文档政策设计并行 | render-only 单一真相源、旧路径删除 | docs gates 短期失配 |
| `Phase 3` | 落实 `WS2`：rights model + deep-water English-first hard cut | WS1/WS3 的结构边界已明确 | 可分批，但需统一 allowlist | rights policy 成立、English-first gate 成立 | 一刀切错到产品内容层 |
| `Phase 4` | 落实 `WS4`：external lane truth compression 与 GHCR 当前态解释收口 | WS1/WS3/WS2 已基本稳住 | 部分并行 | external lane 语义可直接复核 | 容易为了好看美化状态 |
| `Phase 5` | 落实 `WS5`：runtime/logging/cache 强化 | 前四项已稳定，不再频繁改 control plane | 可后置 | runtime 预算与相关性 gate 落地 | 牵连面较广 |
| `Phase 6` | 落实 `WS6`：public value proof realignment | 真相层与边界层已收敛 | 可最后执行 | 结果证明密度追上治理证明密度 | 容易写成宣传稿 |

### 必须先做的

1. `WS1`
2. `WS3`
3. `WS2`

### 可以并行的

- `WS2` 的 policy 设计与 `WS3` 的 control-plane 设计可并行
- `WS4` 的文案/语义压缩可在 `WS2/WS3` 接近完成时提前准备

### 必须在 hard cut 前完成的

- trusted boundary 统一方案
- render-only 单一 source 方案
- English-first allowlist/denylist 边界定义

### 必须在 Gate 生效后再迁移的

- 深水区中文大规模替换
- worker/MCP 结构化日志收口

### 必须在 public surface 改写前完成的

- rights model 决定
- external lane current/historical 语义压缩

### 必须在兼容层删除前完成验证的

- branch protection / required checks 一致性
- docs generated pages 全量校验
- governance language gate 无误杀

### 冻结规则

- 在 `WS1` 完成前，冻结新增 self-hosted PR workflow
- 在 `WS3` 完成前，冻结新增 docs control-plane 字段
- 在 `WS2` 完成前，冻结新增深水区中文 contributor/runtime/governance 文本

---

## [十一] 改造动作 -> 上层判断改变 映射表

| 动作 | 改变什么判断 | 为什么 |
| --- | --- | --- |
| `WS1` 统一 trusted boundary | “CI 主链强但不完全可信” -> “CI trust boundary 真正可托底” | 因为所有 privileged self-hosted PR 路径都会统一受保护 |
| `WS2` rights model + English-first | “可公开看，但不能安全开源” -> “至少协作边界与权利边界清楚” | 因为外部协作最怕看不懂、说不清、授权不明 |
| `WS3` docs control plane 收口 | “docs 很强但维护税高” -> “docs 真相面单一可审计” | 因为 render-only 真相源被压成一份 |
| `WS4` external lane truth compression | “external lane 有状态但不好读” -> “external maturity 可直接复核” | 因为 artifact 语义更少靠人工解释 |
| `WS5` runtime/logging/cache 强化 | “运行治理更多靠保养” -> “运行治理更像结构优势” | 因为预算、retention、correlation 被 gate 化 |
| `WS6` value proof realignment | “治理强于结果证明” -> “结果密度与治理密度更平衡” | 因为 public-safe current proof 更好读 |

---

## [十二] 如果只允许做 3 件事，先做什么

### 1. 先做 `WS1`：Self-hosted PR Trust Boundary Hard Cut

- **为什么是它**
  - 这是唯一明确的 `P0` 安全/信任边界问题。
- **它打掉什么幻觉**
  - “主 CI 很严 = 整个 CI 都可信”
- **它释放什么能力**
  - 后续所有 docs / open-source / external lane 叙事才有可信地基

### 2. 先做 `WS2`：Open-source Rights + Deep-Water English Hard Cut

- **为什么是它**
  - 这是把 public repo 推进到真实协作仓的必要条件。
- **它打掉什么幻觉**
  - “开源健康文件齐全 = 可以安全开源”
- **它释放什么能力**
  - 提升 global contributor friendliness、法务可信度和招聘信号

### 3. 先做 `WS3`：Docs Control Plane Single-Source Hard Cut

- **为什么是它**
  - 不把双账本砍掉，后面所有治理动作都会继续交维护税。
- **它打掉什么幻觉**
  - “generated docs 很多 = docs 真相源已经单一”
- **它释放什么能力**
  - 后续 external lane 和 value proof 的表达可以更稳定地建立在同一真相面上

---

## [十三] 不确定性与落地前核对点

### 高置信事实驱动的动作

- `WS1`：side-door self-hosted workflows
- `WS3`：render-only 双账本、pre-commit IaC 路径漂移
- `WS2`：deep-water 中文残留、rights chain 需要明确
- `WS4`：GHCR external lane 仍未 current-head verified

### 基于中置信反推的动作

- rights chain 最终落地成 DCO、CLA 还是单仓授权模型
- GHCR external closure 需要改 repo settings、org policy、package write policy 的哪个层级

### 落地前要二次核对的地方

- 当前 GitHub org / package 权限能否由仓库本身修复
- English-first gate 的 allowlist 是否会误伤产品内容层
- branch protection / required checks 在 boundary 重构后是否需要先从平台端调整

### 但不得借此逃避完整 Plan

- 本 Plan 默认主路线不变：
  - **先封侧门**
  - **再收权利和语言边界**
  - **再收 docs 真相源**
  - **然后压缩 external truth**
  - **最后补 runtime 与 value proof**

---

## [十四] 执行准备状态

### Current Status

- Repo 当前 `HEAD` 与 `origin/main` 对齐
- 当前 worktree 为 dirty，且这些未提交改动正是本轮治理施工与 Plan 回写本身
- repo-side committed snapshot proof 当前为 `pass`，但当前 dirty worktree 的 workspace verdict 已 fail-close 为 `partial`
- external lane 未闭环，且当前唯一主阻塞已收敛到 GHCR 平台侧 package/permission/ownership 组合边界
- 主要结构性问题已从“缺 strict receipt”转移为：
  - rights chain 的最终法务/协作闭环
  - external lane 的 current-head verified 仍未达成
  - product-output Chinese allowlist 仍需后续细化
  - worker/MCP correlation 的本地可完成首轮已闭环，后续 only-if-needed 深化项不再作为本轮欠账

### Next Actions

1. 若继续执行，唯一主路线优先项是 `WS4` 的平台侧 GHCR closure：按 `docs/reference/external-lane-status.md` 的 repair path 先在 GitHub UI 修正 package existence / Connect repository / Manage Actions access / org package-creation visibility，然后让 current-head hosted publish path 重新验证
2. 其次才是 `WS2` 的产品输出层 locale allowlist 是否继续收紧；这是策略深化，不是当前 blocker
3. `WS5` 不再继续本地扩写，除非出现新的真实诊断证据证明现有 correlation model 不足

### Decision Log

- 判定 `repo_side_strict_missing_current_receipt` 为**已关闭旧问题**，不再进入主路线
- 判定 `upstream/fork drift` 为**当前不适用**
- 判定主路线不走“继续堆治理文档”，而走“信任边界 / 权利边界 / 真相源边界”的三连硬切
- `2026-03-19 16:54 PDT`：`WS1` 采用“共享 hosted reusable trusted boundary + 旁路 workflow needs/if 统一门禁”的实现，而不是在每个 self-hosted job 内部加步骤检查。原因：真正的 trust boundary 必须发生在进入 privileged runner 之前；把检查写在 self-hosted job 里只会把安检搬到商场里面，安全目标没变真。
- `2026-03-19 16:54 PDT`：`ci.yml` 主链暂不重构为 reusable workflow 调用，优先保留现有 `trusted-pr-boundary` job 名称与 required checks 稳定性；本轮只把旁路 workflow 收拢到同一 reusable policy，并让 strictness gate 统一检查。
- `2026-03-19 16:54 PDT`：正式接管本 Plan 作为唯一可信执行蓝图；从此之后以 Plan 文件而不是聊天记忆作为状态源
- `2026-03-19 16:54 PDT`：执行顺序锁定为 `WS1 -> WS2/WS3 并行支撑 -> WS4 -> WS5 -> WS6`
- `2026-03-19 17:02 PDT`：`WS3` 采用“render-manifest 唯一 render-only 清单 + boundary-policy 退回 trust/manual-docs 职责”的 hard cut，同时把 generated docs 从 `change-contract.json` 的手工陪跑列表移除
- `2026-03-19 17:05 PDT`：`WS1` 经 reviewer 审查为 `APPROVE`，无 blocker；因此 `WS1` 状态上调为 `Verified`
- `2026-03-19 17:05 PDT`：`WS3` 在 `render_docs_governance.py` 重渲染后通过 `check_docs_governance.py`，状态上调为 `Verified`
- `2026-03-19 17:09 PDT`：`WS2` 第一阶段采用“rights model + English-first gate + scripts-first hard cut”路线，不直接动产品 UI 或中文 digest 输出，避免误伤产品内容层
- `2026-03-19 17:11 PDT`：`WS4` 采用“先压语义、后追 external verified”的路线；本地只能保证读法更诚实，不能伪造 current-head external closure
- `2026-03-19 17:14 PDT`：`WS5` 先做当前工作区内最直接可完成的治理收口：清理 runtime-cache 过期收据、拉绿 retention/freshness/log retention，并把 `.githooks` 真正接到这份 clone 上
- `2026-03-19 17:18 PDT`：经 Repo-vs-Plan 对账确认，`WS6` 已在 `docs/reference/value-proof.md` 与 `docs/proofs/task-result-proof-pack.md` 落下 current-safe reading boundary，因此保留为 `Partially Completed`
- `2026-03-19 17:31 PDT`：`WS2/WS4/WS5` mixed review 返回 `APPROVE`；据此确认这轮本地已落地的边界压缩与 gate 接线不存在当前 blocker，剩余缺口继续按“平台侧阻塞 / 产品层策略决策 / 后续深化项”分类处理
- `2026-03-19 17:38 PDT`：`WS5` 继续向前推进，在 `apps/worker/worker/main.py` 与 `apps/mcp/server.py` 接上首批结构化关联日志，并用 targeted tests 证明“只有 stdout / 关联性不足”的问题已被真实削弱
- `2026-03-19 17:24 PDT`：最终联合 Gate 对账再次生成新的 run manifests；因此本轮将“收口时先 `prune_runtime_cache --apply` 再重跑 retention/freshness/log retention”记为当前工作区的真实 closing procedure，而不把一次性 PASS 冒充稳定状态
- `2026-03-19 17:52 PDT`：`WS2` 的 product-output Chinese residue 已从“口头 advisory”推进到“脚本中显式 locale allowlist”，当前剩下的不再是边界是否存在，而是后续是否继续收紧
- `2026-03-20 00:28 PDT`：`WS2` 最后一刀已落地：`apps/worker/worker/pipeline/steps/llm_prompts.py` 的内部 prompt/control 中文全部切回 English-first，`check_governance_language.py` 的 product-output locale allowlist 同步移除该文件，公开边界文档也改成“只保留真正终端用户输出层中文”。据此把 `WS2` 从 `Partially Completed` 上调为 `Verified`
- `2026-03-19 17:45 PDT`：重拍 `external-lane-workflows.json` 与 `current-state-summary.md` 后，GHCR lane 已从旧 `queued` 视图升级为 `current-head hosted failure`，失败点明确落在 `publish / Standard image publish preflight`
- `2026-03-19 22:00 PDT`：live GitHub 对账继续压实 GHCR 边界：active `gh` token 缺 `read:packages/write:packages`；具备 `write:packages` 的备用账号 token 查询 org/user package API 都返回 404；hosted current-head workflow 则在 `Standard image publish preflight` 失败，因此当前更像 `token-context + package-path/ownership + package-permission/org-policy` 的组合阻塞
- `2026-03-19 22:06 PDT`：`WS6` 继续推进，已生成独立的 render-only pointer page `docs/generated/public-value-proof.md`，把 value proof、proof pack、newcomer-result-proof 与 current-state-summary 的阅读顺序固定下来
- `2026-03-19 22:13 PDT`：`WS4` 解释层继续收口，把“具备 write:packages 的备用 token 对 org/user package API 仍返回 404”写入 `external-lane-status.md`，防止下一轮再次把 package-path / ownership 问题误读成单纯 token scope 问题
- `2026-03-19 22:40 PDT`：补跑一轮更完整的本地治理 bundle，`check_ci_workflow_strictness`, `check_docs_governance`, `check_governance_language`, `check_current_state_summary`, `check_runtime_cache_retention`, `check_runtime_cache_freshness`, `check_log_retention`, `check_logging_contract`, `check_log_correlation_completeness`, `check_structured_logs` 全部通过
- `2026-03-19 22:55 PDT`：`WS5` 继续收口到“合同、sample、Gate 三层一致”：`logging-contract.json` 新增 optional sample targets，`generate_logging_samples.py` 现在会生成 `worker-commands.jsonl` / `mcp-api.jsonl` 样本，`check_logging_contract.py` 与 `check_log_correlation_completeness.py` 均已通过
- `2026-03-19 22:39 PDT`：补跑扩大后的 targeted regression 集，`apps/mcp/tests/test_api_client.py`, `apps/mcp/tests/test_server_runtime.py`, `apps/worker/tests/test_worker_main_cli_coverage.py`, `apps/worker/tests/test_external_proof_semantics.py`, `apps/worker/tests/test_governance_controls.py` 共 `81 passed in 3.79s`
- `2026-03-19 22:58 PDT`：按用户指定继续执行 `WS5` 的本地小步：不做大改，只在 `apps/mcp/server.py` 现有 request logging 结构上补了稳定 `upstream_operation` 分类，并让错误详情与测试一起认账；这一步的目标不是“日志更花哨”，而是把 `path/method` 压成更适合排障的 operation 语义，比如 `jobs.json_dict`、`artifacts.binary`、`health.timeout`
- `2026-03-19 23:16 PDT`：最终 closeout 复验再次通过 `check_ci_workflow_strictness`, `render_docs_governance`, `check_docs_governance`, `check_governance_language`, `check_logging_contract`, `check_log_correlation_completeness`, `check_structured_logs`, `check_current_state_summary`，以及 worker/MCP targeted regression `85 passed in 1.81s`；据此把 `WS5` 从 `Partially Completed` 上调为 `Verified`
- `2026-03-19 23:16 PDT`：根据 live GHCR 对账与本地新鲜复验，正式裁决本轮剩余未闭环项只剩 `WS4` 平台侧 external closure；继续在本地堆 `WS5` 相关性改动不会显著改变真实成立条件，因此停止本地空转，把总执行状态改为 `Blocked`
- `2026-03-19 23:02 PDT`：继续对 `WS5` 做最后一轮高价值核查后，确认真正值得补的是“行为级验证”，而不是继续扩写 logging 结构；因此只补 `apps/mcp/tests/test_server_runtime.py` 与 `apps/worker/tests/test_worker_main_cli_coverage.py`，用成功/失败/worker-loop 三类分支证明相关性字段不是摆设
- `2026-03-19 23:02 PDT`：新鲜复验表明 `check_logging_contract`, `check_log_correlation_completeness`, `check_structured_logs` 全绿，且 worker/MCP/governance targeted regression 达到 `75 passed in 2.19s`；据此再次确认 `WS5` 已完成当前能力范围内可闭环部分，继续本地扩写不会显著改变真实诊断成立条件
- `2026-03-19 23:20 PDT`：执行最终一致性校准：把 3 分钟人话版与置信边界中仍残留的“旧问题尚未修复”表述改成当前真相，并补记 final cleanup sweep（`prune_runtime_cache --apply`、retention/freshness/log retention、docs governance、current-state summary）的新鲜通过结果，确保 Plan 不再夹带历史残影
- `2026-03-19 23:15 PDT`：继续对 `WS4` 做 repo-side metadata 收口时，确认 `scripts/ci/build_standard_image.sh` 已会动态注入 `org.opencontainers.image.source=${source_repository_url}`；因此本轮只补 `.devcontainer/Dockerfile` 的 fallback source label，并在 `apps/worker/tests/test_governance_controls.py` 新增最小治理测试，避免未来把“脚本有动态 label、Dockerfile 没默认 label”的状态再次漂移回去
- `2026-03-19 23:13 PDT`：继续对 `WS4` 做平台侧压缩取证后，已新增三条高价值事实：其一，repo-side standard image naming 仍完全对齐（workflow / contract / shell exports / readiness artifact 全部指向 `ghcr.io/xiaojiou176-org/video-analysis-extract-ci-standard`）；其二，hosted failing run 明确显示 `GITHUB_TOKEN Permissions -> Packages: write` 且 `docker login ghcr.io` succeeded，因此“忘记申请 packages write”已被排除；其三，具备 `write:packages` 的备用 token 在 org/user/repository GraphQL/REST package views 下看到的仍是空集合或 `404`，因此 GHCR 主阻塞进一步收敛为 package-not-created-or-not-linked / visibility / registry blob-write boundary，而不是 repo-side naming drift
- `2026-03-19 23:36 PDT`：继续推进 `WS4` 但不再把 GitHub 官方修复路径留在聊天里。已把官方 docs 与 live probe 交叉压成仓库内 repair path：当前 build path 已带 `org.opencontainers.image.source`，repo-side image naming 与 workflow permissions 已对齐；剩余最短修复路线是进入 GitHub UI 修 package existence / Connect repository / Manage Actions access / org package-creation visibility。这条路线已写入 `docs/reference/external-lane-status.md`
- `2026-03-19 23:48 PDT`：继续尝试把 `WS4` 从“平台侧读法清楚”推进到“最小远端创建探针”，但本轮会话确认了新的能力边界：本机 Docker daemon 仍不可用，且机器上没有 `oras` / `crane` / `buildctl` / `podman` / `skopeo` / `nerdctl` 这类无 daemon 替代工具；因此当前无法在不 commit/push 的前提下完成本地 GHCR minimal push probe。由此把“平台侧 UI 修复 + 远端 current-head hosted publish 复验”正式收敛为唯一剩余主路线
- `2026-03-19 23:56 PDT`：继续尝试恢复本机 Docker 以推进 `WS4` 的 minimal push probe：执行了 Docker Desktop 可逆重启（quit + reopen），同时复验 `docker version` 与 `curl --unix-socket ~/.docker/run/docker.sock -i http://localhost/_ping`。结果显示 socket 可存在、后台进程可见，但 `_ping` 在 10 秒内仍无任何字节返回，`docker version` 仍超时；因此把“当前会话无可用 Docker daemon”从疑似边界上调为已验证硬边界，不再在本轮继续空转本地推送尝试
- `2026-03-20 00:06 PDT`：继续推进 `WS4` 时，已绕过 Docker daemon 直接打 GHCR Registry API。结果进一步压实为两层：其一，匿名 challenge 与手动 token exchange 已能围绕目标路径 `repository:xiaojiou176-org/video-analysis-extract-ci-standard:pull,push` 成功拿到 bearer token；其二，真正的 `POST /v2/<repo>/blobs/uploads/` 仍返回 `403`，而且 active 路径报 `The token provided does not match expected scopes`，backup 路径报 `permission_denied: write_package`。这说明 blocker 已从“会不会拿不到 token”进一步收敛为“registry upload boundary 仍拒绝当前 token/package state”，继续支持平台侧 package/linkage/access 闭环是唯一主路线
- `2026-03-20 00:18 PDT`：把刚刚的 registry 级证据沉淀成仓库正式产物：新增 `.runtime-cache/reports/governance/ghcr-registry-auth-probe.json` 与 `scripts/governance/probe_ghcr_registry_auth.py`。现在 `WS4` 不再只靠 workflow 日志和 package API 猜测，而是多了一层可重放的原始 registry 证据：challenge scope 能识别目标路径，token exchange 可达，但 upload boundary 仍返回 `403 scope mismatch / write_package`。这进一步支持“平台侧 package/linkage/access 未闭环”才是剩余主阻塞
- `2026-03-20 00:34 PDT`：`WS2` 的 product-output locale allowlist 收口完成最终复验：`apps/worker/worker/pipeline/steps/llm_prompts.py` 已完全清出中文、门禁脚本不再豁免该文件、公开边界文档同步改成“内部 prompt/control 英文、终端用户输出中文可保留”，并通过 `check_governance_language`, `check_docs_governance`, 以及 `apps/worker/tests/test_metadata_and_prompts.py + test_governance_controls.py` 定向回归。据此确认 `WS2` 已真正从策略尾项升级为 `Verified`

### Validation Log

- `git status --short --branch` -> clean
- `git rev-parse HEAD` 与 `git rev-parse origin/main` -> same sha
- `[newcomer-result-proof.json](../../.runtime-cache/reports/governance/newcomer-result-proof.json)` -> `pass`
- `[newcomer-result-proof.json](../../.runtime-cache/reports/governance/newcomer-result-proof.json)` after rerender -> `partial` with `dirty_worktree`
- `[current-state-summary.md](../../.runtime-cache/reports/governance/current-state-summary.md)` after rerender -> `current workspace verdict=partial`
- `[standard-image-publish-readiness.json](../../.runtime-cache/reports/governance/standard-image-publish-readiness.json)` -> `blocked: registry-auth-failure`
- `[external-lane-workflows.json](../../.runtime-cache/reports/governance/external-lane-workflows.json)` -> GHCR `blocked(current-head failure at Standard image publish preflight)`, release evidence `historical`
- `[render-manifest.json](../../config/docs/render-manifest.json)` vs `[boundary-policy.json](../../config/docs/boundary-policy.json)` -> dual-ledger confirmed
- `[.pre-commit-config.yaml](../../.pre-commit-config.yaml)` -> wrong IaC hook path confirmed
- `git shortlog -sne --all` -> `codex-test@example.com` dominance confirmed
- `rg '[\\p{Han}]' apps scripts integrations bin .github` -> deep-water Chinese residue confirmed
- `python3 scripts/governance/check_ci_workflow_strictness.py` -> `pass`
- `rg 'trusted-pr-boundary|uses: ./.github/workflows/_trusted-pr-boundary.yml' .github/workflows/...` -> shared PR trust boundary wiring confirmed
- `python3 scripts/governance/render_docs_governance.py` -> completed after `WS3`
- `python3 scripts/governance/check_docs_governance.py` -> `pass` after `WS3`
- `rg 'scripts/check_iac_entrypoint\\.sh|scripts/governance/check_iac_entrypoint\\.sh' .pre-commit-config.yaml scripts/governance/quality_gate.sh` -> pre-commit/quality-gate path parity confirmed
- `python3 scripts/governance/check_governance_language.py` -> `pass` with advisory-only allowlist residue after `WS2`
- `python3 scripts/governance/check_current_state_summary.py` -> `pass` after `WS4`
- `python3 scripts/governance/probe_external_lane_workflows.py` -> `pass`; GHCR current-head workflow now recorded as `blocked`, failed job `publish`, failed step `Standard image publish preflight`
- `python3 scripts/governance/check_runtime_cache_retention.py` -> `pass` after `WS5`
- `python3 scripts/governance/check_runtime_cache_freshness.py` -> `pass` after `WS5`
- `python3 scripts/governance/check_log_retention.py` -> `pass` after `WS5`
- `python3 scripts/governance/check_governance_language.py` -> `pass` after removing `apps/worker/worker/pipeline/steps/llm_prompts.py` from the locale allowlist and translating the internal prompt/control text back to English
- `rg -n '[\p{Han}]' apps/worker/worker/pipeline/steps/llm_prompts.py` -> no Chinese remains after `WS2` allowlist tightening
- `python3 scripts/governance/check_docs_governance.py` -> `pass` after updating product-output locale policy docs
- `PYTHONPATH="$PWD:$PWD/apps/worker" uv run --extra dev python -m pytest apps/worker/tests/test_metadata_and_prompts.py apps/worker/tests/test_governance_controls.py -q` -> `27 passed in 1.76s` after tightening the locale allowlist and translating internal prompt/control text to English
- `python3 scripts/runtime/prune_runtime_cache.py --apply` -> required again during final reconciliation because the final gate run itself generated fresh run manifests
- `./bin/install-git-hooks` -> `.githooks` activated for current clone
- `git config --get core.hooksPath` -> `.githooks`, so local hook enforcement is now enabled in this clone
- `python3 scripts/governance/check_logging_contract.py` -> `pass` after extending logging contract for worker-commands / mcp-api
- `python3 scripts/governance/check_log_correlation_completeness.py` -> `pass` after extending app correlation targets for worker-commands / mcp-api
- `python3 scripts/governance/check_structured_logs.py` -> `pass` with new worker/MCP logging surfaces still aligned
- `python3 scripts/governance/generate_logging_samples.py` -> `pass` after adding worker-commands / mcp-api sample generation
- local governance verification bundle -> `pass` across CI/docs/language/current-state/runtime/logging gates on the current dirty workspace
- `docs/reference/value-proof.md` + `docs/proofs/task-result-proof-pack.md` -> current-safe reading boundary strengthened without changing current-proof semantics
- `docs/generated/public-value-proof.md` generated and `python3 scripts/governance/check_docs_governance.py` still `pass`
- `WS2/WS4/WS5 mixed reviewer` -> `APPROVE`, no blocker in current local diff set
- `python3 -m py_compile apps/worker/worker/main.py apps/mcp/server.py` -> `pass`
- `PYTHONPATH=\"$PWD:$PWD/apps/worker\" uv run --extra dev python -m pytest apps/mcp/tests/test_api_client.py apps/mcp/tests/test_server_runtime.py apps/worker/tests/test_worker_main_cli_coverage.py -q` -> `49 passed in 1.15s`
- `PYTHONPATH=\"$PWD:$PWD/apps/worker\" uv run --extra dev python -m pytest apps/worker/tests/test_external_proof_semantics.py apps/worker/tests/test_governance_controls.py -q` -> `30 passed in 1.07s`
- `gh auth status` + package API probes + `gh run view 23305669133 --json ...` -> GHCR block is no longer just abstract `registry-auth-failure`; token-context, package lookup path, and hosted preflight failure are now independently evidenced
- `GH_TOKEN="$(gh auth token --user terryyifeng)" gh api '/orgs/xiaojiou176-org/packages?package_type=container&per_page=100' -q 'map(.name)'` -> `[]`
- `GH_TOKEN="$(gh auth token --user terryyifeng)" gh api '/users/xiaojiou176/packages?package_type=container&per_page=100' -q 'map(.name)'` -> `[]`
- `GH_TOKEN="$(gh auth token --user terryyifeng)" gh api graphql -f query='query($owner:String!, $name:String!){ repository(owner:$owner, name:$name){ packages(first:20){ nodes { name packageType } } } }' -F owner='xiaojiou176-org' -F name='video-analysis-extract'` -> repository package nodes `[]`
- `gh run view 23305669133 --repo xiaojiou176-org/video-analysis-extract --log | rg -n "GITHUB_TOKEN Permissions|Packages: write|Packages:" -C 2` -> hosted run explicitly had `Packages: write`
- `gh run view 23305669133 --repo xiaojiou176-org/video-analysis-extract --log | rg -n "Login Succeeded|blob upload|Standard image publish preflight" -C 2` -> hosted run shows `Login Succeeded` immediately before `GHCR blob upload probe ... HTTP 401`
- `curl -I -L -sS https://github.com/orgs/xiaojiou176-org/packages/container/package/video-analysis-extract-ci-standard` -> `HTTP/2 404`
- `curl -I -L -sS https://github.com/users/xiaojiou176/packages/container/package/video-analysis-extract-ci-standard` -> `HTTP/2 404`
- `python3 scripts/ci/contract.py get standard_image.repository` + workflow/script grep -> repo-side standard image naming remains aligned to `ghcr.io/xiaojiou176-org/video-analysis-extract-ci-standard`
- `docs/reference/external-lane-status.md` updated with package-path / ownership / visibility reading rule and `check_docs_governance.py` still `pass`
- final combined closeout suite -> `prune_runtime_cache --apply` + ci/docs/language/current-state/retention/freshness/log gates all `pass`; targeted worker/MCP tests still `49 passed`
- `PYTHONPATH="$PWD:$PWD/apps/worker" uv run --extra dev python -m pytest apps/mcp/tests/test_server_runtime.py -q` -> `14 passed in 0.72s` after adding MCP `upstream_operation` coverage
- `python3 scripts/governance/check_logging_contract.py` -> `pass` after documenting MCP `upstream_operation` semantics in `docs/reference/logging.md`
- `python3 scripts/governance/check_ci_workflow_strictness.py` -> `pass` during final closeout rerun
- `python3 scripts/governance/render_docs_governance.py` -> `completed` during final closeout rerun
- `python3 scripts/governance/check_docs_governance.py` -> `pass` during final closeout rerun
- `python3 scripts/governance/check_governance_language.py` -> `pass` with allowlist advisories only during final closeout rerun
- `python3 scripts/governance/check_logging_contract.py` -> `pass` during final closeout rerun
- `python3 scripts/governance/check_log_correlation_completeness.py` -> `pass` during final closeout rerun
- `python3 scripts/governance/check_structured_logs.py` -> `pass` during final closeout rerun
- `python3 scripts/runtime/prune_runtime_cache.py --apply` -> `pass` during final cleanup sweep
- `python3 scripts/governance/render_docs_governance.py` -> `completed` during final cleanup sweep
- `python3 scripts/governance/check_runtime_cache_retention.py` -> `pass` during final cleanup sweep
- `python3 scripts/governance/check_runtime_cache_freshness.py` -> `pass` during final cleanup sweep
- `python3 scripts/governance/check_log_retention.py` -> `pass` during final cleanup sweep
- `python3 scripts/governance/check_docs_governance.py` -> `pass` after final cleanup sweep rerender
- `python3 scripts/governance/check_current_state_summary.py` -> `pass` after final cleanup sweep rerender
- `python3 scripts/governance/check_current_state_summary.py` -> `pass` during final closeout rerun
- `PYTHONPATH="$PWD:$PWD/apps/worker" uv run --extra dev python -m pytest apps/mcp/tests/test_api_client.py apps/mcp/tests/test_server_runtime.py apps/worker/tests/test_worker_main_cli_coverage.py apps/worker/tests/test_external_proof_semantics.py apps/worker/tests/test_governance_controls.py -q` -> `85 passed in 1.81s`
- `git status --short --branch` -> dirty worktree confirmed during final closeout; expected because the current wave remains intentionally uncommitted
- `git rev-parse HEAD` + `git rev-parse origin/main` -> same sha during final closeout
- `python3 scripts/governance/check_logging_contract.py` -> `pass` after adding worker/MCP behavior-level correlation tests
- `python3 scripts/governance/check_log_correlation_completeness.py` -> `pass` after adding worker/MCP behavior-level correlation tests
- `python3 scripts/governance/check_structured_logs.py` -> `pass` after adding worker/MCP behavior-level correlation tests
- `PYTHONPATH="$PWD:$PWD/apps/worker" uv run --extra dev python -m pytest apps/mcp/tests/test_server_runtime.py apps/worker/tests/test_worker_main_cli_coverage.py apps/worker/tests/test_governance_controls.py apps/worker/tests/test_external_proof_semantics.py -q` -> `75 passed in 2.19s`
- `rg -n 'org.opencontainers.image.source' .devcontainer/Dockerfile scripts/ci/build_standard_image.sh` -> source label fallback in Dockerfile + dynamic build-script label both present after `WS4` metadata patch
- `PYTHONPATH="$PWD:$PWD/apps/worker" uv run --extra dev python -m pytest apps/worker/tests/test_governance_controls.py -q` -> targeted governance controls pass after adding standard-image source-metadata regression guard
- `gh auth status` -> active `xiaojiou176` token still lacks `read:packages/write:packages`; backup `terryyifeng` token has `write:packages` but not `read:org`
- `gh repo view xiaojiou176-org/video-analysis-extract --json nameWithOwner,viewerPermission,isPrivate,url` -> viewerPermission `ADMIN`, repo remains public
- `gh api repos/xiaojiou176-org/video-analysis-extract/actions/permissions/workflow` -> default workflow permissions remain `read`; publish workflow still relies on explicit job-level `packages: write`
- `gh api '/orgs/xiaojiou176-org/packages?package_type=container&per_page=100'` -> `403` for active token because `read:packages` missing
- `GH_TOKEN="$(gh auth token --user terryyifeng)" gh api '/orgs/xiaojiou176-org/packages?package_type=container&per_page=100'` -> `[]`
- `GH_TOKEN="$(gh auth token --user terryyifeng)" gh api '/orgs/xiaojiou176-org/packages/container/video-analysis-extract-ci-standard'` -> `404 Package not found`
- `docker manifest inspect ghcr.io/xiaojiou176-org/video-analysis-extract-ci-standard:7113d86f2294f594aad6f5914a6e3e4ab9a3181d` -> `denied`
- `docker version` -> daemon unavailable in current session (`Cannot connect to the Docker daemon ... /Users/yuyifeng/.docker/run/docker.sock`)
- `docker info --format '{{json .ServerVersion}}'` -> daemon unavailable in current session
- `docker context ls` -> contexts exist, but neither `default` nor `desktop-linux` produced a working server connection
- `command -v oras|crane|buildctl|skopeo|podman|nerdctl` + Homebrew/bin scans -> no dockerless OCI push tool available locally
- `osascript -e 'tell application "Docker" to quit'` + `open -a Docker` -> Docker Desktop restart sequence completed, but daemon did not recover into a usable state for CLI/API callers
- `timeout 10 docker version --format '{{.Server.Version}}'` -> timed out after Docker Desktop restart
- `curl --max-time 10 --unix-socket ~/.docker/run/docker.sock -i http://localhost/_ping` -> timed out with zero bytes after Docker Desktop restart
- `POST https://ghcr.io/v2/xiaojiou176-org/video-analysis-extract-ci-standard/blobs/uploads/` (anonymous challenge) -> `WWW-Authenticate` now cleanly points at `repository:xiaojiou176-org/video-analysis-extract-ci-standard:pull`
- direct bearer exchange against `https://ghcr.io/token?service=ghcr.io&scope=repository:xiaojiou176-org/video-analysis-extract-ci-standard:pull,push` -> `200` for both active and backup token paths
- direct registry upload with exchanged bearer token (active path) -> `403 permission_denied: The token provided does not match expected scopes.`
- direct registry upload with exchanged bearer token (backup path) -> `403 permission_denied: write_package`
- `curl -L -s https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry | rg -n 'org.opencontainers.image.source|inherits the access permissions|GitHub Actions workflows in the linked repository automatically get access'` -> official docs confirm source-label / linked-repository inheritance model
- `curl -L -s https://docs.github.com/en/packages/learn-github-packages/connecting-a-repository-to-a-package | rg -n 'Connect repository|Repository source section|LABEL org.opencontainers.image.source'` -> official docs confirm UI linkage path and command-line source-label path
- `curl -L -s https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility | rg -n 'Manage Actions access|Package Creation|Change visibility'` -> official docs confirm workflow access and org package-creation visibility are package/org settings, not repo YAML
- `curl -L -s https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions | rg -n 'if a workflow creates a package using the GITHUB_TOKEN|The package inherits the visibility and permissions model of the repository|repositories that publish packages using a workflow'` -> official docs confirm `GITHUB_TOKEN` publish/inheritance expectations
- `python3 scripts/governance/probe_ghcr_registry_auth.py` -> wrote `.runtime-cache/reports/governance/ghcr-registry-auth-probe.json`
- `.runtime-cache/reports/governance/ghcr-registry-auth-probe.json` -> anonymous challenge matches `repository:xiaojiou176-org/video-analysis-extract-ci-standard:pull`; direct bearer exchange for `pull,push` succeeds for active/backup accounts; upload boundary still returns `403` with `scope mismatch` (active) / `write_package` (backup)

### Risk / Blocker Log

- `WS2` 当前的 product-output 中文残留已收紧到真正终端用户输出层（digest rendering / localized output fallback）；内部 prompt/control 文本不再享受 allowlist 豁免
- `WS4` 的 GHCR 最终 closure 可能依赖仓库之外的 policy 调整
- live 平台对账已进一步压实：本机 `gh` token 路径缺少 `read:packages / write:packages` 能力；hosted workflow 则在 `Standard image publish preflight` 失败，当前更像 token-context + package-permission / org-policy 组合边界
- live 平台对账已进一步压实：具备 `write:packages` 的备用 token 对 org/user package API 仍返回 `404`，因此 GHCR 阻塞不只是 scope 缺失，还疑似包含 package-path / ownership / visibility 边界
- live 平台对账还表明：具备 `write:packages` 的备用账号 token 对 org/user package API 都返回 404，当前还存在 package path / ownership 不清晰的风险
- live 平台对账已进一步压实：具备 `write:packages` 的备用 token 对 org、user、repository package views 看到的仍是空集合或 `404`，而 hosted run 同时明确拥有 `Packages: write` 且 `docker login` 成功；因此当前最像真的阻塞是 package-not-created-or-not-linked / visibility / registry blob-write acceptance，而不是 repo-side naming drift
- 官方文档与 live probe 现已交叉验证：剩余 blocker 不在 repo YAML，不在 source-label，不在镜像命名，而在 GitHub Packages / GHCR 的 package settings 平面（package existence, Connect repository, Manage Actions access, org package-creation visibility）
- `WS1` 当前已尽量规避 branch protection 漂移：主 `ci.yml` 现有 trusted job 名称未改，但仍需后续 remote probe 再确认 required checks 面完全一致
- 当前执行中的 Plan 文件尚未跟踪到 Git；这不阻碍施工，但必须持续保持其与 Repo 实际状态一致
- 最终对账时，runtime retention 可能因本轮自身 gate 再次生成 run manifests 而短暂变红；当前已确认 closing procedure 是“先 prune，再验”
- `WS6` 仍可继续增强，但当前剩余部分已属于信号增强而非 blocker/structural 闭环
- `WS5` 当前仍未做到 API/worker/MCP 全链 everywhere correlation；这已从 blocker 降为深化项
- `WS4` 当前仍无法仅靠本地 Repo 改动闭环；必须进入平台侧 GHCR package / repo linkage / permissions / visibility 修正后，才能把 `Blocked` 改回 `Verified`
- 当前会话内还新增了一个执行层硬边界：即使 repo-side metadata 已修，本机也没有可用 Docker daemon，且缺少 dockerless OCI push 工具，所以无法在本地直接做最小 GHCR push probe；因此剩余主线进一步收敛成“平台侧 UI 修复 + 远端 current-head hosted publish 复验”
- 上述 Docker 边界在本轮又经过一次可逆重启后复验，结果仍未改变；因此当前不再继续本地 Docker 恢复空转，而把剩余行动完全收敛到 GitHub 平台侧设置与远端 hosted publish 复验
- 直接 registry 探针进一步表明：问题已经不是“拿不到目标路径上的 bearer token”，而是“就算 token exchange 成功，registry upload boundary 仍拒绝当前 caller/package state”。这使得 GHCR blocker 的最细读法变成：`token exchange reachable` + `upload boundary denied` + `package/linkage/access still unresolved`

### Files Planned To Change

- `.github/workflows/ci.yml`
- `.github/workflows/_trusted-pr-boundary.yml`
- `.github/workflows/pre-commit.yml`
- `.github/workflows/contract-diff.yml`
- `.github/workflows/env-governance.yml`
- `.github/workflows/vendor-governance.yml`
- `.pre-commit-config.yaml`
- `apps/worker/worker/main.py`
- `apps/mcp/server.py`
- `apps/mcp/tests/test_server_runtime.py`
- `apps/worker/tests/test_worker_main_cli_coverage.py`
- `docs/reference/logging.md`
- `config/governance/logging-contract.json`
- `config/docs/render-manifest.json`
- `config/docs/boundary-policy.json`
- `config/docs/change-contract.json`
- `scripts/governance/check_docs_governance.py`
- `scripts/governance/render_docs_governance.py`
- `scripts/governance/check_ci_workflow_strictness.py`
- `scripts/governance/check_governance_language.py`
- `scripts/governance/check_log_correlation_completeness.py`
- `scripts/governance/render_current_state_summary.py`
- `scripts/governance/check_logging_contract.py`
- `scripts/governance/generate_logging_samples.py`
- `scripts/ci/e2e_live_smoke.sh`
- `scripts/ci/autofix.py`
- `scripts/deploy/recreate_gce_instance.sh`
- `apps/worker/tests/test_external_proof_semantics.py`
- `apps/worker/tests/test_governance_controls.py`
- `apps/worker/worker/pipeline/steps/llm_prompts.py`
- `apps/worker/worker/pipeline/steps/artifacts.py`
- `apps/worker/worker/pipeline/runner_rendering.py`
- `apps/worker/templates/digest.md.mustache`
- `docs/reference/public-repo-readiness.md`
- `docs/reference/public-rights-and-provenance.md`
- `docs/reference/external-lane-status.md`
- `docs/reference/value-proof.md`
- `docs/reference/project-positioning.md`
- `docs/proofs/task-result-proof-pack.md`
- `docs/generated/public-value-proof.md`
- `docs/testing.md`
- `docs/start-here.md`
- `docs/runbook-local.md`

### Files Changed Log

- `2026-03-19 16:54 PDT`
  - 接管并升级执行账本：`.agents/Plans/2026-03-19_16-40-19__repo-ultimate-single-path-final-form-plan.md`
  - 尚未开始业务/治理面代码改动
- `2026-03-19 17:02 PDT`
  - 新增共享 PR trust boundary 入口：`.github/workflows/_trusted-pr-boundary.yml`
  - 接线 self-hosted PR 旁路 workflow：`.github/workflows/pre-commit.yml`, `.github/workflows/contract-diff.yml`, `.github/workflows/env-governance.yml`, `.github/workflows/vendor-governance.yml`
  - 扩展 fleet-level CI strictness gate：`scripts/governance/check_ci_workflow_strictness.py`
- `2026-03-19 17:04 PDT`
  - 删除 render-only 双账本字段：`config/docs/boundary-policy.json`
  - 收敛 generated docs 的 co-change 手工陪跑要求：`config/docs/change-contract.json`
  - 强化 docs governance gate：`scripts/governance/check_docs_governance.py`
  - 修复 pre-commit IaC guard 路径：`.pre-commit-config.yaml`
  - 重渲染治理文档：`docs/testing.md` 与 `docs/generated/*`
- `2026-03-19 17:09 PDT`
  - 新增 rights model：`docs/reference/contributor-rights-model.md`
  - 升级 public/open-source 边界文档：`docs/reference/public-repo-readiness.md`, `docs/reference/public-rights-and-provenance.md`, `CONTRIBUTING.md`, `README.md`
  - 收紧 English-first 深水区 gate：`scripts/governance/check_governance_language.py`
  - 翻译脚本深水区残留：`scripts/ci/e2e_live_smoke.sh`, `scripts/ci/autofix.py`, `scripts/deploy/recreate_gce_instance.sh`
- `2026-03-20 00:34 PDT`
  - 将内部 prompt/control 层切回 English-first：`apps/worker/worker/pipeline/steps/llm_prompts.py`
  - 收紧 locale allowlist，只保留真正终端用户输出层：`scripts/governance/check_governance_language.py`
  - 同步公开边界文档：`docs/reference/public-repo-readiness.md`, `docs/reference/contributor-rights-model.md`
  - 回写执行账本：`.agents/Plans/2026-03-19_16-40-19__repo-ultimate-single-path-final-form-plan.md`
- `2026-03-19 17:11 PDT`
  - 压缩 external lane 读法：`docs/reference/external-lane-status.md`
  - 强化 current-state summary 语义：`scripts/governance/render_current_state_summary.py`
  - 重拍 runtime-owned summary：`.runtime-cache/reports/governance/current-state-summary.md`
- `2026-03-19 23:36 PDT`
  - 把 GHCR 平台修复路径正式写入 `docs/reference/external-lane-status.md`：包含 Connect repository、Manage Actions access、org package-creation visibility、current-head hosted publish rerun 的顺序化步骤
  - 把这轮官方文档 + live GH/API probe 证据压回 Plan，避免下一轮继续靠聊天记忆拼 GHCR 闭环路径
- `2026-03-19 23:15 PDT`
  - 为标准 CI 镜像补 fallback OCI repository-source metadata：`.devcontainer/Dockerfile`
  - 新增最小治理回归保护，防止标准镜像 source metadata 回退：`apps/worker/tests/test_governance_controls.py`
- `2026-03-19 23:13 PDT`
  - 继续压实 GHCR 平台边界的 reading rule：`docs/reference/external-lane-status.md`
  - 更新执行账本以记录 repo-side naming 对齐、hosted run `Packages: write`、以及 org/user/repository package views 为空的最新平台证据：`.agents/Plans/2026-03-19_16-40-19__repo-ultimate-single-path-final-form-plan.md`
- `2026-03-19 17:14 PDT`
  - 清理 runtime-cache 过期 artifacts：`.runtime-cache/run/manifests/*`, `.runtime-cache/reports/tests/pr-llm-real-smoke-result.json`
  - 拉绿 runtime retention/freshness/log retention gate
  - 在当前 clone 启用 `.githooks`：`./bin/install-git-hooks`
- `2026-03-19 17:18 PDT`
  - 为 value-proof 增补 current-safe reading rule：`docs/reference/value-proof.md`
  - 为 representative proof pack 增补 current-truth pairing boundary：`docs/proofs/task-result-proof-pack.md`
- `2026-03-19 22:06 PDT`
  - 生成独立 public-safe value proof pointer/page：`docs/generated/public-value-proof.md`
  - 扩展 docs control plane render list：`config/docs/render-manifest.json`
  - 扩展 docs governance renderer：`scripts/governance/render_docs_governance.py`
- `2026-03-19 22:13 PDT`
  - 为 GHCR 增补 package-path / ownership 读法：`docs/reference/external-lane-status.md`
  - 复跑 docs/current-state 相关 gate：`scripts/governance/check_docs_governance.py`, `scripts/governance/render_current_state_summary.py`, `scripts/governance/check_current_state_summary.py`
- `2026-03-19 22:45 PDT`
  - 为 GHCR 新 failure 语义补充回归测试：`apps/worker/tests/test_external_proof_semantics.py`
  - 为 logging correlation / public value proof pointer 补充治理测试：`apps/worker/tests/test_governance_controls.py`
- `2026-03-19 22:30 PDT`
  - 将 public-safe value proof pointer 接入更容易发现的入口：`README.md`, `docs/reference/project-positioning.md`
- `2026-03-19 22:58 PDT`
  - 为 MCP upstream request 增补稳定 operation 分类：`apps/mcp/server.py`
  - 为 MCP operation 语义补充 targeted tests：`apps/mcp/tests/test_server_runtime.py`
  - 为日志读法补充 operation 分类说明：`docs/reference/logging.md`
  - 复跑 docs governance，确认新入口接入未破坏 docs control plane
- `2026-03-19 23:02 PDT`
  - 为 MCP dict-success / http-error 相关性补充行为级测试：`apps/mcp/tests/test_server_runtime.py`
  - 为 worker command started/completed/failed 与 worker-loop 生命周期补充行为级测试：`apps/worker/tests/test_worker_main_cli_coverage.py`
  - 复跑 logging contract / correlation / structured log 三道 Gate 与 targeted regression，确认 `WS5` 已无新的本地 evidence-backed 缺口
- `2026-03-19 17:24 PDT`
  - 重新执行 runtime cache maintenance：`python3 scripts/runtime/prune_runtime_cache.py --apply`
  - 确认最终收口口径：`check_runtime_cache_retention.py`, `check_runtime_cache_freshness.py`, `check_log_retention.py` 在 prune 后再次通过
- `2026-03-19 17:38 PDT`
  - 为 worker CLI 控制面接入结构化命令日志：`apps/worker/worker/main.py`
  - 为 MCP 到 API 的关键请求接入结构化请求/失败日志：`apps/mcp/server.py`
  - 同步 logging 文档：`docs/reference/logging.md`
- `2026-03-19 17:45 PDT`
  - 重拍外部工作流探针：`.runtime-cache/reports/governance/external-lane-workflows.json`
  - 重拍 runtime-owned 当前状态页：`.runtime-cache/reports/governance/current-state-summary.md`
  - 将 GHCR lane 从旧 `queued` 语义压实为 `current-head hosted failure at Standard image publish preflight`
- `2026-03-19 22:55 PDT`
  - 将 worker/MCP 新日志面纳入 logging sample 生成：`scripts/governance/generate_logging_samples.py`
  - 将 worker/MCP 新日志面纳入 logging contract optional sample targets：`config/governance/logging-contract.json`
  - 让 logging contract / correlation gate 正式认账这两类新日志面：`scripts/governance/check_logging_contract.py`, `scripts/governance/check_log_correlation_completeness.py`
