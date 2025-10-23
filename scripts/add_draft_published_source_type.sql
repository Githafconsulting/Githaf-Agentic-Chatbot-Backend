-- Migration to add 'draft_published' to source_type constraint
-- This allows documents created from approved learning drafts to be stored

-- Drop the old constraint
ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_source_type_check;

-- Add new constraint with 'draft_published' included
ALTER TABLE documents ADD CONSTRAINT documents_source_type_check
  CHECK (source_type IN ('upload', 'url', 'scraped', 'draft_published'));

-- Verify the constraint
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'documents'::regclass
  AND conname = 'documents_source_type_check';
