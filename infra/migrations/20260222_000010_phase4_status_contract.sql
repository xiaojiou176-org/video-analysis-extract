-- Revision: 20260222_000010
-- Phase 4 contract upgrade: job status + pipeline final status + LLM gate fields

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS llm_required BOOLEAN;

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS llm_gate_passed BOOLEAN;

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS hard_fail_reason TEXT;

-- Backfill historical partial semantics to the new model:
-- 1) pipeline_final_status: partial -> degraded
-- 2) jobs.status: partial -> succeeded (degraded is carried by pipeline_final_status)
UPDATE jobs
SET pipeline_final_status = 'degraded'
WHERE pipeline_final_status = 'partial';

UPDATE jobs
SET pipeline_final_status = 'degraded'
WHERE pipeline_final_status IS NULL
  AND status = 'partial';

UPDATE jobs
SET status = 'succeeded'
WHERE status = 'partial';

-- Defensive normalization for historical/manual writes:
-- make sure values always satisfy the new status contracts before constraints are re-added.
UPDATE jobs
SET status = 'failed'
WHERE status IS NULL
   OR status NOT IN ('queued', 'running', 'succeeded', 'failed');

UPDATE jobs
SET pipeline_final_status = CASE
    WHEN status = 'failed' THEN 'failed'
    WHEN status = 'succeeded' THEN 'succeeded'
    ELSE NULL
END
WHERE pipeline_final_status IS NOT NULL
  AND pipeline_final_status NOT IN ('succeeded', 'degraded', 'failed');

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_pipeline_final_status_check;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_pipeline_final_status_check
    CHECK (
        pipeline_final_status IS NULL
        OR pipeline_final_status IN ('succeeded', 'degraded', 'failed')
    );

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_status_check;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_status_check
    CHECK (status IN ('queued', 'running', 'succeeded', 'failed'));
