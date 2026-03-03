-- Down migration for 20260222_000008_job_kind_video_digest_v1.sql

UPDATE jobs
SET kind = 'phase2_ingest_stub'
WHERE kind = 'video_digest_v1';

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_kind_check;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_kind_check
    CHECK (kind = 'phase2_ingest_stub');
