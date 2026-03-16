# Upstream Governance

本仓不是纯 internal repo。多个外部 API、image、binary 会直接决定主链是否成立，因此必须作为上游系统治理。

## 真相源

- `config/governance/active-upstreams.json`
- `config/governance/upstream-compat-matrix.json`
- `config/governance/upstream-registry.json`
- `config/governance/upstream-templates.json`

## 分层

- `active`：当前现役上游，必须有 evidence 与 freshness discipline。
- `template`：预案层，不计入现役成熟度。
- `retired`：历史上游，保留审计记录但不参与当前主链。

## 硬规则

- `pin`、`digest`、历史 `verified` 不能直接等同于“当前仍兼容”。
- blocker 级上游超 freshness window 必须失败。
- future vendor/fork/patch 一旦现役，必须同步创建 `UPSTREAM.lock`、`README.md`、`PATCHES.md`。

## 门禁

```bash
python3 scripts/governance/check_upstream_governance.py
python3 scripts/governance/check_unregistered_upstream_usage.py
python3 scripts/governance/check_upstream_compat_freshness.py
python3 scripts/governance/check_upstream_same_run_cohesion.py
python3 scripts/governance/check_active_upstream_evidence_fresh.py
python3 scripts/governance/check_upstream_failure_classification.py
python3 scripts/governance/check_vendor_registry_integrity.py
```

补充口径：

- blocker 级兼容链现在不仅要“有新鲜 artifact”，还要能证明这些 artifact 属于同一轮验证批次。
- 你可以把它理解成“同一批货的验收票据必须来自同一次点货”，不能拿上午一张、下午一张、上周一张拼成“好像都验过了”。
- 这条规则由 `check_upstream_same_run_cohesion.py` 执行；非 `verified` 的 blocker row 可以暂时保持 `pending`，但一旦要升为 `verified`，就必须满足同轮次证据束要求。
