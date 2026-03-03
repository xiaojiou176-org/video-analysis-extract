-- Down migration helper for 20260222_000010 (manual rollback aid)
-- Note: this script is not auto-applied by migration runner; execute manually when needed.

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_pipeline_final_status_check;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_pipeline_final_status_check
    CHECK (
        pipeline_final_status IS NULL
        OR pipeline_final_status IN ('succeeded', 'partial', 'failed')
    );

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_status_check;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_status_check
    CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'partial'));

-- Revert semantic mapping for historical compatibility.
UPDATE jobs
SET status = 'partial'
WHERE status = 'succeeded'
  AND pipeline_final_status = 'degraded';

UPDATE jobs
SET pipeline_final_status = 'partial'
WHERE pipeline_final_status = 'degraded';

ALTER TABLE jobs
    DROP COLUMN IF EXISTS llm_required;

ALTER TABLE jobs
    DROP COLUMN IF EXISTS llm_gate_passed;

ALTER TABLE jobs
    DROP COLUMN IF EXISTS hard_fail_reason;
