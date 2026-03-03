-- Down migration for 20260222_000011_embedding_pgvector.sql

DROP TABLE IF EXISTS video_embeddings;
DROP EXTENSION IF EXISTS vector;
