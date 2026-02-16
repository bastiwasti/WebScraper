# WebScraper Documentation Index

This directory contains all documentation for WebScraper project, organized with a numbered naming convention for easy reference.

---

## File Naming Convention

All documentation files follow a format: `{number}_{name}.md`

| Prefix | Number | Purpose | File |
|---------|---------|----------|--------|
| 00_ | 00 | Entry point | 00_readme.md, 00_DOCUMENTATION_INDEX.md |
| 01_ | 01 | Core guides | 01_agent_guide.md, 01_setup_guide.md |
| 10_ | 10 | Architecture & Internals (category) | See below |
| &nbsp;&nbsp;| 11 | Architecture | 11_architecture.md |
| &nbsp;&nbsp;| 12 | Console print documentation | 12_consoleprint.md |
| &nbsp;&nbsp;| 13 | Cron job setup | 13_cron_setup.md |
| 14_ | 14 | Data models & systems | 14_categories.md |
| 99_ | 99 | Historical reference | 99_agent_errors.md |

---

## Documentation Files

### 00_readme.md
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

## docs/ Directory

### docs/00_url_setup_prompt.md
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

## Reading Order

If you're new to project:

1. Start with **00_readme.md** - Quick start and basic usage
2. Then **docs/00_url_setup_prompt.md** - For URL setup (provide full URL + city name)
3. Then **01_setup_guide.md** - If you want to add new city scrapers with detailed guidance
4. Then **01_agent_guide.md** - To understand how agents work in detail
5. Refer to **11_architecture.md** - For deep system understanding
6. Check **14_categories.md** - For category system reference
7. Check **13_cron_setup.md** - For setting up automated daily scraping
8. Check **99_agent_errors.md** - Only for debugging specific historical issues

---

## Quick Reference

| Task | File |
|-------|--------|
| Get started | 00_readme.md |
| URL setup (user provides URL) | docs/00_url_setup_prompt.md |
| Add new city (guided) | 01_setup_guide.md |
| Understand agents | 01_agent_guide.md |
| Understand system | 11_architecture.md |
| Console output | 12_consoleprint.md |
| Setup cron jobs | 13_cron_setup.md |
| Category system | 14_categories.md |
| Debug errors | 99_agent_errors.md |

---

## Documentation Structure

```
WebScraper/
├── docs/
│   └── 00_url_setup_prompt.md  # URL setup prompt (user provides URL + city)
├── 00_DOCUMENTATION_INDEX.md  # This file (documentation index)
├── 00_readme.md            # Entry point and quick start
├── 01_agent_guide.md        # Agent guide (scraper + analyzer)
├── 01_setup_guide.md        # City scraper setup guide
├── 11_architecture.md       # System architecture
├── 12_consoleprint.md       # Console output documentation
├── 13_cron_setup.md        # Cron job configuration
├── 14_categories.md        # Category system documentation
├── 99_agent_errors.md       # Historical error log
├── config.py
├── main.py
├── pipeline.py
├── storage.py
├── requirements.txt
├── agents/                 # Agent implementations
├── rules/                  # URL rules and scrapers
│   └── cities/            # City-specific scrapers
├── data/                  # Database storage
└── logs/                  # Timestamped logs
```
