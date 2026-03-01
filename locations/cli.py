"""CLI command handling for the locations feature."""

from locations.models import LOCATION_CATEGORIES


def handle_command(args) -> None:
    """Dispatch location subcommands.

    Args:
        args: Parsed argparse namespace with 'locations' and optional
              'locations_source', 'locations_category' attributes.
    """
    command = args.locations

    if command == "discover":
        _cmd_discover(args)
    elif command == "check-urls":
        _cmd_check_urls()
    elif command == "list":
        _cmd_list(args)
    elif command == "enrich":
        _cmd_enrich()
    elif command == "stats":
        _cmd_stats()
    else:
        print(f"Unknown locations command: {command}")
        print("Available: discover, check-urls, enrich, list, stats")


def _cmd_discover(args) -> None:
    """Run location discovery."""
    from locations import discover_locations
    source = getattr(args, "locations_source", None)
    discover_locations(source=source)


def _cmd_enrich() -> None:
    """Enrich existing locations with Google Places ratings."""
    from locations import enrich_locations
    enrich_locations()


def _cmd_check_urls() -> None:
    """Run URL health checks."""
    from locations.maintenance import check_all_urls
    check_all_urls()


def _cmd_list(args) -> None:
    """List locations from the database."""
    from locations.storage import get_locations
    category = getattr(args, "locations_category", None)
    locations = get_locations(category=category)

    if not locations:
        print("No locations found.")
        return

    print(f"\n{'ID':>4}  {'Category':<18} {'Name':<40} {'City':<20} {'Dist':>6}  URL Status")
    print("-" * 100)
    for loc in locations:
        dist = f"{loc['distance_km']:.1f}km" if loc["distance_km"] else "?"
        cat_de = LOCATION_CATEGORIES.get(loc["category"], loc["category"])
        print(
            f"{loc['id']:>4}  {cat_de:<18} {loc['name'][:40]:<40} "
            f"{(loc['city'] or '')[:20]:<20} {dist:>6}  {loc['url_status']}"
        )
    print(f"\nTotal: {len(locations)} locations")


def _cmd_stats() -> None:
    """Show location statistics."""
    from locations.storage import get_location_summary
    summary = get_location_summary()

    if summary["total"] == 0:
        print("No locations in database. Run: python main.py --locations discover")
        return

    print(f"\n--- Location Statistics ---")
    print(f"Total locations: {summary['total']}")

    print(f"\nBy category:")
    for cat, count in summary["by_category"].items():
        de_name = LOCATION_CATEGORIES.get(cat, cat)
        print(f"  {de_name:<20} {count:>4}")

    print(f"\nBy source:")
    for src, count in summary["by_source"].items():
        print(f"  {src:<20} {count:>4}")

    if summary["broken_urls"] > 0:
        print(f"\nBroken URLs: {summary['broken_urls']}")
