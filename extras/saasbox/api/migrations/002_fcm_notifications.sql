-- FCM Push Notification Tables Migration
-- Version: 002
-- Date: 2026-01-16
-- Description: Add tables for FCM push notification support
-- Reference: FCM_NOTIFICATION_PLAN.md, ENTERPRISE_ROADMAP.md Phase 5

-- ============================================================================
-- PUSH TOKENS TABLE
-- Stores FCM registration tokens per user device
-- ============================================================================
CREATE TABLE IF NOT EXISTS push_tokens (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    device_type VARCHAR(20) NOT NULL CHECK (device_type IN ('android', 'ios', 'web')),
    device_id VARCHAR(100) NOT NULL,  -- Client-generated UUID for device
    app_version VARCHAR(20),
    is_valid BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT unique_user_device UNIQUE (user_id, device_id)
);

-- Indexes for push_tokens
CREATE INDEX IF NOT EXISTS ix_push_tokens_user ON push_tokens(user_id);
CREATE INDEX IF NOT EXISTS ix_push_tokens_valid ON push_tokens(is_valid) WHERE is_valid = TRUE;

COMMENT ON TABLE push_tokens IS 'FCM push token registration per user device';
COMMENT ON COLUMN push_tokens.device_id IS 'Client-generated UUID for device';
COMMENT ON COLUMN push_tokens.is_valid IS 'Set to False when FCM returns NOT_FOUND/UNREGISTERED';


-- ============================================================================
-- NOTIFICATION PREFERENCES TABLE
-- User notification settings
-- ============================================================================
CREATE TABLE IF NOT EXISTS notification_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,

    -- Global settings
    push_enabled BOOLEAN DEFAULT TRUE,
    quiet_hours_enabled BOOLEAN DEFAULT FALSE,
    quiet_hours_start TIME,  -- e.g., 22:00
    quiet_hours_end TIME,    -- e.g., 08:00

    -- Per-category settings (all default to TRUE)
    favorite_staging_enabled BOOLEAN DEFAULT TRUE,
    favorite_results_enabled BOOLEAN DEFAULT TRUE,
    poll_notifications_enabled BOOLEAN DEFAULT TRUE,
    prediction_results_enabled BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Index for notification_preferences
CREATE INDEX IF NOT EXISTS ix_notification_preferences_user ON notification_preferences(user_id);

COMMENT ON TABLE notification_preferences IS 'User notification preferences per category';
COMMENT ON COLUMN notification_preferences.push_enabled IS 'Global toggle - disables all opt-outable notifications';
COMMENT ON COLUMN notification_preferences.favorite_staging_enabled IS 'Notify when favorite racer is within 5 heats';
COMMENT ON COLUMN notification_preferences.favorite_results_enabled IS 'Notify when favorite racer heat completes';


-- ============================================================================
-- NOTIFICATION LOG TABLE
-- Delivery logging for debugging and audit (retained 30 days)
-- ============================================================================
CREATE TABLE IF NOT EXISTS notification_log (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(20),  -- Nullable for topic-based notifications
    notification_type VARCHAR(50) NOT NULL,
    event_id VARCHAR(20),
    payload JSONB,
    fcm_message_id VARCHAR(100),
    status VARCHAR(20) NOT NULL CHECK (status IN ('sent', 'failed', 'skipped')),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Indexes for notification_log
CREATE INDEX IF NOT EXISTS ix_notification_log_user ON notification_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_notification_log_status ON notification_log(status, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_notification_log_event ON notification_log(event_id, created_at DESC);

COMMENT ON TABLE notification_log IS 'Notification delivery log for debugging (retained 30 days)';
COMMENT ON COLUMN notification_log.payload IS 'Notification content (title, body, data) - PII-safe only';


-- ============================================================================
-- UPDATE USER_FAVORITES TABLE
-- Add notification tracking timestamps
-- ============================================================================
ALTER TABLE user_favorites
    ADD COLUMN IF NOT EXISTS last_staging_notified_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS last_result_notified_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN user_favorites.last_staging_notified_at IS 'Last staging notification sent for this favorite';
COMMENT ON COLUMN user_favorites.last_result_notified_at IS 'Last result notification sent for this favorite';


-- ============================================================================
-- Optional: Add FCM topics tracking to users table
-- (Uncomment if needed - topic subscriptions can also be managed client-side)
-- ============================================================================
-- ALTER TABLE users
--     ADD COLUMN IF NOT EXISTS fcm_topics JSONB DEFAULT '[]';
-- COMMENT ON COLUMN users.fcm_topics IS 'FCM topic subscriptions, e.g., ["event_evt_abc123"]';


-- ============================================================================
-- CLEANUP FUNCTION: Delete old notification logs (30 days retention)
-- Run via scheduled job/cron
-- ============================================================================
CREATE OR REPLACE FUNCTION cleanup_old_notification_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM notification_log
    WHERE created_at < NOW() - INTERVAL '30 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_notification_logs() IS 'Delete notification logs older than 30 days';


-- ============================================================================
-- Grant permissions to app role (if using RLS)
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON push_tokens TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON notification_preferences TO app_user;
GRANT SELECT, INSERT ON notification_log TO app_user;
GRANT USAGE, SELECT ON SEQUENCE push_tokens_id_seq TO app_user;
GRANT USAGE, SELECT ON SEQUENCE notification_preferences_id_seq TO app_user;
GRANT USAGE, SELECT ON SEQUENCE notification_log_id_seq TO app_user;
