# 终局治理验收合同

这份文档只定义三件事：唯一真相源、终局门槛、宣告条件。  
它不是路线图，不是愿景海报，也不是“差不多完成”的说明文。

## 1. 唯一真相源

终局治理只认下面这些结构化事实源：

- `config/governance/root-allowlist.json`
- `config/governance/runtime-outputs.json`
- `config/governance/logging-contract.json`
- `config/governance/dependency-boundaries.json`
- `config/governance/active-upstreams.json`
- `config/governance/upstream-templates.json`
- `config/governance/upstream-compat-matrix.json`

执行入口只认：

```bash
./scripts/governance_gate.sh --mode pre-commit
./scripts/governance_gate.sh --mode pre-push
./scripts/governance_gate.sh --mode ci
./scripts/governance_gate.sh --mode audit
```

说明文档不得再手写一套并行规则。若文档与上述事实源冲突，以结构化事实源为准。

## 2. 终局门槛

### 97 分

- 五维硬门禁全部接入主链并通过：
  - 根目录白名单
  - 运行时输出路径
  - 依赖边界
  - 日志契约
  - 外部上游治理
- 不存在任何旧路径、旧口径、旧字段的主链引用。

### 98 分

- clean-room 验收通过。
- 根目录洁净验收通过。
- 删除 `.runtime-cache/` 后可以重建并重新通过治理门禁。

### 99 分

- 日志证据层贯通：治理/测试/应用至少三类日志有结构化样本且字段完整。
- 上游验证报告贯通：兼容矩阵、验证入口、artifact 合同一致。
- 失败归因可以区分本仓逻辑、测试失败、治理失败、上游失败、版本组合失败。

### 100 分

- 连续 3 次 monthly governance audit 无 drift。
- 所有终局声明都能直接映射到结构化事实源或 artifact。
- 若存在真实 vendor/fork/subtree 使用面，必须被持续验证；若不存在，禁止为了凑分伪造样板。

## 3. 宣告条件

只有同时满足以下条件，才允许宣称仓库达到终局治理口径：

1. `governance_gate.sh` 四种模式都通过。
2. `strict_ci_entry.sh --mode pre-push --strict-full-run 1 --ci-dedupe 0` 通过。
3. monthly governance audit 最近 3 次连续无 drift。
4. 本文每条终局声明都能被事实源或 artifact 复核。

若任一条件不满足，禁止宣称“接近终局”“基本完成”“只差一点”。
