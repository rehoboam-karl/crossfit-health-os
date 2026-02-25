-- Add Google Calendar refresh token to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_calendar_refresh_token TEXT;

-- Index for quick lookup
CREATE INDEX IF NOT EXISTS idx_users_gcal_connected 
  ON users (id) WHERE google_calendar_refresh_token IS NOT NULL;
