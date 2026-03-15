# Rollback Runbook

## Rollback SLO

- Target RTO: <= 15 minutes (trigger to stable restore).
- Rollback scope: API + Worker + Web service units and nginx canary routing.

## Preconditions

- A release manifest exists under `artifacts/releases/<tag>/manifest.json`.
- N-1 artifact checksums exist under `artifacts/releases/<tag>/checksums.sha256`.
- DB rollback readiness report exists under `artifacts/releases/<tag>/rollback/db-rollback-readiness.json`.
- Rollback drill evidence exists under `artifacts/releases/<tag>/rollback/drill.json`.
- `infra/nginx/vd.canary-routing.conf` has been deployed as `/etc/nginx/snippets/vd.canary-routing.conf`.

## DB Rollback Strategy (Mandatory Gate)

1. Run DB rollback readiness validation before release:

```bash
python3 scripts/release/verify_db_rollback_readiness.py \
  --release-tag <release-tag> \
  --output artifacts/releases/<release-tag>/rollback/db-rollback-readiness.json
```

2. Gate policy:
- `missing_policy > 0` means release must be blocked.
- `blocked_without_down > 0` means release must be blocked.
- `invalid_down_sql > 0` means release must be blocked (down file exists but has no executable SQL statement).
- Only `with_down_sql == total_up_migrations` can pass DB rollback gate.

3. Execute rollback drill and write evidence to `artifacts/releases/<release-tag>/rollback/drill.json`.
   Required keys: `release_tag`, `executed_at`, `executor`, `strategy`, `result`, `migrations_checked`.

4. If a migration is irreversible and cannot provide down SQL immediately, it must be listed in `infra/migrations/down/rollback-blockers.json`.
   This is still a blocking state until a real down migration is added.

## Emergency Rollback Steps

1. Route traffic back to stable immediately.

```bash
TARGET_WEIGHT=0 scripts/deploy/canary_rollout.sh --target 0 --step 100
```

2. Checkout and restore the previous known-good tag.

```bash
cd /opt/vd/repo
git fetch --tags
# replace <N-1-tag> with your previous production tag
git checkout <N-1-tag>
```

3. Reinstall dependencies and restart services.

```bash
uv sync --frozen
bash scripts/ci/prepare_web_runtime.sh
npm --prefix apps/web run build
sudo systemctl restart vd-api vd-worker vd-web
```

4. Validate health and critical workflow.

```bash
curl -fsS http://127.0.0.1:9000/healthz
curl -fsS http://127.0.0.1:9000/readyz
curl -fsS http://127.0.0.1:9000/metrics | head -n 20
```

5. Confirm release evidence and incident notes.

- Attach `manifest.json`, `checksums.sha256`, `rollback/db-rollback-readiness.json`, `rollback/drill.json`, failed pipeline evidence, and rollback timestamp to incident record.
- Create follow-up issue for root-cause and permanent fix.
