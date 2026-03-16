# Eval Assets

本目录保存最小 formal eval 资产，用来证明“这个仓库不是靠口头感觉说 AI 变好了”。

## Files

- `golden-set.sample.jsonl`: 最小样例集
- `rubric.md`: 评分维度与失败解释规则
- `baseline.json`: 当前默认 baseline 与 regression gate

## Repo-side Gate

```bash
python3 scripts/governance/check_eval_assets.py
```

这条 gate 只验证资产、规则和 baseline 是否齐套，不把真实 provider 成本强行混进 repo-side 必过链路。
