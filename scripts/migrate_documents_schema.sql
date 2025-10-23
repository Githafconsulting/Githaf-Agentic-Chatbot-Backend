-- ============================================================================
-- Migration Script: Documents Table Schema Refactoring
-- Description: Migrate from storing full text to metadata-only architecture
-- Date: 2025-10-08
-- ============================================================================

-- BACKUP NOTICE: Before running this migration, backup your database!
-- This migration will modify the documents table structure.

-- ============================================================================
-- STEP 1: Create new documents table with proper schema
-- ============================================================================

-- Rename old table to backup
ALTER TABLE IF EXISTS documents RENAME TO documents_backup;

-- Create new documents table with metadata-only structure
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    file_type VARCHAR(50) NOT NULL CHECK (file_type IN ('pdf', 'txt', 'docx', 'html', 'webpage')),
    file_size BIGINT,
    storage_path TEXT,  -- URL to file in Supabase Storage
    download_url TEXT,  -- Public download URL
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('upload', 'url', 'scraped')),
    source_url TEXT,  -- Original URL if from web
    category VARCHAR(100),
    summary TEXT,  -- Optional 200-500 char summary
    chunk_count INTEGER DEFAULT 0,
    metadata JSONB,  -- Additional metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_documents_source_type ON documents(source_type);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_file_type ON documents(file_type);

-- Create updated_at trigger
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
-- STEP 2: Enable Row Level Security (RLS)
-- ============================================================================

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Allow public read access (for chatbot)
CREATE POLICY "Allow public read access" ON documents
    FOR SELECT
    USING (true);

-- Allow authenticated insert/update/delete (for admin users)
CREATE POLICY "Allow authenticated users to insert" ON documents
    FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Allow authenticated users to update" ON documents
    FOR UPDATE
    USING (auth.role() = 'authenticated');

CREATE POLICY "Allow authenticated users to delete" ON documents
    FOR DELETE
    USING (auth.role() = 'authenticated');

-- ============================================================================
-- STEP 3: Create Supabase Storage bucket (via SQL - optional)
-- Note: You can also create this via Supabase Dashboard
-- ============================================================================

-- Insert storage bucket configuration
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'documents',
    'documents',
    false,  -- Private bucket, requires authentication
    10485760,  -- 10MB limit (10 * 1024 * 1024 bytes)
    ARRAY[
        'application/pdf',
        'text/plain',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword'
    ]
)
ON CONFLICT (id) DO NOTHING;

-- Storage policies for documents bucket
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
-- STEP 4: Verify embeddings table is intact
-- ============================================================================

-- The embeddings table should already exist with proper vector type
-- This query just verifies the structure
DO $$
BEGIN
    -- Check if embeddings table exists and has correct schema
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'embeddings'
    ) THEN
        RAISE EXCEPTION 'embeddings table does not exist! Cannot proceed with migration.';
    END IF;

    -- Verify embedding column is vector type
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'embeddings'
        AND column_name = 'embedding'
        AND udt_name = 'vector'
    ) THEN
        RAISE EXCEPTION 'embeddings.embedding column is not vector type! Run fix_embeddings_schema.sql first.';
    END IF;

    RAISE NOTICE 'Embeddings table verified successfully.';
END $$;

-- ============================================================================
-- STEP 5: Create helper function to get document with chunk count
-- ============================================================================

CREATE OR REPLACE FUNCTION get_document_with_stats(doc_id UUID)
RETURNS TABLE (
    id UUID,
    title VARCHAR,
    file_type VARCHAR,
    file_size BIGINT,
    storage_path TEXT,
    download_url TEXT,
    source_type VARCHAR,
    source_url TEXT,
    category VARCHAR,
    summary TEXT,
    chunk_count BIGINT,
    metadata JSONB,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.title,
        d.file_type,
        d.file_size,
        d.storage_path,
        d.download_url,
        d.source_type,
        d.source_url,
        d.category,
        d.summary,
        COUNT(e.id) AS chunk_count,
        d.metadata,
        d.created_at,
        d.updated_at
    FROM documents d
    LEFT JOIN embeddings e ON e.document_id = d.id
    WHERE d.id = doc_id
    GROUP BY d.id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STEP 6: Create function to update chunk count
-- ============================================================================

CREATE OR REPLACE FUNCTION update_document_chunk_count(doc_id UUID)
RETURNS INTEGER AS $$
DECLARE
    chunk_total INTEGER;
BEGIN
    SELECT COUNT(*) INTO chunk_total
    FROM embeddings
    WHERE document_id = doc_id;

    UPDATE documents
    SET chunk_count = chunk_total
    WHERE id = doc_id;

    RETURN chunk_total;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Summary of changes:
-- 1. ✅ Created new documents table with metadata-only schema
-- 2. ✅ Removed 'content' field (full text no longer stored)
-- 3. ✅ Added storage_path, download_url for file references
-- 4. ✅ Added file_type, file_size, summary fields
-- 5. ✅ Created indexes for performance
-- 6. ✅ Enabled RLS with appropriate policies
-- 7. ✅ Created Supabase Storage bucket 'documents'
-- 8. ✅ Created helper functions
-- 9. ✅ Old data preserved in documents_backup table

-- NEXT STEPS:
-- 1. Run data migration script (migrate_to_storage.py) to:
--    - Convert existing documents to PDFs
--    - Upload to Storage
--    - Populate new documents table
-- 2. Verify all data migrated successfully
-- 3. Drop documents_backup table (after verification)

-- To rollback (if needed):
-- DROP TABLE documents;
-- ALTER TABLE documents_backup RENAME TO documents;
