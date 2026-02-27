# Testing Governance Baseline (Phase0)

本文档固化 Phase0 的测试治理基线（D1-D5），作为 CI 与文档一致性的最小真相源。

## D1-D5 拍板结论

| ID | 策略 | 基线要求 |
|---|---|---|
| D1 | PR 强制 live-smoke | `pull_request` 必须执行 `live-smoke`，不得以 optional/跳过放行 |
| D2 | Mutation 阈值 | Python 核心模块 mutation score 必须 `>= 0.85` |
| D3 | Web 覆盖率 | Web 总覆盖率必须 `>= 80%`，Web 核心模块覆盖率必须 `>= 90%` |
| D4 | 禁止 skip 放行 | 关键 gate（含 `live-smoke`）不允许 `skipped` 视为通过 |
| D5 | E2E Real API | E2E 必须包含 Real API 链路验证，不允许仅 mock 覆盖全部门禁 |

## CI 对齐要求

- `docs/testing.md` 必须明确包含上述 D1-D5 关键策略。
- CI 中必须接入 `scripts/check_ci_docs_parity.py` 作为文档一致性门禁。
- 任何 D1-D5 变更必须同步更新本文档与 `docs/testing.md`。

## 失败策略

- 若 `docs/testing.md` 缺失任一关键策略关键词，`check_ci_docs_parity.py` 必须非 0 退出。
- 非 0 退出视为门禁失败，禁止合并。
