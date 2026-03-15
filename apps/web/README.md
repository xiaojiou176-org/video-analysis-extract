# apps/web

`apps/web` 是仓库的管理台与可视化入口，负责展示 feed、jobs、artifacts、UI audit 等控制面信息。

## 责任

- 渲染管理界面与操作入口
- 通过公开 API 契约访问后端
- 产出可审计的 E2E、A11y、覆盖率与 perceived-performance 证据

## 依赖边界

- 可以依赖：Web 本地组件/工具、共享契约、公开 API 类型与文档
- 不允许依赖：`apps/api`、`apps/worker`、`apps/mcp` 的实现文件

## 运行与证据

- Web E2E 与 perceived evidence 进入 `.runtime-cache/evidence/`
- Web 覆盖率与测试报告进入 `.runtime-cache/reports/`
