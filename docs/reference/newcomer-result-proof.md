# Newcomer Result Proof

这页先讲人话：它是“新人第一次进仓，哪些收据已经 fresh 拿到了，哪些还没有”的统一读数，不再让这些判断散落在聊天、历史 log 和脑内记忆里。

## Canonical Runtime Report

- `.runtime-cache/reports/governance/newcomer-result-proof.json`
- `docs/proofs/task-result-proof-pack.md`（代表性结果证据卷宗，供人类读者查看案例，不承担 current verdict）

## Reading Rule

- `newcomer_preflight=status=pass` 代表当前 HEAD 至少拿到了 `validate-profile --profile local` 的 fresh 收据。
- `repo_side_strict_receipt=status=pass` 才能说明当前 HEAD 拿到了 fresh strict receipt。
- `representative_result_cases` 会给出 2-3 个稳定 case id，指向 `docs/proofs/task-result-proof-pack.md` 里的代表性结果案例；这些案例是 public-safe representative proof，不是 current external verdict。
- `repo_side_strict_receipt=status=missing_current_receipt` 不是“命令不存在”，也不是“governance 已经自动兜底通过”，而是“当前 HEAD 的 latest strict receipt 还没被 fresh 捕获成 PASS”。
- `governance_audit_receipt=status=pass` 代表 repo-side governance 总闸已拿到 fresh PASS 收据。
- `worktree_state.dirty=true` 代表当前工作树带有未提交改动；这时报告最多只能诚实到 `partial`，因为 commit-aligned 收据并不能完整证明这份脏工作树。
- newcomer/result proof 的职责是回答“repo-side newcomer 与 strict 收据今天拿到了没有”；它不替代 external lane current verdict。
- 如果你想看“这个仓库到底拿什么代表性结果来证明自己有价值”，请继续读 `docs/proofs/task-result-proof-pack.md`；它提供的是 representative cases，不是 current external verdict。
- 如果你想看“这些 representative cases 应该按什么顺序读”，请读 `docs/generated/public-value-proof.md`；那一页是 pointer，不是 newcomer/current-state receipt。
- 结果证明不只看治理，还会同时引用 eval regression 与 current-proof 对齐结果。
- `docs/generated/external-lane-snapshot.md` 不再提供 current verdict；外层当前状态要看 runtime-owned 汇总和底层 reports。
- `.runtime-cache/reports/governance/current-state-summary.md` 只是 runtime-owned 聚合页，不是免检通行证；如果它自己的 `.meta.json` `source_commit` 不等于当前 HEAD，整页都只能按 `historical` / `mismatch` 理解，不能拿里面的 green-like 行当 current verdict。

补充边界：

- 不得把 `governance_audit_receipt=status=pass` 单独解释成 repo-side done。
- 不得把 `repo_side_strict_receipt=status=missing_current_receipt` 轻描淡写成“差不多完成”；这正是 repo-side current receipt 尚未闭环的信号。
- 不得在 `worktree_state.dirty=true` 时，把 `status=partial` 包装成“已经等价 pass”；这只是“当前脏工作树下，有一批 commit-aligned 收据可参考”。
- 不得把 `remote-required-checks=status=pass`、`governance_audit_receipt=status=pass` 或 newcomer receipt 组合包装成 `ci-final-gate` / `live-smoke` / nightly terminal closure；这些外层 terminal lane 仍要看各自 current runtime/workflow 证据。
- 若要判断“外部世界是否认账”，应转到 `docs/reference/external-lane-status.md` 和 `.runtime-cache/reports/governance/current-state-summary.md`，不要从 newcomer 页面反推 external lane。
- 如果 external lane 的 remote workflow 明明还是旧 head，那么 current-state summary 最多只能保留 `ready` / `blocked` 这类当前本地读数，不能把它升级包装成 current `verified`。

## Why This Exists

- 防止把 “newcomer path 看起来写清楚了” 误读成 “已经有 fresh newcomer receipt”
- 防止把 “repo-side strict 命令启动过” 误读成 “已经拿到 fresh strict PASS 收据”
- 防止把 “governance-audit 已绿” 误读成 “repo-side done 已闭环”
- 防止把 “当前工作树是脏的，但 receipts 都是 pass” 误读成 “当前这份脏工作树已经 fresh 验证完毕”
- 给下一轮把 newcomer/result proof 真正接进主链时，提供一个当前 truth pack 入口
- 防止把“AI 路径返回了某种结构化结果”误读成“该路径已经真实成功执行”
