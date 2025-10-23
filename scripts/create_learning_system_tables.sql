-- Learning System Tables
-- Creates tables for semi-automated knowledge base improvements from user feedback

-- Draft Documents Table
-- Stores AI-generated document drafts pending admin approval
CREATE TABLE IF NOT EXISTS draft_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Draft Content
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT,

    -- Source Information
    source_type VARCHAR(50) DEFAULT 'feedback_generated' CHECK (source_type IN ('feedback_generated', 'manual_draft', 'auto_suggested')),
    source_feedback_ids UUID[],  -- Array of feedback IDs that inspired this draft
    query_pattern TEXT,  -- The query pattern this addresses (e.g., "pricing questions")

    -- Generation Metadata
    generated_by_llm BOOLEAN DEFAULT TRUE,
    llm_model TEXT,  -- e.g., "llama-3.1-8b-instant"
    generation_prompt TEXT,  -- The prompt used to generate this
    confidence_score FLOAT,  -- LLM confidence in this draft (0.0-1.0)

    -- Approval Workflow
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'needs_revision')),
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,

    -- Publishing
    published_document_id UUID REFERENCES documents(id),  -- If approved and published
    published_at TIMESTAMP WITH TIME ZONE,

    -- Statistics
    view_count INTEGER DEFAULT 0,
    feedback_count INTEGER DEFAULT 0,  -- How many feedback items led to this

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for draft_documents
CREATE INDEX IF NOT EXISTS idx_draft_documents_status ON draft_documents(status);
CREATE INDEX IF NOT EXISTS idx_draft_documents_created_at ON draft_documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_draft_documents_source_type ON draft_documents(source_type);
CREATE INDEX IF NOT EXISTS idx_draft_documents_published_doc ON draft_documents(published_document_id);

-- Feedback Insights Table
-- Aggregates feedback patterns to identify knowledge gaps
CREATE TABLE IF NOT EXISTS feedback_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Pattern Information
    query_pattern TEXT NOT NULL,  -- e.g., "pricing questions", "technical support"
    pattern_keywords TEXT[],  -- Keywords that identify this pattern

    -- Metrics
    total_feedback_count INTEGER DEFAULT 0,
    negative_feedback_count INTEGER DEFAULT 0,
    positive_feedback_count INTEGER DEFAULT 0,
    avg_rating FLOAT,

    -- Sample Queries
    sample_queries TEXT[],  -- 3-5 example queries
    sample_feedback_ids UUID[],  -- Reference to actual feedback

    -- Status
    status VARCHAR(20) DEFAULT 'identified' CHECK (status IN ('identified', 'draft_created', 'resolved', 'monitoring')),
    priority VARCHAR(10) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),

    -- Resolution
    draft_document_id UUID REFERENCES draft_documents(id),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,

    -- Timestamps
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for feedback_insights
CREATE INDEX IF NOT EXISTS idx_feedback_insights_status ON feedback_insights(status);
CREATE INDEX IF NOT EXISTS idx_feedback_insights_priority ON feedback_insights(priority);
CREATE INDEX IF NOT EXISTS idx_feedback_insights_negative_count ON feedback_insights(negative_feedback_count DESC);

-- Learning Metrics Table
-- Tracks the effectiveness of the learning system
CREATE TABLE IF NOT EXISTS learning_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Period
    metric_date DATE NOT NULL,

    -- Feedback Stats
    total_feedback INTEGER DEFAULT 0,
    negative_feedback INTEGER DEFAULT 0,
    feedback_with_comments INTEGER DEFAULT 0,

    -- Draft Stats
    drafts_generated INTEGER DEFAULT 0,
    drafts_approved INTEGER DEFAULT 0,
    drafts_rejected INTEGER DEFAULT 0,
    approval_rate FLOAT,  -- drafts_approved / drafts_generated

    -- Knowledge Base Stats
    documents_added_from_feedback INTEGER DEFAULT 0,
    avg_time_to_resolution_hours FLOAT,  -- Time from feedback to published doc

    -- Impact Stats
    queries_resolved INTEGER DEFAULT 0,  -- Queries that now get good responses
    satisfaction_improvement FLOAT,  -- Change in avg satisfaction

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(metric_date)
);

-- Indexes for learning_metrics
CREATE INDEX IF NOT EXISTS idx_learning_metrics_date ON learning_metrics(metric_date DESC);

-- Update trigger for draft_documents
CREATE OR REPLACE FUNCTION update_draft_documents_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_draft_documents_timestamp
BEFORE UPDATE ON draft_documents
FOR EACH ROW
EXECUTE FUNCTION update_draft_documents_timestamp();

-- Update trigger for feedback_insights
CREATE OR REPLACE FUNCTION update_feedback_insights_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_feedback_insights_timestamp
BEFORE UPDATE ON feedback_insights
FOR EACH ROW
EXECUTE FUNCTION update_feedback_insights_timestamp();

-- Comments for documentation
COMMENT ON TABLE draft_documents IS 'AI-generated document drafts from user feedback, pending admin approval';
COMMENT ON TABLE feedback_insights IS 'Aggregated feedback patterns identifying knowledge gaps';
COMMENT ON TABLE learning_metrics IS 'Daily metrics tracking learning system effectiveness';

COMMENT ON COLUMN draft_documents.source_feedback_ids IS 'Array of feedback IDs that inspired this draft';
COMMENT ON COLUMN draft_documents.confidence_score IS 'LLM confidence in draft quality (0.0-1.0)';
COMMENT ON COLUMN draft_documents.status IS 'Approval workflow status: pending, approved, rejected, needs_revision';

COMMENT ON COLUMN feedback_insights.query_pattern IS 'Human-readable pattern name (e.g., "pricing questions")';
COMMENT ON COLUMN feedback_insights.priority IS 'Issue priority based on frequency and impact';
COMMENT ON COLUMN feedback_insights.status IS 'Resolution status: identified, draft_created, resolved, monitoring';
