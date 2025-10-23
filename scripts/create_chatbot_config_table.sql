-- Chatbot Configuration Table
-- Stores configurable settings for chatbot behavior, intents, and RAG pipeline

CREATE TABLE IF NOT EXISTS chatbot_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Intent Configuration
    intent_patterns JSONB DEFAULT '{
        "greeting": ["^hi\\b", "^hello\\b", "^hey\\b", "^good\\s+(morning|afternoon|evening|day)", "^greetings\\b"],
        "farewell": ["^bye\\b", "^goodbye\\b", "^see\\s+you", "^farewell\\b", "^take\\s+care"],
        "gratitude": ["^thank", "^thanks", "^thx\\b", "\\bappreciate", "^grateful"],
        "help": ["^help\\b", "^what\\s+can\\s+you\\s+do", "^how\\s+can\\s+you\\s+help"],
        "chit_chat": ["^how\\s+are\\s+you", "^what''s\\s+your\\s+name", "^are\\s+you\\s+(a\\s+)?bot"]
    }'::jsonb,
    intent_enabled JSONB DEFAULT '{
        "greeting": true,
        "farewell": true,
        "gratitude": true,
        "help": true,
        "chit_chat": true,
        "out_of_scope": true
    }'::jsonb,

    -- Confidence Thresholds
    pattern_confidence_threshold FLOAT DEFAULT 0.7,
    llm_fallback_enabled BOOLEAN DEFAULT true,
    llm_confidence_threshold FLOAT DEFAULT 0.6,

    -- RAG Configuration
    rag_top_k INTEGER DEFAULT 5,
    rag_similarity_threshold FLOAT DEFAULT 0.5,
    chunk_size INTEGER DEFAULT 500,
    chunk_overlap INTEGER DEFAULT 50,

    -- LLM Configuration
    llm_model TEXT DEFAULT 'llama-3.1-8b-instant',
    llm_temperature FLOAT DEFAULT 0.7,
    llm_max_tokens INTEGER DEFAULT 500,

    -- Topic Keywords for Trending Queries
    topic_keywords JSONB DEFAULT '{
        "services": ["service", "services", "offer", "provide", "specialize"],
        "pricing": ["price", "pricing", "cost", "fee", "rate", "payment"],
        "contact": ["contact", "email", "phone", "address", "location"],
        "hours": ["hours", "open", "available", "schedule"],
        "process": ["process", "how do", "work", "steps"],
        "technology": ["technology", "tech", "tools", "framework"],
        "support": ["support", "help", "assist", "problem", "issue"],
        "team": ["team", "employees", "staff", "people"],
        "projects": ["project", "portfolio", "clients", "work"]
    }'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default configuration (only if table is empty)
INSERT INTO chatbot_config (
    intent_patterns,
    intent_enabled,
    pattern_confidence_threshold,
    llm_fallback_enabled,
    llm_confidence_threshold,
    rag_top_k,
    rag_similarity_threshold,
    chunk_size,
    chunk_overlap,
    llm_model,
    llm_temperature,
    llm_max_tokens,
    topic_keywords
)
SELECT
    '{
        "greeting": ["^hi\\b", "^hello\\b", "^hey\\b", "^good\\s+(morning|afternoon|evening|day)", "^greetings\\b", "^howdy\\b", "^what''s\\s+up", "^yo\\b", "^hiya\\b"],
        "farewell": ["^bye\\b", "^goodbye\\b", "^see\\s+you", "^farewell\\b", "^take\\s+care", "^good\\s+night", "^have\\s+a\\s+good"],
        "gratitude": ["^thank", "^thanks", "^thx\\b", "\\bappreciate", "^grateful", "^much\\s+appreciated"],
        "help": ["^help\\b", "^what\\s+can\\s+you\\s+do\\s*\\?*$", "^how\\s+can\\s+you\\s+help", "^can\\s+you\\s+help", "^i\\s+need\\s+help"],
        "chit_chat": ["^how\\s+are\\s+you", "^what''s\\s+your\\s+name", "^are\\s+you\\s+(a\\s+)?bot", "^are\\s+you\\s+real", "^tell\\s+me\\s+(a\\s+)?joke"]
    }'::jsonb,
    '{
        "greeting": true,
        "farewell": true,
        "gratitude": true,
        "help": true,
        "chit_chat": true,
        "out_of_scope": true
    }'::jsonb,
    0.7,
    true,
    0.6,
    5,
    0.5,
    500,
    50,
    'llama-3.1-8b-instant',
    0.7,
    500,
    '{
        "services": ["service", "services", "offer", "provide", "do you do", "specialize", "expertise"],
        "pricing": ["price", "pricing", "cost", "costs", "how much", "expensive", "rate", "rates", "fee", "fees", "payment"],
        "contact": ["contact", "email", "phone", "call", "reach", "address", "location", "office", "where"],
        "hours": ["hours", "open", "available", "availability", "schedule", "when", "time"],
        "process": ["process", "how do", "how does", "work", "steps", "procedure", "workflow"],
        "technology": ["technology", "technologies", "tech", "tools", "framework", "platform", "stack"],
        "support": ["support", "help", "assist", "problem", "issue", "trouble", "fix"],
        "team": ["team", "who", "employees", "staff", "people", "experience", "experts"],
        "projects": ["project", "projects", "portfolio", "work", "clients", "case study", "examples"]
    }'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM chatbot_config);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_chatbot_config_updated_at ON chatbot_config(updated_at);

-- Add comments
COMMENT ON TABLE chatbot_config IS 'Stores configurable settings for chatbot behavior including intents, RAG, and LLM parameters';
COMMENT ON COLUMN chatbot_config.intent_patterns IS 'Regex patterns for each intent type (JSONB)';
COMMENT ON COLUMN chatbot_config.intent_enabled IS 'Enable/disable specific intent types';
COMMENT ON COLUMN chatbot_config.pattern_confidence_threshold IS 'Minimum confidence for pattern matching (0-1)';
COMMENT ON COLUMN chatbot_config.llm_fallback_enabled IS 'Use LLM for ambiguous queries';
COMMENT ON COLUMN chatbot_config.rag_top_k IS 'Number of chunks to retrieve for RAG';
COMMENT ON COLUMN chatbot_config.rag_similarity_threshold IS 'Minimum similarity score for chunk retrieval (0-1)';
COMMENT ON COLUMN chatbot_config.llm_temperature IS 'LLM creativity parameter (0-1)';
