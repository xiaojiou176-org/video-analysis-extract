-- Down migration for 20260221_000005_pipeline_mode_multimodal.sql

DROP INDEX IF EXISTS idx_jobs_status_updated_at;

ALTER TABLE jobs
    DROP COLUMN IF EXISTS mode;

ALTER TABLE jobs
    DROP COLUMN IF EXISTS overrides_json;
