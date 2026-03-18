# Architecture Governance

仓库采用责任分层，不采用按语言堆放的拓扑。

## 责任层

- `apps/`：运行时服务与应用入口
- `contracts/`：共享 contract / schema 的唯一公开层
- `integrations/`：外部 API、binary、platform、reader 的唯一转接层
- `infra/`：基础设施、compose、migration、environment contract
- `scripts/`：治理、CI、runtime、deploy、release 入口
- `config/governance/`：治理真相源

## 契约层

- `contracts/source/openapi.yaml`
- `contracts/generated/jsonschema/*`

## 模块归属真相源

- `config/governance/module-ownership.json`

## 硬规则

- 跨 app 共享只允许走 contract/package，不允许走 sibling app 内部实现。
- 跨 app 共享只允许走 `contracts/`，不允许走 sibling app 内部实现。
- `apps/mcp` 不得导入 `apps/api` / `apps/worker` 内部实现。
- `apps/web` 不得通过路径穿透读取后端实现。
- `contracts/` 不得引入网络、env、subprocess、socket 等运行时 side effect。
- 所有外部 provider / binary / platform glue 必须进入 `integrations/`，不得散落在业务层。

当前已完成的收口样例：

- article 外部抓取与正文提取：`integrations/providers/article_fetch.py`
- RSS feed 解析与 risk-control helper：`integrations/providers/rsshub.py`
- YouTube comments API base / video id / request-retry：`integrations/providers/youtube_comments.py`
- Bilibili comments API base / headers / aid/bvid 提取 / request-retry：`integrations/providers/bilibili_comments.py`

## 门禁

```bash
python3 scripts/governance/check_dependency_boundaries.py
python3 scripts/governance/check_module_ownership.py
python3 scripts/governance/check_governance_schema_references_exist.py
python3 scripts/governance/check_contract_locality.py
python3 scripts/governance/check_no_cross_app_implementation_imports.py
python3 scripts/governance/check_generated_vs_handwritten_contract_surfaces.py
```
