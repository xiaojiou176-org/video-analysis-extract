#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# shellcheck source=./scripts/lib/standard_env.sh
source "$ROOT_DIR/scripts/lib/standard_env.sh"

mkdir -p .runtime-cache .runtime-cache/reports/python .runtime-cache/logs/tests
find .runtime-cache/reports/python -maxdepth 1 -type f -name '.coverage*' -delete 2>/dev/null || true
export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"
python3 scripts/runtime/clean_source_runtime_residue.py --apply
ensure_external_uv_project_environment "$ROOT_DIR"
uv sync --frozen --extra dev --extra e2e
set -o pipefail
(
  PYTHONDONTWRITEBYTECODE=1 uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q -rA -n 2 \
    --cov=apps/worker/worker \
    --cov=apps/api/app \
    --cov=apps/mcp/server.py \
    --cov=apps/mcp/tools \
    --cov-report=term-missing:skip-covered \
    --cov-report=xml:.runtime-cache/reports/python/python-coverage.xml \
    --cov-fail-under=95 \
    --junitxml=.runtime-cache/reports/python/python-tests-junit.xml \
    2>&1 | tee .runtime-cache/logs/tests/python-tests.log
) &
test_pid=$!

while kill -0 "${test_pid}" >/dev/null 2>&1; do
  echo "[heartbeat] python tests still running ($(date -u +'%Y-%m-%dT%H:%M:%SZ'))"
  sleep 25
done

wait "${test_pid}"
python3 scripts/runtime/clean_source_runtime_residue.py --apply

set -o pipefail
PYTHONDONTWRITEBYTECODE=1 uv run coverage report \
  --include="*/apps/worker/worker/pipeline/orchestrator.py,*/apps/worker/worker/pipeline/policies.py,*/apps/worker/worker/pipeline/runner.py,*/apps/worker/worker/pipeline/types.py" \
  --show-missing \
  --fail-under=95 \
  2>&1 | tee .runtime-cache/logs/tests/python-coverage-worker-core.log

set -o pipefail
PYTHONDONTWRITEBYTECODE=1 uv run coverage report \
  --include="*/apps/api/app/routers/ingest.py,*/apps/api/app/routers/jobs.py,*/apps/api/app/routers/subscriptions.py,*/apps/api/app/routers/videos.py,*/apps/api/app/services/jobs.py,*/apps/api/app/services/subscriptions.py,*/apps/api/app/services/videos.py" \
  --show-missing \
  --fail-under=95 \
  2>&1 | tee .runtime-cache/logs/tests/python-coverage-api-core.log

python - <<'PY'
import xml.etree.ElementTree as ET
from pathlib import Path

report = Path(".runtime-cache/reports/python/python-tests-junit.xml")
if not report.is_file():
    raise SystemExit("python skip guard failed: junit report missing")

root = ET.parse(report).getroot()
suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
tests = sum(int(suite.attrib.get("tests", "0")) for suite in suites)
skipped = sum(int(suite.attrib.get("skipped", "0")) for suite in suites)

if tests == 0:
    raise SystemExit("python skip guard failed: collected 0 tests")
if skipped > 0:
    raise SystemExit(f"python skip guard failed: skipped={skipped} (no silent skip allowed)")
print(f"python skip guard passed: tests={tests}, skipped={skipped}")
PY
