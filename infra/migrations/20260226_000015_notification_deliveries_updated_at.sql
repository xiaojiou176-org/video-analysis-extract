ALTER TABLE notification_deliveries
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE notification_deliveries
SET updated_at = COALESCE(updated_at, created_at, NOW())
WHERE updated_at IS NULL;
