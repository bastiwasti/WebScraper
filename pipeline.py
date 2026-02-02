"""Orchestrates the three-agent pipeline: Scraper -> Analyzer -> Writer, and stores events in DB."""

from agents import ScraperAgent, AnalyzerAgent, WriterAgent
from storage import insert_events, insert_raw_summary


def run_pipeline(
    location: str = "",
    max_search: int = 8,
    fetch_urls: int = 3,
    model: str | None = None,
    base_url: str | None = None,
    save_to_db: bool = True,
    cities: list[str] | None = None,
    search_queries: list[str] | None = None,
) -> tuple[str, list[dict], str]:
    """
    Run the full pipeline:
    1. Scraper: search + fetch (events in region) -> raw event summary text
    2. Analyzer: raw text -> structured event list (name, description, location, date, time, source)
    3. Save events to SQLite (for automation and next agents)
    4. Writer: structured list -> email-ready document

    Returns:
        (raw_summary, structured_events, email_document)
    """
    from config import DEFAULT_LOCATION

    scraper = ScraperAgent(model=model, base_url=base_url)
    analyzer = AnalyzerAgent(model=model, base_url=base_url)
    writer = WriterAgent(model=model, base_url=base_url)

    loc = location or DEFAULT_LOCATION
    raw_summary = scraper.run(
        location=loc,
        max_search=max_search,
        fetch_urls=fetch_urls,
        cities=cities,
        search_queries=search_queries,
    )

    if save_to_db:
        insert_raw_summary(loc, max_search, fetch_urls, raw_summary)

    structured_events = analyzer.run(raw_summary)

    if save_to_db and structured_events:
        insert_events(structured_events)

    email_document = writer.run(structured_events)

    return raw_summary, structured_events, email_document
