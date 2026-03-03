-- Down migration for 20260222_000007_delivery_retry_and_health.sql

DROP INDEX IF EXISTS idx_provider_health_checks_kind_status;
DROP INDEX IF EXISTS idx_provider_health_checks_checked_at;
DROP TABLE IF EXISTS provider_health_checks;

DROP INDEX IF EXISTS idx_notification_deliveries_retry;

ALTER TABLE notification_deliveries
    DROP CONSTRAINT IF EXISTS notification_deliveries_attempt_count_check;

ALTER TABLE notification_deliveries
    DROP COLUMN IF EXISTS attempt_count;

ALTER TABLE notification_deliveries
    DROP COLUMN IF EXISTS last_attempt_at;

ALTER TABLE notification_deliveries
    DROP COLUMN IF EXISTS next_retry_at;

ALTER TABLE notification_deliveries
    DROP COLUMN IF EXISTS last_error_kind;
