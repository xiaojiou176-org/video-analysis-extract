-- Down migration for 20260221_000003_phase4_observability.sql

DROP INDEX IF EXISTS idx_jobs_pipeline_final_status;

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_pipeline_final_status_check;

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_degradation_count_check;

ALTER TABLE jobs
    DROP COLUMN IF EXISTS pipeline_final_status;

ALTER TABLE jobs
    DROP COLUMN IF EXISTS degradation_count;

ALTER TABLE jobs
    DROP COLUMN IF EXISTS last_error_code;
