# Worker Module Governance

## 0. Canonical Scope

- This file is the English-first canonical governance surface for the worker module.
- `apps/worker/AGENTS.md` and `apps/worker/CLAUDE.md` MUST stay content-identical.

## 1. Module Mission

- This module runs the main video processing pipeline: poll, pipeline execution, state write-back, and artifact generation.
- It MUST work with Temporal and follow the `3-stage + 9-step pipeline` contract strictly.

## 2. Tech Stack

- Python 3.11+
- Temporal worker
- pytest

## 3. Lazy-Load Navigation

1. `apps/worker/worker/main.py` for the worker entrypoint
2. `apps/worker/worker/pipeline/` for pipeline orchestration
3. `apps/worker/worker/temporal/` for workflows and activities
4. `apps/worker/tests/` for module tests

## 4. Required Commands

```bash
./bin/dev-worker
./bin/python-tests
```

## 5. Verification Requirements (MUST)

1. Any pipeline behavior change MUST pass `apps/worker/tests`.
2. Any change to `PIPELINE_STEPS` MUST sync `docs/state-machine.md` and complete the matching verification.
3. Any cross-module change MUST also satisfy the root gates: env contract, backend pytest, web lint, and the fake assertion gate.
4. Any startup-path or end-to-end flow change MUST run `./bin/smoke-full-stack`, or the delivery report MUST explicitly explain why it was not run.

## 6. Module Document Truth Order

1. `apps/worker/AGENTS.md`
2. `apps/worker/CLAUDE.md`
3. `docs/state-machine.md`
4. `docs/start-here.md`
5. `docs/runbook-local.md`
6. Root `AGENTS.md` / `CLAUDE.md`

Conflict handling:
Worker behavior contracts defer to `docs/state-machine.md` and this module document first. Cross-module and global rules defer to the root governance documents.

## 7. Doc Drift Triggers

- If `PIPELINE_STEPS` changes in `apps/worker/worker/pipeline/types.py`, sync `docs/state-machine.md`.
- If worker startup parameters, runtime paths, or script defaults change, sync `docs/start-here.md`, `docs/runbook-local.md`, and `README.md`.
- If environment variables change, sync `.env.example`, `ENVIRONMENT.md`, and `infra/config/env.contract.json`.

## 8. Hook Alignment

- `pre-commit`: `./bin/quality-gate --mode pre-commit` including `scripts/governance/ci_or_local_gate_doc_drift.sh --scope staged`
- `pre-push`: `./bin/strict-ci --mode pre-push --heartbeat-seconds 20 --ci-dedupe 0` including `scripts/governance/ci_or_local_gate_doc_drift.sh --scope push`
