-- Approximate nearest-neighbor index for embedding search (cosine distance).
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON chunks
    USING hnsw (embedding vector_cosine_ops);
