-- Revision: 20260308_000016
-- Add content_type to videos for article vs video pipeline routing

ALTER TABLE videos
    ADD COLUMN IF NOT EXISTS content_type TEXT NOT NULL DEFAULT 'video';

ALTER TABLE videos
    DROP CONSTRAINT IF EXISTS videos_content_type_check;

ALTER TABLE videos
    ADD CONSTRAINT videos_content_type_check CHECK (content_type IN ('video', 'article'));
