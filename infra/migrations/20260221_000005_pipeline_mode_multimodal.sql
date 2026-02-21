-- Revision: 20260221_000005
-- Add pipeline mode/overrides fields for multimodal processing.

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS mode VARCHAR(64);

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS overrides_json JSONB;

CREATE INDEX IF NOT EXISTS idx_jobs_status_updated_at
    ON jobs(status, updated_at DESC);
