# Eval Rubric

## Dimensions

| Dimension | What it means |
| --- | --- |
| factuality | 关键事实不乱编，不与输入证据冲突 |
| coverage | 关键输入信号没有被漏掉 |
| citation_hygiene | 引用与证据边界清楚，不把猜测写成事实 |
| failure_honesty | 无法确认时会老实标记边界，不假装完整 |

## Pass Rule

- 单条样例必须没有 blocker 级 factuality failure
- 总通过率必须达到 baseline 中声明的最低值

## Regression Gate

- 任一关键维度低于 baseline floor 时阻断
- 总通过率低于 baseline 时阻断
- 若只是 external-provider 波动，则记录为 external lane，不直接污染 repo-side gate
