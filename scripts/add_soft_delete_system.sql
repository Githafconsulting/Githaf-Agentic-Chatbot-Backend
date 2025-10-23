-- =====================================================
-- Soft Delete System Migration
-- Adds soft delete and update tracking to core tables
-- Created: January 10, 2025
-- =====================================================

-- Add soft delete columns to conversations table
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS deleted_by UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES users(id);

-- Add soft delete columns to messages table
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS deleted_by UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES users(id);

-- Add soft delete columns to feedback table
ALTER TABLE feedback
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS deleted_by UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES users(id);

-- Add indexes for soft delete queries
CREATE INDEX IF NOT EXISTS idx_conversations_deleted_at ON conversations(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_deleted_at ON messages(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_feedback_deleted_at ON feedback(deleted_at) WHERE deleted_at IS NOT NULL;

-- Create a view for all deleted items (for admin dashboard)
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

ORDER BY deleted_at DESC;

-- Function to soft delete a conversation and its related messages
CREATE OR REPLACE FUNCTION soft_delete_conversation(
    p_conversation_id UUID,
    p_user_id UUID
) RETURNS VOID AS $$
BEGIN
    -- Soft delete the conversation
    UPDATE conversations
    SET deleted_at = NOW(), deleted_by = p_user_id
    WHERE id = p_conversation_id AND deleted_at IS NULL;

    -- Soft delete all messages in the conversation
    UPDATE messages
    SET deleted_at = NOW(), deleted_by = p_user_id
    WHERE conversation_id = p_conversation_id AND deleted_at IS NULL;

    -- Soft delete all feedback on messages in the conversation
    UPDATE feedback
    SET deleted_at = NOW(), deleted_by = p_user_id
    WHERE message_id IN (
        SELECT id FROM messages WHERE conversation_id = p_conversation_id
    ) AND deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;

-- Function to recover a conversation and its related messages
CREATE OR REPLACE FUNCTION recover_conversation(
    p_conversation_id UUID
) RETURNS VOID AS $$
BEGIN
    -- Recover the conversation
    UPDATE conversations
    SET deleted_at = NULL, deleted_by = NULL
    WHERE id = p_conversation_id AND deleted_at IS NOT NULL;

    -- Recover all messages in the conversation
    UPDATE messages
    SET deleted_at = NULL, deleted_by = NULL
    WHERE conversation_id = p_conversation_id AND deleted_at IS NOT NULL;

    -- Recover all feedback on messages in the conversation
    UPDATE feedback
    SET deleted_at = NULL, deleted_by = NULL
    WHERE message_id IN (
        SELECT id FROM messages WHERE conversation_id = p_conversation_id
    ) AND deleted_at IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- Function to permanently delete old soft-deleted items (30+ days)
CREATE OR REPLACE FUNCTION cleanup_old_deleted_items() RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
    conversation_count INTEGER;
    message_count INTEGER;
    feedback_count INTEGER;
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

    deleted_count := conversation_count + message_count + feedback_count;

    RAISE NOTICE 'Cleaned up % conversations, % messages, % feedback items',
        conversation_count, message_count, feedback_count;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to permanently delete a specific item immediately
CREATE OR REPLACE FUNCTION permanent_delete_conversation(
    p_conversation_id UUID
) RETURNS VOID AS $$
BEGIN
    -- Check if conversation is soft-deleted
    IF NOT EXISTS (
        SELECT 1 FROM conversations
        WHERE id = p_conversation_id AND deleted_at IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'Conversation must be soft-deleted before permanent deletion';
    END IF;

    -- Permanently delete feedback on messages
    DELETE FROM feedback
    WHERE message_id IN (
        SELECT id FROM messages WHERE conversation_id = p_conversation_id
    );

    -- Permanently delete messages
    DELETE FROM messages
    WHERE conversation_id = p_conversation_id;

    -- Permanently delete conversation
    DELETE FROM conversations
    WHERE id = p_conversation_id;
END;
$$ LANGUAGE plpgsql;

-- Create update tracking trigger function
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers for update tracking
DROP TRIGGER IF EXISTS conversations_update_timestamp ON conversations;
CREATE TRIGGER conversations_update_timestamp
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS messages_update_timestamp ON messages;
CREATE TRIGGER messages_update_timestamp
    BEFORE UPDATE ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS feedback_update_timestamp ON feedback;
CREATE TRIGGER feedback_update_timestamp
    BEFORE UPDATE ON feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Grant permissions (adjust as needed)
GRANT SELECT ON deleted_items_view TO authenticated;

COMMENT ON VIEW deleted_items_view IS 'Unified view of all soft-deleted items across conversations, messages, and feedback tables';
COMMENT ON FUNCTION soft_delete_conversation IS 'Soft deletes a conversation and all its related messages and feedback';
COMMENT ON FUNCTION recover_conversation IS 'Recovers a soft-deleted conversation and all its related messages and feedback';
COMMENT ON FUNCTION cleanup_old_deleted_items IS 'Permanently deletes items that have been soft-deleted for more than 30 days';
COMMENT ON FUNCTION permanent_delete_conversation IS 'Permanently deletes a soft-deleted conversation immediately (cannot be recovered)';
