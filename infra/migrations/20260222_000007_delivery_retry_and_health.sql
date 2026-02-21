-- Revision: 20260222_000007
-- Notification retry metadata + provider health canary table

ALTER TABLE notification_deliveries
    ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE notification_deliveries
    ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMPTZ;

ALTER TABLE notification_deliveries
    ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMPTZ;

ALTER TABLE notification_deliveries
    ADD COLUMN IF NOT EXISTS last_error_kind VARCHAR(32);

ALTER TABLE notification_deliveries
    DROP CONSTRAINT IF EXISTS notification_deliveries_attempt_count_check;

ALTER TABLE notification_deliveries
    ADD CONSTRAINT notification_deliveries_attempt_count_check
    CHECK (attempt_count >= 0);

CREATE INDEX IF NOT EXISTS idx_notification_deliveries_retry
    ON notification_deliveries(status, next_retry_at, kind);

CREATE TABLE IF NOT EXISTS provider_health_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    check_kind VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL,
    error_kind VARCHAR(32),
    message TEXT,
    payload_json JSONB,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT provider_health_checks_status_check CHECK (
        status IN ('ok', 'warn', 'fail')
    ),
    CONSTRAINT provider_health_checks_kind_check CHECK (
        check_kind IN ('rsshub', 'youtube_data_api', 'gemini', 'resend')
    )
);

CREATE INDEX IF NOT EXISTS idx_provider_health_checks_checked_at
    ON provider_health_checks(checked_at DESC);

CREATE INDEX IF NOT EXISTS idx_provider_health_checks_kind_status
    ON provider_health_checks(check_kind, status, checked_at DESC);
