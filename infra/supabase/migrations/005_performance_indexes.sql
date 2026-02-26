-- Migration: 005_performance_indexes
-- Description: Add indexes for frequently queried columns to improve performance
-- Date: 2026-02-26

-- Index: users table - auth_user_id lookup (used on every authenticated request)
CREATE INDEX IF NOT EXISTS idx_users_auth_user_id
ON users(auth_user_id);

-- Index: weekly_schedules - user_id + active (used to fetch active schedule)
CREATE INDEX IF NOT EXISTS idx_weekly_schedules_user_active
ON weekly_schedules(user_id, active)
WHERE active = true;

-- Index: recovery_metrics - user_id + date descending (used for latest recovery data)
CREATE INDEX IF NOT EXISTS idx_recovery_metrics_user_date
ON recovery_metrics(user_id, date DESC);

-- Index: workout_sessions - user_id + started_at descending (used for session history)
CREATE INDEX IF NOT EXISTS idx_workout_sessions_user_started
ON workout_sessions(user_id, started_at DESC);

-- Index: workout_sessions - user_id + completed_at (used for filtering completed sessions)
CREATE INDEX IF NOT EXISTS idx_workout_sessions_user_completed
ON workout_sessions(user_id, completed_at DESC)
WHERE completed_at IS NOT NULL;

-- Index: personal_records - user_id + movement_name (used for PR lookups)
CREATE INDEX IF NOT EXISTS idx_personal_records_user_movement
ON personal_records(user_id, movement_name);

-- Index: biomarker_readings - user_id + test_date descending (used for biomarker history)
CREATE INDEX IF NOT EXISTS idx_biomarker_readings_user_date
ON biomarker_readings(user_id, test_date DESC);

-- Index: weekly_reviews - user_id + week_number (used for review lookups)
CREATE INDEX IF NOT EXISTS idx_weekly_reviews_user_week
ON weekly_reviews(user_id, week_number);

-- Index: session_feedback - user_id + date (used for feedback retrieval)
CREATE INDEX IF NOT EXISTS idx_session_feedback_user_date
ON session_feedback(user_id, date DESC);

-- Index: workout_templates - methodology + workout_type + difficulty_level
-- (used by adaptive engine to select templates)
CREATE INDEX IF NOT EXISTS idx_workout_templates_selection
ON workout_templates(methodology, workout_type, difficulty_level)
WHERE is_public = true;

-- Partial index: workout_templates - user-created templates
CREATE INDEX IF NOT EXISTS idx_workout_templates_user
ON workout_templates(created_by_coach_id)
WHERE is_public = false;

-- Comments for documentation
COMMENT ON INDEX idx_users_auth_user_id IS 'Fast lookup for JWT authentication';
COMMENT ON INDEX idx_weekly_schedules_user_active IS 'Quick retrieval of active schedule per user';
COMMENT ON INDEX idx_recovery_metrics_user_date IS 'Optimized for latest recovery metrics query';
COMMENT ON INDEX idx_workout_sessions_user_started IS 'Fast session history retrieval';
COMMENT ON INDEX idx_workout_sessions_user_completed IS 'Partial index for completed sessions only';
COMMENT ON INDEX idx_personal_records_user_movement IS 'Fast PR lookups by movement';
COMMENT ON INDEX idx_biomarker_readings_user_date IS 'Optimized biomarker history queries';
COMMENT ON INDEX idx_weekly_reviews_user_week IS 'Fast weekly review retrieval';
COMMENT ON INDEX idx_session_feedback_user_date IS 'Optimized feedback queries';
COMMENT ON INDEX idx_workout_templates_selection IS 'Adaptive engine template selection';
COMMENT ON INDEX idx_workout_templates_user IS 'User-created template lookups';

-- Analyze tables to update statistics for query planner
ANALYZE users;
ANALYZE weekly_schedules;
ANALYZE recovery_metrics;
ANALYZE workout_sessions;
ANALYZE personal_records;
ANALYZE biomarker_readings;
ANALYZE weekly_reviews;
ANALYZE session_feedback;
ANALYZE workout_templates;
