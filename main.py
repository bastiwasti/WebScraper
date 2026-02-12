"""Entry point for the WeeklyMail multi-agent pipeline."""

import argparse
import sys
from pathlib import Path

import requests

from config import DEFAULT_LOCATION, LLM_PROVIDER, DEEPSEEK_MODEL
from storage import get_runs
from pipeline import run_pipeline





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
        "--cities",
        nargs="*",
        help="Cities to scrape (default: all). Available: monheim, langenfeld, leverkusen, hilden, dormagen, ratingen, solingen, haan.",
    )
    parser.add_argument(
        "--url",
        "-u",
        help="Specific URL or folder to scrape (e.g., --url lust_auf or --url https://lust-auf-leverkusen.de/). Overrides --cities.",
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
        default=DEEPSEEK_MODEL,
        help=f"Model name (default: {LLM_PROVIDER.upper()} model {DEEPSEEK_MODEL}).",
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
        "--reset-db",
        action="store_true",
        help="Reset database (drop and recreate all tables).",
    )
    parser.add_argument(
        "--load-summary",
        type=int,
        help="Load raw summary by ID and print it (for debugging).",
    )
    parser.add_argument(
        "--reanalyze-run",
        type=int,
        help="Re-analyze events from a specific scraper run ID (requires saved raw summary).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=3,
        help="Number of events to analyze per LLM call (default: 3).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=5000,
        help="Maximum characters per chunk (default: 5000).",
    )
    args = parser.parse_args()
    
    def resolve_url(url_or_folder: str) -> str:
        """Resolve --url argument to actual URL.
        
        Args:
            url_or_folder: Either a full URL or a folder name (e.g., 'lust_auf').
        
        Returns:
            Actual URL string to scrape.
        """
        # If it's already a full URL, return as-is
        if url_or_folder.startswith(('http://', 'https://')):
            return url_or_folder
        
        # Otherwise, treat it as a folder name
        from rules.urls import CITY_URLS
        
        folder_lower = url_or_folder.lower().strip()
        
        # Search for folder in all cities
        for city, url_dict in CITY_URLS.items():
            for subfolder, url in url_dict.items():
                if subfolder.lower() == folder_lower:
                    return url
        
        print(f"Error: Folder '{url_or_folder}' not found in any city", file=sys.stderr)
        sys.exit(1)
    
    # Resolve URL if --url is provided (overrides --cities)
    urls_to_use: list[str] = []
    if args.url:
        resolved_url = resolve_url(args.url)
        urls_to_use.append(resolved_url)
        args.cities = []  # Clear cities to prevent auto-detection
        print(f"Running single URL mode: {resolved_url}")
    elif not args.cities:
        # Default: scrape all cities
        from rules.urls import get_all_urls
        urls_to_use = get_all_urls()
        print(f"Running all cities mode: {len(urls_to_use)} URLs")

    if args.reset_db:
        from storage import reset_database
        print("Resetting database...")
        reset_database()
        print("✓ Database reset complete")
        sys.exit(0)

    if args.list_runs:
        runs = get_runs()
        if not runs:
            print("No runs found in database.")
        else:
            print("Pipeline runs:")
            for r in runs:
                duration = f"{r['duration']:.2f}s" if r.get('duration') else "N/A"
                print(f"  Run ID {r['id']} | Agent: {r['agent']} | Events found: {r['events_found']} | Valid: {r['valid_events']} | Event count: {r['event_count']} | Created: {r['created_at']}")
                if r.get('start_time'):
                    print(f"    Duration: {duration}")
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

    if args.reanalyze_run is not None:
        from agents import AnalyzerAgent
        from storage import get_raw_summary_by_run_id, create_run, insert_events

        run_id_to_analyze = args.reanalyze_run
        
        raw_summary_data = get_raw_summary_by_run_id(run_id_to_analyze)
        if not raw_summary_data:
            print(f"Error: No raw summary found for run ID {run_id_to_analyze}", file=sys.stderr)
            print("Run 'python3 main.py --list-runs' to see available runs.", file=sys.stderr)
            sys.exit(1)
        
        raw_summary = raw_summary_data["raw_summary"]
        print(f"Re-analyzing run {run_id_to_analyze} ({raw_summary_data.get('max_search')} max_search, {raw_summary_data.get('fetch_urls')} fetch_urls)")
        print(f"Location: {raw_summary_data['location']}")
        if raw_summary_data.get('cities'):
            print(f"Cities: {', '.join(raw_summary_data['cities'])}")
        print(f"Raw summary length: {len(raw_summary):,} characters\n")
        
        print(f"Running pipeline: ANALYZER agent")
        print(f"LLM: {LLM_PROVIDER.upper()} | Model: {args.model} | DB: {not args.no_db}\n")
        
        analyzer = AnalyzerAgent(model=args.model)
        new_run_id = create_run("analyzer", None)
        
        structured_events = analyzer.run(
            new_run_id,
            raw_summary,
            save_to_db=not args.no_db,
            chunk_size=args.chunk_size,
            max_chars=args.max_chars,
        )
        
        print("\n--- Structured events (Agent 2) ---")
        print(structured_events)
        
        print(f"\nFound {len(structured_events)} events.")
        
        if not args.no_db and structured_events:
            from config import DB_PATH
            insert_events(structured_events, new_run_id)
            print(f"Events saved to DB: {DB_PATH}")
            print(f"Analyzer run ID: {new_run_id}")
            print(f"Re-analyzed from scraper run: {run_id_to_analyze}")
        
        sys.exit(0)

    print(f"Running pipeline: {args.agent.upper()} agent")
    print(f"LLM: {LLM_PROVIDER.upper()} | Model: {args.model} | Location: {args.location or '(general)'} | DB: {not args.no_db}\n")

    if args.agent == "all":
        raw_summary, structured_events = run_pipeline(
            location=args.location,
            max_search=args.max_search,
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
            
            if not args.no_db:
                run_id = create_run("scraper", args.location)
            else:
                run_id = 0
            
            raw_summary, url_metrics, city_event_counts = scraper.run(
                run_id=run_id,
                location=args.location,
                max_search=args.max_search,
                cities=args.cities if not urls_to_use else None,  # Use cities only if --url not provided
                search_queries=args.search_queries,
                urls=urls_to_use if urls_to_use else None,  # Use explicit URLs if --url provided
            )
            print("--- Raw summary (Agent 1) ---")
            print(raw_summary)

            if not args.no_db:
                summary_id = insert_raw_summary(
                    location=args.location,
                    max_search=args.max_search,
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
            run_id = create_run("analyzer", None)
            structured_events = analyzer.run(run_id, raw_summary, save_to_db=not args.no_db)
            print("--- Structured events (Agent 2) ---")
            print(structured_events)

            if not args.no_db and structured_events:
                from config import DB_PATH
                print(f"Events saved to DB: {DB_PATH}")


if __name__ == "__main__":
    main()
