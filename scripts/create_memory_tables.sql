-- Phase 4: Advanced Memory - Database Schema
-- Tables for semantic memory, conversation summaries, and user preferences

-- ========================================
-- Semantic Memory Table
-- ========================================
CREATE TABLE IF NOT EXISTS semantic_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('preference', 'request', 'context', 'followup', 'problem', 'other')),
    confidence FLOAT NOT NULL DEFAULT 0.7 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    embedding vector(384) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for semantic_memory
CREATE INDEX IF NOT EXISTS idx_semantic_memory_session ON semantic_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_semantic_memory_category ON semantic_memory(category);
CREATE INDEX IF NOT EXISTS idx_semantic_memory_created_at ON semantic_memory(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_memory_confidence ON semantic_memory(confidence);

-- Vector index for semantic search
CREATE INDEX IF NOT EXISTS idx_semantic_memory_embedding ON semantic_memory
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- ========================================
-- Vector Search Function for Semantic Memory
-- ========================================
CREATE OR REPLACE FUNCTION match_semantic_memory(
  query_embedding vector(384),
  session_filter text,
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  content text,
  category text,
  confidence float,
  similarity float,
  created_at timestamp with time zone,
  metadata jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    semantic_memory.id,
    semantic_memory.content,
    semantic_memory.category,
    semantic_memory.confidence,
    1 - (semantic_memory.embedding <=> query_embedding) AS similarity,
    semantic_memory.created_at,
    semantic_memory.metadata
  FROM semantic_memory
  WHERE semantic_memory.session_id = session_filter
    AND 1 - (semantic_memory.embedding <=> query_embedding) > match_threshold
  ORDER BY semantic_memory.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ========================================
-- Conversation Summaries Table
-- ========================================
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE UNIQUE,
    main_topic TEXT NOT NULL,
    user_intent TEXT NOT NULL,
    key_points TEXT[] DEFAULT '{}',
    resolution_status TEXT NOT NULL DEFAULT 'unresolved' CHECK (resolution_status IN ('resolved', 'partially_resolved', 'unresolved')),
    followup_needed BOOLEAN DEFAULT FALSE,
    sentiment TEXT NOT NULL DEFAULT 'neutral' CHECK (sentiment IN ('positive', 'neutral', 'negative')),
    message_count INTEGER DEFAULT 0,
    first_message_at TIMESTAMP WITH TIME ZONE,
    last_message_at TIMESTAMP WITH TIME ZONE,
    summarized_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for conversation_summaries
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_conversation ON conversation_summaries(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_resolution ON conversation_summaries(resolution_status);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_followup ON conversation_summaries(followup_needed);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_sentiment ON conversation_summaries(sentiment);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_summarized_at ON conversation_summaries(summarized_at DESC);

-- Full-text search index on main_topic and user_intent
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_topic_search ON conversation_summaries
  USING gin(to_tsvector('english', main_topic || ' ' || user_intent));

-- ========================================
-- User Preferences Table
-- ========================================
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT UNIQUE NOT NULL,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for user_preferences
CREATE INDEX IF NOT EXISTS idx_user_preferences_session ON user_preferences(session_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_updated_at ON user_preferences(updated_at DESC);

-- GIN index for JSONB preferences (allows efficient querying)
CREATE INDEX IF NOT EXISTS idx_user_preferences_jsonb ON user_preferences USING gin(preferences);

-- ========================================
-- Sample Data (Optional)
-- ========================================

-- No sample data needed for these tables (populated dynamically)

-- ========================================
-- Trigger for updated_at timestamps
-- ========================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for all Phase 4 tables
DROP TRIGGER IF EXISTS update_semantic_memory_updated_at ON semantic_memory;
CREATE TRIGGER update_semantic_memory_updated_at
    BEFORE UPDATE ON semantic_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_conversation_summaries_updated_at ON conversation_summaries;
CREATE TRIGGER update_conversation_summaries_updated_at
    BEFORE UPDATE ON conversation_summaries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_preferences_updated_at ON user_preferences;
CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- Verification Queries
-- ========================================

-- Verify tables created
SELECT table_name
FROM information_schema.tables
WHERE table_name IN ('semantic_memory', 'conversation_summaries', 'user_preferences');

-- Verify indexes created
SELECT indexname
FROM pg_indexes
WHERE tablename IN ('semantic_memory', 'conversation_summaries', 'user_preferences')
ORDER BY tablename, indexname;

-- Verify function created
SELECT routine_name
FROM information_schema.routines
WHERE routine_name = 'match_semantic_memory';
