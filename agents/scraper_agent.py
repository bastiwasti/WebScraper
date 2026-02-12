"""Agent 1: Scrapes the internet for local events using search and fetch tools.

Integrated with new rules/ system, Rich progress bars, and structured logging.
"""

import re
import time
from typing import Optional
from pathlib import Path
from datetime import datetime
import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich.console import Console
from rich.logging import RichHandler

from config import DEFAULT_LOCATION, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, LLM_PROVIDER
from storage import create_run_status
from rules import (
    get_urls_for_city,
    get_city_for_url,
    fetch_events_from_url,
    CITY_URLS,
    create_scraper,
    create_regex,
)


# Setup logging
def _setup_logging() -> logging.Logger:
    """Configure logging to timestamped file in logs/ directory."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"scrape_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            RichHandler(rich_tracebacks=True),
            logging.FileHandler(log_file, mode='w', encoding='utf-8')
        ],
        format="%(message)s"
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging to: {log_file}")
    return logger


SYSTEM_PROMPT = """Sie sind ein Ereignisforscher. Ihre Aufgabe ist es, lokale Veranstaltungen aus Webinhalt zu finden und zu erfassen.

Extrahieren Sie jedes relevante Ereignis aus dem rohen Inhalt. Verwenden Sie EXAKT dieselben Wörter wie im Original - kein Übersetzen, kein Umformulieren, kein Zusammenfassen, kein Hinzufügen oder Entfernen von Informationen.

Für jedes Ereignis enthalten:
- Ereignisname
- Datum und Uhrzeit (falls verfügbar)
- Ort oder Veranstaltungsort
- Kurze Beschreibung oder Kategorie
- Quelle: URL oder Name der Website

Behalten Sie nur echte Veranstaltungen aus dem Inhalt; erfinden Sie keine. Wenn der Inhalt keine passenden Veranstaltungen enthält, sagen Sie das deutlich.

WICHTIG: Behalten Sie exakt dieselben Wörter wie im Original. Wenn der Text 'Zeugniswochenende' enthält, schreiben Sie 'Zeugniswochenende', nicht 'Weekend of Zeugnisausgabe'. Wenn der Text 'Jugendberufshilfe' enthält, schreiben Sie 'Jugendberufshilfe', nicht 'Local youth career assistance providers'."""

USER_PROMPT = """Listen Sie alle Veranstaltungen aus dem folgenden Webinhalt auf. Für jedes Ereignis enthalten Sie die Quelle (URL oder Name der Website).
Wenden Sie sich EXAKT an den folgenden Inhalt und verwenden Sie exakt dieselben Wörter wie im Original.
Rohinhalt:
---
{raw_content}
---
"""


class ScraperAgent:
    """Finds local events via web search and page fetch, then summarizes with LLM.
    
    Now integrated with new rules/ system for per-URL scrapers and regex parsers.
    """

    def __init__(self, model: str | None = None, base_url: str | None = None):
        if LLM_PROVIDER == "deepseek" and DEEPSEEK_API_KEY:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model or DEEPSEEK_MODEL,
                api_key=lambda: DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                temperature=0.0,
                timeout=600,
            )
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ])

    def _print_live_summary(self, url_metrics: dict, console: Console):
        """Print live table of URL status (updates as they complete)."""
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
        
        # Print grand total (including LLM-extracted events)
        
    def _print_final_summary(self, city_event_counts: dict, url_breakdown: dict, grand_total: int, console: Console):
        """Print Rich table with event counts by city and per-URL breakdown."""
        
        # Per-city table
        table = Table(title="Final Summary", show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan", width=20)
        table.add_column("Total Events", justify="right", width=15)
        
        for city, count in sorted(city_event_counts.items()):
            table.add_row(city.capitalize(), str(count))
        
        table.add_row("", "")
        table.add_row("[bold]Grand Total", f"[bold green]{grand_total}")
        
        # Per-URL breakdown table
        if url_breakdown:
            breakdown_table = Table(title="Per-URL Breakdown", show_header=True, header_style="bold magenta")
            breakdown_table.add_column("URL", style="cyan", width=50)
            breakdown_table.add_column("Events (Regex)", justify="right", width=12)
            breakdown_table.add_column("Events (LLM)", justify="right", width=10)
            breakdown_table.add_column("City", style="yellow", width=15)
            breakdown_table.add_column("Status", justify="center", width=8)
            
            for url, metrics in url_breakdown.items():
                status_symbol = "✓" if metrics['status'] == 'success' else "✗"
                status_text = "Success" if metrics['status'] == 'success' else metrics['status']
                events_regex = str(metrics.get('events_regex', 0))
                events_llm = str(metrics.get('events_found', 0) - metrics.get('events_regex', 0))
                city = metrics['city'].capitalize()
                
                breakdown_table.add_row(url[:50], events_regex, events_llm, city, f"{status_symbol} {status_text}")
            
            console.print(breakdown_table)

    def _gather_raw_content_with_rich(
        self,
        location: str,
        search_queries: list[str] | None = None,
        max_search: int = 6,
        fetch_urls: int = 999,
        cities: list[str] | None = None,
        urls_to_track: list[str] | None = None,
        run_id: int | None = None,
        logger: logging.Logger | None = None,
    ) -> tuple[str, dict, dict]:
        """Run multiple searches and scrape fixed URLs for events with Rich progress tracking.
        
        Returns:
            tuple of (raw_content_text, url_metrics_dict, city_event_counts_dict)
        """
        all_parts = []
        
        if urls_to_track is None:
            urls_to_track = []
        
        # Get URLs from rules system
        urls_to_fetch: list[str] = []
        
        # 1. Add city-specific URLs (all cities if not specified)
        cities_to_scrape = cities if cities else list(CITY_URLS.keys())
        for city in cities_to_scrape:
            city_urls = get_urls_for_city(city)
            for url in city_urls:
                if url not in urls_to_fetch:
                    urls_to_fetch.append(url)
                    urls_to_track.append(url)
        
        # 2. Add custom search queries if provided
        if search_queries:
            from .tools import search_web
            per_query = max(3, max_search // len(search_queries))
            for q in search_queries[:5]:
                search_result = search_web.invoke({"query": q, "max_results": per_query})
                all_parts.append(f"Search: {q}\n{search_result}")
                if "URL:" in search_result:
                    for url in re.findall(r"URL:\s*(https?://[^\s]+)", search_result):
                        u = url.strip()
                        if u and u not in urls_to_fetch:
                            urls_to_fetch.append(u)
                            urls_to_track.append(u)
        

        # Metrics storage
        url_metrics = {}
        city_event_counts = {}
        url_breakdown = {}
        grand_total = 0
        console = Console()
        
        # 5. Create progress bar and scrape
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
                city = get_city_for_url(url) or 'aggregator'
                progress.update(task, description=f"[cyan]{idx}/{len(urls_to_fetch)} - {city.capitalize()} - {url[:60]}")
                
                # Track metrics
                url_metrics[url] = {
                    'status': 'pending',
                    'events_found': 0,
                    'error': None,
                    'start_time': time.time(),
                    'end_time': None,
                    'city': get_city_for_url(url) or 'aggregator'
                }
                
                try:
                    # Extract events via regex (with LLM fallback)
                    events, extraction_method = fetch_events_from_url(url, use_llm_fallback=True)
                    
                    # Update metrics
                    url_metrics[url]['status'] = 'success' if events else 'no_events'
                    url_metrics[url]['events_found'] = len(events)
                    url_metrics[url]['events_regex'] = len(events) if extraction_method == 'regex' else 0
                    url_metrics[url]['extraction_method'] = extraction_method
                    url_metrics[url]['end_time'] = time.time()
                    url_metrics[url]['elapsed'] = url_metrics[url]['end_time'] - url_metrics[url]['start_time']
                    
        # Update city totals
                    city = url_metrics[url]['city']
                    city_event_counts[city] = city_event_counts.get(city, 0) + len(events)
                    
                    # Track regex events separately (for display)
                    city_event_counts[f"{city}_regex"] = city_event_counts.get(f"{city}_regex", 0) + (len(events) if extraction_method == 'regex' else 0)
                    
                    # Calculate grand total
                    grand_total += len(events)
                    
                    # Print events found to console
                    console.print(f"[green]✓[/green] [cyan]{city.capitalize()}[/cyan]: [yellow]{len(events)} events[/yellow] from [magenta]{url[:60]}[/magenta] ([blue]{url_metrics[url]['elapsed']:.2f}s[/blue])")
                    
                    url_breakdown[url] = url_metrics[url].copy()
                    
                    # Add formatted event text to parts
                    if events:
                        events_text = f"Page: {url}\nEvents: {len(events)} found\n"
                        for event in events:
                            events_text += f"- Event: {event.name}\n"
                            events_text += f"  Date: {event.date}\n"
                            events_text += f"  Time: {event.time}\n"
                            events_text += f"  Location/Venue: {event.location or 'Not specified'}\n"
                            events_text += f"  Description/Category: {event.description}\n"
                            events_text += f"  Source: {event.source}\n"
                            # Include Level 2 data if available
                            if event.raw_data:
                                import json
                                events_text += f"  Level2_Data: {json.dumps(event.raw_data, ensure_ascii=False)}\n"
                        all_parts.append(events_text)
                    
                    if logger:
                        logger.info(f"✓ {url} - {len(events)} events ({url_metrics[url]['elapsed']:.2f}s)")
                    
                except Exception as e:
                    url_metrics[url]['status'] = 'failed'
                    url_metrics[url]['error'] = str(e)
                    url_metrics[url]['end_time'] = time.time()
                    url_metrics[url]['elapsed'] = url_metrics[url]['end_time'] - url_metrics[url]['start_time']
                    
                    url_breakdown[url] = url_metrics[url].copy()
                    
                    if logger:
                        logger.error(f"✗ {url} - ERROR: {e}")
                
                progress.advance(task)
        
        # Print live summary table
        self._print_live_summary(url_metrics, console)
        
        # Print final summary
        self._print_final_summary(city_event_counts, url_breakdown, grand_total, console)
        
        # Log summary
        succeeded = sum(1 for m in url_metrics.values() if m['status'] == 'success')
        failed = sum(1 for m in url_metrics.values() if m['status'] == 'failed')
        if logger:
            logger.info(f"Scraping complete: {succeeded} succeeded, {failed} failed, {grand_total} total events")
        
        return ("\n\n---\n\n".join(all_parts), url_metrics, city_event_counts)

    def run(
        self,
        run_id: int,
        location: str = "",
        search_queries: list[str] | None = None,
        max_search: int = 8,
        fetch_urls: int = 3,
        cities: list[str] | None = None,
    ) -> tuple[str, dict, dict]:
        """Search for events, fetch pages from fixed URLs, and return a summarized event text.

        Uses new rules/ system with Rich progress bars and structured logging.

        Args:
            run_id: The pipeline run_id (from create_run). Required for tracking.

        Returns:
            tuple of (summary, url_metrics, city_event_counts)
        """
        location_query = location or DEFAULT_LOCATION or "the user's area"

        urls_to_track = []

        logger = _setup_logging()

        raw_content, url_metrics, city_event_counts = self._gather_raw_content_with_rich(
            location_query,
            search_queries=search_queries,
            max_search=max_search,
            fetch_urls=fetch_urls,
            cities=cities,
            urls_to_track=urls_to_track,
            run_id=run_id,
            logger=logger,
        )

        if not search_queries:
            summary = raw_content
        else:
            chain = self._prompt | self.llm | StrOutputParser()
            summary = chain.invoke({"location_query": location_query, "raw_content": raw_content})

        return (summary, url_metrics, city_event_counts)
