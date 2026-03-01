# MCP PostgreSQL Configuration

This document describes the MCP (Model Context Protocol) setup for accessing the PostgreSQL database in WebScraper.

## Overview

The project uses an MCP server to provide database access to AI coding tools (OpenCode, Claude Code). This enables data analysis and natural language queries about the events database.

The WebScraper data lives in a `webscraper` schema inside the shared `vmpostgres` PostgreSQL database (shared with the JobSearch project).

## Configuration

### Claude Code (.mcp.json)

Location: `/home/vscode/projects/WebScraper/.mcp.json`

```json
{
  "mcpServers": {
    "webscraper_db": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres",
               "postgresql://webscraper:webscraper@localhost:5432/vmpostgres?options=-csearch_path%3Dwebscraper"]
    }
  }
}
```

### OpenCode (opencode.json)

Location: `/home/vscode/projects/WebScraper/opencode.json`

```json
{
  "mcp": {
    "webscraper_db": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-postgres",
                  "postgresql://webscraper:webscraper@localhost:5432/vmpostgres?options=-csearch_path%3Dwebscraper"],
      "enabled": true
    }
  }
}
```

**Server**: `@modelcontextprotocol/server-postgres`
**Connection**: PostgreSQL on `localhost:5432`, database `vmpostgres`, schema `webscraper`
**User**: `webscraper` (full access) or `jobsearch_readonly` (read-only)

## Available MCP Tools

| Tool | Description | Parameters |
|-------|-------------|-------------|
| `webscraper_db_read_query` | Execute SELECT queries to read data | `query`: SQL SELECT statement |
| `webscraper_db_write_query` | Execute INSERT/UPDATE/DELETE queries | `query`: SQL statement |
| `webscraper_db_list_tables` | Get a list of all tables | None |
| `webscraper_db_describe_table` | View schema information for a table | `table_name`: Name of table |
| `webscraper_db_export_query` | Export query results as CSV/JSON | `query`: SQL SELECT, `format`: "csv" or "json" |
| `webscraper_db_list_insights` | List all business insights | None |

## Database Schema

### Tables

| Table | Purpose |
|-------|---------|
| `runs` | Pipeline run tracking (agent, location, timestamp) |
| `status` | Run status with metrics (duration, event counts) |
| `events` | Structured event data (name, description, location, date, etc.) |
| `events_distinct` | Deduplicated events (best row per name+start_datetime+origin) |
| `raw_summaries` | Raw text from scraper (for debugging) |
| `locations` | Family-friendly places (Ausflüge feature) |

### Events Table

Main table containing event data:

- `id` - Primary key (SERIAL)
- `run_id` - Associated pipeline run
- `name` - Event name
- `description` - Event description
- `location` - Event location
- `start_datetime` - Event start time
- `end_datetime` - Event end time
- `category` - Event category (family, education, sport, etc.)
- `source` - Source website
- `city` - City name
- `event_url` - URL to event detail page
- `detail_scraped` - Whether detail page was fetched (0/1)
- `raw_data` - Raw JSON data
- `origin` - Data origin identifier (e.g., "leverkusen_lust_auf")

### Indexes

- `idx_events_start_datetime` - For time-based queries
- `idx_events_end_datetime` - For time-based queries
- `idx_events_category` - For category filtering
- `idx_events_run_id` - For run-based queries

## Usage Examples

### Ask natural language questions

```
Show me events happening this weekend in Monheim
```

```
How many events are in the database for each city?
```

```
List all family events in Leverkusen sorted by date
```

### Direct SQL queries

```
Use webscraper_db_read_query to find events in the 'sport' category
```

```
Show me the database schema for the events table using webscraper_db_describe_table
```

### Export data

```
Export all events from this week as CSV using webscraper_db_export_query
```

## Multi-Project Setup

The `vmpostgres` database is shared between projects:

| Schema | Project | Tables |
|--------|---------|--------|
| `webscraper` | WebScraper | events, events_distinct, runs, status, raw_summaries, locations |
| `jobsearch` | JobSearch | jobs, scrape_runs, alembic_version |

Both schemas are visible in PGWeb at `localhost:8080`.

## Security

- **Shared database**: Both projects use the same PostgreSQL instance (port 5432)
- **Schema isolation**: Each project has its own schema
- **Read-only user**: `jobsearch_readonly` has SELECT-only access to both schemas
- **Credentials**: Connection uses `webscraper` user with password authentication

## Troubleshooting

### MCP server not loading

```bash
# Test the MCP server manually
npx -y @modelcontextprotocol/server-postgres "postgresql://webscraper:webscraper@localhost:5432/vmpostgres?options=-csearch_path%3Dwebscraper"
```

### Database connection failed

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection
psql -h localhost -U jobsearch -d vmpostgres -c "SET search_path TO webscraper; SELECT COUNT(*) FROM events;"
```

### Schema not found

```bash
# Run the init script
psql -h localhost -U webscraper -d vmpostgres -f scripts/init_postgres.sql
```

## Resources

- [MCP Documentation](https://opencode.ai/docs/mcp-servers/)
- [MCP Postgres Server](https://github.com/modelcontextprotocol/server-postgres)
- [OpenCode Config](https://opencode.ai/docs/config/)
