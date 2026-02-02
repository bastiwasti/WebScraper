"""Entry point for the WeeklyMail multi-agent pipeline."""

import argparse
import sys
from pathlib import Path

import requests

from config import DEFAULT_LOCATION, LLM_MODEL, OLLAMA_BASE_URL, LLM_PROVIDER, ZAI_MODEL, XAI_MODEL, GROQ_MODEL, DEEPSEEK_MODEL
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
        description="WeeklyMail: Scrape local events -> structure -> generate email-ready document."
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
        default=DEEPSEEK_MODEL if LLM_PROVIDER == "deepseek" else GROQ_MODEL if LLM_PROVIDER == "groq" else ZAI_MODEL if LLM_PROVIDER == "zai" else XAI_MODEL if LLM_PROVIDER == "xai" else LLM_MODEL,
        help=f"Model name (default depends on provider: ollama={LLM_MODEL}, xai={XAI_MODEL}, zai={ZAI_MODEL}, groq={GROQ_MODEL}, deepseek={DEEPSEEK_MODEL}).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Write email document to this file (default: print only).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print raw summary and structured events as well.",
    )
    parser.add_argument(
        "--agent",
        choices=["scraper", "analyzer", "writer", "all"],
        default="all",
        help="Run only this agent (default: all).",
    )
    parser.add_argument(
        "--list-summaries",
        action="store_true",
        help="List all saved raw summaries from database.",
    )
    parser.add_argument(
        "--load-summary",
        type=int,
        help="Load raw summary by ID and print it (for debugging).",
    )
    args = parser.parse_args()

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
        raw_summary, structured_events, email_doc = run_pipeline(
            location=args.location,
            max_search=args.max_search,
            fetch_urls=args.fetch_urls,
            model=args.model,
            save_to_db=not args.no_db,
            cities=args.cities,
            search_queries=args.search_queries,
        )

        if args.verbose:
            print("--- Raw summary (Agent 1) ---")
            print(raw_summary[:2000] + ("..." if len(raw_summary) > 2000 else ""))
            print("\n--- Structured events (Agent 2) ---")
            print(structured_events)
            print("\n--- Email document (Agent 3) ---")

        print(email_doc)

        if args.output:
            args.output.write_text(email_doc, encoding="utf-8")
            print(f"\nWritten to: {args.output}")
        if not args.no_db and structured_events:
            from config import DB_PATH
            print(f"Events saved to DB: {DB_PATH}")

    else:
        from agents import ScraperAgent, AnalyzerAgent, WriterAgent
        from storage import insert_events

        if args.agent == "scraper":
            scraper = ScraperAgent(model=args.model)
            raw_summary = scraper.run(
                location=args.location,
                max_search=args.max_search,
                fetch_urls=args.fetch_urls,
                cities=args.cities,
                search_queries=args.search_queries,
            )
            print("--- Raw summary (Agent 1) ---")
            print(raw_summary)

            if not args.no_db:
                from storage import insert_raw_summary, get_raw_summaries
                summary_id = insert_raw_summary(
                    location=args.location,
                    max_search=args.max_search,
                    fetch_urls=args.fetch_urls,
                    raw_summary=raw_summary,
                    cities=args.cities,
                    search_queries=args.search_queries,
                )
                from config import DB_PATH
                print(f"\nRaw summary saved to DB: {DB_PATH} (ID: {summary_id})")

        elif args.agent == "analyzer":
            analyzer = AnalyzerAgent(model=args.model)
            raw_summary = input("Paste raw summary text:\n")
            structured_events = analyzer.run(raw_summary)
            print("--- Structured events (Agent 2) ---")
            print(structured_events)

            if not args.no_db and structured_events:
                insert_events(structured_events)
                from config import DB_PATH
                print(f"Events saved to DB: {DB_PATH}")

        elif args.agent == "writer":
            writer = WriterAgent(model=args.model)
            import json
            structured_events = json.loads(input("Paste structured events JSON:\n"))
            email_doc = writer.run(structured_events)
            print("--- Email document (Agent 3) ---")
            print(email_doc)

            if args.output:
                args.output.write_text(email_doc, encoding="utf-8")
                print(f"\nWritten to: {args.output}")


if __name__ == "__main__":
    main()
