# WebScraper Documentation Index

This directory contains all documentation for WebScraper project, organized with a numbered naming convention for easy reference.

---

## File Naming Convention

All documentation files follow a format: `{number}_{name}.md`

| Prefix | Number | Purpose | File |
|---------|---------|----------|--------|
| 00_ | 00 | Entry point | README.md (root), 00_DOCUMENTATION_INDEX.md, 00_url_setup_prompt.md |
| 01_ | 01 | Core guides | 01_agent_guide.md, 01_setup_guide.md |
| 10_ | 10 | Architecture & Internals (category) | See below |
| &nbsp;&nbsp;| 11 | Architecture | 11_architecture.md |
| &nbsp;&nbsp;| 12 | Console print documentation | 12_consoleprint.md |
| &nbsp;&nbsp;| 13 | Cron job setup | 13_cron_setup.md |
| 14_ | 14 | Data models & systems | 14_categories.md |
| 20_ | 20 | Implementation notes | 20_rausgegangen_implementation.md |
| 30_ | 30 | City implementation plans | 30_leverkusen_implementation_plan.md |
| 40_ | 40 | Configuration & Integration | 40_mcp_postgres_setup.md |
| 50_ | 50 | Standalone Features | 50_locations_feature.md |
| 99_ | 99 | Historical reference | 99_agent_errors.md |

---

## Documentation Files

### README.md (root directory)
**Purpose:** Main entry point and quick start guide
**For:** New users getting started with project

**Contents:**
- Quick start (installation, configuration, running)
- CLI options and usage
- Supported cities
- Project structure overview
- Database schema
- Tech stack

---

## 00_ Entry & Reference

### 00_DOCUMENTATION_INDEX.md
**Purpose:** This file - documentation index and navigation
**For:** Finding specific documentation files

---

## 01_ Core Guides

**Purpose:** Step-by-step guides for development and setup

**For:** Developers learning the system and adding new features

### 01_agent_guide.md
**Purpose:** Comprehensive guide for both scraper and analyzer agents
**For:** Developers working on or extending agent functionality

**Contents:**
- Scraper agent workflow and components
- Analyzer agent workflow and components
- URL rules system
- Adding new event sources
- LLM integration (DeepSeek)
- Performance optimization
- Debugging tips
- Base class reference

---

### 01_setup_guide.md
**Purpose:** Step-by-step guide for adding new city scrapers
**For:** Developers adding new event sources to system

**Contents:**
- Directory structure for city scrapers
- Required files per URL (scraper.py, regex.py)
- URL configuration (rules/urls.py)
- Date filtering requirements (14 days)
- Navigation patterns (Load More, pagination, calendar)
- Data fields to extract
- Regex patterns (primary extraction method)
- Complete working examples

**IMPORTANT:** All scrapers MUST implement navigation to load 14 days of events from webpage.

---

## docs/ Directory Reference Files

### 00_url_setup_prompt.md
**Purpose:** Complete prompt for setting up new event scrapers from user-provided URL
**For:** Users/AI systems implementing new event sources

**Contents:**
- Required information from user (full URL + city name)
- 7 proven implementation patterns from existing scrapers
- Pattern detection logic (REST API, Static HTML, Dynamic HTML, etc.)
- Template-based implementation workflow
- URL registration in `rules/urls.py`
- Testing strategy (module imports, single URL, field validation)
- Self-correction loop (3 attempts maximum)
- Common issues and fixes
- Implementation checklist (before, during, after)
- Success criteria
- Reference examples from working scrapers

**Usage:** This is the PRIMARY prompt for URL setup - user provides full URL + city name, system handles everything else.

**Patterns Available:**
1. REST API (JSON) - Fastest, use if API endpoint available
2. Static HTML (Basic) - Fast, plain HTML parsing
3. Static HTML + 2-Level - Medium speed, richer data from detail pages
4. Dynamic HTML + Load More - Slowest, JavaScript required
5. Static HTML + Pagination - Medium speed, URL-based pagination
6. 2-Level with URL Extraction - Medium speed, detail page scraping
7. Custom HTML Parsing - Most flexible, non-standard structures

---

## 10 Architecture & Internals

**Category:** Deep dive into system architecture, components, and technical internals

### 11_architecture.md
**Purpose:** Deep system reference for internals
**For:** Developers understanding system design and data flow

**Contents:**
- System overview and core components
- Pipeline flow (scraper → analyzer)
- Component architecture
- Data models (Event, RuleEntry)
- Agent communication
- Database schema (tables, relationships)
- LLM integration details
- Error handling strategies
- Performance characteristics
- Extensibility guidelines

---

### 12_consoleprint.md
**Purpose:** Documentation of console output system
**For:** Developers understanding Rich library usage and output patterns

**Contents:**
- Rich library basics
- Color coding conventions
- Print output types (tables, progress bars, status messages)
- Table structure and column management
- Adding new columns
- Live progress tracking
- Debugging print statements

---

### 13_cron_setup.md
**Purpose:** Cron job configuration for daily automatic event scraping
**For:** System administrators setting up automated scraping

**Contents:**
- Crontab entries for daily scraping (3:00 AM CET)
- Log rotation configuration (30-day retention)
- System timezone settings
- Log file locations and format
- Troubleshooting commands
- Modification examples (change run time, log retention, cities)

**Note:** This feature is production-ready and active.

---

## 14 Data Models & Systems

**Category:** Data structures, utilities, and system components

### 14_categories.md
**Purpose:** Centralized category management system
**For:** Developers understanding category inference and normalization

**Contents:**
- 10 standardized categories (family, education, sport, culture, market, festival, adult, community, nature, other)
- Category inference with priority-based matching
- Category normalization (aliases to standard IDs)
- Date and time normalization utilities
- Helper functions (get_all_categories, is_valid_category, get_category_name)
- Usage examples for scrapers
- Testing strategies
- Migration guide for updating scrapers

**Note:** All scrapers use this centralized system for consistent categorization.

---

## 20 Implementation Notes

**Category:** Implementation details for specific aggregators and components

### 20_rausgegangen_implementation.md
**Purpose:** Documentation of rausgegangen.de aggregator implementation
**For:** Developers understanding the hybrid scraping approach

**Contents:**
- Hybrid approach (Level 1 + Level 2)
- Directory structure
- Scraper implementation details
- Performance optimization strategies

---

## 30 City Implementation Plans

**Category:** City-specific implementation plans and strategies

### 30_leverkusen_implementation_plan.md
**Purpose:** Implementation plan for Leverkusen city scraper
**For:** Developers implementing new city scrapers based on Leverkusen pattern

**Contents:**
- URL structure and navigation
- Data extraction strategy
- Implementation timeline
- Testing approach

---

## 40 Configuration & Integration

**Category:** OpenCode configuration and MCP integration

### 40_mcp_postgres_setup.md
**Purpose:** MCP configuration for PostgreSQL database access (Claude Code + OpenCode)
**For:** Developers using AI tools to query the events database

**Contents:**
- MCP server configuration (PostgreSQL, webscraper schema)
- Available database tools
- Usage examples (natural language queries, SQL queries, exports)
- Multi-project setup (webscraper + jobsearch schemas)
- Security and troubleshooting

**Note:** Database schema details are now in [docs/80_database_schema.md](80_database_schema.md).

---

## 50 Features

**Category:** Standalone features beyond the events pipeline

### 50_locations_feature.md
**Purpose:** Locations/Ausflüge feature — family-friendly places within 30km of Monheim
**For:** Users and developers working with the locations discovery and maintenance system

**Contents:**
- CLI commands (discover, list, stats, check-urls)
- Location categories (playground, museum, park, garden, zoo, pool, sport, etc.)
- Data sources (Overpass API, manual seed file, future Google Places)
- Database schema (locations table)
- MCP query examples
- Discovery pipeline flow
- Maintenance (URL health checking)
- File structure and configuration

**Note:** Completely independent from the events pipeline. Locations are permanent places, not time-bound events.

---

## 99 Historical Reference

**Category:** Historical logs and error tracking

### 99_agent_errors.md
**Purpose:** Historical error log from development
**For:** Debugging and understanding past issues

**Contents:**
- Chronological error log (#001 - #014)
- Error context and root cause
- Attempted solutions
- Status (resolved/open)
- Lessons learned and prevention strategies

**Note:** This is a historical reference. Most issues are resolved.

---

## docs/autonomous/ Directory

**Purpose:** Autonomous execution logs and investigation reports
**For:** Debugging, understanding agent decisions, and tracking implementation history

### Autonomous Logs (2x_*)
Format: `2x_{city}_autonomous_{timestamp}.md`
- Monheim: `2x_monheim_autonomous_2026-02-26T19:34:50.md`
- Burscheid: `2x_burscheid_autonomous_2026-02-16T22:23:28.md`
- Leichlingen: `2x_leichlingen_autonomous_2026-02-16T20:41:00.md`
- Hitdorf: `2x_hitdorf_autonomous_2026-02-16T19:32:53.md`

**Contents:**
- Task info (URL, city name)
- Pattern detected
- Files created
- Testing results
- Issues encountered
- Solutions applied

### Investigation Reports (investigation_*)
Format: `investigation_{city}.md`
- `investigation_monheim.md`
- `investigation_burscheid.md`

**Contents:**
- URL under investigation
- HTML structure analysis
- Data sources identified
- Event card structure
- Navigation patterns
- Implementation recommendations

---

## Reading Order

If you're new to the project:

1. **README.md** (root) — Quick start and basic usage
2. **docs/00_url_setup_prompt.md** — How to add new event sources (provide URL + city name)
3. **docs/01_agent_guide.md** — How the scraper and analyzer agents work
4. **docs/11_architecture.md** — Deep system architecture reference
5. **docs/80_database_schema.md** — Complete database documentation

Everything else is reference material — consult as needed.

---

## Quick Reference

| Task | File |
|-------|--------|
| Get started | README.md (root) |
| Add new event source | docs/00_url_setup_prompt.md |
| Add new city (detailed) | docs/01_setup_guide.md |
| Understand agents | docs/01_agent_guide.md |
| System architecture | docs/11_architecture.md |
| Console output | docs/12_consoleprint.md |
| Cron jobs | docs/13_cron_setup.md |
| Category system | docs/14_categories.md |
| MCP Postgres setup | docs/40_mcp_postgres_setup.md |
| Locations feature | docs/50_locations_feature.md |
| Debug errors | docs/99_agent_errors.md |
| Autonomous logs | docs/autonomous/ |

---

## Documentation Structure

```
WebScraper/
├── README.md                   # Main entry point and quick start
├── docs/
│   ├── 00_DOCUMENTATION_INDEX.md  # This file (documentation index)
│   ├── 00_url_setup_prompt.md     # URL setup prompt
│   ├── 01_agent_guide.md          # Agent guide (scraper + analyzer)
│   ├── 01_setup_guide.md          # City scraper setup guide
│   ├── 11_architecture.md         # System architecture
│   ├── 12_consoleprint.md         # Console output documentation
│   ├── 13_cron_setup.md          # Cron job configuration
│   ├── 14_categories.md          # Category system documentation
│   ├── 20_rausgegangen_implementation.md  # Rausgegangen implementation
│   ├── 30_leverkusen_implementation_plan.md  # Leverkusen implementation plan
│   ├── 40_mcp_postgres_setup.md          # MCP PostgreSQL configuration
│   ├── 50_locations_feature.md           # Locations/Ausflüge feature
│   ├── 99_agent_errors.md         # Historical error log
│   └── autonomous/               # Autonomous execution logs
│       ├── 2x_monheim_autonomous_2026-02-26T19:34:50.md
│       ├── 2x_burscheid_autonomous_2026-02-16T22:23:28.md
│       ├── 2x_leichlingen_autonomous_2026-02-16T20:41:00.md
│       ├── 2x_hitdorf_autonomous_2026-02-16T19:32:53.md
│       ├── investigation_monheim.md
│       └── investigation_burscheid.md
├── config.py
├── main.py
├── pipeline.py
├── storage.py
├── requirements.txt
├── agents/                 # Agent implementations
├── rules/                  # URL rules and scrapers
│   └── cities/            # City-specific scrapers
├── scripts/               # Database scripts
└── logs/                  # Timestamped logs
```
