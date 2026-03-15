# Upstream Compatibility Policy

`config/governance/upstream-compat-matrix.json` 记录的是“哪些上游组合被允许进入主链”，不是永久荣誉榜。

## 兼容判定最小条件

每条 matrix row 至少需要：

- `verification_status`
- `last_verified_at`
- `last_verified_run_id`
- `freshness_window_hours`
- `verification_scope`
- `verification_artifacts`

## Freshness Policy

- blocker 链路：推荐 `<= 72h`
- important 链路：推荐 `<= 168h`
- 超出 freshness window 后，即使 artifact 仍存在，也必须视为 `stale`

## 硬规则

- current verification 只能基于 freshness window 内的 artifact。
- artifact metadata 必须能追溯到 `source_run_id` 与 `source_commit`。
- 兼容矩阵的失败归因必须落到统一 failure class 枚举。
