-- Down migration for 20260223_000012_subscriptions_category_and_notification_rules.sql

DROP INDEX IF EXISTS idx_subscriptions_adapter_type;
DROP INDEX IF EXISTS idx_subscriptions_category;

ALTER TABLE subscriptions
    DROP CONSTRAINT IF EXISTS subscriptions_adapter_type_check;

ALTER TABLE subscriptions
    DROP CONSTRAINT IF EXISTS subscriptions_category_check;

ALTER TABLE subscriptions
    DROP COLUMN IF EXISTS category;

ALTER TABLE subscriptions
    DROP COLUMN IF EXISTS tags;

ALTER TABLE subscriptions
    DROP COLUMN IF EXISTS adapter_type;

ALTER TABLE subscriptions
    DROP COLUMN IF EXISTS source_url;

ALTER TABLE notification_configs
    DROP COLUMN IF EXISTS category_rules;
