# Repo Governance Final Form Execution Plan

## Header

- Plan Title: Repo Governance Final Form Execution Plan
- Created At: 2026-03-15 15:47:13 America/Los_Angeles
- Last Updated: 2026-03-15 16:49:42 America/Los_Angeles
- Repo Name: 视频分析提取
- Repo Path: /Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取
- Repo Archetype: hybrid-repo
- Final Goal: Push the repository to final-form governance for architecture, cache, logging, root cleanliness, and upstream integration.
- Current Status: In Progress
- Current Phase: Phase G - Runtime Metadata Completeness Gate Landed
- Current Workstream: WS-06 Logging Finalization
- Current Truth Source Rule: This file is the only in-repo execution truth source for this governance run.

## Objective

This plan is not an archive. It is the live execution control board for the current final-form governance hard cut. The execution target is not "improve the repo a bit." The execution target is to remove structural ambiguity, close every repo-side governance gap that can be completed locally, and leave only explicit external blockers if any remain.

The repo must end this run closer to the following final-form state:

1. Architecture governance = 30 / 30
2. Cache governance = 20 / 20
3. Logging governance = 20 / 20
4. Root cleanliness governance = 10 / 10
5. Upstream integration governance = 20 / 20

## Score Targets

| Dimension | Target | Current Audit Baseline | Required End State |
| :- | :- | :- | :- |
| Architecture Governance | 30 / 30 | 25 / 30 | No ghost layers, no stale boundary truth, contracts/integrations/tests/root tree aligned |
| Cache Governance | 20 / 20 | 17 / 20 | `temp` removed, `tmp` only, write-time metadata discipline, cold rebuild proof |
| Logging Governance | 20 / 20 | 17 / 20 | JSONL primary source, console derived only, run-correlation and evidence fully aligned |
| Root Cleanliness Governance | 10 / 10 | 8 / 10 | Root allowlist + denylist + dirtiness fail-close + no generic root residue |
| Upstream Integration Governance | 20 / 20 | 17 / 20 | Single upstream fact plane, explicit integration boundary, blocker compat rows truthfully enforced |

## Current Status

| Dimension | Target | Current Status | Gaps | Verification Status |
| :- | :- | :- | :- | :- |
| Architecture Governance | 30 / 30 | In Progress | Active ghost `packages` references are cleared, but repo-level tests are still not normalized into a final root test layer | Partially Verified |
| Cache Governance | 20 / 20 | In Progress | Active runtime scratch paths are now hard-cut to `.runtime-cache/tmp`; write-time metadata hardening is still pending | Partially Verified |
| Logging Governance | 20 / 20 | In Progress | Structured logs are strong but not yet normalized into final `events/console` split | Partially Verified |
| Root Cleanliness Governance | 10 / 10 | In Progress | Root is governed, generic `data/` is gone, denylist hardening is live, and no active bridge remains; root budget tightening is still pending | Partially Verified |
| Upstream Integration Governance | 20 / 20 | In Progress | Active inventory is strong, but final-form single fact plane and stricter adapter-only enforcement still pending | Partially Verified |

## Final Form Blueprint

### Target Root Tree

```text
repo/
├── .agents/
├── .devcontainer/
├── .githooks/
├── .github/
├── .runtime-cache/
├── AGENTS.md
├── CHANGELOG.md
├── CLAUDE.md
├── ENVIRONMENT.md
├── README.md
├── apps/
├── artifacts/
├── bin/
├── config/
├── contracts/
├── docs/
├── env/
├── infra/
├── integrations/
├── scripts/
├── tests/
├── pyproject.toml
├── uv.lock
└── biome.json
```

### Target Runtime Output Tree

```text
.runtime-cache/
├── run/
├── logs/
│   ├── events/
│   └── console/
├── reports/
├── evidence/
└── tmp/
```

### Target Governance Truth Surfaces

- Root governance: `config/governance/root-allowlist.json`, `config/governance/root-denylist.json`, `config/governance/root-layout-budget.json`
- Runtime outputs: `config/governance/runtime-outputs.json`
- Logging: `config/governance/logging-contract.json`
- Boundaries: `config/governance/dependency-boundaries.json`, `config/governance/module-ownership.json`
- Bridges: `config/governance/bridges.json`
- Upstreams: final target is `config/governance/upstreams/*`

## Workstream Table

| Workstream | Status | Priority | Current Owner | Recent Action | Next Step | Validation Status |
| :- | :- | :- | :- | :- | :- | :- |
| WS-00 Plan Control Board | In Progress | P0 | Codex | Rebased the plan into a final-form execution control board and synced first execution results | Keep this file synchronized after every structural step | Partially Verified |
| WS-01 Architecture Hard-Cut Cleanup | Partially Completed | P0 | Codex | Removed active ghost `packages` references, added governance reference-existence enforcement, relocated root `data/`, and re-proved governance audit | Start the runtime path hard cut from `temp` to `tmp` | Verified |
| WS-02 Root Governance Finalization | Partially Completed | P0 | Codex | Added root denylist control plane and wired semantic-cleanliness against it | Decide whether stricter root denylist coverage needs more exact-path assertions now that generic root `data/` is gone | Verified |
| WS-03 Public Entrypoint Hard Cut | Completed | P1 | Codex | Expanded `bin/*` wrapper coverage, repointed active front-door and reference/deploy docs, removed the final active public bridge, and updated bridge gate semantics to accept zero active bridges | Keep scanning deeper docs for clarity, but public bridge removal is complete | Verified |
| WS-04 Runtime Output Hard Cut | Partially Completed | P0 | Codex | Repointed active runtime paths to `tmp`, removed `temp` from runtime outputs, cleared the temp bridge, and re-proved governance + targeted tests | Decide whether any hidden non-gated legacy scratch references remain outside active surfaces | Verified |
| WS-05 Runtime Metadata Hardening | Partially Completed | P1 | Codex | Added runtime metadata completeness gate, wired it into governance, fixed the first missing `source_run_id`, and re-proved full governance audit | Continue converting remaining freshness-required writers from maintenance-backed metadata toward write-time-only correctness | Verified |
| WS-06 Logging Finalization | Pending | P1 | Codex | Final `events/console` split defined | Normalize structured and console log paths and keep JSONL primary | Not Started |
| WS-07 Evidence/Test Surface Re-Layering | Pending | P1 | Codex | Final tree defined | Move report/evidence outputs into final layered structure | Not Started |
| WS-08 Upstream Fact Plane Consolidation | Pending | P1 | Codex | Final upstream target tree defined | Collapse active inventory surfaces into one control plane and strengthen adapter-only enforcement | Not Started |
| WS-09 CI / Gate Hardening | Pending | P0 | Codex | New gates identified | Wire all new policy checks into governance audit / quality / strict-ci | Not Started |
| WS-10 Bridge Removal And Closure | Pending | P0 | Codex | Active bridges inventoried | Freeze writers, remove readers, delete bridges on deadline | Not Started |

## Task Checklist

### WS-00 Plan Control Board

- [x] Replace prior partial control board with this final-form execution plan
  - Goal: make this file the live source of truth for the rest of the run
  - Validation: new timestamped plan file exists under `.agents/Plans/`
  - Evidence: `.agents/Plans/2026-03-15_15-47-13__repo-governance-final-form-execution-plan.md`
- [-] Update this file after every structural change
  - Goal: prevent chat-only state drift
  - Validation: `Last Updated`, `Current Phase`, `Current Workstream`, workstream table, task checklist, decision log, validation log, files changed log remain current

### WS-01 Architecture Hard-Cut Cleanup

- [x] Remove ghost `packages` / `packages.shared-contracts` references from active governance truth
  - Goal: eliminate stale layer references from policy and docs
  - Change Targets: `config/governance/module-ownership.json`, `config/governance/dependency-boundaries.json`, `config/governance/bridges.json`, `docs/reference/architecture-governance.md`
  - Validation: active-path search for `packages/shared-contracts|packages/|packages.` now returns zero hits
- [x] Add governance reference existence gate
  - Goal: fail when governance files point at non-existent layers
  - Change Targets: new `scripts/governance/check_governance_schema_references_exist.py`, `scripts/governance/gate.sh`, docs
  - Validation: `python3 scripts/governance/check_governance_schema_references_exist.py`
- [x] Remove or relocate root `data/`
  - Goal: eliminate generic root data holding pen
  - Change Targets: root `data/`, new `tests/fixtures/` and/or `artifacts/performance/`
  - Validation: root allowlist passes without `data`; mapping data now lives in `config/source-names/`; RSSHub probe snapshots now live in `artifacts/performance/rsshub/`

### WS-02 Root Governance Finalization

- [x] Add explicit root denylist
- [ ] Remove generic root residues from allowlist
- [ ] Re-tighten root layout budget after cleanup
- [ ] Ensure all mainline commands re-prove root dirtiness clean

### WS-03 Public Entrypoint Hard Cut

- [x] Remove remaining legacy public entrypoint bridge references from active docs/workflows/hook surfaces
- [x] Add public entrypoint registry gate
- [x] Mark `scripts/* -> bin/*` bridge writer-frozen
- [x] Remove the bridge after references are zero

### WS-04 Runtime Output Hard Cut

- [x] Replace active legacy scratch-root paths with `.runtime-cache/tmp/**`
- [ ] Update tool/runtime scripts and tests to final tmp-only paths
- [x] Remove `temp` from `runtime-outputs.json`
- [x] Delete `runtime-cache-temp-to-tmp-cutover` bridge

### WS-05 Runtime Metadata Hardening

- [ ] Identify every freshness-required writer still relying on maintenance-only metadata backfill
- [ ] Convert each to write-time metadata
- [x] Add metadata completeness gate for freshly written runtime artifacts

### WS-06 Logging Finalization

- [ ] Normalize structured logs to `.runtime-cache/logs/events/**`
- [ ] Normalize human-readable console logs to `.runtime-cache/logs/console/**`
- [ ] Keep JSONL as primary truth, console as derived view
- [ ] Add primary-source enforcement gate

### WS-07 Evidence/Test Surface Re-Layering

- [ ] Normalize report trees to final layered structure
- [ ] Normalize browser evidence trees to final layered structure
- [ ] Move repo-level governance tests toward root `tests/`

### WS-08 Upstream Fact Plane Consolidation

- [ ] Create final `config/governance/upstreams/` tree
- [ ] Consolidate active inventory facts into one canonical file
- [ ] Strengthen adapter-only enforcement for external providers/binaries/platforms
- [ ] Keep blocker compat rows honest and fresh-only

### WS-09 CI / Gate Hardening

- [ ] Wire new governance gates into `scripts/governance/gate.sh`
- [ ] Wire relevant gates into `quality-gate` and `strict-ci`
- [ ] Add cold-cache rebuild verification path

### WS-10 Bridge Removal And Closure

- [ ] Freeze active bridge writers
- [ ] Repoint all consumers
- [ ] Delete bridges before expiry
- [ ] End with no unnecessary active bridges

## Decision Log

| Time | Decision | Why | Rejected Alternative | Impact |
| :- | :- | :- | :- | :- |
| 2026-03-15 15:47:13 | Rebase execution onto a new timestamped plan file instead of continuing the earlier partial control board | The user explicitly required a fresh final-form total plan plus ongoing execution tracking | Keep editing the earlier partial board with mixed assumptions | Creates a clean single-source execution board for this run |
| 2026-03-15 15:47:13 | Start execution with architecture truth cleanup before cache/logging hard cuts | Ghost responsibility layers corrupt later policy and path decisions | Jump directly to `temp -> tmp` without fixing stale architecture truth | Prevents later gates from codifying stale structure |
| 2026-03-15 15:54:10 | Remove the completed shared-contracts bridge from the active bridge registry instead of preserving it as live governance state | The old path no longer exists, and keeping it in the active bridge plane keeps resurrecting ghost structure | Keep the completed bridge entry as part of the live registry | Tightens bridge governance to only current/future migration surfaces |
| 2026-03-15 15:55:20 | Reclassify root `data/` by semantics instead of tolerating it as a generic top-level bucket | One file is repo-owned configuration data and the remaining files are retained probe/performance artifacts | Keep `data/` in root because it was already allowlisted | Removes a generic root bucket without losing useful config or evidence |
| 2026-03-15 16:04:20 | Hard-cut runtime scratch paths to `tmp` in one batch instead of preserving a read-compatible `temp` bridge | The runtime output contract is the source of truth; keeping both paths alive would keep cache governance below final form | Migrate only a subset of scripts and leave `temp` as a tolerated bridge | Converts cache governance from bridge-state to final active path semantics and lets the gate enforce a single scratch root |
| 2026-03-15 16:14:30 | Add root denylist and public-entrypoint reference gates before attempting deeper logging or upstream reshaping | Root/public surface regressions are cheap to prevent now and expensive to clean later | Postpone these gates until after larger refactors | Locks the hallway and public front desk before deeper room-by-room work continues |
| 2026-03-15 16:37:00 | Remove the final public-entrypoint bridge entirely and update the bridge gate to treat zero active bridges as a valid final-form state | Leaving an empty compatibility bridge around would preserve bridge-era semantics and keep governance one step short of closure | Keep a completed bridge entry in the registry forever | Moves the control plane from “bridge under control” to “bridge removed” |
| 2026-03-15 16:46:20 | Add a dedicated runtime metadata completeness gate instead of relying on freshness checks alone | Freshness checks can prove an artifact is recent yet still miss incomplete sidecar payloads like blank `source_run_id` | Keep relying on maintenance/freshness scripts to notice metadata defects indirectly | Turns runtime metadata discipline into an explicit fail-close contract and immediately exposed one real defect in the maintenance report metadata |

## Validation Log

| Validation Item | Status | Validation Method | Result | Notes |
| :- | :- | :- | :- | :- |
| Prior governance baseline still green at run start | Completed | `./bin/governance-audit --mode audit` | PASS | Confirms current repo-side governance surface before new hard cuts |
| New control board exists | Completed | file presence | PASS | This plan file is now the source of truth |
| Ghost architecture refs identified | Completed | targeted `rg` scan | PASS | `packages` residues found in governance/docs and queued for removal |
| Temp bridge residues identified | Completed | targeted `rg` scan | PASS | multiple legacy scratch-root surfaces were identified and queued for hard cut |
| Root generic data residue identified | Completed | root inspection | PASS | `data/` existed and was queued for removal/relocation |
| Architecture truth cleanup batch | Completed | `python3 scripts/governance/check_governance_schema_references_exist.py` + `./bin/governance-audit --mode audit` | PASS | New governance existence gate passes and full governance audit stays green after architecture truth cleanup and root data reclassification |
| Runtime tmp-only hard cut batch | Completed | `python3 scripts/governance/check_runtime_outputs.py` + `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/tmp/pytest-governance-env uv run --extra dev pytest apps/worker/tests/test_governance_controls.py apps/worker/tests/test_ci_workflow_strictness.py apps/worker/tests/test_bootstrap_strict_ci_runtime_arm64_optional_deps.py apps/api/tests/test_config_and_source_names.py -q` + `./bin/governance-audit --mode audit` | PASS | Runtime output contract, targeted governance/runtime tests, and full governance audit all pass after the tmp-only cut |
| Root/public hardening batch | Completed | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/tmp/pytest-governance-env uv run --extra dev pytest apps/worker/tests/test_governance_controls.py -q` + `python3 scripts/governance/check_public_entrypoint_references.py` + `./bin/governance-audit --mode audit` | PASS | Root denylist and public-entrypoint registry are both wired into active governance and remain green under full audit |
| Broad active-surface residual scan | Completed | targeted `rg` scans over active docs/config/scripts/workflows | PASS | No active maintenance surface still points at the retired scratch root; legacy public script literals remain only inside the public-entrypoint control-plane config as enforcement inputs |
| Wrapper expansion and doc-front-door recheck | Completed | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/tmp/pytest-governance-env uv run --extra dev pytest apps/worker/tests/test_governance_controls.py -q` + `python3 scripts/governance/check_public_entrypoint_references.py` + `./bin/governance-audit --mode audit` | PASS | Expanded wrapper set remains executable, core governance tests still pass, and active public-entrypoint enforcement stays green after front-door doc rewrites |
| Public bridge removal batch | Completed | `python3 scripts/governance/check_public_entrypoint_references.py` + `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/tmp/pytest-governance-env uv run --extra dev pytest apps/worker/tests/test_governance_controls.py -q` + `./bin/governance-audit --mode audit` | PASS | Bridge registry now tracks zero active bridges and governance fully accepts the bridge-free public-entrypoint state |
| Runtime metadata completeness batch | Completed | `python3 scripts/governance/check_runtime_metadata_completeness.py` + `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/tmp/pytest-governance-env uv run --extra dev pytest apps/worker/tests/test_governance_controls.py -q` + `./bin/governance-audit --mode audit` | PASS | Runtime metadata completeness is now an explicit governance gate; after fixing the maintenance report `source_run_id`, the full governance chain passes with the new requirement enabled |

## Risk / Blocker Log

| Time | Type | Item | Impact | Current Handling |
| :- | :- | :- | :- | :- |
| 2026-03-15 15:47:13 | Risk | `temp -> tmp` path cut touches scripts, docs, tests, CI, and runtime caches | Large coordinated path migration; incomplete cut would break strict verification | Execute after architecture truth cleanup, then re-run governance gates immediately |
| 2026-03-15 15:47:13 | Risk | Root `data/` may contain files without obvious destination | Risk of deleting useful evidence or fixtures | Classify each file into config or artifacts before deleting the root bucket |
| 2026-03-15 16:10:24 | Risk | Some non-gated historical notes may still mention retired scratch paths outside active verification surfaces | Could mislead future edits even if active gates are green | Run one more broad residual scan after root/public-entrypoint hardening and clean any stale historical leftovers that remain relevant |
| 2026-03-15 16:41:05 | Risk | Some deeper reference/deploy docs still mention internal scripts for implementation explanation even though the public bridge is gone | Future editors could confuse internal implementation references with public commands if this wording drifts | Keep public-entrypoint registry gate focused on front-door/public surfaces and continue opportunistic cleanup while deeper workstreams proceed |
| 2026-03-15 16:49:42 | Risk | Freshness-required writers may still be relying on post-write maintenance to fill metadata even though completeness is now enforced | Governance is greener than before, but final form still prefers write-time correctness over maintenance-time repair | Keep the new completeness gate in place and continue inventorying writer paths under WS-05 |

## Files Changed Log

| Time | Files / Paths Changed | Summary |
| :- | :- | :- |
| 2026-03-15 15:47:13 | `.agents/Plans/2026-03-15_15-47-13__repo-governance-final-form-execution-plan.md` | Replaced the partial control board with the final-form execution plan |
| 2026-03-15 15:58:34 | `config/governance/dependency-boundaries.json`, `config/governance/module-ownership.json`, `config/governance/bridges.json`, `config/governance/root-allowlist.json`, `docs/reference/architecture-governance.md`, `scripts/governance/gate.sh`, `scripts/governance/check_governance_schema_references_exist.py`, `apps/api/app/services/source_names.py`, `config/source-names/*`, `artifacts/performance/rsshub/*`, removed root `data/*` | Cleared active ghost-layer references, added governance truth existence enforcement, reclassified root data into config/performance locations, and tightened the active bridge registry |
| 2026-03-15 16:10:24 | `config/governance/runtime-outputs.json`, `config/governance/bridges.json`, `scripts/runtime/prune_state.sh`, `scripts/ci/prepare_web_runtime.sh`, `scripts/ci/run_mutmut.sh`, `scripts/ci/api_real_smoke_local.sh`, `scripts/ci/e2e_live_smoke.sh`, `scripts/governance/audit_github_runner_host.sh`, `scripts/governance/quality_gate.sh`, `scripts/env/compose_env.sh`, `scripts/env/validate_profile.sh`, `scripts/release/generate_release_prechecks.py`, `scripts/release/capture_canary_rollout_evidence.sh`, `apps/web/vitest.config.mts`, `apps/worker/tests/test_governance_controls.py`, `apps/worker/tests/test_ci_workflow_strictness.py`, `apps/worker/tests/test_bootstrap_strict_ci_runtime_arm64_optional_deps.py`, `.github/workflows/contract-diff.yml`, `README.md`, `docs/reference/cache.md`, `docs/runbook-local.md`, `docs/testing.md`, `docs/start-here.md`, `.env.example`, `ENVIRONMENT.md`, `infra/config/env.contract.json`, this plan file | Hard-cut active runtime scratch usage from `temp` to `tmp`, removed the temp bridge from active governance truth, updated docs/config/tests, and re-proved the cut with targeted tests plus governance audit |
| 2026-03-15 16:18:42 | `config/governance/root-denylist.json`, `config/governance/public-entrypoints.json`, `scripts/governance/check_public_entrypoint_references.py`, `scripts/governance/check_root_semantic_cleanliness.py`, `scripts/governance/gate.sh`, `bin/install-git-hooks`, `bin/smoke-full-stack`, `bin/api-real-smoke-local`, `AGENTS.md`, `CLAUDE.md`, `docs/reference/root-governance.md`, `apps/worker/tests/test_governance_controls.py`, `.github/workflows/ci.yml` | Added root denylist and public-entrypoint registry enforcement, introduced wrapper coverage for additional public commands, cleaned the last active legacy bridge reference from CI, and re-proved the batch with targeted tests plus governance audit |
| 2026-03-15 16:31:18 | `bin/prepare-web-runtime`, `bin/init-env-example`, `bin/validate-profile`, `bin/compose-env`, `bin/run-daily-digest`, `bin/run-failure-alerts`, `bin/start-ops-workflows`, `bin/reader-stack`, `bin/recreate-gce-instance`, `bin/final-governance-check`, `bin/canary-rollout`, `README.md`, `docs/start-here.md`, `docs/runbook-local.md`, `apps/api/AGENTS.md`, `apps/api/CLAUDE.md`, `apps/mcp/AGENTS.md`, `apps/mcp/CLAUDE.md`, `apps/worker/AGENTS.md`, `apps/worker/CLAUDE.md`, `apps/web/AGENTS.md`, `apps/web/CLAUDE.md` | Expanded bin wrapper coverage for commonly documented public commands and repointed the main front-door docs plus module collaboration docs away from legacy `scripts/*` command examples |
| 2026-03-15 16:41:05 | `bin/live-smoke`, `bin/smoke-llm-real-local`, `bin/smoke-computer-use-local`, `bin/external-playwright-smoke`, `bin/web-e2e`, `bin/runtime-cache-maintenance`, `bin/apply-runner-startup-metadata`, `bin/run-in-standard-env`, `README.md`, `docs/testing.md`, `docs/reference/env-script-overrides.md`, `docs/reference/dependency-governance.md`, `docs/reference/logging.md`, `docs/reference/cache.md`, `docs/reference/runtime-cache-retention.md`, `docs/deploy/miniflux-nextflux-gce.md`, `docs/deploy/full-stack-gce.md`, `docs/deploy/rollback-runbook.md`, `scripts/governance/check_bridge_expiry.py`, `config/governance/bridges.json` | Expanded wrapper coverage into testing/deploy/reference commands, repointed more active docs away from direct `scripts/*` usage, and removed the final public-entrypoint bridge while teaching the bridge gate that zero active bridges is valid final-form state |
| 2026-03-15 16:49:42 | `scripts/governance/check_runtime_metadata_completeness.py`, `scripts/governance/gate.sh`, `docs/reference/runtime-cache-retention.md`, `docs/reference/evidence-model.md`, `apps/worker/tests/test_governance_controls.py`, `scripts/runtime/prune_runtime_cache.py` | Added a dedicated runtime metadata completeness gate, wired it into governance, documented it, extended governance tests to assert it, and fixed the maintenance report metadata to satisfy the new contract |

## Evidence / Change Index

- Governance baseline verification: `./bin/governance-audit --mode audit`
- Ghost architecture scan: `rg -n "packages/shared-contracts|packages/|packages." ...`
- Temp bridge scan: targeted legacy scratch-root path search across repo surfaces
- Root residue scan: root `data/` listing
- Architecture truth cleanup verification: `python3 scripts/governance/check_governance_schema_references_exist.py`
- Post-cleanup governance verification: `./bin/governance-audit --mode audit`
- Tmp-only hard-cut verification: `python3 scripts/governance/check_runtime_outputs.py`
- Tmp-only targeted regression verification: `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/tmp/pytest-governance-env uv run --extra dev pytest apps/worker/tests/test_governance_controls.py apps/worker/tests/test_ci_workflow_strictness.py apps/worker/tests/test_bootstrap_strict_ci_runtime_arm64_optional_deps.py apps/api/tests/test_config_and_source_names.py -q`
- Tmp-only post-cut governance verification: `./bin/governance-audit --mode audit`
- Root/public registry verification: `python3 scripts/governance/check_public_entrypoint_references.py`
- Root/public regression verification: `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/tmp/pytest-governance-env uv run --extra dev pytest apps/worker/tests/test_governance_controls.py -q`
- Root/public post-cut governance verification: `./bin/governance-audit --mode audit`
- Broad residual scans: targeted `rg` over active docs/config/scripts/workflows for retired scratch-root and legacy public-entrypoint references
- Wrapper expansion verification: `chmod +x` on new `bin/*` wrappers + `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/tmp/pytest-governance-env uv run --extra dev pytest apps/worker/tests/test_governance_controls.py -q`
- Wrapper expansion post-cut governance verification: `python3 scripts/governance/check_public_entrypoint_references.py` + `./bin/governance-audit --mode audit`
- Public-bridge removal verification: `./bin/governance-audit --mode audit` with `bridge-expiry` reporting `PASS (0 bridges tracked)`
- Runtime metadata completeness verification: `python3 scripts/governance/check_runtime_metadata_completeness.py`
- Runtime metadata completeness post-cut governance verification: `./bin/governance-audit --mode audit`

## Next Actions

1. Continue WS-05 by inventorying freshness-required writers that still rely on maintenance-time metadata repair instead of write-time correctness.
2. Start WS-06 logging finalization by mapping which active outputs still need normalization into `logs/events/**` vs `logs/console/**`.
3. Opportunistically continue cleaning deeper explanatory docs where internal implementation script mentions would be clearer as public `bin/*` commands.

## Final Completion Summary

Not complete. This file was created to start the run. Final completion can only be declared after:

- all feasible structural workstreams are complete,
- all key validation gates have been re-run,
- active compatibility bridges are removed or explicitly blocked by an external dependency,
- and this plan file is updated to reflect the real final repository state.
