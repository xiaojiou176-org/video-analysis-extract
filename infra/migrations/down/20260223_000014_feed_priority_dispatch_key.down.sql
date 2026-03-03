-- Down migration for 20260223_000014_feed_priority_dispatch_key.sql

DROP INDEX IF EXISTS uq_notification_deliveries_kind_dispatch_key;

ALTER TABLE notification_deliveries
    DROP COLUMN IF EXISTS dispatch_key;

DROP INDEX IF EXISTS idx_subscriptions_category_priority;

ALTER TABLE subscriptions
    DROP CONSTRAINT IF EXISTS subscriptions_priority_check;

ALTER TABLE subscriptions
    DROP COLUMN IF EXISTS priority;
