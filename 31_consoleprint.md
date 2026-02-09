# Console Print Statement Documentation

This document describes the console output system used in WebScraper, including Rich library usage, print patterns, and how to modify output tables.

## Table of Contents

- [Overview](#overview)
- [Rich Library](#rich-library)
- [Color Coding Conventions](#color-coding-conventions)
- [Print Output Types](#print-output-types)
- [Table Structure](#table-structure)
- [Adding New Columns](#adding-new-columns)
- [Live Progress Tracking](#live-progress-tracking)
- [Examples](#examples)

---

## Overview

WebScraper uses the **Rich library** for formatted console output, providing:
- Colored text and status indicators
- Progress bars with time estimates
- Structured tables with aligned columns
- Live-updating status displays

**Primary Files**:
- `agents/scraper_agent.py` - Scraper output tables and progress
- `agents/analyzer_agent.py` - Analyzer progress messages
- `main.py` - CLI output and run listings
- `pipeline.py` - Pipeline coordination output

---

## Rich Library

### Installation

```bash
pip install rich
```

### Basic Usage

```python
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

# Create console instance
console = Console()

# Print colored text
console.print("[green]Success![/green]")
console.print("[cyan]City:[/cyan] [bold]Berlin[/bold]")

# Print tables
table = Table(title="My Table")
table.add_column("Name", style="cyan")
table.add_column("Count", justify="right")
table.add_row("Events", "42")
console.print(table)
```

---

## Color Coding Conventions

| Color | Usage | Example |
|-------|-------|---------|
| `[green]` | Success, completed items | `✓`, `[green]Success[/green]` |
| `[red]` | Errors, failed items | `✗`, `[red]Error[/red]` |
| `[cyan]` | City names, headers | `[cyan]Berlin[/cyan]` |
| `[yellow]` | Event counts, warnings | `[yellow]42 events[/yellow]` |
| `[magenta]` | URLs, emphasized text | `[magenta]https://example.com[/magenta]` |
| `[blue]` | Time durations, metadata | `[blue]1.23s[/blue]` |
| `[bold]` | Important text, totals | `[bold]Grand Total[/bold]` |

**Status Symbols**:
- `✓` - Success (green)
- `✗` - Failed (red)
- `→` - In progress (yellow)

---

## Print Output Types

### 1. URL Status Table

**Location**: `agents/scraper_agent.py:101-118`

Displays live status of each URL being scraped:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━┓
┃ URL                                        ┃ Status  ┃ Events ┃ Time  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━┩
│ https://example.com/events                │ ✓       │ 15     │ 2.34s │
│ https://another.com                        │ ✗       │ 0      │ 0.12s │
└────────────────────────────────────────────┴─────────┴────────┴───────┘
```

**Code**:
```python
def _print_live_summary(self, url_metrics: dict, console: Console):
    table = Table(title="URL Status", show_header=True, header_style="bold magenta")
    table.add_column("URL", style="cyan", width=50)
    table.add_column("Status", justify="center", width=8)
    table.add_column("Events", justify="right", width=8)
    table.add_column("Time", justify="right", width=8)
    
    for url, metrics in url_metrics.items():
        status = "✓" if metrics['status'] == 'success' else "✗"
        events = str(metrics['events_found'])
        time_str = f"{metrics['elapsed']:.2f}s"
        
        status_style = "green" if metrics['status'] == 'success' else "red"
        
        table.add_row(url[:50], f"[{status_style}]{status}", events, time_str)
    
    console.print(table)
```

### 2. Final Summary Table

**Location**: `agents/scraper_agent.py:122-152`

Displays per-city event counts and grand total:

```
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Category              ┃ Total Events    ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ Berlin                │ 150             │
│ Munich                │ 75              │
│                      │                 │
│ Grand Total           │ 225             │
└──────────────────────┴─────────────────┘
```

**Code**:
```python
def _print_final_summary(self, city_event_counts: dict, url_breakdown: dict, grand_total: int, console: Console):
    table = Table(title="Final Summary", show_header=True, header_style="bold magenta")
    table.add_column("Category", style="cyan", width=20)
    table.add_column("Total Events", justify="right", width=15)
    
    for city, count in sorted(city_event_counts.items()):
        table.add_row(city.capitalize(), str(count))
    
    table.add_row("", "")
    table.add_row("[bold]Grand Total", f"[bold green]{grand_total}")
    
    console.print(table)
```

### 3. Per-URL Breakdown Table

**Location**: `agents/scraper_agent.py:136-152`

Detailed breakdown of each URL with events and status:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━━━┓
┃ URL                                        ┃ Evts ┃ City  ┃ Status ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━━━┩
│ https://example.com/events                │ 15   │ Berlin │ ✓ Success │
│ https://another.com                        │ 0    │ Munich │ ✗ Failed │
└────────────────────────────────────────────┴──────┴───────┴────────┘
```

**With Regex/LLM Columns** (Updated Version):
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━┓
┃ URL                                        ┃ Regex ┃ LLM   ┃ City   ┃ Status ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━┩
│ https://example.com/events                │ 12    │ 10    │ Berlin │ ✓      │
│ https://another.com                        │ 0     │ 0     │ Munich │ ✗      │
└────────────────────────────────────────────┴───────┴───────┴────────┴────────┘
```

### 4. Live Progress Bar

**Location**: `agents/scraper_agent.py:210-216`

Shows real-time scraping progress:

```
Scraping URLs... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45% (9/20) [00:12<00:15]
```

**Code**:
```python
with Progress(
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    TextColumn("({task.completed}/{task.total})"),
    TimeRemainingColumn(),
    console=console
) as progress:
    task = progress.add_task("[cyan]Scraping URLs...", total=len(urls_to_fetch))
    
    for idx, url in enumerate(urls_to_fetch, 1):
        progress.update(task, description=f"[cyan]{idx}/{len(urls_to_fetch)} - {city}")
        # ... scraping logic ...
        progress.advance(task)
```

### 5. Console Status Messages

**Location**: `agents/scraper_agent.py:255`

Live updates per URL:

```
✓ Berlin: 15 events from https://example.com/events (2.34s)
✗ Munich: 0 events from https://another.com (0.12s)
```

**Code**:
```python
console.print(
    f"[green]✓[/green] [cyan]{city.capitalize()}[/cyan]: "
    f"[yellow]{len(events)} events[/yellow] from "
    f"[magenta]{url[:60]}[/magenta] ([blue]{elapsed:.2f}s[/blue])"
)
```

---

## Table Structure

### Creating a Basic Table

```python
from rich.table import Table

table = Table(
    title="My Table",           # Optional title
    show_header=True,           # Show column headers
    header_style="bold magenta", # Style for headers
    show_lines=False            # Show horizontal lines
)

# Add columns
table.add_column("Name", style="cyan", width=20, justify="left")
table.add_column("Count", style="yellow", width=10, justify="right")

# Add rows
table.add_row("Item 1", "42")
table.add_row("Item 2", "100")

# Print table
console.print(table)
```

### Column Options

| Parameter | Type | Description |
|-----------|------|-------------|
| `header` | str | Column header text |
| `style` | str | Rich style for column (e.g., `"cyan"`, `"bold"`) |
| `width` | int | Fixed column width |
| `justify` | str | Text alignment: `"left"`, `"center"`, `"right"`, `"full"` |
| `overflow` | str | Overflow handling: `"fold"`, `"crop"`, `"ellipsis"` |

### Row Options

```python
# Simple row
table.add_row("Value 1", "Value 2")

# Styled cells (using Rich markup)
table.add_row("[green]✓[/green] Success", "[bold]42[/bold]")

# Empty cells
table.add_row("", "")
```

---

## Adding New Columns

### Step 1: Define the Column

Add a new column to your table definition:

```python
table = Table(title="Per-URL Breakdown", show_header=True, header_style="bold magenta")
table.add_column("URL", style="cyan", width=50)
table.add_column("Events (Regex)", justify="right", width=12)  # NEW
table.add_column("Events (LLM)", justify="right", width=10)      # NEW
table.add_column("City", style="yellow", width=15)
table.add_column("Status", justify="center", width=8)
```

### Step 2: Prepare Data Structure

Update your data structure to track the new values:

```python
url_metrics = {
    'https://example.com': {
        'events_regex': 12,  # NEW
        'events_llm': 10,    # NEW
        'city': 'Berlin',
        'status': 'success'
    }
}
```

### Step 3: Add Data to Table

Update the row addition to include the new columns:

```python
for url, metrics in url_breakdown.items():
    status_symbol = "✓" if metrics['status'] == 'success' else "✗"
    events_regex = str(metrics.get('events_regex', 0))  # NEW
    events_llm = str(metrics.get('events_llm', 0))      # NEW
    city = metrics['city'].capitalize()
    
    table.add_row(
        url[:50],
        events_regex,          # NEW
        events_llm,            # NEW
        city,
        f"{status_symbol} Success" if metrics['status'] == 'success' else f"{status_symbol} {metrics['status']}"
    )
```

### Step 4: Print the Table

```python
console.print(table)
```

---

## Live Progress Tracking

### Progress Bar Components

| Component | Description |
|-----------|-------------|
| `TextColumn` | Description text (e.g., "Scraping URLs...") |
| `BarColumn` | Visual progress bar |
| `TextColumn` | Percentage display |
| `TextColumn` | Completed/total count |
| `TimeRemainingColumn` | Estimated time remaining |

### Updating Progress

```python
# Update description
progress.update(task, description=f"[cyan]{idx}/{total} - Processing")

# Advance progress
progress.advance(task)

# Update progress to specific value
progress.update(task, completed=5)

# Update total dynamically
progress.update(task, total=new_total)
```

---

## Examples

### Example 1: Simple Status Table

```python
from rich.console import Console
from rich.table import Table

console = Console()
table = Table(title="System Status")
table.add_column("Component", style="cyan")
table.add_column("Status", justify="center")
table.add_column("Response Time", justify="right")

table.add_row("Database", "[green]✓ Online[/green]", "0.02s")
table.add_row("API", "[green]✓ Online[/green]", "0.15s")
table.add_row("Cache", "[red]✗ Offline[/red]", "N/A")

console.print(table)
```

### Example 2: Colored Progress Messages

```python
from rich.console import Console

console = Console()

# Success message
console.print("[green]✓[/green] Scraping completed successfully")

# Error message
console.print("[red]✗[/red] Failed to fetch URL: [magenta]https://example.com[/magenta]")

# Info message with count
console.print(f"[cyan]Processed:[/cyan] [yellow]{count} events[/yellow] in [blue]{elapsed:.2f}s[/blue]")
```

### Example 3: Two-Column Event Display

```python
table = Table(title="Event Extraction Results")
table.add_column("URL", style="cyan", width=50)
table.add_column("Events (Regex)", justify="right", width=15)
table.add_column("Events (LLM)", justify="right", width=12)

for url, data in url_data.items():
    table.add_row(
        url[:50],
        str(data['regex_count']),
        str(data['llm_count'])
    )

console.print(table)
```

---

## Common Patterns

### Check if extraction was regex-based

```python
# In your scraper, track extraction method
events, extraction_method = fetch_events_from_url(url)

if extraction_method == 'regex':
    regex_count += len(events)
else:
    llm_count += len(events)
```

### Aggregate counts by city

```python
city_counts = {
    'Berlin': {'regex': 50, 'llm': 30},
    'Munich': {'regex': 25, 'llm': 20}
}

total_regex = sum(data['regex'] for data in city_counts.values())
total_llm = sum(data['llm'] for data in city_counts.values())
```

### Handle missing data gracefully

```python
events_regex = metrics.get('events_regex', 0)
events_llm = metrics.get('events_llm', 0)

table.add_row(url, str(events_regex), str(events_llm), city, status)
```

---

## Debugging Print Statements

### Verbose Mode

Enable verbose output with `--verbose` flag:

```bash
python main.py --agent all --verbose
```

### Log Files

All output is also logged to timestamped files in `logs/` directory:

```bash
ls logs/
# scrape_2026-02-09_14-30-15.log
```

### Custom Debug Prints

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Starting scraping...")
logger.error(f"Failed to fetch {url}: {error}")
logger.debug(f"Found {len(events)} events")
```

---

## References

- **Rich Documentation**: https://rich.readthedocs.io/
- **Rich GitHub**: https://github.com/Textualize/rich
- **Related Files**:
  - `agents/scraper_agent.py` - Scraper print statements
  - `agents/analyzer_agent.py` - Analyzer print statements
  - `main.py` - CLI print statements
