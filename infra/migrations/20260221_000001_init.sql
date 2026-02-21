-- Revision: 20260221_000001
-- Phase 1-2 bootstrap schema

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(32) NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    source_value VARCHAR(1024) NOT NULL,
    rsshub_route VARCHAR(1024) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT subscriptions_platform_check CHECK (platform IN ('bilibili', 'youtube')),
    CONSTRAINT subscriptions_source_type_check CHECK (
        source_type IN ('bilibili_uid', 'youtube_channel_id', 'url')
    ),
    CONSTRAINT uq_subscriptions_platform_source UNIQUE (platform, source_type, source_value)
);

CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(32) NOT NULL,
    video_uid VARCHAR(512) NOT NULL,
    source_url VARCHAR(2048) NOT NULL,
    title VARCHAR(500),
    published_at TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_videos_platform_video_uid UNIQUE (platform, video_uid),
    CONSTRAINT videos_platform_check CHECK (platform IN ('bilibili', 'youtube'))
);

CREATE TABLE IF NOT EXISTS ingest_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL,
    feed_guid VARCHAR(1024),
    feed_link VARCHAR(2048),
    entry_hash VARCHAR(128) NOT NULL,
    video_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ingest_events_subscription_entry_hash UNIQUE (subscription_id, entry_hash),
    CONSTRAINT fk_ingest_events_subscription
        FOREIGN KEY (subscription_id)
        REFERENCES subscriptions(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_ingest_events_video
        FOREIGN KEY (video_id)
        REFERENCES videos(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL,
    kind VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    error_message TEXT,
    artifact_digest_md TEXT,
    artifact_root TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT jobs_kind_check CHECK (kind IN ('phase2_ingest_stub')),
    CONSTRAINT jobs_status_check CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'partial')),
    CONSTRAINT fk_jobs_video
        FOREIGN KEY (video_id)
        REFERENCES videos(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_platform ON subscriptions(platform);
CREATE INDEX IF NOT EXISTS idx_subscriptions_enabled ON subscriptions(enabled);
CREATE INDEX IF NOT EXISTS idx_videos_platform_last_seen ON videos(platform, last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_ingest_events_video_id ON ingest_events(video_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
