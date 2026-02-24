-- Revision: 20260223_000012
-- Subscriptions category/tags + notification category rules

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS category VARCHAR(32) NOT NULL DEFAULT 'misc';

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS adapter_type VARCHAR(32) NOT NULL DEFAULT 'rsshub_route';

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS source_url VARCHAR(2048);

UPDATE subscriptions
SET source_url = source_value
WHERE source_url IS NULL;

ALTER TABLE subscriptions
    DROP CONSTRAINT IF EXISTS subscriptions_category_check;

ALTER TABLE subscriptions
    ADD CONSTRAINT subscriptions_category_check
    CHECK (category IN ('tech', 'creator', 'macro', 'ops', 'misc'));

ALTER TABLE subscriptions
    DROP CONSTRAINT IF EXISTS subscriptions_adapter_type_check;

ALTER TABLE subscriptions
    ADD CONSTRAINT subscriptions_adapter_type_check
    CHECK (adapter_type IN ('rsshub_route', 'rss_generic'));

CREATE INDEX IF NOT EXISTS idx_subscriptions_category
    ON subscriptions(category);

CREATE INDEX IF NOT EXISTS idx_subscriptions_adapter_type
    ON subscriptions(adapter_type);

ALTER TABLE notification_configs
    ADD COLUMN IF NOT EXISTS category_rules JSONB NOT NULL DEFAULT '{}'::jsonb;
