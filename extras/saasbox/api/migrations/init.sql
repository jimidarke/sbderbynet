-- SoapboxDerbyNet SaaS API - Database Initialization
-- This script runs when the PostgreSQL container starts for the first time

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create application role for RLS
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user;
    END IF;
END
$$;

-- Grant permissions
GRANT CONNECT ON DATABASE soapboxderbynet TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;

-- Function to set current organization for RLS
CREATE OR REPLACE FUNCTION set_current_org(org_id TEXT)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.current_org_id', org_id, false);
END;
$$ LANGUAGE plpgsql;

-- Function to get current organization for RLS policies
CREATE OR REPLACE FUNCTION current_org_id()
RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('app.current_org_id', true);
END;
$$ LANGUAGE plpgsql STABLE;

-- Note: Actual table creation is handled by Alembic migrations
-- This file only sets up extensions and functions needed for RLS

-- Example RLS policy (applied after table creation via migration):
-- ALTER TABLE events ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY tenant_isolation_events ON events
--     USING (org_id = current_org_id() OR current_org_id() IS NULL);
