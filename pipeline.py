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
    Run full pipeline:
    1. Scraper: search + fetch (events in region) -> raw event summary text
    2. Analyzer: raw text -> structured event list (name, description, location, date, time, source)
    3. Save events to SQLite (for automation and display)

    Returns:
        (raw_summary, structured_events)
    """
    from config import DEFAULT_LOCATION
    from datetime import datetime
    from storage import (
        create_run,
        insert_raw_summary,
        create_run_status,
        append_to_agent,
        update_run_status_complete,
        update_run_status_analyzed,
        insert_events,
    )

    loc = location or DEFAULT_LOCATION

    scraper = ScraperAgent(model=model, base_url=base_url)
    analyzer = AnalyzerAgent(model=model, base_url=base_url)

    # Create single run_id for the entire pipeline
    run_id = create_run(
        agent="scraper",
        cities=cities,
    )

    # Track pipeline start time
    start_time = datetime.utcnow().isoformat() + "Z"
    
    raw_summary, url_metrics, city_event_counts = scraper.run(
        location=loc,
        max_search=max_search,
        fetch_urls=fetch_urls,
        cities=cities,
        search_queries=search_queries,
        run_id=run_id,
    )
    
    if save_to_db:
        create_run_status(run_id, [], full_run=False, start_time=start_time)

    raw_summary_id = None
    if save_to_db:
        raw_summary_id = insert_raw_summary(loc, max_search, fetch_urls, raw_summary, run_id, cities=cities, search_queries=search_queries)

    structured_events = analyzer.run(
        run_id=run_id,
        raw_event_text=raw_summary,
        scraper_run_id=raw_summary_id,
        save_to_db=save_to_db,
        chunk_size=3,
        max_chars=5000,
        url_metrics=url_metrics if save_to_db else None,
    )

    # Append "analyzer" to agent column
    if save_to_db and structured_events:
        append_to_agent(run_id, "analyzer")

        # Calculate totals
        events_found = len(structured_events)
        valid_events = 0
        for e in structured_events:
            if e.get("name") and e.get("date") and e.get("location") and e.get("source"):
                valid_events += 1

        # Update status with ADD (not REPLACE)
        update_run_status_analyzed(
            run_id,
            events_found,
            valid_events,
            linked_run_id=raw_summary_id,
        )
        insert_events(structured_events, run_id)

        # Track pipeline end time
        end_time = datetime.utcnow().isoformat() + "Z"
        update_run_status_complete(run_id, end_time=end_time)

    return raw_summary, structured_events
