"""Load manually curated seed locations from a JSON file."""

import json
from pathlib import Path
from __future__ import annotations

from locations.models import Location

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_locations.json"


def load_seed_locations() -> list[Location]:
    """Load locations from the seed JSON file."""
    if not SEED_FILE.exists():
        return []

    with open(SEED_FILE, "r", encoding="utf-8") as f:
        entries = json.load(f)

    locations = []
    for entry in entries:
        loc = Location(
            name=entry["name"],
            category=entry.get("category", "other"),
            source="manual",
            source_id=f"manual_{entry['name'].lower().replace(' ', '_')[:50]}",
            description=entry.get("description", ""),
            address=entry.get("address", ""),
            city=entry.get("city", ""),
            postal_code=entry.get("postal_code", ""),
            latitude=entry.get("latitude"),
            longitude=entry.get("longitude"),
            subcategory=entry.get("subcategory", ""),
            opening_hours=entry.get("opening_hours", ""),
            website_url=entry.get("website_url", ""),
            phone=entry.get("phone", ""),
        )
        locations.append(loc)

    return locations
