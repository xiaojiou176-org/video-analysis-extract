-- Revision: 20260223_000014
-- Blueprint hardening: subscriptions.priority + notification delivery dispatch_key

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS priority SMALLINT NOT NULL DEFAULT 50;

ALTER TABLE subscriptions
    DROP CONSTRAINT IF EXISTS subscriptions_priority_check;

ALTER TABLE subscriptions
    ADD CONSTRAINT subscriptions_priority_check
    CHECK (priority >= 0 AND priority <= 100);

CREATE INDEX IF NOT EXISTS idx_subscriptions_category_priority
    ON subscriptions(category, priority DESC);

ALTER TABLE notification_deliveries
    ADD COLUMN IF NOT EXISTS dispatch_key VARCHAR(255);

CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_deliveries_kind_dispatch_key
    ON notification_deliveries(kind, dispatch_key)
    WHERE dispatch_key IS NOT NULL;
