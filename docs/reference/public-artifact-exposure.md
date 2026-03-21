# Public Artifact Exposure

下面这张表的作用很简单：告诉未来维护者“哪些样本能对外，哪些只能内部留档”。

| Surface | Classification | Reason | Action |
| --- | --- | --- | --- |
| `artifacts/performance/cwv-budget.json` | safe to publish | 仅包含前端预算阈值 | 保持公开 |
| `artifacts/performance/rum-baseline.json` | publish after sanitization | 来自真实观测聚合，但已去掉生产来源标识 | 仅保留聚合指标，不写真实来源 |
| `artifacts/performance/rum-observations.json` | replace with synthetic sample | 样本形态容易被误读为直接生产导出 | 仅保留脱敏数值样本与合成来源说明 |
| `artifacts/performance/rsshub/*.tsv` | forbidden in tracked public tree unless explicitly allowlisted | 原始 probe TSV 会暴露真实路由、对象或公网节点语境 | 默认禁止；只有 policy 中显式 allowlist 的 sample 才能被 track |
| `artifacts/performance/rsshub/public_probe_summary.sample.tsv` | safe to publish via explicit allowlist | 合成化、脱敏后的公开样本 | 只允许保留这一份 allowlisted 分类摘要，不保留真实 route / uid / up_name |
| `artifacts/releases/*` | safe to publish with boundary note | 历史 evidence 可公开，但不能冒充当前 release verdict | 必须保留“historical examples, not canonical verdict”说明 |
| `docs/generated/public-value-proof.md` | safe to publish as tracked pointer page | 它只负责告诉读者“先看哪几层证据”，不承载 current runtime verdict | 允许 track，但必须保持 pointer-only 语义 |
| `.agents/Plans/*.md` | internal-only execution ledger | 这些文件记录内部施工顺序、决策草稿与执行状态，不属于 public-safe narrative | 默认不 track；只允许当前执行中的本地文件存在于工作树 |
| `.agents/Conversations/**` | internal-only session residue | 会混入对话上下文、临时结论和未审内容 | 默认禁止进入 tracked public tree |
| `.env` | local private worktree only | 包含运行时 secrets；就算未被 Git 跟踪，也不能被目录级打包分享 | 只允许本地存在，永不进入 public-safe surface |
| `.runtime-cache/**` | runtime-owned current-state evidence | 这些产物用于 current truth 与本地验证，不是 clone-safe narrative | 允许本地生成，禁止当作 tracked public surface |

## Default Rules

- 只要样本依赖真实密钥、真实用户、真实客户路由、或生产级身份语境，默认不直接 public。
- 对外优先用 sanitized / synthetic evidence。
- internal-only 资产可以保留在仓库，但不能作为 public narrative 主证据。
- internal-only 资产也不能因为“没有被 Git 跟踪”就被默认为可打包分享；worktree-level sharing 必须显式排除 `.env`、`.runtime-cache/**`、`.agents/Plans/**`、`.agents/Conversations/**`。
- tracked public tree 中禁止保留原始 provider probe TSV、真实公网路由、真实对象标识。
- 如果某个样本要进入 tracked public tree，必须同时满足：policy 显式 allowlist、文件真实存在、并且仍属于脱敏或合成证据。
- tracked `artifacts/releases/**/manifest.json` 若保留在 Git 中，必须显式声明 `historical_example=true` 与 `evidence_scope=historical-example`。

## Current-proof Rule

- tracked docs 不再承载 commit-sensitive current-state payload。
- `docs/generated/external-lane-snapshot.md` 只能当 pointer / reading rule。
- 当前 external/public 状态必须从 runtime-owned reports 读取，尤其是 `.runtime-cache/reports/governance/current-state-summary.md` 与底层 runtime artifacts。
- 当前 public/security freshness 还必须读取 `.runtime-cache/reports/governance/open-source-audit-freshness.json`；旧 commit 的 gitleaks 收据不能当 current artifact exposure proof。
- `docs/generated/public-value-proof.md` 可以作为 public-safe 导航页存在于 tracked tree，但它只是阅读指引，不得升级包装成 current proof artifact。
