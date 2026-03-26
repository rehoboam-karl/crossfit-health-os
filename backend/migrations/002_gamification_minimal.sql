-- Migration: Add Gamification Fields (Minimal)
-- For Supabase - adds columns to existing tables

-- Add onboarding fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS primary_goal VARCHAR(20) DEFAULT 'both';
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_time VARCHAR(20) DEFAULT 'morning';
ALTER TABLE users ADD COLUMN IF NOT EXISTS baseline_readiness INTEGER DEFAULT 70;

-- Note: Run the full migration in Supabase dashboard or via psql
-- See: 002_gamification.sql for complete schema
