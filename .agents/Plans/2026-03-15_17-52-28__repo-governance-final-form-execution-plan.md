# Repo Governance Final Form Execution Plan

## Header

- Plan Title: Repo Governance Final Form Execution Plan
- Created At: 2026-03-15 17:52:28 America/Los_Angeles
- Last Updated: 2026-03-15 19:33:00 America/Los_Angeles
- Repo Name: 视频分析提取
- Repo Path: `/Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取`
- Repo Archetype: `hybrid-repo`
- Objective: Push the repo to Final Form across architecture, cache, logging, root cleanliness, and upstream integration governance with hard-cut execution and no long-lived compatibility leaks.
- Current Execution Status: `In Progress`
- Current Phase: `Phase B - Execution`
- Current Workstream: `WS11 Upstream Governance Final Closure`

## Objective

Turn the repo into a machine-governed engineering system where:

- root is a clean policy foyer, not a dump room
- shared boundaries are contract-first and machine-enforced
- repo-side runtime output has one legal root and one legal scratch lane
- logs, reports, and evidence are layered and traceable by run identity
- upstream systems are governed as first-class external boundaries, not casual dependencies

## Score Targets

| Dimension | Target |
| :-- | :-- |
| Architecture Governance | 30/30 |
| Cache Governance | 20/20 |
| Logging Governance | 20/20 |
| Root Cleanliness Governance | 10/10 |
| Upstream Integration Governance | 20/20 |
| Total | 100/100 |

## Current Status

### Audit Snapshot

- Current strongest area: architecture, logging, and root governance control plane already exist and largely pass.
- Freshly closed blocker: the undeclared legacy runtime scratch lane under `.runtime-cache/` has been removed and governance audit is green again.
- Current most important structural gap: root cleanliness and runtime-root closure have now been tied together locally, but the stronger closure still needs to be carried further into broader execution paths and later workstreams.
- Current upstream maturity gap: same-run cohesion is now enforced and two blocker rows have been freshly re-proved, but `rsshub-youtube-ingest-chain` still lacks a clean passing smoke bundle and `resend-digest-delivery-chain` still lacks a standardized compat evidence lane.
- Fresh WS3 progress: current-run release/readiness outputs now land in canonical `.runtime-cache/reports/release-readiness/` lanes with managed runtime metadata.
- Fresh execution-hygiene progress: local Python test execution now has a stable public entrypoint that avoids root `.venv` pollution by default.

### Current Status By Dimension

| Dimension | Status | Current Truth |
| :-- | :-- | :-- |
| Architecture Governance | `Partially Completed` | Strong responsibility layering and boundary checks already exist. |
| Cache Governance | `Partially Completed` | Runtime root is back to declared lanes, maintenance now fails closed on unknown children, and `tmp` is covered by retention checks. |
| Logging Governance | `Partially Completed` | Contract and samples are strong; full-chain closure still needs reinforcement. |
| Root Cleanliness Governance | `Partially Completed` | Root-level gates pass, but runtime-root hygiene is not yet tied into final cleanliness verdict. |
| Upstream Integration Governance | `Partially Completed` | Inventory and matrix exist; `gemini-worker-llm-chain` and `strict-ci-compose-image-set` are now freshly re-proved, but two blocker rows still need closure. |

## Workstream Table

| Workstream | Status | Priority | Current Owner | Recent Action | Next Step | Verification Status |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| WS1 Directory and Responsibility Layer Hardening | `Not Started` | P1 | Codex | Audit complete | Freeze target tree and align allowlist/docs | `Not Verified` |
| WS2 Dependency Boundary and Contract-First Hardening | `Not Started` | P1 | Codex | Audit complete | Extend contract/upstream coupling rules | `Not Verified` |
| WS3 Generated / Build / Release Artifact Separation | `In Progress` | P1 | Codex | Moved prechecks, KPI summary, and release-readiness current-run outputs into canonical report lanes, updated docs/CI wiring, and re-rendered generated docs | Continue normalizing any remaining release/readiness current-run outputs | `Partially Verified` |
| WS4 Cache Closure and Runtime Output Hard Cut | `Verified` | P0 | Codex | Removed legacy scratch-lane residue, hardened maintenance against unknown children, tmp age semantics, and racey disappearing files | Move to broader closure workstreams | `Verified` |
| WS5 Logging Schema / Correlation / Evidence Linkage | `Not Started` | P1 | Codex | Audit complete | Expand full-chain writer coverage and linkage checks | `Not Verified` |
| WS6 Test Evidence Layering | `Not Started` | P1 | Codex | Audit complete | Normalize current-run evidence/report trees | `Not Verified` |
| WS7 Root Cleanliness Final Closure | `In Progress` | P1 | Codex | Root dirtiness check now also fails on undeclared runtime-root direct children | Propagate stronger cleanliness semantics into remaining validation surfaces | `Partially Verified` |
| WS8 Public Entrypoint / Wrapper Finalization | `Not Started` | P2 | Codex | Audit complete | Eliminate direct public `scripts/*` usage | `Not Verified` |
| WS9 CI / Hook / Enforcement Wiring | `In Progress` | P1 | Codex | Wired runtime-root closure, same-run cohesion, managed Python tests, render output drift fixes, tmp budget alignment, and pushed debug-build strict pre-push all the way through local pass | Continue converting remaining operator surfaces away from stale raw entrypoints and repo-tmp test env assumptions | `Partially Verified` |
| WS10 Docs / ADR / Module README Alignment | `Not Started` | P2 | Codex | Audit complete | Realign docs after structural hard cuts land | `Not Verified` |
| WS11 Upstream Governance Final Closure | `In Progress` | P1 | Codex | Re-proved `gemini-worker-llm-chain` and `strict-ci-compose-image-set` on the current snapshot, but `rsshub-youtube-ingest-chain` still fails inside live smoke and `resend-digest-delivery-chain` still lacks a standardized compat evidence lane | Isolate the remaining live smoke failure and add/run a standardized resend compat receipt | `Partially Verified` |
| WS12 Bridge and Compatibility Layer Burn-Down | `Not Started` | P2 | Codex | Audit complete | Track and remove any temporary bridges | `Not Verified` |

## Task Checklist

### WS4 Cache Closure and Runtime Output Hard Cut

- [x] Remove illegal legacy scratch-lane residue and restore runtime-root contract closure.
  - Target: old undeclared runtime scratch artifacts under `.runtime-cache/`
  - Verification: `./bin/governance-audit --mode audit`
  - Evidence: governance audit must no longer fail on undeclared runtime child
- [x] Extend runtime maintenance to detect or clean unknown direct children under `.runtime-cache/`.
  - Target: `scripts/runtime/prune_runtime_cache.py`, `scripts/runtime/run_runtime_cache_maintenance.sh`
  - Verification: `./bin/runtime-cache-maintenance --assert-clean`
- [x] Add or extend a runtime root closure gate so unknown runtime children fail fast in pre-commit, pre-push, and CI.
  - Target: governance scripts + CI/hook wiring
  - Verification: governance audit and strict CI
- [x] Include `tmp` in assert-clean retention coverage and confirm no blind spots remain.
  - Target: `scripts/governance/check_runtime_cache_retention.py`
  - Verification: retention gate green
- [ ] Prove cache can be deleted and rebuilt in the same snapshot.
  - Target: runtime rebuild drill
  - Verification: clean + rebuild + smoke pass

### WS3 Generated / Build / Release Artifact Separation

- [-] Eliminate any current-run release-readiness output that bypasses canonical `reports` or `artifacts` lanes.
- [x] Confirm release-readiness current-run outputs live only in `.runtime-cache/reports/**` for the prechecks lane.
- [ ] Confirm archival release evidence lives only in `artifacts/releases/**`.
- [x] Move current-run KPI summary and release-readiness outputs into `.runtime-cache/reports/release-readiness/**`.

### WS7 Root Cleanliness Final Closure

- [x] Upgrade root dirtiness check so runtime-root closure is part of the same final cleanliness verdict.
- [-] Confirm install/lint/test/build/e2e/mutation do not create unknown root or runtime-root entries.

### WS11 Upstream Governance Final Closure

- [x] Add same-run cohesion enforcement for blocker compat rows.
- [ ] Re-drive blocker upstream verification rows on current snapshot where possible.
- [x] Re-drive `gemini-worker-llm-chain` on current snapshot and promote it with current artifact metadata.
- [x] Re-drive `strict-ci-compose-image-set` via debug-build strict pre-push and promote it with current quality-gate summary metadata.
- [x] Ensure current-run compat proof cannot be silently substituted by historical artifacts.
  - Evidence: fresh audit shows several pending blocker rows currently point at missing run artifacts, so they are no longer being over-claimed as verified.

## Decision Log

| Time | Decision | Why | Rejected Alternative | Impact |
| :-- | :-- | :-- | :-- | :-- |
| 2026-03-15 17:52:28 | Use this file as the single execution control board inside the repo. | Chat context is not durable enough for long hard-cut governance work. | Keeping progress only in chat would drift and lose execution truth. | All work must be mirrored here after each structural step. |
| 2026-03-15 17:52:28 | Start with WS4 cache closure before broader polish. | Fresh governance audit is currently red specifically because of runtime-root drift. | Starting with docs or dashboard polish would create fake progress. | WS4 is the first honest blocker lane. |
| 2026-03-15 18:06:00 | Treat runtime maintenance robustness as part of the hard cut, not optional polish. | Unknown-child cleanup crashed on malformed metadata and disappearing tmp files, which would make the governance system itself unreliable. | Deleting only the visible residue would have hidden a structural weakness. | `prune_runtime_cache.py` now self-heals malformed metadata, skips vanished files, and gives `tmp` its own age semantics. |
| 2026-03-15 18:18:00 | Treat root dirtiness as “root foyer + runtime-root entrance” instead of top-level-only cleanliness. | Final Form cleanliness cannot claim success if `.runtime-cache/` quietly grows undeclared children. | Keeping root-dirtiness scoped only to top-level entries would preserve a false-clean state. | `check_root_dirtiness_after_tasks.py` now fails on undeclared runtime-root direct children too. |
| 2026-03-15 18:34:00 | Do not upgrade blocker upstream rows by inference; require same-run artifact reality first. | Fresh matrix inspection showed several pending blocker rows currently reference missing artifacts, so current work must build stronger closure rules instead of polishing wording. | Promoting rows based on inventory fields or old matrix timestamps would recreate the same fake-maturity bug this repo has been fighting. | WS11 now becomes the next honest critical path after WS4 and WS7 local closure. |
| 2026-03-15 18:48:00 | Enforce same-run cohesion only for blocker rows that claim `verified`, but still report pending blocker bundle gaps. | The repo needs an honest gate that blocks fake promotions without instantly turning all pending blocker rows into false failures. | Failing every pending blocker row immediately would conflate “not yet proven” with “invalid state” and would not help stage work. | `check_upstream_same_run_cohesion.py` now makes “verified blocker” a higher bar while preserving honest pending states. |
| 2026-03-15 18:56:00 | Treat current-run release/readiness outputs as machine reports, not scratch artifacts. | Precheck JSON and rollback-readiness reports describe the current run's verification state, so they belong in the report cabinet, not the tmp workbench. | Leaving them under scratch-like paths would keep WS3 half-finished and make current-vs-archived evidence harder to reason about. | `generate_release_prechecks.py` now emits canonical current-run outputs under `.runtime-cache/reports/release-readiness/`. |
| 2026-03-15 19:08:00 | Promote managed local Python test execution to a public entrypoint. | Root `.venv` creation is a governance smell; relying on engineers to remember `UV_PROJECT_ENVIRONMENT` is not a stable final-form answer. | Leaving raw `uv run pytest` as the default documented path would keep reintroducing root pollution. | Added `bin/python-tests`, taught `scripts/ci/python_tests.sh` to force an external uv environment, and started moving docs/module contracts to the new entrypoint. |
| 2026-03-15 19:18:00 | Current-run KPI and readiness summaries belong in `.runtime-cache/reports/release-readiness/`, not `artifacts/release-readiness/`. | They are current-run machine reports, not long-lived release archives. | Keeping them under `artifacts/` would blur current-run truth with archival evidence. | `collect_kpi.py`, `build_readiness_report.py`, CI upload paths, docs, and render logic now point at canonical current-run report lanes. |
| 2026-03-15 19:23:00 | `pr_llm_real_smoke.sh` must start API with the same write-token semantics as other real smoke entrypoints. | The first strict re-drive proved Gemini external probe was green but local `/computer-use/run` was 401 due to local auth mismatch. | Treating that as an upstream failure would have been a false diagnosis. | `pr_llm_real_smoke.sh` now exports managed write tokens and starts API through `scripts/runtime/dev_api.sh`. |
| 2026-03-15 19:28:00 | `tmp` budget must align with the repo's formal web-runtime design, while repo-local pytest env residue should be cleared. | The deepest strict gate reached `runtime-cache-maintenance` failure because formal `web-runtime` plus leftover pytest env exceeded file-count budget. | Pretending `web-runtime` is not an official tmp resident would contradict current repo design. | Cleared `.runtime-cache/tmp/pytest-governance-env`, raised tmp file-count budget to fit the formal web-runtime workspace, and re-proved retention/audit gates. |
| 2026-03-15 19:31:00 | Treat `gemini-worker-llm-chain` and `strict-ci-compose-image-set` as freshly verified on this snapshot. | Both now have real current-run artifacts and pass same-run cohesion rules. | Leaving them pending would keep the matrix behind repo reality. | Blocker rows promoted from pending to verified with current run ids and timestamps. |

## Validation Log

| Validation Item | Status | Method | Result | Notes |
| :-- | :-- | :-- | :-- | :-- |
| Governance audit current state | `Passed` | `./bin/governance-audit --mode audit` | PASS after runtime-root cleanup and maintenance hardening | Fresh local proof on current snapshot |
| Root allowlist | `Passed` | `python3 scripts/governance/check_root_allowlist.py --strict-local-private` | PASS | Root foyer rules are alive |
| Logging contract | `Passed` | `python3 scripts/governance/check_logging_contract.py` | PASS | Logging control plane healthy |
| Dependency boundaries | `Passed` | `python3 scripts/governance/check_dependency_boundaries.py` | PASS | Internal graph largely healthy |
| Upstream governance | `Passed` | `python3 scripts/governance/check_upstream_governance.py` | PASS | Control plane exists |
| Upstream compat freshness | `Passed` | `python3 scripts/governance/check_upstream_compat_freshness.py` | PASS | Only verified rows enforced right now |
| Runtime cache retention including `tmp` | `Passed` | `python3 scripts/governance/check_runtime_cache_retention.py` | PASS | Unknown-child closure plus tmp retention are now green |
| Root dirtiness with runtime-root closure | `Passed` | `python3 scripts/governance/check_root_dirtiness_after_tasks.py --write-snapshot ... && --compare-snapshot ...` | PASS | Cleanliness now checks root and runtime-root together |
| Governance contract tests | `Passed` | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/tmp/pytest-governance-env uv run pytest apps/worker/tests/test_governance_controls.py apps/api/tests/test_quality_gate_script_contract.py -q` | 15 passed | Used controlled tmp env instead of root `.venv` |
| Upstream blocker artifact reality check | `Passed` | Matrix artifact existence audit | Pending blocker rows still lack multiple current artifacts; verified rows are not being falsely promoted in current gate output | Confirms WS11 is the next honest workstream |
| Upstream same-run cohesion gate | `Passed` | `python3 scripts/governance/check_upstream_same_run_cohesion.py` | PASS (`verified_blocker_rows=0 pending_blocker_rows=4`) | Same-run rule is now live for blocker rows |
| Upstream verify entrypoint | `Passed` | `./bin/upstream-verify` | PASS with same-run cohesion included | Entry-level enforcement now includes the new upstream gate |
| Release prechecks canonical current-run lane | `Passed` | `python3 scripts/release/generate_release_prechecks.py --repo-root . --skip-observability-checks` | Outputs now land under `.runtime-cache/reports/release-readiness/` and carry runtime metadata | WS3 current-run report placement has started landing |
| Release/readiness path contract tests | `Passed` | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/tmp/pytest-governance-env uv run pytest apps/worker/tests/test_release_prechecks_observability.py apps/worker/tests/test_supply_chain_ci_contracts.py -q` | 14 passed | Script/docs/tests are aligned on the new path |
| Managed Python test entrypoint contract | `Passed` | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/tmp/pytest-governance-env uv run pytest apps/worker/tests/test_governance_controls.py apps/worker/tests/test_supply_chain_ci_contracts.py apps/worker/tests/test_release_prechecks_observability.py apps/api/tests/test_quality_gate_script_contract.py -q` | 31 passed | New `bin/python-tests` and managed uv environment rules are covered by contract tests |

## Risk / Blocker Log

| Time | Type | Description | Impact | Can Continue? | Unblock Condition |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 2026-03-15 17:52:28 | `Resolved` | Legacy release-readiness residue under an old runtime scratch lane had left an undeclared direct child under runtime root. | The original governance blocker is closed. | Yes | Closed by cleanup plus maintenance hardening; keep regression guards in place. |
| 2026-03-15 17:52:28 | `Resolved` | Runtime maintenance previously reasoned mostly over declared subdirs and could miss future unknown runtime children. | Drift would have been able to recur. | Yes | Closed locally by unknown-child fail-close behavior and runtime-root cleanliness integration. |
| 2026-03-15 17:52:28 | `Risk` | Blocker upstream compat rows still need fresh same-snapshot closure. | Upstream governance cannot honestly reach 20/20 yet. | Yes | Build same-run cohesion checks and re-verify blocker rows. |
| 2026-03-15 18:22:00 | `Risk` | Default `uv run` behavior created a root `.venv`, which is incompatible with final root cleanliness. | Uncontrolled local test execution can still pollute the root if not routed through a controlled environment. | Yes | Standardize all local governance test execution on repo-external or `.runtime-cache/tmp` managed environments; reject root `.venv` creation in later workstreams. |
| 2026-03-15 18:34:00 | `Risk` | Pending blocker upstream rows currently reference missing run artifacts such as `pr-llm-real-smoke-result.json`, `e2e-live-smoke-result.json`, `smoke-full-stack.jsonl`, and `compat-resend-daily-sent.log`. | The repo can claim governance control-plane maturity but cannot honestly claim upstream Final Form closure yet. | Yes | Add same-run cohesion enforcement and re-drive blocker row evidence on the current snapshot. |
| 2026-03-15 18:48:00 | `Risk` | same-run cohesion is now enforced, but current blocker rows are still pending because several row-specific evidence files do not exist on this snapshot. | WS11 is structurally safer now, but not complete. | Yes | Produce real current-run blocker bundles or keep rows pending. |
| 2026-03-15 18:56:00 | `Risk` | Other release/readiness helpers may still reference mixed current-run vs archived lanes beyond the first prechecks path hard cut. | WS3 has started but is not yet fully normalized. | Yes | Continue scanning and migrating remaining release/readiness current-run outputs. |
| 2026-03-15 19:08:00 | `Risk` | Root `.venv` pollution is now avoided by the new default test entrypoint, but many docs and workflows still contain raw `uv sync` / `uv run pytest` idioms that need staged normalization. | Execution hygiene has improved, but the repo is not yet globally consistent on this policy. | Yes | Continue migrating operator-facing and policy-facing surfaces toward managed public entrypoints. |
| 2026-03-15 19:33:00 | `Risk` | `rsshub-youtube-ingest-chain` still lacks a clean passing smoke bundle. A scoped rerun skipped out-of-scope computer-use, but the live smoke chain still failed deeper in `e2e_live_smoke` and needs targeted debugging. | Upstream governance cannot honestly claim this blocker row yet. | Yes | Fix the remaining `e2e_live_smoke` contract/live-path failure and re-run scoped full-stack smoke. |
| 2026-03-15 19:33:00 | `Risk` | `resend-digest-delivery-chain` still has no standardized compat evidence lane for `.runtime-cache/logs/tests/compat-resend-daily-sent.log`. | The resend blocker row remains pending even though full-stack/daily workflow surfaces are healthier. | Yes | Add or reuse a managed resend compat smoke entrypoint that emits the required log with runtime metadata, then re-drive the row. |

## Files Changed Log

| Time | Files / Paths Changed | Summary |
| :-- | :-- | :-- |
| 2026-03-15 17:52:28 | `.agents/Plans/2026-03-15_17-52-28__repo-governance-final-form-execution-plan.md` | Created execution source of truth. |
| 2026-03-15 18:24:00 | `scripts/runtime/prune_runtime_cache.py` | Added unknown runtime-child fail-close handling, malformed metadata self-heal, disappearing-file tolerance, and `tmp`-specific age semantics. |
| 2026-03-15 18:24:00 | `scripts/governance/check_runtime_cache_retention.py` | Added `tmp` to assert-clean retention coverage. |
| 2026-03-15 18:24:00 | `scripts/governance/common.py` | Made runtime metadata reads tolerant of malformed sidecars so maintenance can self-heal. |
| 2026-03-15 18:24:00 | `scripts/governance/check_root_dirtiness_after_tasks.py` | Upgraded cleanliness verdict to include undeclared runtime-root direct children. |
| 2026-03-15 18:24:00 | `apps/worker/tests/test_governance_controls.py` | Added governance contract assertions for runtime maintenance hardening and stronger root dirtiness semantics. |
| 2026-03-15 18:24:00 | `docs/reference/root-governance.md` | Documented that root cleanliness now includes runtime-root direct-child closure. |
| 2026-03-15 18:34:00 | `.runtime-cache/tmp/pytest-governance-env` | Established a controlled tmp-based local governance test environment after rejecting root `.venv` behavior. |
| 2026-03-15 18:48:00 | `scripts/governance/check_upstream_same_run_cohesion.py` | Added blocker-row same-run cohesion gate and cohesion report artifact. |
| 2026-03-15 18:48:00 | `scripts/governance/gate.sh`, `bin/upstream-verify` | Wired same-run cohesion into governance and upstream verification entrypoints. |
| 2026-03-15 18:48:00 | `docs/reference/upstream-governance.md`, `docs/reference/upstream-compatibility-policy.md` | Documented same-run blocker proof requirements and shared-report limitations. |
| 2026-03-15 18:48:00 | `apps/worker/tests/test_governance_controls.py` | Added contract assertions for same-run cohesion gate wiring. |
| 2026-03-15 18:56:00 | `scripts/release/generate_release_prechecks.py` | Moved current-run prechecks and rollback-readiness outputs into `.runtime-cache/reports/release-readiness/` while keeping scratch state in `.runtime-cache/tmp/`. |
| 2026-03-15 18:56:00 | `README.md`, `docs/runbook-local.md` | Updated operator-facing commands to point at the canonical current-run report lane. |
| 2026-03-15 18:56:00 | `apps/worker/tests/test_supply_chain_ci_contracts.py` | Added regression guard for canonical release precheck report placement. |
| 2026-03-15 19:08:00 | `scripts/ci/python_tests.sh`, `bin/python-tests` | Added a managed public Python test entrypoint that forces an external uv project environment and avoids root `.venv` drift. |
| 2026-03-15 19:08:00 | `config/governance/public-entrypoints.json` | Registered `bin/python-tests` as a required public entrypoint. |
| 2026-03-15 19:08:00 | `apps/api/AGENTS.md`, `apps/api/CLAUDE.md`, `apps/worker/AGENTS.md`, `apps/worker/CLAUDE.md`, `apps/mcp/AGENTS.md`, `apps/mcp/CLAUDE.md`, `docs/testing.md` | Started migrating module and operator docs from raw pytest invocations to the managed public entrypoint. |
| 2026-03-15 19:18:00 | `scripts/ci/collect_kpi.py`, `scripts/release/build_readiness_report.py`, `.github/workflows/ci.yml`, `README.md`, `docs/runbook-local.md`, `docs/testing.md`, `scripts/governance/render_docs_governance.py`, `docs/generated/*.md` | Moved current-run KPI/readiness reports into `.runtime-cache/reports/release-readiness/` and synced generated docs/control plane. |
| 2026-03-15 19:23:00 | `scripts/ci/pr_llm_real_smoke.sh`, `config/governance/upstream-compat-matrix.json` | Fixed local API auth semantics for real Gemini smoke and promoted the Gemini blocker row after a passing current-run receipt. |
| 2026-03-15 19:28:00 | `config/governance/runtime-outputs.json` | Aligned tmp budget with the formal web-runtime workspace and removed repo-local pytest environment residue. |

## Next Actions

1. Debug the remaining `e2e_live_smoke` live-path failure and re-drive scoped `smoke-full-stack` to close `rsshub-youtube-ingest-chain`.
2. Add or reuse a managed resend compat smoke/log entrypoint and re-drive `resend-digest-delivery-chain`.
3. Continue WS9 by removing the last stale raw test-entrypoint assumptions from operator-facing and policy-facing surfaces.
4. After the remaining two blocker rows are either freshly re-proved or classified as external-only blockers, re-run `./bin/upstream-verify` and the deepest strict chain again to lock final status.

## Final Completion Summary

- Status: `In Progress`
- Final completion has not been reached.
- This plan file is now the single source of truth for execution state, verification state, risk state, and next actions.
