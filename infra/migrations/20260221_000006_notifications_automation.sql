-- Revision: 20260221_000006
-- Notification automation schema updates.

DO $$
DECLARE
    target_table regclass := to_regclass('notification_deliveries');
BEGIN
    IF target_table IS NOT NULL AND EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'notification_deliveries_kind_check'
          AND conrelid = target_table
    ) THEN
        ALTER TABLE notification_deliveries
            DROP CONSTRAINT notification_deliveries_kind_check;
    END IF;
END $$;

ALTER TABLE notification_deliveries
    ADD CONSTRAINT notification_deliveries_kind_check CHECK (
        kind IN ('test_email', 'failure_alert', 'daily_digest', 'video_digest')
    );

CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_deliveries_video_digest_job_id
    ON notification_deliveries(job_id)
    WHERE kind = 'video_digest' AND job_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS daily_digest_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    local_date DATE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    summary_json JSONB,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_daily_digest_runs_local_date UNIQUE (local_date),
    CONSTRAINT daily_digest_runs_status_check CHECK (
        status IN ('running', 'succeeded', 'failed', 'partial')
    )
);
