# Newcomer Result Proof

这页先讲人话：它是“新人第一次进仓，哪些收据已经 fresh 拿到了，哪些还没有”的统一读数，不再让这些判断散落在聊天、历史 log 和脑内记忆里。

## Canonical Runtime Report

- `.runtime-cache/reports/governance/newcomer-result-proof.json`

## Reading Rule

- `newcomer_preflight=status=pass` 代表当前 HEAD 至少拿到了 `validate-profile --profile local` 的 fresh 收据。
- `repo_side_strict_receipt=status=pass` 才能说明当前 HEAD 拿到了 fresh strict receipt。
- `repo_side_strict_receipt=status=missing_current_receipt` 不是失败，而是“这条最重收据还没在当前 commit 上被 fresh 捕获”。
- `governance_audit_receipt=status=pass` 代表 repo-side governance 总闸已拿到 fresh PASS 收据。
- 结果证明不只看治理，还会同时引用 eval regression 与 current-proof 对齐结果。

## Why This Exists

- 防止把 “newcomer path 看起来写清楚了” 误读成 “已经有 fresh newcomer receipt”
- 防止把 “repo-side strict 命令启动过” 误读成 “已经拿到 fresh strict PASS 收据”
- 给下一轮把 newcomer/result proof 真正接进主链时，提供一个当前 truth pack 入口
