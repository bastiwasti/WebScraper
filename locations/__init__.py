"""Locations/Ausflüge feature — discover and manage family-friendly locations."""

import math
from typing import Optional

from config import MONHEIM_LAT, MONHEIM_LNG, LOCATIONS_RADIUS_KM
from locations.models import Location
from locations.storage import upsert_locations, init_locations_db, get_locations, update_location_rating


def _deduplicate(locations: list[Location], threshold_m: float = 100.0) -> list[Location]:
    """Remove duplicates by coordinate proximity + name similarity.

    Two entries match if they are within threshold_m meters of each other
    AND their names match (case-insensitive).
    """
    kept: list[Location] = []

    for loc in locations:
        is_dup = False
        for existing in kept:
            if _is_duplicate(loc, existing, threshold_m):
                is_dup = True
                break
        if not is_dup:
            kept.append(loc)

    return kept


def _is_duplicate(a: Location, b: Location, threshold_m: float) -> bool:
    """Check if two locations are duplicates."""
    if a.latitude is None or b.latitude is None:
        # Can't compare by coordinates, fall back to exact name match
        return a.name.lower().strip() == b.name.lower().strip()

    dist_m = _haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)
    if dist_m > threshold_m:
        return False

    # Within distance threshold — check name similarity
    return a.name.lower().strip() == b.name.lower().strip()


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in meters between two points."""
    R = 6_371_000  # Earth radius in meters
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def discover_locations(source: Optional[str] = None) -> list[Location]:
    """Run the full location discovery pipeline.

    Args:
        source: Optional filter — 'overpass', 'manual', or None for all sources.

    Returns:
        List of discovered and stored locations.
    """
    init_locations_db()
    all_locations: list[Location] = []

    # Source 1: Overpass API
    if source is None or source == "overpass":
        print("Discovering locations via OpenStreetMap / Overpass API ...")
        from locations.sources.overpass import discover_all_categories
        overpass_locs = discover_all_categories()
        all_locations.extend(overpass_locs)

    # Source 2: Google Places API
    if source is None or source == "google":
        print("Discovering locations via Google Places API ...")
        from locations.sources.google_places import discover_all_categories as google_discover
        google_locs = google_discover()
        all_locations.extend(google_locs)

    # Source 3: Manual seed file
    if source is None or source == "manual":
        print("Loading manual seed locations ...")
        from locations.sources.manual import load_seed_locations
        seed_locs = load_seed_locations()
        all_locations.extend(seed_locs)
        print(f"  → {len(seed_locs)} manual locations loaded")

    # Calculate distances from Monheim center
    for loc in all_locations:
        loc.calculate_distance(MONHEIM_LAT, MONHEIM_LNG)

    # Filter by radius
    before = len(all_locations)
    all_locations = [loc for loc in all_locations if loc.distance_km is not None and loc.distance_km <= LOCATIONS_RADIUS_KM]
    print(f"Distance filter: {before} → {len(all_locations)} (within {LOCATIONS_RADIUS_KM}km)")

    # Deduplicate
    before = len(all_locations)
    all_locations = _deduplicate(all_locations)
    if before != len(all_locations):
        print(f"Deduplication: {before} → {len(all_locations)}")

    # Store in database
    count = upsert_locations(all_locations)
    print(f"\nStored {count} locations in database.")

    # Print summary
    _print_summary(all_locations)

    return all_locations


def _print_summary(locations: list[Location]) -> None:
    """Print a summary table of discovered locations."""
    from locations.models import LOCATION_CATEGORIES

    counts: dict[str, int] = {}
    for loc in locations:
        counts[loc.category] = counts.get(loc.category, 0) + 1

    print("\n--- Discovery Summary ---")
    print(f"{'Category':<20} {'DE Name':<20} {'Count':>6}")
    print("-" * 48)
    total = 0
    for cat_id, de_name in LOCATION_CATEGORIES.items():
        c = counts.get(cat_id, 0)
        if c > 0:
            print(f"{cat_id:<20} {de_name:<20} {c:>6}")
            total += c
    print("-" * 48)
    print(f"{'TOTAL':<20} {'':<20} {total:>6}")


def enrich_locations(max_calls: int = 200) -> int:
    """Enrich existing locations with Google Places data (ratings).

    Searches Google Places for each location that has coordinates but no rating.
    Only updates fields that are currently empty.

    Args:
        max_calls: Maximum API calls to make (cost control).

    Returns:
        Number of locations enriched.
    """
    import time
    from locations.sources.google_places import search_single_location

    init_locations_db()

    # Get locations without ratings that have coordinates
    locations = get_locations()
    candidates = [
        loc for loc in locations
        if loc["latitude"] is not None
        and loc["longitude"] is not None
        and loc["rating"] is None
    ]

    if not candidates:
        print("No locations without ratings found.")
        return 0

    # Limit to max_calls
    if len(candidates) > max_calls:
        print(f"Limiting to {max_calls} of {len(candidates)} candidates (cost control)")
        candidates = candidates[:max_calls]
    else:
        print(f"Enriching {len(candidates)} locations ...")

    enriched = 0
    api_calls = 0

    for loc in candidates:
        result = search_single_location(
            lat=loc["latitude"],
            lng=loc["longitude"],
            name=loc["name"],
        )
        api_calls += 1

        if result and result.get("rating"):
            update_location_rating(
                location_id=loc["id"],
                rating=result["rating"],
                user_rating_count=result.get("userRatingCount"),
                google_maps_url=result.get("googleMapsUri", ""),
            )
            enriched += 1
            print(f"  ✓ {loc['name'][:40]:<40} → {result['rating']} stars ({result.get('userRatingCount', '?')} reviews)")

        # Rate limit
        time.sleep(0.2)

        # Progress update every 50 calls
        if api_calls % 50 == 0:
            print(f"  ... {api_calls} API calls, {enriched} enriched so far")

    print(f"\nEnrichment complete: {enriched}/{api_calls} locations updated with ratings")
    return enriched
