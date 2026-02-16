"""Centralized category management for event classification.

This module provides a flexible, standardized category system for all scrapers.
Categories are stored with German display names and support multi-language keyword inference.

Usage:
    from rules import categories

    # Infer category from text
    cat = categories.infer_category("Konzert für Kinder")
    # Returns: "culture" (matches "Konzert" before "Kinder")

    # Normalize any category to standard
    normalized = categories.normalize_category("sports")
    # Returns: "sport"

    # Get all categories
    all_cats = categories.get_all_categories()

    # Check validity
    is_valid = categories.is_valid_category("culture")
    # Returns: True
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Category:
    """Category definition with display names and keywords.

    Attributes:
        id: Unique category identifier (e.g., "culture")
        name_de: German display name
        name_en: English display name
        keywords_de: German keywords for inference
        keywords_en: English keywords for inference
        priority: Inference priority (lower = checked first)
    """
    id: str
    name_de: str
    name_en: str
    keywords_de: List[str]
    keywords_en: List[str]
    priority: int


# Standardized categories (10 categories - flexible but not overwhelming)
_CATEGORIES: List[Category] = [
    Category(
        id="family",
        name_de="Familie",
        name_en="Family",
        keywords_de=[
            "familie", "kinder", "jugend", "kind", "baby", "schule",
            "eltern", "familien", "schulkinder", "schüler",
            "familientag", "kindertag", "familienfest",
        ],
        keywords_en=[
            "family", "children", "kids", "teens", "school", "parents",
        ],
        priority=1,
    ),
    Category(
        id="education",
        name_de="Bildung",
        name_en="Education",
        keywords_de=[
            "kurs", "workshop", "vhs", "volkshochschule", "bildung",
            "schule", "bibliothek", "weiterbildung", "unterricht",
            "vortrag", "seminar", "schulung", "ausbildung",
        ],
        keywords_en=[
            "course", "workshop", "school", "library", "education",
            "training", "lecture", "seminar",
        ],
        priority=2,
    ),
    Category(
        id="sport",
        name_de="Sport",
        name_en="Sport",
        keywords_de=[
            "sport", "fitness", "laufen", "schwimmen", "rad", "fußball",
            "tennis", "yoga", "wandern", "turnier", "sportveranstaltung",
            "sportart", "sportstätte", "turnhalle", "schwimmbad",
            "jogging", "radfahren", "faehrrad",
        ],
        keywords_en=[
            "sport", "sports", "fitness", "running", "swimming", "cycling",
            "football", "tennis", "yoga", "hiking", "tournament",
        ],
        priority=3,
    ),
    Category(
        id="culture",
        name_de="Kultur",
        name_en="Culture",
        keywords_de=[
            "ausstellung", "konzert", "theater", "film", "kino", "lesung",
            "buch", "vortrag", "führung", "tour", "kunst", "museum",
            "kultur", "opera", "orchester", "chor", "jazz", "musik",
            "galerie", "vernissage", "kulturveranstaltung", "kunstausstellung",
        ],
        keywords_en=[
            "exhibition", "concert", "theater", "film", "cinema", "reading",
            "book", "lecture", "tour", "art", "museum", "culture",
            "opera", "orchestra", "choir", "jazz", "music", "gallery",
        ],
        priority=4,
    ),
    Category(
        id="market",
        name_de="Markt",
        name_en="Market",
        keywords_de=[
            "markt", "markttag", "messe", "flohmarkt", "verkauf",
            "verkaufsmarkt", "weihnachtsmarkt", "frühlingsmarkt",
            "floßmarkt", "bauernmarkt", "handwerkermarkt",
        ],
        keywords_en=[
            "market", "fair", "sale", "flea market",
        ],
        priority=5,
    ),
    Category(
        id="festival",
        name_de="Fest",
        name_en="Festival",
        keywords_de=[
            "fest", "festival", "karneval", "fastnacht", "kirmes",
            "volksfest", "weihnachtsmarkt", "stadtfest", "dorfesta",
            "sommerfest", "kirmes", "schützenfest",
        ],
        keywords_en=[
            "festival", "carnival", "fair", "christmas market", "street festival",
        ],
        priority=6,
    ),
    Category(
        id="adult",
        name_de="Erwachsene",
        name_en="Adult",
        keywords_de=[
            "erwachsen", "adult", "senior", "senioren", "abend", "nacht",
            "bar", "club", "party", "frauen", "damen", "damenabend",
            "herren", "nachtleben", "diskothek", "tanzabend",
        ],
        keywords_en=[
            "adult", "seniors", "women", "ladies", "night", "party",
            "club", "bar",
        ],
        priority=7,
    ),
    Category(
        id="community",
        name_de="Gemeinschaft",
        name_en="Community",
        keywords_de=[
            "treffen", "verein", "club", "gruppe", "nachbarschaft",
            "soziales", "gemeinschaft", "bürgerverein", "sportverein",
            "musikverein", "gesangsverein", "chorverein",
        ],
        keywords_en=[
            "meeting", "club", "group", "neighborhood", "social",
            "community", "association",
        ],
        priority=8,
    ),
    Category(
        id="nature",
        name_de="Natur",
        name_en="Nature",
        keywords_de=[
            "natur", "wanderung", "spaziergang", "umwelt", "garten",
            "park", "wald", "see", "landschaft", "naturschutz",
            "grünanlagen", "stadtpark",
        ],
        keywords_en=[
            "nature", "hike", "walk", "environment", "garden",
            "park", "forest", "lake", "landscape",
        ],
        priority=9,
    ),
    Category(
        id="other",
        name_de="Sonstiges",
        name_en="Other",
        keywords_de=[],
        keywords_en=[],
        priority=10,
    ),
]


# Category normalization mapping (aliases to standard category IDs)
_CATEGORY_ALIASES: dict[str, str] = {
    # Sports variants
    "sports": "sport",
    # Venue names that indicate culture
    "schauplatz": "culture",
    # Education venues
    "vhs": "education",
    "volkshochschule": "education",
    "library": "education",
    "bibliothek": "education",
    "school": "education",
    "schule": "education",
    "museum": "culture",
    # Adults/women categories
    "women": "adult",
    "frauen": "adult",
    "damen": "adult",
    "seniors": "adult",
    "senioren": "adult",
    # Family categories
    "familie": "family",
    "familien": "family",
    # Festivals
    "karneval": "festival",
    "fastnacht": "festival",
    # Culture variants
    "kultur": "culture",
    "musik": "culture",
    "music": "culture",
    # Market variants
    "markt": "market",
}


def normalize_category(category: str) -> str:
    """Normalize any category to standard category ID.

    Handles aliases (e.g., "sports" → "sport", "kultur" → "culture")
    and preserves existing standard categories.

    Args:
        category: Raw category string from any source.

    Returns:
        Standard category ID (e.g., "sport", "culture").

    Examples:
        >>> normalize_category("sports")
        'sport'
        >>> normalize_category("kultur")
        'culture'
        >>> normalize_category("sport")
        'sport'
        >>> normalize_category("unknown")
        'unknown'  # Preserved if not in aliases
    """
    if not category:
        return "other"

    category_lower = category.lower().strip()

    # Check if it's already a valid category ID
    if category_lower in [c.id for c in _CATEGORIES]:
        return category_lower

    # Check aliases
    if category_lower in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[category_lower]

    # Return original if no match found (preserve data)
    return category_lower


def infer_category(text: str, name: str = "") -> str:
    """Infer category from event description and name.

    Uses first-match priority system:
    1. Searches German keywords (in priority order)
    2. Searches English keywords (in priority order)
    3. Returns "other" if no match

    Priority order: family → education → sport → culture → market → festival → adult → community → nature → other

    Args:
        text: Event description text.
        name: Event name/title (optional).

    Returns:
        Category ID (e.g., "family", "sport", "culture", "other").

    Examples:
        >>> infer_category("Konzert für Kinder")
        'family'  # "Kinder" matches before "Konzert"
        >>> infer_category("Fußballturnier")
        'sport'
        >>> infer_category("Bücherlesung")
        'culture'
    """
    combined = f"{text} {name}".lower()

    # Search categories by priority (1 = first checked, 10 = last)
    sorted_categories = sorted(_CATEGORIES, key=lambda c: c.priority)

    for category in sorted_categories:
        # Check German keywords first
        for keyword in category.keywords_de:
            if keyword in combined:
                return category.id

        # Check English keywords
        for keyword in category.keywords_en:
            if keyword in combined:
                return category.id

    return "other"


def get_all_categories() -> List[Category]:
    """Return all defined category objects.

    Returns:
        List of Category objects sorted by priority.
    """
    return sorted(_CATEGORIES, key=lambda c: c.priority)


def is_valid_category(category: str) -> bool:
    """Check if a category ID is valid.

    Args:
        category: Category ID to validate.

    Returns:
        True if category exists, False otherwise.
    """
    category_lower = category.lower().strip() if category else ""
    return category_lower in [c.id for c in _CATEGORIES]


def get_default_category() -> str:
    """Return the default category ID.

    Returns:
        "other" as the fallback category.
    """
    return "other"


def get_category_by_id(category_id: str) -> Optional[Category]:
    """Get Category object by ID.

    Args:
        category_id: Category ID to look up.

    Returns:
        Category object or None if not found.
    """
    category_lower = category_id.lower().strip() if category_id else ""
    for category in _CATEGORIES:
        if category.id == category_lower:
            return category
    return None


def get_category_name(category_id: str, language: str = "de") -> str:
    """Get display name for a category.

    Args:
        category_id: Category ID (e.g., "culture").
        language: Language code ("de" or "en"). Defaults to "de".

    Returns:
        Display name in requested language, or category ID if not found.

    Examples:
        >>> get_category_name("culture")
        'Kultur'
        >>> get_category_name("culture", language="en")
        'Culture'
        >>> get_category_name("unknown")
        'unknown'
    """
    category = get_category_by_id(category_id)
    if not category:
        return category_id

    if language.lower() == "en":
        return category.name_en
    else:
        return category.name_de
