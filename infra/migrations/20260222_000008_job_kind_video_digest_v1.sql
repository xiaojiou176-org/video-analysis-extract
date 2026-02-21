-- Revision: 20260222_000008
-- Job kind rename: phase2_ingest_stub -> video_digest_v1 (compatibility window)

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_kind_check;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_kind_check
    CHECK (kind IN ('phase2_ingest_stub', 'video_digest_v1'));

UPDATE jobs
SET kind = 'video_digest_v1'
WHERE kind = 'phase2_ingest_stub';
