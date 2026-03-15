# Repo Governance Final Form Execution Plan

## Header

- Plan Title: Repo Governance Final Form Execution Plan
- Created At: 2026-03-15 06:07:57 America/Los_Angeles
- Last Updated: 2026-03-15 07:05:10 America/Los_Angeles
- Repo Name: 视频分析提取
- Repo Path: /Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取
- Repo Archetype: hybrid-repo
- Final Goal: Push the repository to final-form governance for architecture, cache, logging, root cleanliness, and upstream integration.
- Current Status: Partially Completed
- Current Phase: Phase F - Batch 3 Run Manifest Foundation
- Current Workstream: WS-05 Logging And Correlation Hardening

## Objective

This file is the single execution truth source for the current governance refactor. It is not an archive note. It records the target state, current state, migration workstreams, decisions, validations, blockers, changed files, and the next irreversible actions.

## Score Targets

| Dimension | Target |
| :- | :- |
| Architecture Governance | 30 / 30 |
| Cache Governance | 20 / 20 |
| Logging Governance | 20 / 20 |
| Root Cleanliness Governance | 10 / 10 |
| Upstream Integration Governance | 20 / 20 |

## Current Status

| Dimension | Target | Current Audit Baseline | Execution Target | Status |
| :- | :- | :- | :- | :- |
| Architecture Governance | 30 / 30 | 25 / 30 | Hard-cut public entrypoint split, contracts purity, explicit integration layer | In Progress |
| Cache Governance | 20 / 20 | 17 / 20 | Single runtime output root with write-time metadata discipline | In Progress |
| Logging Governance | 20 / 20 | 16 / 20 | Unified run manifest, correlation, upstream failure classification | In Progress |
| Root Cleanliness Governance | 10 / 10 | 8 / 10 | Root allowlist + budget + dirtiness fail-closed with new `.agents` and `bin` | In Progress |
| Upstream Integration Governance | 20 / 20 | 17 / 20 | Inventory + compatibility + explicit integration boundary | In Progress |

## Workstream Table

| Workstream | Status | Priority | Current Owner | Recent Action | Next Step | Validation Status |
| :- | :- | :- | :- | :- | :- | :- |
| WS-00 Plan Control Board | Completed | P0 | Codex | Landed and continuously updated the in-repo execution ledger | Keep it current in later sessions | Verified |
| WS-01 Public Entrypoint Migration | Completed | P0 | Codex | Added stable `bin/*` entrypoints and repointed active docs/hooks/workflows/tests | Extend cutover to deeper historical surfaces only if they become active again | Verified |
| WS-02 Root Governance Alignment | Completed | P0 | Codex | Legalized `.agents` and `bin` in allowlist, semantic cleanliness, and budget | Preserve root budget headroom in later phases | Verified |
| WS-03 Bridge Registry And Expiry Gate | Completed | P1 | Codex | Added bridge registry, bridge expiry gate, and wired it into governance audit | Use the registry to close future bridges instead of adding ad-hoc shims | Verified |
| WS-04 Runtime Output And Metadata Hardening | In Progress | P1 | Codex | Added managed artifact writer coverage gate after migrating more high-value report writers | Continue covering deeper release/runtime writers and then hard-cut `temp -> tmp` | Partially Verified |
| WS-05 Logging And Correlation Hardening | In Progress | P1 | Codex | Added run-manifest bootstrap for stable public entrypoints and wired a manifest coverage gate | Extend manifests into stronger completeness validation and upstream-specific logging channels | Partially Verified |
| WS-06 Contracts And Generated Surface Split | Blocked | P1 | Codex | Deferred after stabilizing entrypoint/root/runtime control plane | Requires broad repo move from `packages/shared-contracts` to `contracts/` on a cleaner shared-file baseline | Not Started |
| WS-07 Integration Boundary Refactor | Blocked | P1 | Codex | Deferred after stabilizing public entrypoints and governance control plane | Requires large-scale extraction of direct upstream coupling into `integrations/*` on a cleaner shared-file baseline | Not Started |
| WS-08 Docs And Governance Surface Repoint | Partially Completed | P2 | Codex | Repointed active top-level and module docs to `bin/*`; historical/generated surfaces intentionally left untouched in this batch | Finish render-driven and historical-surface cleanup when the contract and integration moves start | Partially Verified |
| WS-09 Validation And Closure | Partially Completed | P0 | Codex | Root, bridge, doctor, governance audit, and targeted pytest all passed for batch 1 | Keep re-running after later structural batches | Verified |

## Task Checklist

### WS-00 Plan Control Board

- [x] Create `.agents/Plans/`
  - Goal: Land the execution plan inside the repo.
  - Validation: plan file exists under `.agents/Plans/`.
  - Evidence: `.agents/Plans/2026-03-15_06-07-57__repo-governance-final-form-execution-plan.md`
- [-] Keep this plan file synchronized with every structural action
  - Goal: Prevent chat-only state drift.
  - Validation: `Last Updated`, `Current Phase`, `Current Workstream`, `Decision Log`, `Validation Log`, `Files Changed Log` stay current.

### WS-01 Public Entrypoint Migration

- [x] Add stable `bin/*` public entrypoints
  - Goal: Introduce stable public wrappers without rewriting internal shell implementations yet.
  - Validation: wrapper files exist under `bin/`.
  - Evidence: `bin/bootstrap-full-stack`, `bin/full-stack`, `bin/dev-api`, `bin/dev-worker`, `bin/dev-mcp`, `bin/quality-gate`, `bin/strict-ci`, `bin/governance-audit`, `bin/upstream-verify`
- [x] Repoint hooks to `bin/*`
  - Validation: `.githooks/pre-commit`, `.githooks/pre-push`
  - Evidence: hooks now call `bin/quality-gate` and `bin/strict-ci`
- [x] Repoint governance and CI workflows to `bin/*`
  - Validation: `.github/workflows/ci.yml`, `monthly-governance-audit.yml`, `vendor-governance.yml`
  - Evidence: strict CI and governance audit jobs now call `bin/*`
- [x] Repoint top-level docs to `bin/*`
  - Validation: `README.md`, `docs/start-here.md`, `docs/testing.md`, `docs/runbook-local.md`, `docs/governance/final-form.md`, module `AGENTS.md` / `CLAUDE.md`
  - Evidence: active doc surfaces now expose `bin/*` as the public path
- [x] Repoint workflow strictness checks and tests to `bin/*`
  - Validation: `scripts/governance/check_ci_workflow_strictness.py`, `scripts/governance/check_ci_smoke_drift.sh`, targeted pytest
  - Evidence: 43 governance/workflow tests passed

### WS-02 Root Governance Alignment

- [x] Add `.agents` to tracked root allowlist
- [x] Add `bin` to tracked root allowlist
- [x] Increase root directory budget to match the new final-form structure
- [x] Update root governance docs to explain `.agents` and `bin`

### WS-03 Bridge Registry And Expiry Gate

- [x] Create governance bridge registry
  - Goal: Record every temporary compatibility bridge with owner and removal deadline.
  - Validation: `config/governance/bridges.json` exists and is schema-valid.
- [x] Add bridge expiry validation script
  - Goal: Fail when bridges age out without closure.
  - Validation: `scripts/governance/check_bridge_expiry.py` executes successfully after wiring.
- [x] Wire bridge expiry script into governance gate
  - Validation: `./bin/governance-audit --mode audit`
  - Evidence: bridge expiry check passed inside governance audit

### WS-04 Runtime Output And Metadata Hardening

- [x] Legalize `.runtime-cache/tmp` as a governed bridge target
  - Goal: Prevent the bridge registry from declaring a runtime child that governance still treats as illegal.
  - Validation: `python3 scripts/governance/check_runtime_outputs.py`
  - Evidence: runtime outputs pass with both `tmp` and `temp` declared
- [x] Fix validation commands to avoid root `.venv` pollution
  - Goal: Keep root clean during targeted pytest runs.
  - Validation: rerun targeted pytest with `PYTHONDONTWRITEBYTECODE=1` and `UV_PROJECT_ENVIRONMENT=.runtime-cache/temp/pytest-governance-env`
  - Evidence: root allowlist and governance audit pass after test runs
- [ ] Identify every freshness-required artifact write path
- [-] Force write-time sidecar metadata instead of maintenance-only backfill
- [x] Add managed artifact writer helpers for repo-side runtime outputs
  - Goal: Stop duplicating ad-hoc metadata logic in individual scripts.
  - Validation: helper-backed scripts import and execute.
  - Evidence: `scripts/governance/common.py` now exposes `maybe_write_runtime_metadata`, `write_text_artifact`, `write_json_artifact`
- [x] Move key Python report writers to managed artifact helpers
  - Goal: Push high-frequency `.runtime-cache/reports/**` producers to write metadata at write time.
  - Validation: modified scripts parse and run `--help` / direct check commands successfully.
  - Evidence: `scripts/governance/check_runtime_cache_freshness.py`, `scripts/governance/build_nightly_flaky_report.py`, `scripts/governance/report_env_governance.py`, `scripts/ci/autofix.py`, `scripts/ci/gemini_ui_ux_audit.py`
- [x] Move key smoke diagnostics JSON writers to managed artifact helpers
  - Goal: Reduce maintenance-only metadata dependence for `.runtime-cache/reports/tests/*.json`.
  - Validation: shell syntax passes for modified smoke scripts.
  - Evidence: `scripts/ci/smoke_llm_real_local.sh`, `scripts/ci/external_playwright_smoke.sh`
- [x] Add runtime artifact writer coverage gate
  - Goal: Stop relying on memory to find unmanaged `.runtime-cache/reports/**` and `.runtime-cache/evidence/**` writers.
  - Validation: `python3 scripts/governance/check_runtime_artifact_writer_coverage.py`
  - Evidence: gate is wired in `scripts/governance/gate.sh`, documented in `docs/reference/evidence-model.md`, and passes
- [ ] Add validation that fresh artifacts are metadata-complete immediately after generation

### WS-05 Logging And Correlation Hardening

- [x] Define run-manifest-first policy
  - Goal: Stable public entrypoints should register an explicit run manifest before they hand off to internal scripts.
  - Validation: `scripts/runtime/write_run_manifest.py`, `scripts/runtime/entrypoint.sh`, `docs/reference/evidence-model.md`
  - Evidence: `.runtime-cache/run/manifests/*.json` now appear after public entrypoint execution
- [ ] Add upstream-specific log channel plan
- [x] Ensure public entrypoints allocate run correlation before invoking internal scripts
  - Goal: `bin/*` entrypoints should not rely on downstream scripts to invent their run correlation context.
  - Validation: `python3 scripts/governance/check_public_entrypoint_manifests.py`
  - Evidence: all governed `bin/*` entrypoints now source `scripts/runtime/entrypoint.sh` and call `vd_entrypoint_bootstrap`

### WS-06 Contracts And Generated Surface Split

- [ ] Design `contracts/source` and `contracts/generated` move
- [ ] Freeze new writes into `packages/shared-contracts`
- [ ] Add migration bridge and cutover checkpoints

### WS-07 Integration Boundary Refactor

- [ ] Inventory direct upstream coupling points
- [ ] Define explicit `integrations/` target tree
- [ ] Prepare hard-cut migration rules for direct upstream calls

### WS-08 Docs And Governance Surface Repoint

- [ ] Repoint README/start-here/runbook/testing to stable public entrypoints
- [ ] Keep high-drift facts in SSOT/render sources, not manual mirrors
- [ ] Record every public command migration in docs

### WS-09 Validation And Closure

- [ ] Run root allowlist checks
- [ ] Run root dirtiness checks
- [ ] Run bridge expiry gate
- [ ] Run governance gate
- [ ] Run targeted tests for changed governance contracts

## Decision Log

| Time | Decision | Why | Rejected Alternative | Impact |
| :- | :- | :- | :- | :- |
| 2026-03-15 06:07:57 | Use `.agents/Plans/` as the in-repo execution control plane | User explicitly required in-repo plan as single source of truth | Keep state only in chat | Introduces a new tracked top-level governance directory |
| 2026-03-15 06:07:57 | Start with public entrypoint hardening before deeper contracts/integrations refactors | Public entrypoints are the highest-leverage hard cut and the least invasive way to make governance real immediately | Jump directly into `contracts/` or `integrations/` moves while public docs and CI still call old paths | Forces hooks, CI, and docs onto stable `bin/*` wrappers first |
| 2026-03-15 06:10:40 | Add a bridge registry before finishing the first hard cut | The repo already has multiple migration fronts; bridges must be tracked from day one so temporary aliases do not become permanent infrastructure | Delay bridge tracking until after the first public entrypoint migration | Gives every bridge a deadline and an owner before more cutovers begin |
| 2026-03-15 06:16:00 | Treat `.runtime-cache/tmp` as a governed bridge subdir now, not a future-only idea | The bridge registry must not point at a runtime path that the control plane still rejects | Remove the tmp bridge entry and pretend the migration will happen later | Lets the runtime output control plane recognize the final-form target while `temp` still exists |
| 2026-03-15 06:18:00 | Use `PYTHONDONTWRITEBYTECODE=1` plus `UV_PROJECT_ENVIRONMENT=.runtime-cache/temp/pytest-governance-env` for governance pytest validation | A plain `uv run pytest` created a root `.venv`, which violates root cleanliness | Tolerate `.venv` in root allowlist | Keeps validation clean without weakening root governance |
| 2026-03-15 06:23:00 | Stop this session after the public-entrypoint/root/runtime bridge batch instead of forcing the `contracts/` and `integrations/` hard cuts on the current dirty worktree | The remaining moves are broad shared-file migrations with high conflict risk against existing in-flight governance edits | Attempt repo-wide moves blindly in the current dirty state | Converts the remaining scope into explicit blocked workstreams rather than unsafe half-migrations |
| 2026-03-15 06:39:00 | Add a shared managed-artifact helper before touching more report writers | Repeating per-script metadata glue would create another form of drift | Patch each report writer ad-hoc | Centralizes write-time metadata discipline in one reusable helper surface |
| 2026-03-15 06:41:00 | Cover the highest-value Python report writers first, then the highest-value smoke diagnostics JSON writers | These files land in freshness-required runtime report paths most often and are cheap to validate | Try to patch every report/evidence writer in one batch | Produces measurable metadata hardening progress without turning the batch into an unsafe repo-wide sweep |
| 2026-03-15 06:47:00 | Make `bin/doctor` set `PYTHONDONTWRITEBYTECODE=1` unconditionally | The official doctor entrypoint must not be allowed to create its own `__pycache__` residue under source directories | Accept `doctor` as a special-case dirty command | Keeps the diagnosis entrypoint aligned with root cleanliness rules |
| 2026-03-15 06:54:00 | Add a runtime artifact writer coverage gate after migrating the first high-value writers | Without a gate, WS-04 would regress back into manual spot-checking | Keep inventory only in the execution plan | Turns the remaining runtime metadata hardening work into a machine-audited backlog instead of a memory task |
| 2026-03-15 07:01:00 | Start WS-05 with static public-entrypoint manifest enforcement instead of historical run-data enforcement | Historical `.runtime-cache` contents are noisy and would make a first manifest gate brittle | Fail builds on missing manifests for old run data before the new entrypoints have had time to populate clean manifests | Gives the repo a reliable run-manifest foundation without being blocked by historical artifacts |

## Validation Log

| Validation Item | Status | Validation Method | Result | Notes |
| :- | :- | :- | :- | :- |
| Plan file exists in repo | Completed | File presence | Created | Initial landing step complete |
| `.agents` legal under root governance | Completed | `check_root_allowlist` + `check_root_layout_budget` + `check_root_zero_unknowns` + semantic cleanliness via governance audit | PASS | `.agents` is now a governed public control-plane directory |
| `bin/*` wrappers exist | Completed | File presence + executable bit + `--help` smoke | PASS | Stable public entrypoints now exist and advertise the new paths |
| Bridge registry exists | Completed | File presence + `check_bridge_expiry.py` + governance audit | PASS | Bridge control plane is live |
| Root governance batch | Completed | `python3 scripts/governance/check_root_allowlist.py --strict-local-private && python3 scripts/governance/check_root_layout_budget.py && python3 scripts/governance/check_root_zero_unknowns.py && python3 scripts/governance/check_bridge_expiry.py && python3 scripts/governance/check_runtime_outputs.py` | PASS | Confirms `.agents`, `bin`, bridge registry, and runtime output bridge are legal |
| Governance control plane batch | Completed | `./bin/governance-audit --mode audit` | PASS | Full governance gate passed after all batch-1 fixes |
| Workflow/governance tests | Completed | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/temp/pytest-governance-env uv run pytest apps/worker/tests/test_governance_controls.py apps/worker/tests/test_ci_workflow_strictness.py -q` | PASS (43 passed, 2 warnings) | Warnings are existing pytest config warnings about `reruns` / `reruns_delay` on Python 3.14, not failures |
| Stable public doctor entrypoint | Completed | `./bin/doctor` | PASS | Quick governance health entrypoint is available and no longer leaves bytecode residue under `apps/` or `scripts/` |
| Managed artifact helper batch | Completed | `python3 scripts/governance/check_runtime_cache_freshness.py` + helper-based script `--help` smoke + shell syntax checks | PASS | Confirms helper-backed report writers and smoke scripts still parse and the freshness report itself now writes through the helper |
| Runtime artifact writer coverage gate | Completed | `python3 scripts/governance/check_runtime_artifact_writer_coverage.py` + targeted pytest | PASS | The new gate is wired, documented, and currently passes on the active script surface |
| Public entrypoint manifest gate | Completed | `bash -n bin/* scripts/runtime/entrypoint.sh && python3 scripts/governance/check_public_entrypoint_manifests.py` | PASS | Static gate confirms all governed `bin/*` entrypoints write manifests before handoff |
| Run manifest foundation | Completed | `./bin/doctor && ./bin/governance-audit --help >/dev/null && ./bin/strict-ci --help >/dev/null` plus manifest directory inspection | PASS | Public entrypoints now create `.runtime-cache/run/manifests/<run_id>.json` artifacts |

## Risk / Blocker Log

| Time | Type | Description | Impact | What Can Continue | Resolution Condition |
| :- | :- | :- | :- | :- | :- |
| 2026-03-15 06:07:57 | Risk | Current worktree already contains extensive governance refactor changes not authored in this step | Any overwrite or revert could destroy in-flight governance work | Additive hardening around existing direction | Only apply targeted patches with local context reads |
| 2026-03-15 06:07:57 | Resolved | Adding `.agents` and `bin` would violate current root allowlist and budget unless control plane changed in the same batch | Would have broken root gates | Resolved in batch 1 | Root allowlist, budget, and semantic cleanliness now all pass |
| 2026-03-15 06:10:40 | Resolved | `bin/*` wrappers initially lacked executable bits and wiring | Public entrypoint hard cut would have remained cosmetic | Resolved in batch 1 | `chmod +x` applied, hooks/workflows/docs/tests updated, help paths updated |
| 2026-03-15 06:16:00 | Resolved | Bridge registry pointed to `.runtime-cache/tmp` before runtime outputs control plane allowed it | Governance audit failed on an undeclared runtime child | Resolved in batch 1 | `tmp` is now a declared governed bridge subdir |
| 2026-03-15 06:18:00 | Resolved | A plain `uv run pytest` created a root `.venv` during validation | Root cleanliness was violated by the validation path itself | Resolved for current validation batch | Clean validation now uses `PYTHONDONTWRITEBYTECODE=1` and `UV_PROJECT_ENVIRONMENT=.runtime-cache/temp/pytest-governance-env` |
| 2026-03-15 06:23:00 | Blocker | `contracts/` hard cut and `integrations/` extraction remain broad shared-file moves on top of a heavily dirty worktree with many pre-existing governance edits | High risk of clobbering in-flight local refactors and leaving the repo in a half-migrated state | Further additive hardening and validation can continue in later sessions | Re-enter on a stabilized shared-file baseline or with explicit scope to carry the large-scale moves end-to-end |
| 2026-03-15 06:44:20 | Risk | Write-time metadata hardening is still partial; many runtime report/evidence writers remain outside the new helper path | Runtime maintenance is still doing some cleanup work that should eventually be unnecessary | Additional high-value writers can keep moving to the helper incrementally | Finish inventory of freshness-required writers and wire remaining hot paths |
| 2026-03-15 06:49:40 | Resolved | `bin/doctor` created `__pycache__` under `scripts/governance`, violating root/runtime cleanliness by using plain `python3` semantics | Would have made the official diagnosis entrypoint self-contradictory | Resolved in batch 2 | `bin/doctor` now exports `PYTHONDONTWRITEBYTECODE=1` and passes clean rerun validation |
| 2026-03-15 06:56:30 | Risk | The new coverage gate only audits script-side runtime report/evidence writers with recognizable direct write patterns; it does not yet prove every possible runtime artifact path across the whole repo is helper-backed | WS-04 is stronger but still not complete | Continue migrating deeper release/runtime writers and expand the gate if new patterns emerge | Finish writer inventory and add post-generation metadata completeness validation |
| 2026-03-15 07:05:10 | Risk | WS-05 currently guarantees that stable public entrypoints create run manifests, but it does not yet guarantee that every downstream log/report/evidence path is linked back to a manifest in a completeness gate | Correlation is better, but not yet final-form complete | Continue with manifest completeness validation and upstream channel planning | Add a manifest completeness gate that checks current-run artifacts against generated manifests |

## Files Changed Log

| Time | Files / Paths Changed Since Last Update |
| :- | :- |
| 2026-03-15 06:07:57 | `.agents/Plans/2026-03-15_06-07-57__repo-governance-final-form-execution-plan.md` created |
| 2026-03-15 06:10:40 | `bin/*` wrappers created; `config/governance/bridges.json` created; `scripts/governance/check_bridge_expiry.py` created |
| 2026-03-15 06:14:00 | Root governance control plane updated for `.agents` / `bin`; hooks and key workflows moved to `bin/*`; active top-level and module docs repointed; workflow strictness checks and targeted tests updated |
| 2026-03-15 06:18:00 | `scripts/governance/common.py` hardened for out-of-repo temp artifacts; governance tests updated for versioned config evolution; `.runtime-cache/tmp` legalized as a governed bridge subdir |
| 2026-03-15 06:22:00 | Added `bin/clean-runtime`, `bin/prune-runtime`, `bin/doctor`; updated public help/usage strings to advertise `bin/*` instead of leaking internal `scripts/*` paths |
| 2026-03-15 06:44:20 | Added managed runtime artifact helpers in `scripts/governance/common.py`; migrated key report writers and smoke diagnostics JSON writers to write-time metadata-backed paths |
| 2026-03-15 06:49:40 | `bin/doctor` hardened to suppress repo-side bytecode residue; validation rerun confirmed no lingering `__pycache__` under `apps/` or `scripts/` |
| 2026-03-15 06:56:30 | `scripts/ci/collect_kpi.py` and `scripts/release/build_readiness_report.py` migrated to managed artifact helpers; added `scripts/governance/check_runtime_artifact_writer_coverage.py`; wired the new gate into governance control plane and evidence docs |
| 2026-03-15 07:05:10 | Added `scripts/runtime/entrypoint.sh`, `scripts/runtime/write_run_manifest.py`, and `scripts/governance/check_public_entrypoint_manifests.py`; wired stable `bin/*` entrypoints to emit run manifests before handoff |

## Next Actions

1. Continue WS-04 by inventorying the remaining deeper release/runtime writers and expanding helper coverage beyond the current script-side hot paths.
2. Continue WS-05 by adding a manifest completeness gate that validates current-run logs/reports/evidence against run manifests, not just static entrypoint wiring.
3. Re-enter WS-06/WS-07 only after agreeing on a clean shared-file baseline for the broad `contracts/` and `integrations/` moves.
4. Extend the `bin/*` cutover to generated and historical explanatory surfaces only if they become active governance inputs again.
5. Keep this file current before any later structural batch starts.

## Final Completion Summary

Batch 1 completed and verified:

- Landed the in-repo execution control board under `.agents/Plans/`.
- Added stable public `bin/*` entrypoints and moved active hooks, workflows, docs, and workflow-governance tests to them.
- Legalized `.agents` and `bin` in root allowlist, budget, and semantic cleanliness rules.
- Added bridge registry + bridge expiry gate and wired the gate into governance audit.
- Added `bin/doctor`, `bin/prune-runtime`, and `bin/clean-runtime` to start turning final-form operational commands into stable public entrypoints.
- Closed the two real validation regressions discovered during execution:
  - root `.venv` pollution from plain `uv run pytest`
  - undeclared `.runtime-cache/tmp` bridge target
- Verified the batch with root/runtime checks, governance audit, doctor, wrapper help, and targeted pytest.

Remaining workstreams are not marked complete. `WS-06` and `WS-07` are explicitly blocked because the required repo-wide `contracts/` and `integrations/` hard cuts would be unsafe to force on top of the current heavily dirty shared-file worktree without a cleaner migration baseline.

Batch 2 progress completed and verified:

- Added reusable managed artifact helpers in `scripts/governance/common.py`.
- Moved several high-value Python runtime report writers to write-time metadata helpers.
- Moved two key smoke diagnostics JSON writers to the same helper discipline.
- Fixed `bin/doctor` so the official diagnosis entrypoint no longer leaves bytecode residue in source directories.
- Added a runtime artifact writer coverage gate so the remaining WS-04 surface is machine-audited rather than memory-driven.
- Verified shell syntax, helper-backed script importability, runtime cache freshness report execution, clean `bin/doctor` execution, the new coverage gate, and the targeted governance/workflow pytest suite.

Batch 3 progress completed and verified:

- Added a run-manifest bootstrap layer for stable public `bin/*` entrypoints.
- Added a static public-entrypoint manifest coverage gate and wired it into governance control plane and evidence docs.
- Verified that public entrypoints now emit `.runtime-cache/run/manifests/<run_id>.json` without leaving bytecode residue.

WS-05 is no longer “not started”; it now has a concrete run-manifest-first foundation. It remains incomplete because there is not yet a stronger manifest completeness gate for current-run logs/reports/evidence, and there is not yet an upstream-specific logging channel plan.

WS-04 remains in progress because the repository still contains additional freshness-required report/evidence writers that have not yet been migrated to the helper path.
