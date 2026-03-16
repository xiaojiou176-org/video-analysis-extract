# AI Evaluation

这套评估先讲人话，就是“给模型出一张固定考卷”，以后每次改 prompt、tool path、guardrail 或 provider 行为，都能知道是变好还是变坏。

## Minimal Formal Eval Kit

- golden set：`evals/golden-set.sample.jsonl`
- rubric：`evals/rubric.md`
- baseline：`evals/baseline.json`
- asset guard：`python3 scripts/governance/check_eval_assets.py`
- deterministic regression：`python3 scripts/evals/run_regression.py`
- regression gate：`python3 scripts/governance/check_eval_regression.py`

## Current Coverage

- 当前 repo-side deterministic golden set 已扩到 **20 个 case**
- 覆盖两大任务面：
  - structured outline / topic coverage
  - grounded digest / citation hygiene / failure honesty
- 这仍然不是 provider-heavy live eval，也不是学术 benchmark；它的目标是让 repo-side 改动可以被更厚地判定进退

## Eval Goal

当前不追求学术 benchmark，而追求三件事：

1. 能判断回归
2. 能解释为什么不过
3. 能把质量、引用卫生、失败诚实度纳入同一套 rubric

## Repo-side Deterministic Regression

repo-side 现在不只检查“考卷在不在”，还要检查“评分器能不能把固定样卷跑出结果”。

- `run_regression.py` 会对 golden set 里的 `fixture_response` 做 deterministic 评分
- 输出写入 `.runtime-cache/reports/evals/<run_id>.json`
- `check_eval_regression.py` 会检查最新 regression report 是否存在、是否带 metadata、是否满足 baseline

## Regression Gate

repo-side 最小门禁现在分两层：

- baseline 文件存在且字段完整
- golden set 至少有可复用样例
- rubric 明确维度与通过规则
- regression policy 明确 block 条件
- deterministic regression report fresh 存在，且 pass_rate / 维度分数不低于 baseline

## Cost / Quality / Latency Triangle

- 质量优先： factuality、coverage、citation hygiene、failure honesty
- 成本受控：先用小样本 golden set + fixture responses 做 deterministic regression，而不是每次都跑重型 live eval
- 延迟受控：repo-side 强制 deterministic regression；真实 provider/live eval 继续放在 external lane
