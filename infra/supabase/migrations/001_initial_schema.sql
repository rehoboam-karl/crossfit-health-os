-- CrossFit Health OS - Initial Database Schema
-- Supabase PostgreSQL Migration

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For full-text search

-- ==============================================
-- CORE USER MANAGEMENT
-- ==============================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Auth (linked to Supabase Auth)
    auth_user_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Profile
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    birth_date DATE,
    gender TEXT CHECK (gender IN ('male', 'female', 'other')),
    
    -- Biometrics
    weight_kg NUMERIC(5, 2),
    height_cm NUMERIC(5, 2),
    body_fat_percentage NUMERIC(4, 2),
    
    -- Fitness Level
    fitness_level TEXT CHECK (fitness_level IN ('beginner', 'intermediate', 'advanced', 'elite')),
    experience_years NUMERIC(3, 1),
    
    -- Goals & Preferences
    primary_goal TEXT, -- 'strength', 'conditioning', 'weight_loss', 'competition'
    training_frequency_per_week INT DEFAULT 5,
    preferences JSONB DEFAULT '{}', -- Workout preferences, equipment, etc.
    
    -- Timezone
    timezone TEXT DEFAULT 'America/Sao_Paulo',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro', 'elite'))
);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==============================================
-- TRAINING SYSTEM
-- ==============================================

-- Workout Templates (HWPO, Mayhem, CompTrain)
CREATE TABLE workout_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Template Info
    name TEXT NOT NULL,
    description TEXT,
    methodology TEXT CHECK (methodology IN ('hwpo', 'mayhem', 'comptrain', 'custom')),
    difficulty_level TEXT CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced', 'rx', 'scaled')),
    
    -- Structure
    workout_type TEXT CHECK (workout_type IN ('strength', 'metcon', 'skill', 'conditioning', 'mixed')),
    duration_minutes INT,
    movements JSONB NOT NULL, -- Array of movement objects
    
    -- Programming
    target_stimulus TEXT, -- 'power', 'strength', 'endurance', 'speed'
    rep_scheme TEXT,
    rest_periods TEXT,
    
    -- Metadata
    tags TEXT[], -- ['barbell', 'gymnastics', 'monostructural']
    equipment_required TEXT[],
    video_url TEXT,
    
    -- Access Control
    is_public BOOLEAN DEFAULT FALSE,
    created_by_coach_id UUID REFERENCES users(id)
);

-- User Workout Sessions (actual workouts performed)
CREATE TABLE workout_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    template_id UUID REFERENCES workout_templates(id),
    
    -- Timing
    scheduled_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_minutes NUMERIC(6, 2),
    
    -- Workout Details
    workout_type TEXT NOT NULL,
    movements JSONB NOT NULL,
    prescribed_weight_kg JSONB, -- Weight for each movement
    actual_weight_kg JSONB,
    prescribed_reps JSONB,
    actual_reps JSONB,
    
    -- Performance Metrics
    score NUMERIC(10, 2), -- Time (seconds) or rounds+reps for AMRAP
    score_type TEXT CHECK (score_type IN ('time', 'rounds', 'reps', 'weight', 'distance')),
    rpe_score INT CHECK (rpe_score BETWEEN 1 AND 10), -- Rate of Perceived Exertion
    
    -- Heart Rate Data (from Apple Watch/Garmin)
    avg_heart_rate_bpm INT,
    max_heart_rate_bpm INT,
    heart_rate_zones JSONB, -- Time in each HR zone
    calories_burned INT,
    
    -- Pre-workout Readiness
    hrv_pre_workout INT, -- milliseconds
    sleep_quality_pre INT CHECK (sleep_quality_pre BETWEEN 1 AND 10),
    
    -- Post-workout
    muscle_groups_worked TEXT[],
    notes TEXT,
    video_url TEXT,
    
    -- Metadata
    location TEXT, -- 'home', 'gym', 'outdoor'
    weather_conditions JSONB,
    
    CONSTRAINT valid_duration CHECK (duration_minutes IS NULL OR duration_minutes > 0)
);

CREATE INDEX idx_workout_sessions_user_started ON workout_sessions(user_id, started_at DESC);
CREATE INDEX idx_workout_sessions_type ON workout_sessions(workout_type);

-- Exercise Sets (individual sets within a workout)
CREATE TABLE exercise_sets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
    
    -- Set Info
    set_number INT NOT NULL,
    movement_name TEXT NOT NULL,
    
    -- Performance
    reps INT,
    weight_kg NUMERIC(6, 2),
    distance_meters NUMERIC(8, 2),
    duration_seconds NUMERIC(6, 2),
    
    -- Form & Quality
    form_rating INT CHECK (form_rating BETWEEN 1 AND 5),
    tempo TEXT, -- '3-1-1-0' (eccentric-pause-concentric-pause)
    rest_after_seconds INT,
    
    -- Notes
    notes TEXT,
    
    CONSTRAINT valid_set CHECK (reps IS NOT NULL OR distance_meters IS NOT NULL OR duration_seconds IS NOT NULL)
);

CREATE INDEX idx_exercise_sets_session ON exercise_sets(session_id, set_number);

-- ==============================================
-- RECOVERY & READINESS
-- ==============================================

CREATE TABLE recovery_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Sleep (from Apple HealthKit)
    sleep_duration_hours NUMERIC(4, 2),
    sleep_quality_score INT CHECK (sleep_quality_score BETWEEN 1 AND 100),
    deep_sleep_hours NUMERIC(4, 2),
    rem_sleep_hours NUMERIC(4, 2),
    sleep_disruptions INT,
    
    -- Heart Rate Variability (HRV)
    hrv_rmssd_ms INT, -- Root Mean Square of Successive Differences
    hrv_baseline_ms INT, -- User's 30-day baseline
    hrv_ratio NUMERIC(4, 2), -- today / baseline (1.0 = normal, >1.1 = recovered, <0.9 = fatigued)
    
    -- Resting Heart Rate
    resting_heart_rate_bpm INT,
    resting_hr_baseline_bpm INT,
    
    -- Subjective Metrics
    stress_level INT CHECK (stress_level BETWEEN 1 AND 10),
    muscle_soreness INT CHECK (muscle_soreness BETWEEN 1 AND 10),
    energy_level INT CHECK (energy_level BETWEEN 1 AND 10),
    mood_score INT CHECK (mood_score BETWEEN 1 AND 10),
    
    -- Calculated Readiness Score (0-100)
    readiness_score INT CHECK (readiness_score BETWEEN 0 AND 100),
    
    -- Notes
    notes TEXT,
    
    UNIQUE(user_id, date)
);

CREATE INDEX idx_recovery_metrics_user_date ON recovery_metrics(user_id, date DESC);

-- ==============================================
-- HEALTH & BIOMARKERS
-- ==============================================

-- Biomarker Types (reference table)
CREATE TABLE biomarker_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL, -- 'testosterone_total', 'vitamin_d', 'glucose_fasting'
    display_name TEXT NOT NULL,
    category TEXT NOT NULL, -- 'hormones', 'metabolic', 'vitamins', 'lipids', 'inflammatory'
    unit TEXT NOT NULL, -- 'ng/dL', 'nmol/L', 'mg/dL', 'mmol/L'
    
    -- Reference Ranges
    optimal_min NUMERIC(10, 2),
    optimal_max NUMERIC(10, 2),
    normal_min NUMERIC(10, 2),
    normal_max NUMERIC(10, 2),
    
    -- Metadata
    description TEXT,
    clinical_significance TEXT
);

-- Lab Results
CREATE TABLE biomarker_readings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    biomarker_type_id UUID NOT NULL REFERENCES biomarker_types(id),
    
    -- Test Info
    test_date DATE NOT NULL,
    lab_name TEXT,
    
    -- Result
    value NUMERIC(10, 2) NOT NULL,
    unit TEXT NOT NULL,
    
    -- Status
    status TEXT CHECK (status IN ('optimal', 'normal', 'low', 'high', 'critical')),
    
    -- Source
    pdf_url TEXT, -- Supabase Storage URL of uploaded lab report
    ocr_confidence NUMERIC(3, 2), -- If extracted via OCR
    manually_entered BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_biomarker_readings_user_type ON biomarker_readings(user_id, biomarker_type_id, test_date DESC);

-- ==============================================
-- NUTRITION
-- ==============================================

-- Meal Plans
CREATE TABLE meal_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Plan Details
    name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    
    -- Macronutrient Targets (can vary by day type)
    training_day_calories INT,
    training_day_protein_g INT,
    training_day_carbs_g INT,
    training_day_fat_g INT,
    
    rest_day_calories INT,
    rest_day_protein_g INT,
    rest_day_carbs_g INT,
    rest_day_fat_g INT,
    
    -- Preferences
    dietary_restrictions TEXT[], -- ['gluten_free', 'dairy_free', 'vegan']
    meal_timing_strategy TEXT, -- 'zone', 'intermittent_fasting', 'flexible'
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Meal Logs
CREATE TABLE meal_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    meal_plan_id UUID REFERENCES meal_plans(id),
    
    -- Timing
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    meal_time TEXT CHECK (meal_time IN ('breakfast', 'lunch', 'dinner', 'snack', 'pre_workout', 'post_workout')),
    
    -- Macros
    calories INT,
    protein_g NUMERIC(6, 2),
    carbs_g NUMERIC(6, 2),
    fat_g NUMERIC(6, 2),
    fiber_g NUMERIC(6, 2),
    
    -- Food Items
    foods JSONB, -- Array of food objects with quantities
    
    -- Media
    photo_url TEXT, -- Supabase Storage URL
    ai_estimation BOOLEAN DEFAULT FALSE, -- If macros estimated via AI
    
    -- Notes
    notes TEXT
);

CREATE INDEX idx_meal_logs_user_time ON meal_logs(user_id, logged_at DESC);

-- ==============================================
-- INTEGRATIONS
-- ==============================================

-- Apple HealthKit Data Sync
CREATE TABLE healthkit_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Sync Info
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_type TEXT NOT NULL, -- 'hrv', 'sleep', 'workout', 'steps', 'heart_rate'
    
    -- Date Range
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    
    -- Data Payload
    data JSONB NOT NULL,
    
    -- Metadata
    device_name TEXT,
    source_app TEXT
);

CREATE INDEX idx_healthkit_data_user_type ON healthkit_data(user_id, data_type, start_date DESC);

-- Google Calendar Events
CREATE TABLE calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Google Calendar Info
    google_event_id TEXT UNIQUE NOT NULL,
    calendar_id TEXT NOT NULL,
    
    -- Event Details
    event_type TEXT CHECK (event_type IN ('workout', 'meal', 'recovery', 'other')),
    title TEXT NOT NULL,
    description TEXT,
    
    -- Timing
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    
    -- Sync Status
    last_synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sync_direction TEXT CHECK (sync_direction IN ('to_calendar', 'from_calendar', 'bidirectional'))
);

CREATE INDEX idx_calendar_events_user_time ON calendar_events(user_id, start_time);

-- ==============================================
-- GAMIFICATION & SOCIAL
-- ==============================================

-- User Achievements
CREATE TABLE achievements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Achievement Details
    achievement_type TEXT NOT NULL, -- 'first_murph', '100_workouts', 'bodyweight_snatch'
    title TEXT NOT NULL,
    description TEXT,
    
    -- Earned
    earned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Metadata
    icon_url TEXT,
    badge_tier TEXT CHECK (badge_tier IN ('bronze', 'silver', 'gold', 'platinum'))
);

-- Personal Records (PRs)
CREATE TABLE personal_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Movement
    movement_name TEXT NOT NULL,
    record_type TEXT CHECK (record_type IN ('1rm', '3rm', '5rm', '10rm', 'max_reps', 'best_time')),
    
    -- Record
    value NUMERIC(10, 2) NOT NULL, -- Weight (kg), reps, or time (seconds)
    unit TEXT NOT NULL,
    
    -- Context
    achieved_at TIMESTAMPTZ NOT NULL,
    session_id UUID REFERENCES workout_sessions(id),
    
    -- Notes
    notes TEXT,
    video_url TEXT,
    
    UNIQUE(user_id, movement_name, record_type)
);

CREATE INDEX idx_personal_records_user_movement ON personal_records(user_id, movement_name);

-- ==============================================
-- ROW LEVEL SECURITY (RLS)
-- ==============================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE workout_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE exercise_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE recovery_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE biomarker_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE meal_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE meal_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE healthkit_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE achievements ENABLE ROW LEVEL SECURITY;
ALTER TABLE personal_records ENABLE ROW LEVEL SECURITY;

-- Users can only read/update their own data
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid() = auth_user_id);

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid() = auth_user_id);

-- Workout sessions
CREATE POLICY "Users can view own workouts" ON workout_sessions
    FOR SELECT USING (auth.uid() = (SELECT auth_user_id FROM users WHERE id = user_id));

CREATE POLICY "Users can insert own workouts" ON workout_sessions
    FOR INSERT WITH CHECK (auth.uid() = (SELECT auth_user_id FROM users WHERE id = user_id));

CREATE POLICY "Users can update own workouts" ON workout_sessions
    FOR UPDATE USING (auth.uid() = (SELECT auth_user_id FROM users WHERE id = user_id));

-- Recovery metrics
CREATE POLICY "Users can view own recovery" ON recovery_metrics
    FOR SELECT USING (auth.uid() = (SELECT auth_user_id FROM users WHERE id = user_id));

CREATE POLICY "Users can insert own recovery" ON recovery_metrics
    FOR INSERT WITH CHECK (auth.uid() = (SELECT auth_user_id FROM users WHERE id = user_id));

-- (Add similar policies for other tables)

-- ==============================================
-- FUNCTIONS & TRIGGERS
-- ==============================================

-- Function to calculate readiness score
CREATE OR REPLACE FUNCTION calculate_readiness_score(
    p_hrv_ratio NUMERIC,
    p_sleep_quality INT,
    p_stress_level INT,
    p_soreness INT
) RETURNS INT AS $$
DECLARE
    readiness INT;
BEGIN
    readiness := (
        (p_hrv_ratio * 40) +
        (p_sleep_quality * 0.3) +
        ((10 - p_stress_level) * 2) +
        ((10 - p_soreness) * 1)
    );
    
    RETURN GREATEST(0, LEAST(100, readiness));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Trigger to auto-calculate readiness score
CREATE OR REPLACE FUNCTION update_readiness_score()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.hrv_ratio IS NOT NULL AND NEW.sleep_quality_score IS NOT NULL THEN
        NEW.readiness_score := calculate_readiness_score(
            NEW.hrv_ratio,
            NEW.sleep_quality_score,
            COALESCE(NEW.stress_level, 5),
            COALESCE(NEW.muscle_soreness, 5)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calculate_recovery_readiness
    BEFORE INSERT OR UPDATE ON recovery_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_readiness_score();

-- ==============================================
-- INDEXES FOR PERFORMANCE
-- ==============================================

-- Full-text search indexes
CREATE INDEX idx_workout_templates_search ON workout_templates USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));
CREATE INDEX idx_movements_gin ON workout_templates USING gin(movements);

-- Common query patterns
CREATE INDEX idx_sessions_completed ON workout_sessions(completed_at DESC) WHERE completed_at IS NOT NULL;
CREATE INDEX idx_biomarkers_recent ON biomarker_readings(user_id, test_date DESC);
CREATE INDEX idx_meals_recent ON meal_logs(user_id, logged_at DESC);

-- ==============================================
-- INITIAL DATA SEEDING
-- ==============================================

-- Insert common biomarker types
INSERT INTO biomarker_types (name, display_name, category, unit, optimal_min, optimal_max, normal_min, normal_max, description) VALUES
('testosterone_total', 'Testosterone (Total)', 'hormones', 'ng/dL', 600, 1000, 300, 1000, 'Total testosterone for male athletes'),
('testosterone_free', 'Testosterone (Free)', 'hormones', 'pg/mL', 9, 30, 5, 30, 'Free (bioavailable) testosterone'),
('cortisol_am', 'Cortisol (Morning)', 'hormones', 'μg/dL', 10, 20, 6, 23, 'Morning cortisol levels'),
('vitamin_d', 'Vitamin D (25-OH)', 'vitamins', 'ng/mL', 50, 80, 30, 100, '25-hydroxyvitamin D'),
('glucose_fasting', 'Glucose (Fasting)', 'metabolic', 'mg/dL', 75, 95, 70, 100, 'Fasting blood glucose'),
('hba1c', 'HbA1c', 'metabolic', '%', 4.0, 5.4, 4.0, 5.6, 'Glycated hemoglobin (3-month glucose average)'),
('crp', 'C-Reactive Protein', 'inflammatory', 'mg/L', 0, 1, 0, 3, 'General inflammation marker'),
('creatinine', 'Creatinine', 'kidney', 'mg/dL', 0.7, 1.3, 0.6, 1.4, 'Kidney function marker'),
('ldl_cholesterol', 'LDL Cholesterol', 'lipids', 'mg/dL', 0, 100, 0, 130, 'Low-density lipoprotein cholesterol'),
('hdl_cholesterol', 'HDL Cholesterol', 'lipids', 'mg/dL', 50, 100, 40, 100, 'High-density lipoprotein cholesterol'),
('triglycerides', 'Triglycerides', 'lipids', 'mg/dL', 0, 100, 0, 150, 'Blood triglycerides'),
('iron_serum', 'Iron (Serum)', 'minerals', 'μg/dL', 60, 170, 50, 180, 'Serum iron levels'),
('ferritin', 'Ferritin', 'minerals', 'ng/mL', 50, 200, 20, 300, 'Iron storage protein'),
('tsh', 'TSH', 'thyroid', 'mIU/L', 0.5, 2.5, 0.4, 4.0, 'Thyroid stimulating hormone'),
('t3_free', 'T3 (Free)', 'thyroid', 'pg/mL', 3.0, 4.2, 2.3, 4.2, 'Free triiodothyronine'),
('t4_free', 'T4 (Free)', 'thyroid', 'ng/dL', 1.0, 1.8, 0.8, 1.8, 'Free thyroxine');

-- Sample workout templates (HWPO-style)
INSERT INTO workout_templates (name, description, methodology, difficulty_level, workout_type, duration_minutes, movements, target_stimulus, equipment_required, tags) VALUES
(
    'HWPO Strength Monday',
    'Heavy barbell strength session - Mat Fraser methodology',
    'hwpo',
    'rx',
    'strength',
    45,
    '[
        {"movement": "back_squat", "sets": 5, "reps": 5, "rest": "3min", "intensity": "85%"},
        {"movement": "bench_press", "sets": 4, "reps": 8, "rest": "2min", "intensity": "75%"},
        {"movement": "barbell_row", "sets": 3, "reps": 10, "rest": "90s"}
    ]'::jsonb,
    'strength',
    ARRAY['barbell', 'squat_rack', 'bench'],
    ARRAY['strength', 'upper_body', 'lower_body', 'hwpo']
),
(
    'Mayhem Metcon',
    'Classic Rich Froning-style metabolic conditioning',
    'mayhem',
    'rx',
    'metcon',
    20,
    '[
        {"movement": "thruster", "weight_kg": 42.5, "reps": 21},
        {"movement": "chest_to_bar_pullups", "reps": 21},
        {"movement": "thruster", "weight_kg": 42.5, "reps": 15},
        {"movement": "chest_to_bar_pullups", "reps": 15},
        {"movement": "thruster", "weight_kg": 42.5, "reps": 9},
        {"movement": "chest_to_bar_pullups", "reps": 9}
    ]'::jsonb,
    'power_endurance',
    ARRAY['barbell', 'pullup_bar'],
    ARRAY['metcon', 'couplet', 'mayhem', 'for_time']
);

COMMENT ON TABLE users IS 'Core user profiles with biometrics and preferences';
COMMENT ON TABLE workout_sessions IS 'Individual workout sessions performed by users';
COMMENT ON TABLE recovery_metrics IS 'Daily recovery metrics (HRV, sleep, readiness)';
COMMENT ON TABLE biomarker_readings IS 'Lab test results and biomarker tracking';
COMMENT ON TABLE meal_logs IS 'Nutrition tracking - meals and macros';
