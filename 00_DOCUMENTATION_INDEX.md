# WebScraper Documentation Index

This directory contains all documentation for the WebScraper project, organized with a numbered naming convention for easy reference.

---

## File Naming Convention

All documentation files follow the format: `{number}_{name}.md`

| Prefix | Number | Purpose | File |
|---------|---------|----------|--------|
| 00_ | 00 | Entry point | 00_readme.md |
| 10_ | 10 | Agent guide | 10_agent_guide.md |
| 20_ | 20 | Setup guide | 20_setup_guide.md |
| 30_ | 30 | Architecture | 30_architecture.md |
| 99_ | 99 | Error log | 99_agent_errors.md |

---

## Documentation Files

### 00_readme.md
**Purpose**: Main entry point and quick start guide
**For**: New users getting started with project

**Contents**:
- Quick start (installation, configuration, running)
- CLI options and usage
- Supported cities
- Project structure overview
- Database schema
- Tech stack
- **2-Level Scraping** (see 90_ToDo_Scraper.md)

### 10_agent_guide.md
**Purpose**: Comprehensive guide for both scraper and analyzer agents
**For**: Developers working on or extending agent functionality

**Contents**:
- Scraper agent workflow and components
- Analyzer agent workflow and components
- URL rules system
- Adding new event sources
- LLM integration (DeepSeek)
- Performance optimization
- Debugging tips
- Base class reference

### 20_setup_guide.md
**Purpose**: Step-by-step guide for adding new city scrapers
**For**: Developers adding new event sources to the system

**Contents**:
- Directory structure for city scrapers
- Required files per URL (scraper.py, regex.py)
- URL configuration (rules/urls.py)
- Date filtering requirements (14 days)
- Navigation patterns (Load More, pagination, calendar)
- Data fields to extract
- Regex patterns (primary extraction method)
- Complete working examples

**IMPORTANT**: All scrapers MUST implement navigation to load 14 days of events from the webpage.

### 30_architecture.md
**Purpose**: Deep system reference for internals
**For**: Developers understanding system design and data flow

**Contents**:
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

### 99_agent_errors.md
**Purpose**: Historical error log from development
**For**: Debugging and understanding past issues

**Contents**:
- Chronological error log (#001 - #014)
- Error context and root cause
- Attempted solutions
- Status (resolved/open)
- Lessons learned and prevention strategies

**Note**: This is a historical reference. Most issues are resolved.

---

## Reading Order

If you're new to the project:

1. Start with **00_readme.md** - Quick start and basic usage
2. Then **20_setup_guide.md** - If you want to add new city scrapers
3. Then **10_agent_guide.md** - To understand how agents work in detail
4. Refer to **30_architecture.md** - For deep system understanding
5. Check **99_agent_errors.md** - Only for debugging specific historical issues

---

## Quick Reference

| Task | File |
|-------|--------|
| Get started | 00_readme.md |
| Add new city | 20_setup_guide.md |
| Understand agents | 10_agent_guide.md |
| Understand system | 30_architecture.md |
| Debug errors | 99_agent_errors.md |

---

## Documentation Structure

```
WebScraper/
├── 00_readme.md           # Entry point
├── 10_agent_guide.md       # Agent guide (scraper + analyzer)
├── 20_setup_guide.md       # City scraper setup guide
├── 30_architecture.md       # System architecture
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
