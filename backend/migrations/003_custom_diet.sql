-- Migration: Add Custom Diet Plans
-- For users who upload their own diet PDF

CREATE TABLE IF NOT EXISTS user_diet_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name VARCHAR(255),
    file_url TEXT,
    daily_calories INTEGER,
    protein_g INTEGER,
    carbs_g INTEGER,
    fat_g INTEGER,
    meals JSONB DEFAULT '[]',
    supplements TEXT[] DEFAULT '{}',
    notes TEXT,
    parsed_data JSONB,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_diet_plans_user ON user_diet_plans(user_id, active);

-- Update users table with app focus fields
ALTER TABLE users ADD COLUMN IF NOT EXISTS app_focus VARCHAR(20) DEFAULT 'full';
ALTER TABLE users ADD COLUMN IF NOT EXISTS nutrition_enabled BOOLEAN DEFAULT TRUE;

-- Add meal_reminder to notification types
-- (type is VARCHAR so no migration needed for enum)
