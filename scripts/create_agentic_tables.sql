-- =============================================================================
-- AGENTIC CHATBOT v2.0 - DATABASE MIGRATION SCRIPT
-- =============================================================================
-- Description: Creates all missing tables and RPC functions for full agentic functionality
-- Date: January 15, 2025
-- Version: 2.0.0
--
-- Tables Created:
--   1. semantic_memory (Phase 4: Advanced Memory)
--   2. user_preferences (Phase 4: Advanced Memory)
--   3. response_evaluations (Phase 1: Observation Layer)
--   4. agent_metrics (Phase 6: Metrics & Observability)
--   5. tool_executions (Phase 5: Tool Ecosystem)
--   6. learning_history (Phase 3: Self-Improvement)
--   7. conversation_summaries (Conversation Summary Service)
--   8. appointments (Phase 5: Calendar Tool)
--   9. crm_contacts (Phase 5: CRM Tool)
--  10. crm_interactions (Phase 5: CRM Tool)
--
-- RPC Functions Created:
--   1. match_semantic_memory (vector search for semantic memory)
-- =============================================================================

-- Ensure pgvector extension is enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- TABLE 1: semantic_memory (Phase 4: Advanced Memory)
-- =============================================================================
-- Purpose: Store extracted semantic facts from conversations
-- Used by: memory_service.py
-- =============================================================================

CREATE TABLE IF NOT EXISTS semantic_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('preference', 'request', 'context', 'followup', 'problem', 'other')),
    confidence FLOAT NOT NULL DEFAULT 0.7,
    embedding vector(384) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for semantic_memory
CREATE INDEX IF NOT EXISTS idx_semantic_memory_session
    ON semantic_memory(session_id);

CREATE INDEX IF NOT EXISTS idx_semantic_memory_conversation
    ON semantic_memory(conversation_id);

CREATE INDEX IF NOT EXISTS idx_semantic_memory_category
    ON semantic_memory(category);

CREATE INDEX IF NOT EXISTS idx_semantic_memory_confidence
    ON semantic_memory(confidence);

-- Vector index for semantic search
CREATE INDEX IF NOT EXISTS idx_semantic_memory_embedding
    ON semantic_memory
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

COMMENT ON TABLE semantic_memory IS 'Stores extracted semantic facts from conversations for long-term memory';
COMMENT ON COLUMN semantic_memory.category IS 'Type of fact: preference, request, context, followup, problem, other';
COMMENT ON COLUMN semantic_memory.confidence IS 'Confidence score from LLM extraction (0.0-1.0)';

-- =============================================================================
-- TABLE 2: user_preferences (Phase 4: Advanced Memory)
-- =============================================================================
-- Purpose: Store user preferences across sessions
-- Used by: memory_service.py
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT UNIQUE NOT NULL,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for user_preferences
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_preferences_session
    ON user_preferences(session_id);

CREATE INDEX IF NOT EXISTS idx_user_preferences_updated
    ON user_preferences(updated_at);

COMMENT ON TABLE user_preferences IS 'Stores user preferences and settings across sessions';
COMMENT ON COLUMN user_preferences.preferences IS 'JSONB object containing user-specific preferences';

-- =============================================================================
-- TABLE 3: response_evaluations (Phase 1: Observation Layer)
-- =============================================================================
-- Purpose: Log validation results for response quality tracking
-- Used by: validation_service.py
-- =============================================================================

CREATE TABLE IF NOT EXISTS response_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    is_valid BOOLEAN NOT NULL,
    confidence FLOAT NOT NULL,
    issues TEXT[] DEFAULT ARRAY[]::TEXT[],
    retry_recommended BOOLEAN DEFAULT FALSE,
    suggested_adjustment TEXT,
    validation_latency_ms INTEGER,
    error_type TEXT, -- 'rate_limit', 'validation_failure', NULL (success)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for response_evaluations
CREATE INDEX IF NOT EXISTS idx_response_evaluations_message
    ON response_evaluations(message_id);

CREATE INDEX IF NOT EXISTS idx_response_evaluations_valid
    ON response_evaluations(is_valid);

CREATE INDEX IF NOT EXISTS idx_response_evaluations_confidence
    ON response_evaluations(confidence);

CREATE INDEX IF NOT EXISTS idx_response_evaluations_retry
    ON response_evaluations(retry_recommended);

CREATE INDEX IF NOT EXISTS idx_response_evaluations_created
    ON response_evaluations(created_at);

COMMENT ON TABLE response_evaluations IS 'Logs validation results for response quality monitoring';
COMMENT ON COLUMN response_evaluations.issues IS 'Array of detected issues (e.g., hallucination, verbosity)';
COMMENT ON COLUMN response_evaluations.error_type IS 'Type of validation error: rate_limit, validation_failure, or NULL';

-- =============================================================================
-- TABLE 4: agent_metrics (Phase 6: Metrics & Observability)
-- =============================================================================
-- Purpose: Store performance metrics for agent monitoring
-- Used by: metrics_service.py
-- =============================================================================

CREATE TABLE IF NOT EXISTS agent_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_type TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_unit TEXT DEFAULT 'count', -- 'ms', 'tokens', 'percent', 'count', 'bytes'
    context JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for agent_metrics
CREATE INDEX IF NOT EXISTS idx_agent_metrics_type_timestamp
    ON agent_metrics(metric_type, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_agent_metrics_timestamp
    ON agent_metrics(timestamp DESC);

COMMENT ON TABLE agent_metrics IS 'Stores performance metrics for agent observability and monitoring';
COMMENT ON COLUMN agent_metrics.metric_type IS 'Type: latency, accuracy, retry_rate, token_usage, confidence, etc.';
COMMENT ON COLUMN agent_metrics.context IS 'Additional context (session_id, intent, query_type, etc.)';

-- =============================================================================
-- TABLE 5: tool_executions (Phase 5: Tool Ecosystem)
-- =============================================================================
-- Purpose: Log tool execution results for debugging and monitoring
-- Used by: tool_registry.py
-- =============================================================================

CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_params JSONB NOT NULL,
    success BOOLEAN NOT NULL,
    result JSONB,
    error TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for tool_executions
CREATE INDEX IF NOT EXISTS idx_tool_executions_conversation
    ON tool_executions(conversation_id);

CREATE INDEX IF NOT EXISTS idx_tool_executions_session
    ON tool_executions(session_id);

CREATE INDEX IF NOT EXISTS idx_tool_executions_tool_name
    ON tool_executions(tool_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tool_executions_success
    ON tool_executions(success);

CREATE INDEX IF NOT EXISTS idx_tool_executions_created
    ON tool_executions(created_at DESC);

COMMENT ON TABLE tool_executions IS 'Logs tool execution results for monitoring and debugging';
COMMENT ON COLUMN tool_executions.tool_name IS 'Name of the tool executed (e.g., send_email, calendar, web_search)';

-- =============================================================================
-- TABLE 6: learning_history (Phase 3: Self-Improvement)
-- =============================================================================
-- Purpose: Track learning job executions and threshold adjustments
-- Used by: learning_service.py, scheduler.py
-- =============================================================================

CREATE TABLE IF NOT EXISTS learning_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL DEFAULT 'weekly_learning',
    total_analyzed INTEGER DEFAULT 0,
    issues_found TEXT[] DEFAULT ARRAY[]::TEXT[],
    root_causes TEXT[] DEFAULT ARRAY[]::TEXT[],
    knowledge_gaps TEXT[] DEFAULT ARRAY[]::TEXT[],
    adjustments_applied JSONB DEFAULT '{}'::jsonb,
    recommendations TEXT[] DEFAULT ARRAY[]::TEXT[],
    confidence FLOAT,
    success BOOLEAN NOT NULL,
    error TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for learning_history
CREATE INDEX IF NOT EXISTS idx_learning_history_job_type
    ON learning_history(job_type, executed_at DESC);

CREATE INDEX IF NOT EXISTS idx_learning_history_success
    ON learning_history(success);

CREATE INDEX IF NOT EXISTS idx_learning_history_executed
    ON learning_history(executed_at DESC);

COMMENT ON TABLE learning_history IS 'Tracks learning job executions and threshold adjustments over time';
COMMENT ON COLUMN learning_history.adjustments_applied IS 'JSONB object with old_value -> new_value for each adjusted parameter';
COMMENT ON COLUMN learning_history.confidence IS 'Confidence score from LLM analysis (0.0-1.0)';

-- =============================================================================
-- TABLE 7: conversation_summaries (Used by conversation_summary_service.py)
-- =============================================================================
-- Purpose: Store AI-generated summaries of conversations
-- Used by: conversation_summary_service.py
-- =============================================================================

CREATE TABLE IF NOT EXISTS conversation_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID UNIQUE NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    main_topic TEXT,
    user_intent TEXT,
    key_points TEXT[] DEFAULT ARRAY[]::TEXT[],
    entities_mentioned JSONB DEFAULT '{}'::jsonb,
    sentiment TEXT, -- 'positive', 'neutral', 'negative'
    resolution_status TEXT, -- 'resolved', 'unresolved', 'escalated'
    followup_needed BOOLEAN DEFAULT FALSE,
    summary_text TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for conversation_summaries
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_conversation
    ON conversation_summaries(conversation_id);

CREATE INDEX IF NOT EXISTS idx_conversation_summaries_session
    ON conversation_summaries(session_id);

CREATE INDEX IF NOT EXISTS idx_conversation_summaries_resolution
    ON conversation_summaries(resolution_status);

CREATE INDEX IF NOT EXISTS idx_conversation_summaries_followup
    ON conversation_summaries(followup_needed);

CREATE INDEX IF NOT EXISTS idx_conversation_summaries_sentiment
    ON conversation_summaries(sentiment);

COMMENT ON TABLE conversation_summaries IS 'Stores AI-generated summaries of conversations for quick review';
COMMENT ON COLUMN conversation_summaries.key_points IS 'Array of main points discussed in the conversation';
COMMENT ON COLUMN conversation_summaries.entities_mentioned IS 'JSONB object of entities (people, places, products) mentioned';

-- =============================================================================
-- TABLE 8: appointments (Phase 5: Calendar Tool)
-- =============================================================================
-- Purpose: Store appointments for calendar management
-- Used by: tools/calendar_tool.py
-- =============================================================================

CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    attendees TEXT[] DEFAULT ARRAY[]::TEXT[],
    location TEXT,
    status TEXT DEFAULT 'scheduled', -- 'scheduled', 'confirmed', 'cancelled', 'completed'
    reminder_sent BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for appointments
CREATE INDEX IF NOT EXISTS idx_appointments_session
    ON appointments(session_id);

CREATE INDEX IF NOT EXISTS idx_appointments_conversation
    ON appointments(conversation_id);

CREATE INDEX IF NOT EXISTS idx_appointments_start_time
    ON appointments(start_time);

CREATE INDEX IF NOT EXISTS idx_appointments_status
    ON appointments(status);

COMMENT ON TABLE appointments IS 'Stores appointments created through calendar tool';
COMMENT ON COLUMN appointments.status IS 'Status: scheduled, confirmed, cancelled, completed';

-- =============================================================================
-- TABLE 9: crm_contacts (Phase 5: CRM Tool)
-- =============================================================================
-- Purpose: Store CRM contact information
-- Used by: tools/crm_tool.py
-- =============================================================================

CREATE TABLE IF NOT EXISTS crm_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    company TEXT,
    position TEXT,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    status TEXT DEFAULT 'active', -- 'active', 'inactive', 'lead', 'customer'
    notes TEXT,
    last_contact_date TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for crm_contacts
CREATE UNIQUE INDEX IF NOT EXISTS idx_crm_contacts_email
    ON crm_contacts(email);

CREATE INDEX IF NOT EXISTS idx_crm_contacts_status
    ON crm_contacts(status);

CREATE INDEX IF NOT EXISTS idx_crm_contacts_company
    ON crm_contacts(company);

CREATE INDEX IF NOT EXISTS idx_crm_contacts_updated
    ON crm_contacts(updated_at DESC);

COMMENT ON TABLE crm_contacts IS 'Stores CRM contact information for customer relationship management';
COMMENT ON COLUMN crm_contacts.status IS 'Status: active, inactive, lead, customer';

-- =============================================================================
-- TABLE 10: crm_interactions (Phase 5: CRM Tool)
-- =============================================================================
-- Purpose: Log all interactions with CRM contacts
-- Used by: tools/crm_tool.py
-- =============================================================================

CREATE TABLE IF NOT EXISTS crm_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID NOT NULL REFERENCES crm_contacts(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    interaction_type TEXT NOT NULL, -- 'email', 'chat', 'phone', 'meeting', 'note'
    subject TEXT,
    notes TEXT NOT NULL,
    outcome TEXT, -- 'positive', 'neutral', 'negative', 'pending'
    followup_required BOOLEAN DEFAULT FALSE,
    followup_date TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for crm_interactions
CREATE INDEX IF NOT EXISTS idx_crm_interactions_contact
    ON crm_interactions(contact_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_crm_interactions_conversation
    ON crm_interactions(conversation_id);

CREATE INDEX IF NOT EXISTS idx_crm_interactions_type
    ON crm_interactions(interaction_type);

CREATE INDEX IF NOT EXISTS idx_crm_interactions_followup
    ON crm_interactions(followup_required, followup_date);

COMMENT ON TABLE crm_interactions IS 'Logs all interactions with CRM contacts for relationship tracking';
COMMENT ON COLUMN crm_interactions.interaction_type IS 'Type: email, chat, phone, meeting, note';

-- =============================================================================
-- RPC FUNCTION 1: match_semantic_memory
-- =============================================================================
-- Purpose: Vector similarity search for semantic memory retrieval
-- Used by: memory_service.py -> retrieve_semantic_memory()
-- =============================================================================

CREATE OR REPLACE FUNCTION match_semantic_memory(
    query_embedding vector(384),
    session_filter text,
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id uuid,
    session_id text,
    conversation_id uuid,
    content text,
    category text,
    confidence float,
    similarity float,
    created_at timestamp with time zone
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        semantic_memory.id,
        semantic_memory.session_id,
        semantic_memory.conversation_id,
        semantic_memory.content,
        semantic_memory.category,
        semantic_memory.confidence,
        1 - (semantic_memory.embedding <=> query_embedding) AS similarity,
        semantic_memory.created_at
    FROM semantic_memory
    WHERE semantic_memory.session_id = session_filter
      AND 1 - (semantic_memory.embedding <=> query_embedding) > match_threshold
    ORDER BY semantic_memory.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_semantic_memory IS 'Vector similarity search for semantic memory retrieval by session';

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================
-- Run these after migration to verify success:
--
-- SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE '%semantic%' OR tablename LIKE '%agent%' OR tablename LIKE '%learning%';
-- SELECT proname FROM pg_proc WHERE proname = 'match_semantic_memory';
-- SELECT COUNT(*) FROM semantic_memory;
-- SELECT COUNT(*) FROM response_evaluations;
-- SELECT COUNT(*) FROM agent_metrics;
-- =============================================================================

-- Migration complete!
SELECT
    'Migration complete! Created 10 tables and 1 RPC function for Agentic Chatbot v2.0' AS status,
    NOW() AS timestamp;
