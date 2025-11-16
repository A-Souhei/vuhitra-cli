-- Initialize PostgreSQL database with useful extensions for data analysis

\echo 'Creating extensions for vuhitra database...'

-- Connect to the vuhitra database
\c vuhitra;

-- Enable UUID support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for text search and similarity
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable hstore for key-value storage
CREATE EXTENSION IF NOT EXISTS hstore;

-- Enable btree_gin and btree_gist for better indexing
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Enable postgis for spatial data (if available in alpine)
-- Commented out as it requires separate installation
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- Create a sample schema for data analysis
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant permissions to the vuhitra user
GRANT ALL PRIVILEGES ON SCHEMA analytics TO vuhitra;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO vuhitra;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO vuhitra;

-- Set search path to include analytics schema
ALTER DATABASE vuhitra SET search_path TO public, analytics;

\echo 'Database initialization complete!'
\echo 'Available extensions: uuid-ossp, pg_trgm, hstore, btree_gin, btree_gist'
\echo 'Available schemas: public, analytics'
