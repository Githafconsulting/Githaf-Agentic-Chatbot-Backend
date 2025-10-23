-- Migration: Add ended_at column to conversations table
-- This tracks when the chatbot window was closed by the user

-- Add ended_at column
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS ended_at TIMESTAMP WITH TIME ZONE;

-- Add index for querying by ended_at
CREATE INDEX IF NOT EXISTS idx_conversations_ended_at ON conversations(ended_at DESC);

-- Add comment
COMMENT ON COLUMN conversations.ended_at IS 'Timestamp when the user closed the chatbot window';
