-- =====================================================
-- Add Drafts to Soft Delete System
-- Updates deleted_items_view and cleanup function to include drafts
-- Created: January 15, 2025
-- =====================================================

-- Add index for soft delete queries on draft_documents
CREATE INDEX IF NOT EXISTS idx_draft_documents_deleted_at ON draft_documents(deleted_at) WHERE deleted_at IS NOT NULL;

-- Recreate the deleted_items_view to include drafts
CREATE OR REPLACE VIEW deleted_items_view AS
SELECT
    'conversation' AS item_type,
    c.id,
    c.session_id AS identifier,
    NULL AS content,
    c.deleted_at,
    c.deleted_by,
    c.created_at,
    u.email AS deleted_by_email,
    (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) AS related_count
FROM conversations c
LEFT JOIN users u ON c.deleted_by = u.id
WHERE c.deleted_at IS NOT NULL

UNION ALL

SELECT
    'message' AS item_type,
    m.id,
    m.conversation_id::TEXT AS identifier,
    m.content,
    m.deleted_at,
    m.deleted_by,
    m.created_at,
    u.email AS deleted_by_email,
    0 AS related_count
FROM messages m
LEFT JOIN users u ON m.deleted_by = u.id
WHERE m.deleted_at IS NOT NULL

UNION ALL

SELECT
    'feedback' AS item_type,
    f.id,
    f.message_id::TEXT AS identifier,
    f.comment AS content,
    f.deleted_at,
    f.deleted_by,
    f.created_at,
    u.email AS deleted_by_email,
    0 AS related_count
FROM feedback f
LEFT JOIN users u ON f.deleted_by = u.id
WHERE f.deleted_at IS NOT NULL

UNION ALL

SELECT
    'draft' AS item_type,
    d.id,
    d.title AS identifier,
    SUBSTRING(d.content, 1, 200) AS content,
    d.deleted_at,
    d.deleted_by,
    d.created_at,
    u.email AS deleted_by_email,
    0 AS related_count
FROM draft_documents d
LEFT JOIN users u ON d.deleted_by = u.id
WHERE d.deleted_at IS NOT NULL

ORDER BY deleted_at DESC;

-- Update cleanup function to include drafts
CREATE OR REPLACE FUNCTION cleanup_old_deleted_items() RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
    conversation_count INTEGER;
    message_count INTEGER;
    feedback_count INTEGER;
    draft_count INTEGER;
BEGIN
    -- Delete old conversations and count them
    DELETE FROM conversations
    WHERE deleted_at IS NOT NULL
    AND deleted_at < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS conversation_count = ROW_COUNT;

    -- Delete old messages
    DELETE FROM messages
    WHERE deleted_at IS NOT NULL
    AND deleted_at < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS message_count = ROW_COUNT;

    -- Delete old feedback
    DELETE FROM feedback
    WHERE deleted_at IS NOT NULL
    AND deleted_at < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS feedback_count = ROW_COUNT;

    -- Delete old drafts
    DELETE FROM draft_documents
    WHERE deleted_at IS NOT NULL
    AND deleted_at < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS draft_count = ROW_COUNT;

    deleted_count := conversation_count + message_count + feedback_count + draft_count;

    RAISE NOTICE 'Cleaned up % conversations, % messages, % feedback items, % drafts',
        conversation_count, message_count, feedback_count, draft_count;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Update comments
COMMENT ON VIEW deleted_items_view IS 'Unified view of all soft-deleted items across conversations, messages, feedback, and drafts tables';
COMMENT ON FUNCTION cleanup_old_deleted_items IS 'Permanently deletes items (including drafts) that have been soft-deleted for more than 30 days';
