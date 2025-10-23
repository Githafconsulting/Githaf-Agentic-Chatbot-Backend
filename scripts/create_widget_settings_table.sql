-- =============================================================================
-- WIDGET SETTINGS TABLE
-- =============================================================================
-- Description: Stores widget customization settings
-- Date: January 15, 2025
-- =============================================================================

CREATE TABLE IF NOT EXISTS widget_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Appearance Settings
    widget_theme VARCHAR(20) DEFAULT 'modern' CHECK (widget_theme IN ('modern', 'minimal', 'classic')),
    primary_color VARCHAR(7) DEFAULT '#1e40af',  -- Hex color
    accent_color VARCHAR(7) DEFAULT '#0ea5e9',   -- Hex color
    button_size VARCHAR(10) DEFAULT 'medium' CHECK (button_size IN ('small', 'medium', 'large')),
    show_notification_badge BOOLEAN DEFAULT TRUE,

    -- Position Settings
    widget_position VARCHAR(20) DEFAULT 'bottom-right' CHECK (widget_position IN ('top-left', 'top-right', 'bottom-left', 'bottom-right')),
    horizontal_padding INTEGER DEFAULT 20 CHECK (horizontal_padding >= 0 AND horizontal_padding <= 200),
    vertical_padding INTEGER DEFAULT 20 CHECK (vertical_padding >= 0 AND horizontal_padding <= 200),
    z_index INTEGER DEFAULT 1000 CHECK (z_index >= 0 AND z_index <= 99999),

    -- Content Settings
    widget_title TEXT DEFAULT 'Githaf AI Assistant',
    widget_subtitle TEXT DEFAULT 'Always here to help',
    greeting_message TEXT DEFAULT 'Hi! How can I help you today?',
    api_url TEXT DEFAULT '/api/v1/chat/',

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on updated_at for quick access to latest settings
CREATE INDEX IF NOT EXISTS idx_widget_settings_updated_at ON widget_settings(updated_at DESC);

-- Insert default settings (only if table is empty)
INSERT INTO widget_settings (
    widget_theme, primary_color, accent_color, button_size, show_notification_badge,
    widget_position, horizontal_padding, vertical_padding, z_index,
    widget_title, widget_subtitle, greeting_message, api_url
)
SELECT 'modern', '#1e40af', '#0ea5e9', 'medium', TRUE,
       'bottom-right', 20, 20, 1000,
       'Githaf AI Assistant', 'Always here to help', 'Hi! How can I help you today?', '/api/v1/chat/'
WHERE NOT EXISTS (SELECT 1 FROM widget_settings);

COMMENT ON TABLE widget_settings IS 'Stores widget customization settings for the chat widget';
COMMENT ON COLUMN widget_settings.widget_theme IS 'Theme style: modern (gradient + animation), minimal (flat + border), classic (simple gradient)';
COMMENT ON COLUMN widget_settings.widget_position IS 'Position on page: top-left, top-right, bottom-left, bottom-right';
COMMENT ON COLUMN widget_settings.primary_color IS 'Primary color in hex format (#RRGGBB)';
COMMENT ON COLUMN widget_settings.accent_color IS 'Accent color in hex format (#RRGGBB)';

-- Migration complete
SELECT 'Widget settings table created successfully!' AS status;
