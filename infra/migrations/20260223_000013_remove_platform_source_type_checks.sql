-- Revision: 20260223_000013
-- Remove hard-coded platform/source_type check constraints for extensibility

ALTER TABLE subscriptions
    DROP CONSTRAINT IF EXISTS subscriptions_platform_check;

ALTER TABLE subscriptions
    DROP CONSTRAINT IF EXISTS subscriptions_source_type_check;

ALTER TABLE videos
    DROP CONSTRAINT IF EXISTS videos_platform_check;
