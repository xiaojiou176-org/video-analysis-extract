# Upstream Compatibility Policy

`config/governance/upstream-compat-matrix.json` records which upstream combinations are allowed to enter the mainline. It is not a permanent hall of fame.

## Minimum Conditions For A Compatibility Verdict

Each matrix row must define at least:

- `verification_status`
- `last_verified_at`
- `last_verified_run_id`
- `freshness_window_hours`
- `verification_scope`
- `verification_artifacts`

## Status Semantics

- `verified`: this combination has real acceptance artifacts inside its freshness window. Think of it as “this batch was just inspected and the receipt is on file.”
- `pending`: the combination is still supported, but the current workspace has no fresh acceptance artifacts. It must not be reported as “just verified.”
- `declared`: only designed or registered; not yet promoted into the current mainline verification surface.
- `waived`: explicitly exempted, and the reason must be explained by docs or a decision record.

## Freshness Policy

- blocker lanes: recommended `<= 72h`
- important lanes: recommended `<= 168h`
- once an artifact exceeds its freshness window, it must be treated as `stale` even if the file still exists

## Hard Rules

- A `verified` status may only be backed by artifacts inside the freshness window; non-`verified` rows do not count as current compatibility proof.
- Artifact metadata must trace back to both `source_run_id` and `source_commit`.
- Failure attribution inside the compatibility matrix must map to the shared failure-class enum.
- To upgrade a blocker row to `verified`, its row-specific artifact set must form the same-run evidence bundle referenced by `last_verified_run_id`.
- Shared governance summary pages such as `upstream-compat-report.json` can serve as indexes, but they cannot independently prove same-run closure for blocker rows.
