-- Pgvector similarity search function
-- Run this in your Supabase SQL Editor after creating the schema

CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(384),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  document_id UUID,
  content TEXT,
  similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
  SELECT
    embeddings.id,
    embeddings.document_id,
    embeddings.chunk_text AS content,
    1 - (embeddings.embedding <=> query_embedding) AS similarity
  FROM embeddings
  WHERE 1 - (embeddings.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;

-- Alternative: If you want to join with document metadata
CREATE OR REPLACE FUNCTION match_documents_with_metadata(
  query_embedding VECTOR(384),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  document_id UUID,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
  SELECT
    embeddings.id,
    embeddings.document_id,
    embeddings.chunk_text AS content,
    documents.metadata,
    1 - (embeddings.embedding <=> query_embedding) AS similarity
  FROM embeddings
  JOIN documents ON embeddings.document_id = documents.id
  WHERE 1 - (embeddings.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;

-- Test the function (example)
-- SELECT * FROM match_documents('[0.1, 0.2, ...]'::vector(384), 0.5, 3);
