# Root Governance

根目录只承担两类职责：

- **公共仓库资产**：允许被 Git 跟踪、允许作为公共制度入口存在。
- **本地私有容忍项**：允许出现在根目录，但必须保持 untracked。

## 公共仓库资产真相源

- `config/governance/root-allowlist.json` 的 `tracked_root_allowlist`
- `config/governance/root-denylist.json`
- `config/governance/root-layout-budget.json`
- `config/governance/public-entrypoints.json`

## 终局入口约束

- `.agents/Plans/`：仓库内执行计划与施工控制板，属于受治理的公共制度入口。
- `bin/`：稳定公开命令入口。人类、Hook、CI、文档只应引用 `bin/*`，不应再把 `scripts/*` 当作长期公共接口。

## 本地私有容忍项

以下路径允许出现在根目录，但必须保持 untracked：

- `.env`
- `.vscode/`
- `.codex/`
- `.claude/`
- `.cursor/`

## 门禁

```bash
python3 scripts/governance/check_root_allowlist.py --strict-local-private
python3 scripts/governance/check_root_layout_budget.py
python3 scripts/governance/check_root_zero_unknowns.py
python3 scripts/governance/check_root_dirtiness_after_tasks.py --compare-snapshot <snapshot>
python3 scripts/governance/check_public_entrypoint_references.py
```

补充口径：

- `check_root_dirtiness_after_tasks.py` 现在不只检查“根目录门厅”有没有新增垃圾，还会同步检查 `.runtime-cache/` 这个仓库级运行时出口是否长出未登记的直系子目录。
- 换句话说，根目录洁净的最终裁决已经升级为“门厅干净 + 运行时总杂物间入口也没有偷偷长歪”。

## 硬规则

- 禁止新增未登记顶级项。
- 禁止把 denylist 中的泛化目录重新放回根目录。
- 禁止将本地私有容忍项纳入 Git。
- 禁止把局部 helper、实验脚本、一次性输出平铺到根目录。
- 禁止为方便起见绕过 `bin/*` 直接把 `scripts/*` 暴露给文档、Hook 或 Workflow 作为公共入口。
