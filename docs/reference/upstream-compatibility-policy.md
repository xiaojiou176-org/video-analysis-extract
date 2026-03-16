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

## 状态语义

- `verified`：这条组合在 freshness window 内真的有验收工件，等同于“这批货刚验过，票据就在档案柜里”。
- `pending`：组合仍被支持，但当前工作区没有新鲜验收工件，不能冒充“刚验过”。
- `declared`：只有设计/登记，没有进入当前主链验证面。
- `waived`：明确豁免，必须由文档或决策记录解释原因。

## Freshness Policy

- blocker 链路：推荐 `<= 72h`
- important 链路：推荐 `<= 168h`
- 超出 freshness window 后，即使 artifact 仍存在，也必须视为 `stale`

## 硬规则

- `verified` 状态只能基于 freshness window 内的 artifact；非 `verified` 行不计入当前兼容性通过证明。
- artifact metadata 必须能追溯到 `source_run_id` 与 `source_commit`。
- 兼容矩阵的失败归因必须落到统一 failure class 枚举。
- blocker 行若要升级到 `verified`，其 row-specific artifact 必须和 `last_verified_run_id` 形成同轮次证据束。
- `upstream-compat-report.json` 这类共享治理汇总页可以作为辅助索引，但不能单独充当 blocker 行的 same-run 闭环证明。
