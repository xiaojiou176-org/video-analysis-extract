-- Down migration for 20260221_000001_init.sql
-- Reverts bootstrap schema objects introduced by this migration.

DROP TABLE IF EXISTS ingest_events;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS videos;
DROP TABLE IF EXISTS subscriptions;
