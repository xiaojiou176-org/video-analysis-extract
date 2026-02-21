-- Revision: 20260221_000002
-- Phase 3 artifact persistence fields

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS artifact_digest_md TEXT;

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS artifact_root TEXT;

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_status_check;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_status_check
    CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'partial'));
