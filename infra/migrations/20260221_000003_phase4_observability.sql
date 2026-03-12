-- Revision: 20260221_000003
-- Phase 4 observability fields on jobs

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS pipeline_final_status VARCHAR(32);

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS degradation_count INTEGER;

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS last_error_code VARCHAR(128);

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_pipeline_final_status_check;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_pipeline_final_status_check
    CHECK (
        pipeline_final_status IS NULL
        OR pipeline_final_status IN ('succeeded', 'degraded', 'failed')
    );

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_degradation_count_check;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_degradation_count_check
    CHECK (
        degradation_count IS NULL
        OR degradation_count >= 0
    );

CREATE INDEX IF NOT EXISTS idx_jobs_pipeline_final_status
    ON jobs(pipeline_final_status);
