-- Revision: 20260222_000009
-- Job kind finalize: enforce video_digest_v1 as the only persisted value.

UPDATE jobs
SET kind = 'video_digest_v1'
WHERE kind = 'phase2_ingest_stub';

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_kind_check;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_kind_check
    CHECK (kind = 'video_digest_v1');
