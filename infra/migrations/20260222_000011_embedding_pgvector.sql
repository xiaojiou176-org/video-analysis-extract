-- Revision: 20260222_000011
-- Embedding storage for transcript/outline chunks via pgvector

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS video_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL,
    job_id UUID NOT NULL,
    content_type VARCHAR(32) NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding_model VARCHAR(128) NOT NULL,
    embedding vector(768) NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_video_embeddings_video
        FOREIGN KEY (video_id)
        REFERENCES videos(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_video_embeddings_job
        FOREIGN KEY (job_id)
        REFERENCES jobs(id)
        ON DELETE CASCADE,
    CONSTRAINT video_embeddings_content_type_check
        CHECK (content_type IN ('transcript', 'outline')),
    CONSTRAINT uq_video_embeddings_job_content_chunk
        UNIQUE (job_id, content_type, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_video_embeddings_video_id
    ON video_embeddings(video_id);

CREATE INDEX IF NOT EXISTS idx_video_embeddings_job_id
    ON video_embeddings(job_id);

CREATE INDEX IF NOT EXISTS idx_video_embeddings_content_type
    ON video_embeddings(content_type);

CREATE INDEX IF NOT EXISTS idx_video_embeddings_embedding_hnsw
    ON video_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
