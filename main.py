"""Entry point for the WeeklyMail multi-agent pipeline."""

import argparse
import sys
from pathlib import Path

import requests

from config import DEFAULT_LOCATION, LLM_MODEL, OLLAMA_BASE_URL, LLM_PROVIDER, DEEPSEEK_MODEL
from storage import get_runs
from pipeline import run_pipeline


def check_ollama(base_url: str = OLLAMA_BASE_URL) -> bool:
    """Return True if Ollama is reachable, else False."""
    try:
        r = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="WeeklyMail: Scrape local events -> structure for display.",
    )
    parser.add_argument(
        "--location",
        "-l",
        default=DEFAULT_LOCATION,
        help="Location for event search (e.g. 'Berlin', 'Munich').",
    )
    parser.add_argument(
        "--max-search",
        type=int,
        default=8,
        help="Max number of search results to use (default: 8).",
    )
    parser.add_argument(
        "--fetch-urls",
        type=int,
        default=3,
        help="Number of pages to fetch and scrape (default: 3).",
    )
    parser.add_argument(
        "--cities",
        nargs="*",
        help="Cities to scrape (default: all). Available: monheim, langenfeld, leverkusen, hilden, dormagen, ratingen, solingen, haan.",
    )
    parser.add_argument(
        "--search-queries",
        nargs="+",
        help="Custom search queries for finding events (optional).",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Do not save events to the SQLite database.",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=DEEPSEEK_MODEL if LLM_PROVIDER == "deepseek" else LLM_MODEL,
        help=f"Model name (default depends on provider: deepseek={DEEPSEEK_MODEL}, ollama={LLM_MODEL}).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print raw summary and structured events as well.",
    )
    parser.add_argument(
        "--agent",
        choices=["scraper", "analyzer", "all"],
        default="all",
        help="Run only this agent (default: all).",
    )
    parser.add_argument(
        "--list-summaries",
        action="store_true",
        help="List all saved raw summaries from database.",
    )
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List all pipeline runs with event counts.",
    )
    parser.add_argument(
        "--full-run",
        action="store_true",
        help="Run as full pipeline (analyzer updates same run_id as scraper).",
    )
    parser.add_argument(
        "--load-summary",
        type=int,
        help="Load raw summary by ID and print it (for debugging).",
    )
    args = parser.parse_args()

    if args.list_runs:
        runs = get_runs()
        if not runs:
            print("No runs found in database.")
        else:
            print("Pipeline runs:")
            for r in runs:
                print(f"  Run ID {r['id']} | Agent: {r['agent']} | Events found: {r['events_found']} | Valid: {r['valid_events']} | Event count: {r['event_count']} | Created: {r['created_at']}")
                if r.get('start_time'):
                    print(f"    Duration: {r['duration']:.2f}s")
                if r.get('linked_run_id'):
                    print(f"    Linked to: {r['linked_run_id']}")
        sys.exit(0)

    if args.list_summaries:
        from storage import get_raw_summaries
        summaries = get_raw_summaries()
        if not summaries:
            print("No raw summaries found in database.")
        else:
            print("Saved raw summaries:")
            for s in summaries:
                cities_str = f"Cities: {s['cities']}" if s['cities'] else ""
                queries_str = f"Queries: {s['search_queries']}" if s['search_queries'] else ""
                details = " | ".join(filter(None, [cities_str, queries_str]))
                print(f"  ID {s['id']} | {s['created_at']} | Loc: '{s['location']}' | Max: {s['max_search']} | Fetch: {s['fetch_urls']}")
                if details:
                    print(f"    {details}")
        sys.exit(0)

    if args.load_summary is not None:
        from storage import get_raw_summary_by_id
        summary = get_raw_summary_by_id(args.load_summary)
        if not summary:
            print(f"No raw summary found with ID {args.load_summary}.", file=sys.stderr)
            sys.exit(1)
        print(f"--- Raw summary (ID: {summary['id']}, Created: {summary['created_at']}) ---")
        print(f"Location: {summary['location']} | Max search: {summary['max_search']} | Fetch URLs: {summary['fetch_urls']}")
        if summary['cities']:
            print(f"Cities: {summary['cities']}")
        if summary['search_queries']:
            print(f"Search queries: {summary['search_queries']}")
        print()
        print(summary['raw_summary'])
        sys.exit(0)

    if not check_ollama():
        print("Ollama is not running or not reachable.", file=sys.stderr)
        print(f"Start Ollama (e.g. run 'ollama serve' or start the Ollama app), then run again.", file=sys.stderr)
        print(f"Expected base URL: {OLLAMA_BASE_URL}", file=sys.stderr)
        sys.exit(1)

    print(f"Running pipeline: {args.agent.upper()} agent")
    print(f"LLM: {LLM_PROVIDER.upper()} | Model: {args.model} | Location: {args.location or '(general)'} | DB: {not args.no_db}\n")

    if args.agent == "all":
        raw_summary, structured_events = run_pipeline(
            location=args.location,
            max_search=args.max_search,
            fetch_urls=args.fetch_urls,
            model=args.model,
            save_to_db=not args.no_db,
            cities=args.cities,
            search_queries=args.search_queries,
            full_run=args.full_run,
        )

        if args.verbose:
            print("--- Raw summary (Agent 1) ---")
            print(raw_summary[:2000] + ("..." if len(raw_summary) > 2000 else ""))
            print("\n--- Structured events (Agent 2) ---")
            print(structured_events)

        print(f"\nFound {len(structured_events)} events.")

        if not args.no_db and structured_events:
            from config import DB_PATH
            print(f"Events saved to DB: {DB_PATH}")

    else:
        from agents import ScraperAgent, AnalyzerAgent
        from storage import insert_events, create_run, insert_raw_summary

        if args.agent == "scraper":
            scraper = ScraperAgent(model=args.model)
            raw_summary, url_metrics, city_event_counts = scraper.run(
                location=args.location,
                max_search=args.max_search,
                fetch_urls=args.fetch_urls,
                cities=args.cities,
                search_queries=args.search_queries,
            )
            print("--- Raw summary (Agent 1) ---")
            print(raw_summary)

            if not args.no_db:
                run_id = create_run("scraper", args.location)
                summary_id = insert_raw_summary(
                    location=args.location,
                    max_search=args.max_search,
                    fetch_urls=args.fetch_urls,
                    raw_summary=raw_summary,
                    run_id=run_id,
                    cities=args.cities,
                    search_queries=args.search_queries,
                )
                from config import DB_PATH
                print(f"\nRaw summary saved to DB: {DB_PATH} (Run ID: {run_id}, Summary ID: {summary_id})")

        elif args.agent == "analyzer":
            analyzer = AnalyzerAgent(model=args.model)
            raw_summary = input("Paste raw summary text:\n")
            structured_events = analyzer.run(raw_summary, save_to_db=not args.no_db)
            print("--- Structured events (Agent 2) ---")
            print(structured_events)

            if not args.no_db and structured_events:
                from config import DB_PATH
                print(f"Events saved to DB: {DB_PATH}")


if __name__ == "__main__":
    main()
