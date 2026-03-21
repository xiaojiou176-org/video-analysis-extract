# API Module Governance

## 0. Canonical Scope

- This file is the English-first canonical governance surface for the API module.
- `apps/api/AGENTS.md` and `apps/api/CLAUDE.md` MUST stay content-identical.

## 1. Module Mission

- This module is the HTTP control plane for the video analysis system.
- It MUST expose `/healthz` and `/api/v1/*` reliably.
- It MUST provide stable capabilities for subscriptions, jobs, artifacts, notifications, and retrieval.

## 2. Tech Stack

- Python 3.11+
- FastAPI + Pydantic + SQLAlchemy
- pytest

## 3. Lazy-Load Navigation

1. `apps/api/app/main.py` for the FastAPI entrypoint
2. `apps/api/app/routers/` for route handlers
3. `apps/api/app/services/` for business services
4. `apps/api/app/repositories/` for data access
5. `apps/api/tests/` for module tests

## 4. Required Commands

```bash
./bin/dev-api
./bin/python-tests
```

## 5. Verification Requirements (MUST)

1. Any API logic change MUST pass `apps/api/tests`.
2. Any cross-module change MUST also satisfy the root gates: env contract, backend pytest, web lint, and the fake assertion gate.
3. Placebo tests such as `expect(true).toBe(true)` or other invalid assertions MUST NOT be committed.
4. Any startup-path or end-to-end flow change MUST run `./bin/smoke-full-stack`, or the delivery report MUST explicitly explain why it was not run.

## 6. Module Document Truth Order

1. `apps/api/AGENTS.md`
2. `apps/api/CLAUDE.md`
3. `docs/start-here.md`
4. `docs/runbook-local.md`
5. `README.md`
6. Root `AGENTS.md` / `CLAUDE.md`

Conflict handling:
Module-level execution details defer to this file first. Cross-module and global rules defer to the root governance documents.

## 7. Doc Drift Triggers

- If API contracts, authentication behavior, or route behavior changes, sync `README.md`.
- If environment variables change, sync `.env.example`, `ENVIRONMENT.md`, and `infra/config/env.contract.json`.
- If startup or runtime procedures change, sync `docs/start-here.md` and `docs/runbook-local.md`.

## 8. Hook Alignment

- `pre-commit`: `./bin/quality-gate --mode pre-commit` including `scripts/governance/ci_or_local_gate_doc_drift.sh --scope staged`
- `pre-push`: `./bin/strict-ci --mode pre-push --heartbeat-seconds 20 --ci-dedupe 0` including `scripts/governance/ci_or_local_gate_doc_drift.sh --scope push`
