# Runtime Cache Retention

`.runtime-cache/` is the only legal repo-side runtime output root.

## Source Of Truth

- `config/governance/runtime-outputs.json`

## Canonical Compartments

- `run/`
- `logs/`
- `reports/`
- `evidence/`
- `tmp/`

The list above must match the `subdirectories` declared in `config/governance/runtime-outputs.json` exactly. The only legal scratch compartment is `tmp/`; the old `temp/` dual wording is no longer allowed.

Each compartment must declare:

- `owner`
- `classification`
- `ttl_days`
- `max_total_size_mb`
- `max_file_count`
- `rebuild_entrypoint`
- `freshness_required`

## Metadata Rules

Artifacts under `reports/**` and `evidence/**` must ship with sidecar metadata that includes at least:

- `created_at`
- `source_entrypoint`
- `source_run_id`
- `source_commit`
- `verification_scope`
- `freshness_window_hours`

## Gates And Maintenance Entrypoints

```bash
python3 scripts/runtime/prune_runtime_cache.py --assert-clean
python3 scripts/governance/check_runtime_cache_retention.py
python3 scripts/governance/check_runtime_metadata_completeness.py
python3 scripts/governance/check_runtime_cache_freshness.py
./bin/runtime-cache-maintenance --normalize-only
```

## Hard Rules

- Historical artifacts must not be reused as current verification once they exceed their freshness window.
- After deleting `.runtime-cache/**`, the repository must be able to rebuild the runtime tree through standard entrypoints.
