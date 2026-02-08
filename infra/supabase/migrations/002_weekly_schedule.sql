-- Migration: Weekly Training Schedule & Meal Plans
-- Date: 2026-02-08
-- Description: Add tables for weekly training schedules and auto-generated meal plans

-- ============================================
-- Weekly Training Schedules
-- ============================================

CREATE TABLE IF NOT EXISTS weekly_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    name VARCHAR(100) NOT NULL,
    methodology VARCHAR(20) NOT NULL CHECK (methodology IN ('hwpo', 'mayhem', 'comptrain', 'custom')),
    
    -- JSONB structure:
    -- {
    --   "monday": {"day": "monday", "sessions": [...], "rest_day": false},
    --   "tuesday": {...},
    --   ...
    -- }
    schedule JSONB NOT NULL,
    
    start_date DATE NOT NULL,
    end_date DATE,
    active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_date_range CHECK (end_date IS NULL OR end_date > start_date)
);

-- Indexes
CREATE INDEX idx_weekly_schedules_user ON weekly_schedules(user_id);
CREATE INDEX idx_weekly_schedules_active ON weekly_schedules(user_id, active) WHERE active = true;
CREATE INDEX idx_weekly_schedules_dates ON weekly_schedules(start_date, end_date);

-- RLS
ALTER TABLE weekly_schedules ENABLE ROW LEVEL SECURITY;

CREATE POLICY weekly_schedules_user_policy ON weekly_schedules
    FOR ALL
    USING (auth.uid() = (SELECT auth_user_id FROM users WHERE id = user_id));


-- ============================================
-- Weekly Meal Plans (Auto-generated from Training Schedule)
-- ============================================

CREATE TABLE IF NOT EXISTS weekly_meal_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    training_schedule_id UUID NOT NULL REFERENCES weekly_schedules(id) ON DELETE CASCADE,
    
    -- JSONB structure:
    -- {
    --   "monday": {
    --     "day": "monday",
    --     "meals": [
    --       {"meal_type": "pre_workout", "time": "05:00", "duration_minutes": 20, ...},
    --       {"meal_type": "breakfast", "time": "07:00", ...}
    --     ],
    --     "training_day": true,
    --     "total_calories": 2800
    --   },
    --   ...
    -- }
    meal_plans JSONB NOT NULL,
    
    -- Meal timing offsets (in minutes)
    pre_workout_offset_minutes INT DEFAULT -60,  -- 60min before workout
    post_workout_offset_minutes INT DEFAULT 30,  -- 30min after workout
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_meal_plans_user ON weekly_meal_plans(user_id);
CREATE INDEX idx_meal_plans_schedule ON weekly_meal_plans(training_schedule_id);
CREATE INDEX idx_meal_plans_created ON weekly_meal_plans(created_at DESC);

-- RLS
ALTER TABLE weekly_meal_plans ENABLE ROW LEVEL SECURITY;

CREATE POLICY meal_plans_user_policy ON weekly_meal_plans
    FOR ALL
    USING (auth.uid() = (SELECT auth_user_id FROM users WHERE id = user_id));


-- ============================================
-- Auto-update Trigger
-- ============================================

CREATE OR REPLACE FUNCTION update_schedule_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER weekly_schedules_updated_at
    BEFORE UPDATE ON weekly_schedules
    FOR EACH ROW
    EXECUTE FUNCTION update_schedule_updated_at();

CREATE TRIGGER meal_plans_updated_at
    BEFORE UPDATE ON weekly_meal_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_schedule_updated_at();


-- ============================================
-- Helper Functions
-- ============================================

-- Get current week's schedule for a user
CREATE OR REPLACE FUNCTION get_current_week_schedule(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    current_schedule RECORD;
BEGIN
    SELECT schedule INTO current_schedule
    FROM weekly_schedules
    WHERE user_id = p_user_id
      AND active = true
      AND start_date <= CURRENT_DATE
      AND (end_date IS NULL OR end_date >= CURRENT_DATE)
    ORDER BY start_date DESC
    LIMIT 1;
    
    RETURN COALESCE(current_schedule.schedule, '{}'::JSONB);
END;
$$ LANGUAGE plpgsql;

-- Get today's training sessions
CREATE OR REPLACE FUNCTION get_today_training_sessions(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    schedule_json JSONB;
    day_key TEXT;
BEGIN
    -- Get day of week (lowercase)
    day_key := LOWER(TO_CHAR(CURRENT_DATE, 'Day'));
    day_key := TRIM(day_key);
    
    -- Get schedule
    schedule_json := get_current_week_schedule(p_user_id);
    
    -- Return today's sessions
    RETURN schedule_json -> day_key;
END;
$$ LANGUAGE plpgsql;

-- Get today's meals
CREATE OR REPLACE FUNCTION get_today_meals(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    meal_plan RECORD;
    day_key TEXT;
BEGIN
    -- Get day of week
    day_key := LOWER(TO_CHAR(CURRENT_DATE, 'Day'));
    day_key := TRIM(day_key);
    
    SELECT meal_plans INTO meal_plan
    FROM weekly_meal_plans wmp
    JOIN weekly_schedules ws ON ws.id = wmp.training_schedule_id
    WHERE wmp.user_id = p_user_id
      AND ws.active = true
    ORDER BY wmp.created_at DESC
    LIMIT 1;
    
    RETURN COALESCE(meal_plan.meal_plans -> day_key, '{}'::JSONB);
END;
$$ LANGUAGE plpgsql;


-- ============================================
-- Sample Data (for testing)
-- ============================================

-- Insert sample schedule for first user
DO $$
DECLARE
    sample_user_id UUID;
BEGIN
    -- Get first user (if exists)
    SELECT id INTO sample_user_id FROM users LIMIT 1;
    
    IF sample_user_id IS NOT NULL THEN
        INSERT INTO weekly_schedules (user_id, name, methodology, schedule, start_date, active)
        VALUES (
            sample_user_id,
            'HWPO 5x per week',
            'hwpo',
            '{
                "monday": {
                    "day": "monday",
                    "sessions": [
                        {"time": "06:00", "duration_minutes": 90, "workout_type": "strength", "notes": "Heavy squats"}
                    ],
                    "rest_day": false
                },
                "tuesday": {
                    "day": "tuesday",
                    "sessions": [
                        {"time": "06:00", "duration_minutes": 60, "workout_type": "metcon", "notes": null}
                    ],
                    "rest_day": false
                },
                "wednesday": {
                    "day": "wednesday",
                    "sessions": [
                        {"time": "18:00", "duration_minutes": 45, "workout_type": "skill", "notes": "Gymnastics"}
                    ],
                    "rest_day": false
                },
                "thursday": {
                    "day": "thursday",
                    "sessions": [
                        {"time": "06:00", "duration_minutes": 75, "workout_type": "mixed", "notes": null}
                    ],
                    "rest_day": false
                },
                "friday": {
                    "day": "friday",
                    "sessions": [
                        {"time": "06:00", "duration_minutes": 60, "workout_type": "metcon", "notes": "Competition simulation"}
                    ],
                    "rest_day": false
                },
                "saturday": {
                    "day": "saturday",
                    "sessions": [],
                    "rest_day": true
                },
                "sunday": {
                    "day": "sunday",
                    "sessions": [],
                    "rest_day": true
                }
            }'::JSONB,
            CURRENT_DATE,
            true
        );
    END IF;
END $$;


COMMENT ON TABLE weekly_schedules IS 'Weekly training schedules with multiple sessions per day';
COMMENT ON TABLE weekly_meal_plans IS 'Auto-generated meal plans synced with training schedule';
COMMENT ON FUNCTION get_current_week_schedule IS 'Get active weekly schedule for a user';
COMMENT ON FUNCTION get_today_training_sessions IS 'Get today training sessions from active schedule';
COMMENT ON FUNCTION get_today_meals IS 'Get today meals from active meal plan';
