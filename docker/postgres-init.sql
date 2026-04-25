-- docker/postgres-init.sql
-- Additional initialization for the parking database

-- Ensure the parking database exists (created by POSTGRES_DB env var,
-- but this script runs after that)

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Note: Tables will be created by Alembic migrations, not here.
-- This file is for extensions and any pre-migration setup.
