-- Phase 5: Tool Ecosystem - Database Schema
-- Tables for calendar appointments and CRM data

-- ========================================
-- Appointments Table (Calendar Tool)
-- ========================================
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    description TEXT NOT NULL,
    attendee_email TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'confirmed', 'cancelled', 'completed')),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for appointments
CREATE INDEX IF NOT EXISTS idx_appointments_start_time ON appointments(start_time);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_appointments_attendee_email ON appointments(attendee_email);

-- ========================================
-- CRM Contacts Table
-- ========================================
CREATE TABLE IF NOT EXISTS crm_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    company TEXT,
    phone TEXT,
    industry TEXT,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for CRM contacts
CREATE INDEX IF NOT EXISTS idx_crm_contacts_email ON crm_contacts(email);
CREATE INDEX IF NOT EXISTS idx_crm_contacts_company ON crm_contacts(company);
CREATE INDEX IF NOT EXISTS idx_crm_contacts_industry ON crm_contacts(industry);
CREATE INDEX IF NOT EXISTS idx_crm_contacts_created_at ON crm_contacts(created_at DESC);

-- Full-text search index on name and company
CREATE INDEX IF NOT EXISTS idx_crm_contacts_search ON crm_contacts
  USING gin(to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(company, '')));

-- GIN index for tags array
CREATE INDEX IF NOT EXISTS idx_crm_contacts_tags ON crm_contacts USING gin(tags);

-- ========================================
-- CRM Interactions Table
-- ========================================
CREATE TABLE IF NOT EXISTS crm_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID NOT NULL REFERENCES crm_contacts(id) ON DELETE CASCADE,
    interaction_type TEXT NOT NULL CHECK (interaction_type IN ('call', 'email', 'meeting', 'chat', 'other')),
    notes TEXT NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for CRM interactions
CREATE INDEX IF NOT EXISTS idx_crm_interactions_contact_id ON crm_interactions(contact_id);
CREATE INDEX IF NOT EXISTS idx_crm_interactions_type ON crm_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_crm_interactions_occurred_at ON crm_interactions(occurred_at DESC);

-- ========================================
-- Trigger for updated_at timestamps
-- ========================================

-- Reuse the update_updated_at_column function if it exists, otherwise create it
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for appointments
DROP TRIGGER IF EXISTS update_appointments_updated_at ON appointments;
CREATE TRIGGER update_appointments_updated_at
    BEFORE UPDATE ON appointments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Triggers for CRM contacts
DROP TRIGGER IF EXISTS update_crm_contacts_updated_at ON crm_contacts;
CREATE TRIGGER update_crm_contacts_updated_at
    BEFORE UPDATE ON crm_contacts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- Sample Data (Optional for testing)
-- ========================================

-- Insert sample appointments (commented out by default)
-- INSERT INTO appointments (start_time, duration_minutes, description, attendee_email, status)
-- VALUES
--     ('2025-01-15 10:00:00+00', 60, 'Initial consultation', 'client@example.com', 'scheduled'),
--     ('2025-01-16 14:00:00+00', 30, 'Follow-up call', 'client2@example.com', 'confirmed');

-- Insert sample CRM contacts (commented out by default)
-- INSERT INTO crm_contacts (email, name, company, phone, industry, tags)
-- VALUES
--     ('john.doe@techcorp.com', 'John Doe', 'TechCorp Inc', '+1-555-0100', 'Technology', ARRAY['lead', 'interested']),
--     ('jane.smith@healthcare.com', 'Jane Smith', 'HealthCare Partners', '+1-555-0200', 'Healthcare', ARRAY['customer', 'enterprise']);

-- ========================================
-- Verification Queries
-- ========================================

-- Verify tables created
SELECT table_name
FROM information_schema.tables
WHERE table_name IN ('appointments', 'crm_contacts', 'crm_interactions');

-- Verify indexes created
SELECT indexname
FROM pg_indexes
WHERE tablename IN ('appointments', 'crm_contacts', 'crm_interactions')
ORDER BY tablename, indexname;
