-- ============================================================
-- Fix Embeddings Table Schema - Change from TEXT to VECTOR
-- ============================================================
--
-- PROBLEM: Embeddings are stored as TEXT strings instead of
-- proper pgvector VECTOR type, preventing similarity search
--
-- SOLUTION: Convert embedding column to vector(384) type
-- ============================================================

-- Step 1: Drop the existing embedding column
ALTER TABLE embeddings DROP COLUMN IF EXISTS embedding;

-- Step 2: Add embedding column with correct vector type
ALTER TABLE embeddings ADD COLUMN embedding vector(384);

-- Step 3: Create index for faster vector similarity search
-- Note: HNSW index is more efficient than IVFFlat for most use cases
CREATE INDEX IF NOT EXISTS embeddings_embedding_idx
ON embeddings
USING hnsw (embedding vector_cosine_ops);

-- Step 4: Update match_documents function to return chunk_text instead of content
DROP FUNCTION IF EXISTS match_documents(vector(384), float, int);

CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(384),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  document_id uuid,
  content text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    e.id,
    e.document_id,
    e.chunk_text AS content,  -- Map chunk_text to content for API compatibility
    1 - (e.embedding <=> query_embedding) AS similarity
  FROM embeddings e
  WHERE 1 - (e.embedding <=> query_embedding) > match_threshold
  ORDER BY e.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION match_documents(vector(384), float, int) TO authenticated;
GRANT EXECUTE ON FUNCTION match_documents(vector(384), float, int) TO anon;

-- Step 5: Verify the schema
-- Run this to check: SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'embeddings';
