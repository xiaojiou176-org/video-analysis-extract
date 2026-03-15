# Shared Contracts Agent Notes

- 这里是公开 contract 层，不是运行时代码层。
- 允许修改：OpenAPI、JSON schema、schema README、与 contract 对齐直接相关的文档。
- 禁止修改：引入运行时代码、环境读取、网络访问、shell 行为、复制 app 内部实现。
- 修改后必须跑：
  - `python3 scripts/governance/check_contract_surfaces.py`
  - `python3 scripts/governance/check_contract_locality.py`
  - `python3 scripts/governance/check_generated_vs_handwritten_contract_surfaces.py`
