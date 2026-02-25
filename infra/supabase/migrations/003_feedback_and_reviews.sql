-- Migration: Session Feedback and Weekly Reviews
-- Date: 2026-02-08
-- Description: Add tables for session feedback and AI-powered weekly reviews

-- ============================================
-- Session Feedback
-- ============================================

CREATE TABLE IF NOT EXISTS session_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
    
    date DATE NOT NULL,
    
    -- Subjective metrics
    rpe_score INT NOT NULL CHECK (rpe_score BETWEEN 1 AND 10),
    difficulty VARCHAR(30) NOT NULL CHECK (difficulty IN ('too_easy', 'appropriate', 'hard_but_manageable', 'too_hard')),
    technique_quality INT NOT NULL CHECK (technique_quality BETWEEN 1 AND 10),
    pacing VARCHAR(20) NOT NULL CHECK (pacing IN ('too_fast', 'good', 'too_slow')),
    
    energy_level_pre INT NOT NULL CHECK (energy_level_pre BETWEEN 1 AND 10),
    energy_level_post INT NOT NULL CHECK (energy_level_post BETWEEN 1 AND 10),
    
    would_repeat BOOLEAN DEFAULT true,
    favorite_part TEXT,
    least_favorite_part TEXT,
    notes TEXT,
    
    -- Movement-specific feedback (JSONB)
    -- [{"movement": "back_squat", "prescribed_sets": 5, "actual_sets": 5, "actual_reps": [5,5,5,5,4], ...}]
    movements_feedback JSONB DEFAULT '[]'::JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(session_id)  -- One feedback per session
);

-- Indexes
CREATE INDEX idx_feedback_user ON session_feedback(user_id);
CREATE INDEX idx_feedback_date ON session_feedback(date DESC);
CREATE INDEX idx_feedback_session ON session_feedback(session_id);

-- RLS
ALTER TABLE session_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY feedback_user_policy ON session_feedback
    FOR ALL
    USING (auth.uid() = (SELECT auth_user_id FROM users WHERE id = user_id));


-- ============================================
-- Weekly Reviews (AI-Generated)
-- ============================================

CREATE TABLE IF NOT EXISTS weekly_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    week_number INT NOT NULL CHECK (week_number BETWEEN 1 AND 52),
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    
    -- Overview
    summary TEXT NOT NULL,
    planned_sessions INT NOT NULL,
    completed_sessions INT NOT NULL,
    adherence_rate FLOAT CHECK (adherence_rate BETWEEN 0 AND 100),
    avg_rpe FLOAT,
    avg_readiness FLOAT,
    overall_satisfaction INT CHECK (overall_satisfaction BETWEEN 1 AND 10),
    
    -- Analysis
    -- strengths: [{"movement": "squat", "improvement": "...", "confidence": "high"}]
    strengths JSONB DEFAULT '[]'::JSONB,
    
    -- weaknesses: [{"movement": "snatch", "issue": "...", "suggested_focus": "..."}]
    weaknesses JSONB DEFAULT '[]'::JSONB,
    
    recovery_status VARCHAR(20) NOT NULL CHECK (recovery_status IN ('optimal', 'adequate', 'compromised')),
    volume_assessment VARCHAR(20) NOT NULL CHECK (volume_assessment IN ('too_low', 'appropriate', 'too_high')),
    
    -- Progression
    progressions_detected JSONB DEFAULT '[]'::JSONB,  -- ["Back squat +2kg", "Fran -8s"]
    
    -- Next week recommendations
    -- {
    --   "volume_change_pct": -20,
    --   "intensity_change": "maintain",
    --   "focus_movements": ["handstand_walk"],
    --   "special_notes": "Deload week",
    --   "add_skill_work_minutes": 10,
    --   "add_mobility_work": true
    -- }
    next_week_adjustments JSONB NOT NULL,
    
    coach_message TEXT NOT NULL,  -- Motivational message from AI
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ai_model_used VARCHAR(50) DEFAULT 'claude-3-5-sonnet',
    
    UNIQUE(user_id, week_number, week_start_date)
);

-- Indexes
CREATE INDEX idx_reviews_user ON weekly_reviews(user_id);
CREATE INDEX idx_reviews_week ON weekly_reviews(week_number);
CREATE INDEX idx_reviews_created ON weekly_reviews(created_at DESC);
CREATE INDEX idx_reviews_user_week ON weekly_reviews(user_id, week_number DESC);

-- RLS
ALTER TABLE weekly_reviews ENABLE ROW LEVEL SECURITY;

CREATE POLICY reviews_user_policy ON weekly_reviews
    FOR ALL
    USING (auth.uid() = (SELECT auth_user_id FROM users WHERE id = user_id));


-- ============================================
-- Monthly Analysis (Long-term Trends)
-- ============================================

CREATE TABLE IF NOT EXISTS monthly_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    month VARCHAR(7) NOT NULL,  -- "2026-02"
    
    total_sessions INT NOT NULL,
    adherence_rate FLOAT CHECK (adherence_rate BETWEEN 0 AND 100),
    
    -- Strength progress
    -- [{"movement": "back_squat", "start_value": 140, "end_value": 145, "change_pct": 3.6, "unit": "kg"}]
    strength_progress JSONB DEFAULT '[]'::JSONB,
    
    -- Conditioning progress
    -- [{"benchmark_name": "fran", "start_time": "4:32", "end_time": "4:15", "improvement_seconds": 17}]
    conditioning_progress JSONB DEFAULT '[]'::JSONB,
    
    -- Body composition
    -- {"weight_kg": {"start": 80, "end": 79.2}, "body_fat_pct": {"start": 15, "end": 14.1}}
    body_composition JSONB,
    
    -- Injury report
    -- {"injuries": [], "minor_issues": ["elbow_tweak_week3"], "days_missed": 1}
    injury_report JSONB,
    
    volume_trend VARCHAR(20) CHECK (volume_trend IN ('increasing', 'stable', 'decreasing')),
    overall_assessment TEXT NOT NULL,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ai_model_used VARCHAR(50) DEFAULT 'gemini-1.5-pro',
    
    UNIQUE(user_id, month)
);

-- Indexes
CREATE INDEX idx_analysis_user ON monthly_analysis(user_id);
CREATE INDEX idx_analysis_month ON monthly_analysis(month DESC);

-- RLS
ALTER TABLE monthly_analysis ENABLE ROW LEVEL SECURITY;

CREATE POLICY analysis_user_policy ON monthly_analysis
    FOR ALL
    USING (auth.uid() = (SELECT auth_user_id FROM users WHERE id = user_id));


-- ============================================
-- Helper Functions
-- ============================================

-- Calculate adherence rate for a week
CREATE OR REPLACE FUNCTION calculate_weekly_adherence(
    p_user_id UUID,
    p_week_start DATE,
    p_week_end DATE
) RETURNS FLOAT AS $$
DECLARE
    planned_count INT;
    completed_count INT;
BEGIN
    SELECT COUNT(*) INTO planned_count
    FROM workout_sessions
    WHERE user_id = p_user_id
      AND started_at::DATE BETWEEN p_week_start AND p_week_end;
    
    IF planned_count = 0 THEN
        RETURN 0;
    END IF;
    
    SELECT COUNT(*) INTO completed_count
    FROM workout_sessions
    WHERE user_id = p_user_id
      AND started_at::DATE BETWEEN p_week_start AND p_week_end
      AND completed_at IS NOT NULL;
    
    RETURN (completed_count::FLOAT / planned_count * 100);
END;
$$ LANGUAGE plpgsql;

-- Get average RPE for a week
CREATE OR REPLACE FUNCTION calculate_avg_rpe(
    p_user_id UUID,
    p_week_start DATE,
    p_week_end DATE
) RETURNS FLOAT AS $$
BEGIN
    RETURN (
        SELECT COALESCE(AVG(rpe_score), 7)
        FROM session_feedback
        WHERE user_id = p_user_id
          AND date BETWEEN p_week_start AND p_week_end
    );
END;
$$ LANGUAGE plpgsql;

-- Get average readiness for a week
CREATE OR REPLACE FUNCTION calculate_avg_readiness(
    p_user_id UUID,
    p_week_start DATE,
    p_week_end DATE
) RETURNS FLOAT AS $$
BEGIN
    RETURN (
        SELECT COALESCE(AVG(readiness_score), 70)
        FROM recovery_metrics
        WHERE user_id = p_user_id
          AND date BETWEEN p_week_start AND p_week_end
    );
END;
$$ LANGUAGE plpgsql;


-- ============================================
-- Views for Analysis
-- ============================================

-- Weekly performance summary view
CREATE OR REPLACE VIEW weekly_performance_summary AS
SELECT 
    ws.user_id,
    DATE_TRUNC('week', started_at::DATE) AS week_start,
    COUNT(*) AS total_sessions,
    COUNT(CASE WHEN completed_at IS NOT NULL THEN 1 END) AS completed_sessions,
    AVG(ws.duration_minutes) AS avg_duration,
    AVG(sf.rpe_score) AS avg_rpe
FROM workout_sessions ws
LEFT JOIN session_feedback sf ON ws.id = sf.session_id
GROUP BY ws.user_id, DATE_TRUNC('week', started_at::DATE);


COMMENT ON TABLE session_feedback IS 'Post-workout subjective feedback from athletes';
COMMENT ON TABLE weekly_reviews IS 'AI-generated weekly performance reviews';
COMMENT ON TABLE monthly_analysis IS 'Long-term trend analysis';
COMMENT ON FUNCTION calculate_weekly_adherence IS 'Calculate adherence % for a week';
COMMENT ON FUNCTION calculate_avg_rpe IS 'Calculate average RPE for a week';
COMMENT ON FUNCTION calculate_avg_readiness IS 'Calculate average readiness score for a week';
