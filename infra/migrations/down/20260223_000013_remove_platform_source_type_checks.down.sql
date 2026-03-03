-- Down migration for 20260223_000013_remove_platform_source_type_checks.sql

ALTER TABLE subscriptions
    ADD CONSTRAINT subscriptions_platform_check
    CHECK (platform IN ('bilibili', 'youtube'));

ALTER TABLE subscriptions
    ADD CONSTRAINT subscriptions_source_type_check
    CHECK (source_type IN ('bilibili_uid', 'youtube_channel_id', 'url'));

ALTER TABLE videos
    ADD CONSTRAINT videos_platform_check
    CHECK (platform IN ('bilibili', 'youtube'));
