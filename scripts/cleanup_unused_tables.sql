-- =============================================================================
-- DATABASE CLEANUP SCRIPT - Remove Unused Tables
-- =============================================================================
-- Description: Removes orphaned database tables that are defined but never used
-- Date: January 2025
-- Version: 1.0.0
--
-- Tables to Delete: 1
--   - learning_history (defined in schema but no INSERT statements in codebase)
--
-- Impact: Frees up database storage with zero risk (no code dependencies)
-- =============================================================================

-- Optional: Backup data first (table is likely empty, but safe practice)
-- Uncomment the line below if you want to backup before deletion
-- CREATE TABLE learning_history_backup AS SELECT * FROM learning_history;

-- =============================================================================
-- STEP 1: Verify table exists and check row count
-- =============================================================================
DO $$
DECLARE
    row_count INTEGER;
    table_exists BOOLEAN;
BEGIN
    -- Check if table exists
    SELECT EXISTS (
        SELECT FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename = 'learning_history'
    ) INTO table_exists;

    IF table_exists THEN
        -- Get row count
        SELECT COUNT(*) INTO row_count FROM learning_history;

        RAISE NOTICE '✓ Table learning_history exists with % rows', row_count;

        IF row_count > 0 THEN
            RAISE WARNING '⚠ Table learning_history has % rows. Consider backing up before deletion!', row_count;
        ELSE
            RAISE NOTICE '✓ Table learning_history is empty - safe to delete';
        END IF;
    ELSE
        RAISE NOTICE '✓ Table learning_history does not exist - nothing to delete';
    END IF;
END $$;

-- =============================================================================
-- STEP 2: Delete orphaned table
-- =============================================================================
DROP TABLE IF EXISTS learning_history CASCADE;

-- =============================================================================
-- STEP 3: Verification
-- =============================================================================
DO $$
DECLARE
    table_exists BOOLEAN;
BEGIN
    -- Verify deletion
    SELECT EXISTS (
        SELECT FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename = 'learning_history'
    ) INTO table_exists;

    IF NOT table_exists THEN
        RAISE NOTICE '✓ SUCCESS: learning_history has been deleted';
    ELSE
        RAISE WARNING '✗ FAILED: learning_history still exists';
    END IF;
END $$;

-- Final status message
SELECT
    'Cleanup complete! Removed 1 unused table (learning_history)' AS status,
    NOW() AS timestamp;

-- =============================================================================
-- VERIFICATION QUERY (Run this to confirm)
-- =============================================================================
-- This should return 0 rows if deletion was successful
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('learning_history');

-- =============================================================================
-- ROLLBACK INSTRUCTIONS (If you need to restore)
-- =============================================================================
-- If you created a backup and need to restore:
--
-- CREATE TABLE learning_history (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     job_type TEXT NOT NULL DEFAULT 'weekly_learning',
--     total_analyzed INTEGER DEFAULT 0,
--     issues_found TEXT[] DEFAULT ARRAY[]::TEXT[],
--     root_causes TEXT[] DEFAULT ARRAY[]::TEXT[],
--     knowledge_gaps TEXT[] DEFAULT ARRAY[]::TEXT[],
--     adjustments_applied JSONB DEFAULT '{}'::jsonb,
--     recommendations TEXT[] DEFAULT ARRAY[]::TEXT[],
--     confidence FLOAT,
--     success BOOLEAN NOT NULL,
--     error TEXT,
--     executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
-- );
--
-- INSERT INTO learning_history SELECT * FROM learning_history_backup;
-- =============================================================================
