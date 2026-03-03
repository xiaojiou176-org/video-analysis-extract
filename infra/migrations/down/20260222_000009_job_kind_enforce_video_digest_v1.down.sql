-- Down migration for 20260222_000009_job_kind_enforce_video_digest_v1.sql

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_kind_check;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_kind_check
    CHECK (kind IN ('phase2_ingest_stub', 'video_digest_v1'));
