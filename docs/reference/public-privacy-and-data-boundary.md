# Public Privacy And Data Boundary

这页专门回答一个问题：**这个公开仓到底会不会把不该公开的数据、遥测、样本、运行信息一起带出去。**

## Canonical Sources

- 样本公开边界：`docs/reference/public-artifact-exposure.md`
- current external/public 口径：`docs/reference/public-repo-readiness.md`
- 安全报告边界：`SECURITY.md`
- 环境模板：`.env.example`

## What The Public Repo Does Not Ship

- 不随仓库公开真实 provider key、真实 token、真实私有部署拓扑。
- 不把真实生产样本、真实公网路由、真实对象标识直接留在 tracked public tree。
- 不承诺 hosted telemetry backend，也不把私有观测链路包装成公共产品能力。

## Public-safe Data Rule

- public tree 里允许的样本，必须是 **sanitized** 或 **synthetic**。
- `artifacts/performance/rsshub/public_probe_summary.sample.tsv` 这类样本，只有在 policy 显式 allowlist 且仍为脱敏/合成证据时才允许保留。
- `rum-baseline` / `rum-observations` 这类公开样本，只能保留聚合指标，不保留真实来源身份线索。

## Operator Boundary

- provider/live lane 需要的真实账号、真实配额、真实外部服务状态，不属于 public repo 默认交付内容。
- `repo-side done` 与 `external done` 必须分层说明；后者可能依赖真实 provider、GHCR、远端 workflow、平台权限。
- 外部链路如果 blocked，必须诚实写成 blocker，不能因为仓库已经公开就说“外部也可高信心采用”。
- 平台能力如果只是 policy 文档里写了入口，但 current probe 没有证明当前可用，也必须按 conditional capability 说明，不能包装成默认可用。

## Privacy Rule

- 当前公开仓的重点是 **source-first 可审阅**，不是收集用户遥测的 hosted 产品。
- 如果未来新增任何会落到 tracked public surface 的观测样本、截图、日志、trace、HTML、TSV、HAR、video evidence，必须先在 `public-artifact-exposure.md` 增加明确分类与处理动作。
- 对外样本一律默认最小暴露面：能聚合就不公开原始，能 synthetic 就不公开半真实。

## Reporting Rule

对外说明“数据 / 隐私 / 样本”时，至少要同时说清：

- 哪些只是 sanitized sample
- 哪些不是当前 official proof
- 哪些 external lane 需要真实 provider 条件
- 仓库本身不提供 hosted privacy promise
