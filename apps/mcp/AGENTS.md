# MCP Module Governance

## 0. Canonical Scope

- This file is the English-first canonical governance surface for the MCP module.
- `apps/mcp/AGENTS.md` and `apps/mcp/CLAUDE.md` MUST stay content-identical.

## 1. Module Mission

- This module is the MCP tool layer for the video analysis system.
- It MUST expose stable tool interfaces to upstream agents.
- It MUST map MCP calls to API and service capabilities reliably, with verifiable parameters and return shapes.

## 2. Tech Stack

- Python 3.11+
- FastMCP
- pytest

## 3. Lazy-Load Navigation

1. `apps/mcp/server.py` for the MCP server entrypoint
2. `apps/mcp/tools/` for tool implementations
3. `apps/mcp/schemas/` for request and response schemas
4. `apps/mcp/tests/` for module tests

## 4. Required Commands

```bash
./bin/dev-mcp
./bin/python-tests
```

## 5. Verification Requirements (MUST)

1. Any MCP tool parameter, return-shape, or routing change MUST pass `apps/mcp/tests`.
2. Any API/MCP contract-linked change MUST add matching tests and sync `README.md`.
3. Any cross-module change MUST also satisfy the root gates: env contract, backend pytest, web lint, and the fake assertion gate.
4. Any startup-path or integration-flow change MUST run `./bin/smoke-full-stack`, or the delivery report MUST explicitly explain why it was not run.

## 6. Module Document Truth Order

1. `apps/mcp/AGENTS.md`
2. `apps/mcp/CLAUDE.md`
3. `docs/start-here.md`
4. `docs/runbook-local.md`
5. `README.md`
6. Root `AGENTS.md` / `CLAUDE.md`

Conflict handling:
MCP tool-layer execution details defer to this module document first. Cross-module and global rules defer to the root governance documents.

## 7. Doc Drift Triggers

- If MCP tool names, parameter schemas, or return shapes change, sync `README.md` and the related module documents.
- If MCP startup procedures or script defaults change, sync `docs/start-here.md` and `docs/runbook-local.md`.
- If environment variables change, sync `.env.example`, `ENVIRONMENT.md`, and `infra/config/env.contract.json`.

## 8. Hook Alignment

- `pre-commit`: `./bin/quality-gate --mode pre-commit` including `scripts/governance/ci_or_local_gate_doc_drift.sh --scope staged`
- `pre-push`: `./bin/strict-ci --mode pre-push --heartbeat-seconds 20 --ci-dedupe 0` including `scripts/governance/ci_or_local_gate_doc_drift.sh --scope push`
