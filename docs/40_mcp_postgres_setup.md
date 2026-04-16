# MCP PostgreSQL Configuration

This document describes the MCP (Model Context Protocol) setup for accessing the PostgreSQL database in WebScraper.

## Overview

The project uses an MCP server to provide database access to AI coding tools (Claude Code, OpenCode). This enables data analysis and natural language queries about the events database.

The WebScraper data lives in a `webscraper` schema inside the shared `vmpostgres` PostgreSQL database.

**Architecture**: PostgreSQL runs in Docker on the Docker host (`192.168.178.160:5432`). The dev VM (`192.168.178.192`) can reach it directly over the local network — no SSH tunnel needed.

## Configuration

### Claude Code (.mcp.json)

Location: `/home/sebastian/projects/WebScraper/.mcp.json`

```json
{
  "mcpServers": {
    "webscraper_db": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres",
               "postgresql://webscraper:webscraper@192.168.178.160:5432/vmpostgres?options=-csearch_path%3Dwebscraper"]
    }
  }
}
```

### OpenCode (opencode.json)

Location: `/home/sebastian/projects/WebScraper/opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "webscraper_db": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-postgres",
                  "postgresql://webscraper:webscraper@192.168.178.160:5432/vmpostgres?options=-csearch_path%3Dwebscraper"],
      "enabled": true
    }
  }
}
```

**Server**: `@modelcontextprotocol/server-postgres`
**Connection**: PostgreSQL on `192.168.178.160:5432`, database `vmpostgres`, schema `webscraper`
**User**: `webscraper`

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

### Tables Overview

| Table | Purpose | Records |
|-------|---------|---------|
| `events` | Raw scraped events (with duplicates) | 108,874 |
| `events_distinct` | Deduplicated unique events | 12,627 |
| `event_ratings` | Agent ratings (references events_distinct.id) | 3,271 |
| `runs` | Pipeline run tracking | 187 |
| `status` | Run status with metrics | 149 |
| `raw_summaries` | Raw text from scraper (for debugging) | 19 |
| `locations` | Family-friendly places (Ausflüge feature) | 2,021 |

**IMPORTANT**: Complete database documentation including relationships, indexes, and query patterns is available in [docs/80_database_schema.md](80_database_schema.md).

**Critical Relationship**:
- `event_ratings.event_id` references `events_distinct.id`, NOT `events.id`
- IDs are independent between `events` and `events_distinct`
- Always use `events_distinct` for rating queries

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
- **Credentials**: MCP connection uses `webscraper` user (full access to `webscraper` schema)
- **Network**: PostgreSQL is only accessible within the local network (not exposed externally)

## Troubleshooting

### MCP server not loading

```bash
# Test the MCP server manually
npx -y @modelcontextprotocol/server-postgres "postgresql://webscraper:webscraper@192.168.178.160:5432/vmpostgres?options=-csearch_path%3Dwebscraper"
```

### Database connection failed

```bash
# Check TCP connectivity to Docker host
nc -zv 192.168.178.160 5432

# Test connection (if psql available)
psql -h 192.168.178.160 -U webscraper -d vmpostgres -c "SET search_path TO webscraper; SELECT COUNT(*) FROM events;"
```

### Schema not found

```bash
# Run the init script (connect to Docker host)
psql -h 192.168.178.160 -U webscraper -d vmpostgres -f scripts/init_postgres.sql
```

## Resources

- [MCP Documentation](https://opencode.ai/docs/mcp-servers/)
- [MCP Postgres Server](https://github.com/modelcontextprotocol/server-postgres)
- [OpenCode Config](https://opencode.ai/docs/config/)
