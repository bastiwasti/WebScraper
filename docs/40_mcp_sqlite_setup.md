# OpenCode MCP SQLite Configuration

This document describes the MCP (Model Context Protocol) setup for accessing the SQLite database in WebScraper.

## Overview

The project uses an MCP server to provide read-only database access to OpenCode. This enables faster data analysis and natural language queries about the events database.

## Configuration

Location: `/home/vscode/projects/WebScraper/opencode.json`

### MCP Server

```json
"mcp": {
  "webscraper_db": {
    "type": "local",
    "command": ["npx", "-y", "@executeautomation/database-server", "data/events.db"],
    "enabled": true
  }
}
```

**Server**: `@executeautomation/database-server`
**Package Source**: https://github.com/executeautomation/mcp-database-server
**Database Path**: `data/events.db` (relative to project root)

### Read-Only Access

Write operations are globally disabled to prevent accidental data modification:

```json
"tools": {
  "webscraper_db_write_query": false,
  "webscraper_db_create_table": false,
  "webscraper_db_alter_table": false,
  "webscraper_db_drop_table": false,
  "webscraper_db_append_insight": false
}
```

## Available MCP Tools

Only read-only tools are available:

| Tool | Description | Parameters |
|-------|-------------|-------------|
| `webscraper_db_read_query` | Execute SELECT queries to read data | `query`: SQL SELECT statement |
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
| `raw_summaries` | Raw text from scraper (for debugging) |
| `city_coordinates` | City coordinates (lat/lng) for distance calculations |
| `city_road_distances` | Road distances between cities |

### Events Table

Main table containing event data:

- `id` - Primary key
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

### Indexes

- `idx_events_start_datetime` - For time-based queries
- `idx_events_end_datetime` - For time-based queries
- `idx_events_category` - For category filtering
- `idx_events_run_id` - For run-based queries
- `idx_events_dedup` - For deduplication (name, location, start_datetime, created_at)

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

## Global Usage

This configuration is in the project root, making it available when working in this directory. For other repositories using SQLite:

1. Copy `opencode.json` to the other project root
2. Update the database path: `"command": ["npx", "-y", "@executeautomation/database-server", "your/database.db"]`

## Security

- **Read-only**: All write operations are disabled
- **Local-only**: Database is accessed directly from the filesystem
- **No credentials**: No username/password required for SQLite

## Troubleshooting

### MCP server not loading

```bash
# Test the MCP server manually
npx -y @executeautomation/database-server data/events.db
```

### Database not found

Ensure the `data/events.db` file exists:

```bash
ls -la data/events.db
```

If the database doesn't exist, run the scraper first:

```bash
python main.py --cities monheim --no-db --verbose
```

### Tools not available in prompts

Add `use` keyword to your prompt:

```
Show me all sport events. Use webscraper_db tools.
```

## Resources

- [MCP Documentation](https://opencode.ai/docs/mcp-servers/)
- [MCP Database Server](https://github.com/executeautomation/mcp-database-server)
- [OpenCode Config](https://opencode.ai/docs/config/)
