# AI Evaluation

这套评估先讲人话，就是“给模型出一张固定考卷”，以后每次改 prompt、tool path、guardrail 或 provider 行为，都能知道是变好还是变坏。

## Minimal Formal Eval Kit

- golden set：`evals/golden-set.sample.jsonl`
- rubric：`evals/rubric.md`
- baseline：`evals/baseline.json`
- asset guard：`python3 scripts/governance/check_eval_assets.py`

## Eval Goal

当前不追求学术 benchmark，而追求三件事：

1. 能判断回归
2. 能解释为什么不过
3. 能把质量、引用卫生、失败诚实度纳入同一套 rubric

## Regression Gate

repo-side 最小门禁：

- baseline 文件存在且字段完整
- golden set 至少有可复用样例
- rubric 明确维度与通过规则
- regression policy 明确 block 条件

## Cost / Quality / Latency Triangle

- 质量优先： factuality、coverage、citation hygiene、failure honesty
- 成本受控：先用小样本 golden set 做 regression，而不是每次都跑重型 live eval
- 延迟受控：repo-side 只强制资产与 policy，真实 live/provider 评估进入 external lane
