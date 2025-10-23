-- ============================================================================
-- CLEAN MIGRATION: Fresh Database Setup (Keep Users Only)
-- Description: Delete all data except users, create clean schema
-- Date: 2025-10-08
-- ============================================================================

-- ============================================================================
-- STEP 1: DROP ALL EXISTING TABLES (EXCEPT USERS)
-- ============================================================================

-- Drop tables in correct order (child tables first due to foreign keys)
DROP TABLE IF EXISTS feedback CASCADE;
DROP TABLE IF EXISTS embeddings CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS documents_backup CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;

-- NOTE: We keep the users table intact

-- ============================================================================
-- STEP 2: CREATE FRESH DOCUMENTS TABLE (Metadata-only)
-- ============================================================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    file_type VARCHAR(50) NOT NULL CHECK (file_type IN ('pdf', 'txt', 'docx', 'html', 'webpage')),
    file_size BIGINT,
    storage_path TEXT,  -- Path to file in Supabase Storage
    download_url TEXT,  -- Signed download URL
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('upload', 'url', 'scraped')),
    source_url TEXT,  -- Original URL if from web
    category VARCHAR(100),
    summary TEXT,  -- 200-500 char summary
    chunk_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_documents_source_type ON documents(source_type);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_file_type ON documents(file_type);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STEP 3: CREATE EMBEDDINGS TABLE (with proper vector type)
-- ============================================================================

-- Ensure pgvector extension is enabled
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    embedding vector(384) NOT NULL,  -- 384-dimensional vector
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for vector search
CREATE INDEX idx_embeddings_document_id ON embeddings(document_id);
CREATE INDEX idx_embeddings_embedding ON embeddings USING hnsw (embedding vector_cosine_ops);

-- ============================================================================
-- STEP 4: CREATE CONVERSATIONS TABLE
-- ============================================================================

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL UNIQUE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    message_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_conversations_started_at ON conversations(started_at DESC);

-- ============================================================================
-- STEP 5: CREATE MESSAGES TABLE
-- ============================================================================

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    context_used JSONB,  -- Sources used for response
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);

-- ============================================================================
-- STEP 6: CREATE FEEDBACK TABLE
-- ============================================================================

CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating IN (0, 1)),  -- 0 = negative, 1 = positive
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_feedback_message_id ON feedback(message_id);
CREATE INDEX idx_feedback_rating ON feedback(rating);
CREATE INDEX idx_feedback_created_at ON feedback(created_at DESC);

-- ============================================================================
-- STEP 7: CREATE RPC FUNCTION FOR VECTOR SEARCH
-- ============================================================================

CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 5
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
        e.chunk_text AS content,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM embeddings e
    WHERE 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================================================
-- STEP 8: CREATE SUPABASE STORAGE BUCKET
-- ============================================================================

-- Create documents bucket for file storage
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'documents',
    'documents',
    false,  -- Private bucket
    10485760,  -- 10MB limit
    ARRAY[
        'application/pdf',
        'text/plain',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword'
    ]
)
ON CONFLICT (id) DO UPDATE
SET
    public = false,
    file_size_limit = 10485760,
    allowed_mime_types = ARRAY[
        'application/pdf',
        'text/plain',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword'
    ];

-- ============================================================================
-- STEP 9: STORAGE POLICIES
-- ============================================================================

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Authenticated users can upload documents" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can read documents" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can update documents" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can delete documents" ON storage.objects;

-- Create new policies
CREATE POLICY "Authenticated users can upload documents"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'documents');

CREATE POLICY "Authenticated users can read documents"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'documents');

CREATE POLICY "Authenticated users can update documents"
ON storage.objects FOR UPDATE
TO authenticated
USING (bucket_id = 'documents');

CREATE POLICY "Authenticated users can delete documents"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'documents');

-- ============================================================================
-- STEP 10: TABLE RLS POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

-- Documents policies
CREATE POLICY "Allow public read access to documents" ON documents
    FOR SELECT USING (true);

CREATE POLICY "Allow authenticated users to manage documents" ON documents
    FOR ALL USING (auth.role() = 'authenticated');

-- Embeddings policies
CREATE POLICY "Allow public read access to embeddings" ON embeddings
    FOR SELECT USING (true);

CREATE POLICY "Allow authenticated users to manage embeddings" ON embeddings
    FOR ALL USING (auth.role() = 'authenticated');

-- Conversations policies
CREATE POLICY "Allow public access to conversations" ON conversations
    FOR ALL USING (true);

-- Messages policies
CREATE POLICY "Allow public access to messages" ON messages
    FOR ALL USING (true);

-- Feedback policies
CREATE POLICY "Allow public access to feedback" ON feedback
    FOR ALL USING (true);

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Verify setup
DO $$
DECLARE
    doc_count INTEGER;
    emb_count INTEGER;
    user_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO doc_count FROM documents;
    SELECT COUNT(*) INTO emb_count FROM embeddings;
    SELECT COUNT(*) INTO user_count FROM users;

    RAISE NOTICE '✅ Migration Complete!';
    RAISE NOTICE '   - Documents: %', doc_count;
    RAISE NOTICE '   - Embeddings: %', emb_count;
    RAISE NOTICE '   - Users: % (preserved)', user_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Run: python scripts/scrape_githaf_website.py';
    RAISE NOTICE '2. Test file upload via API';
    RAISE NOTICE '3. Test chatbot with new knowledge base';
END $$;
