-- PostgreSQL init script for the shared vmpostgres database.
-- Runs once on first container start (docker-entrypoint-initdb.d).
-- Creates users and schemas for WebScraper (and future JobSearch migration).

-- webscraper user (full access to webscraper schema)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'webscraper') THEN
        CREATE USER webscraper WITH PASSWORD 'WEBSCRAPER_PASSWORD_PLACEHOLDER';
    END IF;
END
$$;

-- jobsearch user (full access to jobsearch schema)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'jobsearch') THEN
        CREATE USER jobsearch WITH PASSWORD 'JOBSEARCH_PASSWORD_PLACEHOLDER';
    END IF;
END
$$;

-- read-only user for PGWeb / MCP tools
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'jobsearch_readonly') THEN
        CREATE USER jobsearch_readonly WITH PASSWORD 'READONLY_PASSWORD_PLACEHOLDER';
    END IF;
END
$$;

-- webscraper schema
CREATE SCHEMA IF NOT EXISTS webscraper;
GRANT ALL ON SCHEMA webscraper TO webscraper;
GRANT USAGE ON SCHEMA webscraper TO jobsearch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA webscraper TO jobsearch_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA webscraper GRANT SELECT ON TABLES TO jobsearch_readonly;

-- jobsearch schema (pre-create for future migration)
CREATE SCHEMA IF NOT EXISTS jobsearch;
GRANT ALL ON SCHEMA jobsearch TO jobsearch;
GRANT USAGE ON SCHEMA jobsearch TO jobsearch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA jobsearch TO jobsearch_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA jobsearch GRANT SELECT ON TABLES TO jobsearch_readonly;
