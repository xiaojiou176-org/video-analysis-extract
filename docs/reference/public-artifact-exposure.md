# Public Artifact Exposure

下面这张表的作用很简单：告诉未来维护者“哪些样本能对外，哪些只能内部留档”。

| Surface | Classification | Reason | Action |
| --- | --- | --- | --- |
| `artifacts/performance/cwv-budget.json` | safe to publish | 仅包含前端预算阈值 | 保持公开 |
| `artifacts/performance/rum-baseline.json` | publish after sanitization | 来自真实观测聚合，但已去掉生产来源标识 | 仅保留聚合指标，不写真实来源 |
| `artifacts/performance/rum-observations.json` | replace with synthetic sample | 样本形态容易被误读为直接生产导出 | 仅保留脱敏数值样本与合成来源说明 |
| `artifacts/performance/rsshub/*` | publish after sanitization | 是性能/稳定性证据，但不能暗示真实内部监控链 | 仅保留公开可解释的 probe 摘要 |
| `artifacts/releases/*` | safe to publish with boundary note | 历史 evidence 可公开，但不能冒充当前 release verdict | 必须保留“historical examples, not canonical verdict”说明 |

## Default Rules

- 只要样本依赖真实密钥、真实用户、真实客户路由、或生产级身份语境，默认不直接 public。
- 对外优先用 sanitized / synthetic evidence。
- internal-only 资产可以保留在仓库，但不能作为 public narrative 主证据。
