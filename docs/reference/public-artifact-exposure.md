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

## Default Rules

- 只要样本依赖真实密钥、真实用户、真实客户路由、或生产级身份语境，默认不直接 public。
- 对外优先用 sanitized / synthetic evidence。
- internal-only 资产可以保留在仓库，但不能作为 public narrative 主证据。
- tracked public tree 中禁止保留原始 provider probe TSV、真实公网路由、真实对象标识。
- 如果某个样本要进入 tracked public tree，必须同时满足：policy 显式 allowlist、文件真实存在、并且仍属于脱敏或合成证据。
- tracked `artifacts/releases/**/manifest.json` 若保留在 Git 中，必须显式声明 `historical_example=true` 与 `evidence_scope=historical-example`。
