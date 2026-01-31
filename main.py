"""Entry point for the WeeklyMail multi-agent pipeline."""

import argparse
import sys
from pathlib import Path

import requests

from config import DEFAULT_LOCATION, LLM_MODEL, OLLAMA_BASE_URL
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
        "--no-db",
        action="store_true",
        help="Do not save events to the SQLite database.",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=LLM_MODEL,
        help=f"Ollama model name (default: {LLM_MODEL}).",
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
    args = parser.parse_args()

    if not check_ollama():
        print("Ollama is not running or not reachable.", file=sys.stderr)
        print(f"Start Ollama (e.g. run 'ollama serve' or start the Ollama app), then run again.", file=sys.stderr)
        print(f"Expected base URL: {OLLAMA_BASE_URL}", file=sys.stderr)
        sys.exit(1)

    print("Running pipeline: Scraper -> Analyzer -> Writer")
    print(f"Location: {args.location or '(general)'} | Model: {args.model} | DB: {not args.no_db}\n")

    raw_summary, structured_events, email_doc = run_pipeline(
        location=args.location,
        max_search=args.max_search,
        fetch_urls=args.fetch_urls,
        model=args.model,
        save_to_db=not args.no_db,
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


if __name__ == "__main__":
    main()
