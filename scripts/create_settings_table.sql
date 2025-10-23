-- System Settings Table
-- Run this in your Supabase SQL editor

CREATE TABLE IF NOT EXISTS system_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Theme Settings
    default_theme VARCHAR(10) DEFAULT 'dark' CHECK (default_theme IN ('light', 'dark')),
    allow_theme_switching BOOLEAN DEFAULT TRUE,
    inherit_host_theme BOOLEAN DEFAULT TRUE,

    -- Language Settings
    default_language VARCHAR(5) DEFAULT 'en',
    enabled_languages TEXT[] DEFAULT '{"en","fr","de","es","ar"}',
    translate_ai_responses BOOLEAN DEFAULT TRUE,
    enable_rtl BOOLEAN DEFAULT TRUE,

    -- Analytics Settings
    enable_country_tracking BOOLEAN DEFAULT TRUE,
    default_date_range VARCHAR(10) DEFAULT '30d' CHECK (default_date_range IN ('7d', '30d', '90d', 'custom')),
    enable_world_map BOOLEAN DEFAULT TRUE,

    -- Privacy Settings
    anonymize_ips BOOLEAN DEFAULT TRUE,
    store_ip_addresses BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default settings (only if table is empty)
INSERT INTO system_settings (
    default_theme,
    allow_theme_switching,
    inherit_host_theme,
    default_language,
    enabled_languages,
    translate_ai_responses,
    enable_rtl,
    enable_country_tracking,
    default_date_range,
    enable_world_map,
    anonymize_ips,
    store_ip_addresses
)
SELECT
    'dark',
    TRUE,
    TRUE,
    'en',
    '{"en","fr","de","es","ar"}',
    TRUE,
    TRUE,
    TRUE,
    '30d',
    TRUE,
    TRUE,
    FALSE
WHERE NOT EXISTS (SELECT 1 FROM system_settings);

-- Create index on updated_at for performance
CREATE INDEX IF NOT EXISTS idx_system_settings_updated_at ON system_settings(updated_at);

COMMENT ON TABLE system_settings IS 'Global system configuration settings';
COMMENT ON COLUMN system_settings.default_theme IS 'Default UI theme: light or dark';
COMMENT ON COLUMN system_settings.enabled_languages IS 'Array of enabled language codes';
COMMENT ON COLUMN system_settings.anonymize_ips IS 'Hash IP addresses for GDPR compliance';
