# JSON Schemas

Phase 3 共享契约副本：
- `common.schema.json`: Worker 通用对象与 pipeline 结果契约。
- `steps.schema.json`: Poll/Process workflow 与 activity 输入输出契约。
- `mcp-tools.schema.json`: MCP tools 完整清单契约（与 `apps/mcp/schemas/tools.json` 保持逐字段一致，包含 notifications/reports 工具）。

源码来源：
- `apps/worker/worker/contracts/*.json`
- `apps/mcp/schemas/tools.json`

一致性校验（本地）：
```bash
python - <<'PY'
import json
from pathlib import Path
src = json.loads(Path("apps/mcp/schemas/tools.json").read_text(encoding="utf-8"))
dst = json.loads(Path("packages/shared-contracts/jsonschema/mcp-tools.schema.json").read_text(encoding="utf-8"))
raise SystemExit(0 if src == dst else 1)
PY
```
