"""Orchestrates the two-agent pipeline: Scraper -> Analyzer, and stores events in DB."""

from agents import ScraperAgent, AnalyzerAgent
from storage import insert_events, insert_raw_summary, create_run, update_run_status_analyzed, create_run_status

def run_pipeline(
    location: str = "",
    max_search: int = 8,
    fetch_urls: int = 3,
    model: str | None = None,
    base_url: str | None = None,
    save_to_db: bool = True,
    cities: list[str] | None = None,
    search_queries: list[str] | None = None,
    full_run: bool = False,
) -> tuple[str, list[dict]]:
    """
    Run the full pipeline:
    1. Scraper: search + fetch (events in region) -> raw event summary text
    2. Analyzer: raw text -> structured event list (name, description, location, date, time, source)
    3. Save events to SQLite (for automation and display)

    Returns:
        (raw_summary, structured_events)
    """
    from config import DEFAULT_LOCATION

    loc = location or DEFAULT_LOCATION

    scraper = ScraperAgent(model=model, base_url=base_url)
    analyzer = AnalyzerAgent(model=model, base_url=base_url)

    raw_summary, url_metrics, city_event_counts = scraper.run(
        location=loc,
        max_search=max_search,
        fetch_urls=fetch_urls,
        cities=cities,
        search_queries=search_queries,
    )

    scraper_run_id = None
    raw_summary_id = None
    if save_to_db:
        scraper_run_id = create_run("scraper", loc)
        raw_summary_id = insert_raw_summary(loc, max_search, fetch_urls, raw_summary, scraper_run_id, cities=cities, search_queries=search_queries)

    structured_events = analyzer.run(raw_summary, scraper_run_id=scraper_run_id if save_to_db else None, url_metrics=url_metrics if save_to_db else None)
    
    analyzer_run_id = None
    if save_to_db and structured_events:
        from storage import update_run_status_analyzed
        if full_run:
            analyzer_run_id = scraper_run_id
            valid_events = 0
            for e in structured_events:
                if e.get("name") and e.get("date") and e.get("location") and e.get("source"):
                    valid_events += 1
            update_run_status_analyzed(analyzer_run_id, len(structured_events), valid_events, linked_run_id=raw_summary_id)
        else:
            analyzer_run_id = create_run("analyzer", loc, raw_summary_id)
            create_run_status(analyzer_run_id, [])
            valid_events = 0
            for e in structured_events:
                if e.get("name") and e.get("date") and e.get("location") and e.get("source"):
                    valid_events += 1
            update_run_status_analyzed(analyzer_run_id, len(structured_events), valid_events, linked_run_id=scraper_run_id)
        insert_events(structured_events, analyzer_run_id)

    return raw_summary, structured_events
