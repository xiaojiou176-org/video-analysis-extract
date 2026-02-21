-- Revision: 20260221_000004
-- Notification configuration and delivery persistence

CREATE TABLE IF NOT EXISTS notification_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    singleton_key SMALLINT NOT NULL DEFAULT 1,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    to_email VARCHAR(320),
    daily_digest_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    daily_digest_hour_utc SMALLINT,
    failure_alert_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_notification_configs_singleton_key UNIQUE (singleton_key),
    CONSTRAINT notification_configs_singleton_key_check CHECK (singleton_key = 1),
    CONSTRAINT notification_configs_daily_digest_hour_utc_check CHECK (
        daily_digest_hour_utc IS NULL
        OR (daily_digest_hour_utc >= 0 AND daily_digest_hour_utc <= 23)
    )
);

CREATE TABLE IF NOT EXISTS notification_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    recipient_email VARCHAR(320) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    provider VARCHAR(32) NOT NULL DEFAULT 'resend',
    provider_message_id VARCHAR(255),
    error_message TEXT,
    payload_json JSONB,
    job_id UUID,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT notification_deliveries_kind_check CHECK (
        kind IN ('test_email', 'failure_alert', 'daily_digest')
    ),
    CONSTRAINT notification_deliveries_status_check CHECK (
        status IN ('queued', 'sent', 'failed', 'skipped')
    ),
    CONSTRAINT fk_notification_deliveries_job
        FOREIGN KEY (job_id)
        REFERENCES jobs(id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_notification_deliveries_kind_status
    ON notification_deliveries(kind, status);

CREATE INDEX IF NOT EXISTS idx_notification_deliveries_created_at
    ON notification_deliveries(created_at DESC);
