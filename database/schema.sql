-- Bật extension pgvector cho vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Bảng chính lưu trữ documents đã được chunk và embed
CREATE TABLE IF NOT EXISTS financial_documents (
    id          BIGSERIAL PRIMARY KEY,
    content     TEXT NOT NULL,                          -- Nội dung text gốc của chunk
    embedding   VECTOR(768),                            -- Vector embedding 768 chiều (Gemini)
    metadata    JSONB DEFAULT '{}'::JSONB,              -- Metadata linh hoạt (ticker, source, date,...)
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Index HNSW cho tìm kiếm vector nhanh (cosine similarity)
-- HNSW cho hiệu năng tốt hơn IVFFlat khi dataset < 1M records
CREATE INDEX IF NOT EXISTS idx_financial_docs_embedding
    ON financial_documents
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Index cho truy vấn metadata (lọc theo ticker, source, etc.)
CREATE INDEX IF NOT EXISTS idx_financial_docs_metadata
    ON financial_documents
    USING gin (metadata);

-- RPC Function: Tìm kiếm documents tương tự nhất
-- Gọi từ Supabase client: supabase.rpc('match_documents', {...})
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        fd.id,
        fd.content,
        fd.metadata,
        1 - (fd.embedding <=> query_embedding) AS similarity
    FROM financial_documents fd
    WHERE 1 - (fd.embedding <=> query_embedding) > match_threshold
    ORDER BY fd.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;