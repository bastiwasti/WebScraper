# MCP Configuration Cleanup Report

**Date:** 2026-03-01  
**Project:** WebScraper  

---

## ✅ Completed Changes

### 1. Project MCP Configuration (`.mcp.json`)

**File:** `/home/vscode/projects/WebScraper/.mcp.json`

**Changed connection string from:**
```
postgresql://jobsearch:jobsearch@localhost:5432/vmpostgres?options=-csearch_path%3Dwebscraper
```

**To:**
```
postgresql://webscraper:webscraper@localhost:5432/vmpostgres?options=-csearch_path%3Dwebscraper
```

### 2. Python Configuration (`config.py`)

**File:** `/home/vscode/projects/WebScraper/config.py:30-31`

**Changed defaults from:**
```python
PG_USER = os.getenv("PG_USER", "jobsearch")
PG_PASSWORD = os.getenv("PG_PASSWORD", "jobsearch")
```

**To:**
```python
PG_USER = os.getenv("PG_USER", "webscraper")
PG_PASSWORD = os.getenv("PG_PASSWORD", "webscraper")
```

### 3. PostgreSQL Setup

**Actions completed:**
- ✅ Created PostgreSQL user `webscraper` with password `webscraper`
- ✅ Granted USAGE on `webscraper` schema
- ✅ Granted ALL PRIVILEGES on all tables in `webscraper` schema
- ✅ Granted ALL PRIVILEGES on all sequences in `webscraper` schema
- ✅ Set default privileges for future tables/sequences
- ✅ Granted CONNECT on `vmpostgres` database

**Preserved:**
- ✅ `jobsearch` user and schema remain intact for the JobSearch project

### 4. Connection Verification

**Test results:**
- ✅ Connection successful with `webscraper:webscraper` credentials
- ✅ Schema access: `webscraper`
- ✅ Tables in schema: 6
  - `events` (14,211 rows)
  - `events_distinct`
  - `locations`
  - `raw_summaries`
  - `runs`
  - `status`

---

## ⚠️ JobSearch MCP (Requires Manual Action)

### Current Situation

The following MCP tools are still available and connected to the `jobsearch` schema:
- `jobsearch-db_query_jobs`
- `jobsearch-db_get_job_stats`
- `jobsearch-db_search_jobs`
- `jobsearch-db_get_scrape_runs`

**These tools are configured at the system level and cannot be modified from this project.**

### How to Disable

#### Option 1: VSCode / Claude Code Settings

1. Open VSCode settings:
   - `Cmd/Ctrl + Shift + P` → "Preferences: Open Settings (JSON)"
   - Or edit: `~/.config/Code/User/settings.json`

2. Add MCP server configuration to disable jobsearch:
   ```json
   {
     "mcp.servers": {
       "jobsearch": {
         "enabled": false
       }
     }
   }
   ```
   *(Note: Exact syntax depends on the MCP server implementation)*

3. Restart VSCode / Claude Code to apply changes

#### Option 2: Claude Desktop Settings (if applicable)

1. Open Claude Desktop settings
2. Navigate to "MCP Servers" section
3. Find the `jobsearch` server entry
4. Disable or remove it
5. Restart Claude Desktop

#### Option 3: Environment Variables

If the MCP server is configured via environment variables:

```bash
# Unset jobsearch MCP configuration
unset MCP_JOBSERVER_ENABLED
unset MCP_JOBSERVER_URL
```

### Verification

After disabling, verify by checking available MCP tools:
- ✅ `webscraper_db_query` should still work
- ❌ `jobsearch-db_*` tools should be gone

---

## 📊 Current MCP Status

### Active MCP Server

**Name:** `webscraper_db`  
**Database:** `vmpostgres` / `webscraper` schema  
**Credentials:** `webscraper:webscraper`  
**Connection String:** `postgresql://webscraper:webscraper@localhost:5432/vmpostgres?options=-csearch_path%3Dwebscraper`

**Available Tools:**
- `webscraper_db_query` - Execute SQL queries on webscraper schema

### System-Level MCP (To be Disabled)

**Name:** `jobsearch-db`  
**Database:** `vmpostgres` / `jobsearch` schema  
**Credentials:** `jobsearch:jobsearch` (preserved for JobSearch project)  
**Status:** Still active, needs manual disable

---

## 🔒 Security Notes

### WebScraper Project
- Now uses dedicated `webscraper` user with limited scope
- Only has access to `webscraper` schema
- Cannot access `jobsearch` schema data

### JobSearch Project (Preserved)
- `jobsearch` user and credentials remain unchanged
- `jobsearch` schema and data remain intact
- Project continues to function normally

---

## 📝 Files Changed

| File | Status |
|------|--------|
| `.mcp.json` | ✅ Updated connection string |
| `config.py` | ✅ Updated default credentials |
| `storage.py` | No changes (uses config defaults) |
| `scripts/migrate_sqlite_to_postgres.py` | No changes (uses config defaults) |

---

## ✅ Checklist

- [x] Update `.mcp.json` connection string
- [x] Update `config.py` default credentials
- [x] Create PostgreSQL user `webscraper`
- [x] Grant permissions on `webscraper` schema
- [x] Test connection with new credentials
- [ ] Disable `jobsearch` MCP server (manual action required)
- [ ] Verify `jobsearch-db-*` tools are no longer available
- [ ] Restart VSCode/Claude Code to apply MCP changes

---

## 📞 Next Steps

1. **Disable JobSearch MCP** using the instructions above
2. **Restart** VSCode or Claude Code to apply MCP changes
3. **Verify** only `webscraper_db_query` tool is available
4. **Test** WebScraper pipeline to ensure database operations work:
   ```bash
   python main.py --cities monheim_am_rhein --no-db --verbose
   ```

---

**End of Report**
