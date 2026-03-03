-- Down migration for 20260221_000006_notifications_automation.sql

DROP TABLE IF EXISTS daily_digest_runs;

DROP INDEX IF EXISTS uq_notification_deliveries_video_digest_job_id;

ALTER TABLE notification_deliveries
    DROP CONSTRAINT IF EXISTS notification_deliveries_kind_check;

ALTER TABLE notification_deliveries
    ADD CONSTRAINT notification_deliveries_kind_check CHECK (
        kind IN ('test_email', 'failure_alert', 'daily_digest')
    );
