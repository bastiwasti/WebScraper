"""Orchestrates two-agent pipeline: Scraper -> Analyzer, and stores events in DB."""

from agents import ScraperAgent, AnalyzerAgent
from storage import insert_events, insert_raw_summary, create_run, update_run_status_analyzed, create_run_status, append_to_agent, update_run_status_complete
from rules import Event


def run_pipeline(
    location: str = "",
    max_search: int = 8,
    model: str | None = None,
    base_url: str | None = None,
    save_to_db: bool = True,
    cities: list[str] | None = None,
    search_queries: list[str] | None = None,
    full_run: bool = False,
    urls: list[str] | None = None,
) -> tuple[str, list[dict]]:
    """
    Run full pipeline with incremental saving:
    1. Scraper: fetches URLs one at a time
    2. Analyzer: processes each URL's events
    3. Save to DB immediately after each URL (incremental)
    
    Args:
        urls: Explicit list of URLs to scrape. If provided, overrides cities parameter.
    
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

    # Initialize tracking variables
    url_metrics = {}
    city_event_counts = {}
    all_structured_events = []
    success_count = 0
    error_count = 0
    total_events_saved = 0
    total_regex_events = 0
    
    # Initialize run status
    if save_to_db:
        create_run_status(run_id, [], full_run=full_run, start_time=start_time, events_regex=0)
    
    # Process URLs incrementally - scrape, analyze, save after each URL
    for url, events, extraction_method, url_metric in scraper.scrape_urls_incrementally(
        run_id=run_id,
        location=loc,
        max_search=max_search,
        cities=cities,
        search_queries=search_queries,
        urls=urls,
    ):
        url_metrics[url] = url_metric
        
        # Track city totals
        city = url_metric.get('city', 'unknown')
        city_event_counts[city] = city_event_counts.get(city, 0) + len(events)
        
        # Track regex events separately
        if extraction_method == 'regex':
            city_event_counts[f"{city}_regex"] = city_event_counts.get(f"{city}_regex", 0) + len(events)
            total_regex_events += len(events)
        
        if extraction_method == 'error':
            error_count += 1
            continue
        
        try:
            # Analyze events from this URL
            structured_events = analyzer.analyze_events(events, url_metrics)
            
            # Save events immediately with per-URL transaction
            if save_to_db and structured_events:
                events_saved = insert_events(structured_events, run_id)
                total_events_saved += events_saved
                success_count += 1
            
            # Accumulate all events for final return
            all_structured_events.extend(structured_events)
            
        except Exception as e:
            error_count += 1
            print(f"ERROR processing events from {url}: {e}")
            continue
    
    # Append "analyzer" to agent column
    if save_to_db and all_structured_events:
        append_to_agent(run_id, "analyzer")
    
    # Calculate totals
    events_found = len(all_structured_events)
    valid_events = sum(1 for e in all_structured_events if e.get("name") and e.get("date") and e.get("location") and e.get("source"))
    
    # Track LLM events (events structured by analyzer)
    llm_events_total = valid_events
    
    # Update status with cumulative totals
    if save_to_db:
        update_run_status_analyzed(
            run_id,
            events_found,
            valid_events,
            events_regex=total_regex_events,
            events_llm=llm_events_total,
            linked_run_id=None,
        )
    
    # Generate raw summary for backward compatibility
    raw_summary_parts = []
    for url, metric in url_metrics.items():
        if metric['status'] == 'success':
            raw_summary_parts.append(f"Page: {url}\nEvents: {metric['events_found']} found")
    
    raw_summary = "\n\n---\n\n".join(raw_summary_parts)
    
    # Track pipeline end time
    end_time = datetime.utcnow().isoformat() + "Z"
    update_run_status_complete(run_id, end_time=end_time)
    
    # Print summary
    print(f"\nPipeline complete:")
    print(f"  URLs processed: {len(url_metrics)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {error_count}")
    print(f"  Total events saved: {total_events_saved}")
    print(f"  Total events in memory: {events_found}")
    
    return raw_summary, all_structured_events
