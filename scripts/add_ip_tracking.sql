-- Add IP tracking and country columns to conversations table
-- Run this migration in Supabase SQL Editor

ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS ip_address TEXT,
ADD COLUMN IF NOT EXISTS country_code VARCHAR(2),
ADD COLUMN IF NOT EXISTS country_name TEXT;

-- Create index for country queries
CREATE INDEX IF NOT EXISTS idx_conversations_country_code ON conversations(country_code);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at_country ON conversations(created_at, country_code);

-- Add comment
COMMENT ON COLUMN conversations.ip_address IS 'Client IP address (can be anonymized for GDPR)';
COMMENT ON COLUMN conversations.country_code IS 'ISO 3166-1 alpha-2 country code';
COMMENT ON COLUMN conversations.country_name IS 'Full country name';
