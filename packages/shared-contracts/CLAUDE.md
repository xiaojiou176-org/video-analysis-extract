# Shared Contracts Memory

- `packages/shared-contracts` 是跨边界 contract-only 层。
- `openapi.yaml` 是 API public surface 真相源。
- `jsonschema/*.json` 是共享 schema 副本，必须与上游 contract surface 保持可校验一致。
- 禁止在这里放运行时 helper、env access、network code、subprocess、socket、shell glue。
- 任何 contract 变更都必须同步通过 governance parity checks。
