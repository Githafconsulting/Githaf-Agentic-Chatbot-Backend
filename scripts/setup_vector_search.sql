-- Setup vector search function for pgvector
-- This function performs cosine similarity search on embeddings

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS match_documents(vector(384), float, int);

-- Create the match_documents function
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
    e.content,
    1 - (e.embedding <=> query_embedding) AS similarity
  FROM embeddings e
  WHERE 1 - (e.embedding <=> query_embedding) > match_threshold
  ORDER BY e.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION match_documents(vector(384), float, int) TO authenticated;
GRANT EXECUTE ON FUNCTION match_documents(vector(384), float, int) TO anon;
