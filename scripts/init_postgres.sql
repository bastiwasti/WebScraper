-- Initialize the webscraper schema in the jobsearch database.
-- Run once: python3 scripts/run_sql.py scripts/init_postgres.sql

CREATE SCHEMA IF NOT EXISTS webscraper;

-- Main user gets full access
GRANT ALL ON SCHEMA webscraper TO jobsearch;

-- Read-only user for PGWeb
GRANT USAGE ON SCHEMA webscraper TO jobsearch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA webscraper TO jobsearch_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA webscraper GRANT SELECT ON TABLES TO jobsearch_readonly;
