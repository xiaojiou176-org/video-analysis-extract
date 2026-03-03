-- Down migration for 20260226_000015_notification_deliveries_updated_at.sql

ALTER TABLE notification_deliveries
    DROP COLUMN IF EXISTS updated_at;
