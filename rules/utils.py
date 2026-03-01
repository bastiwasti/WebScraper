"""Utility functions for date, time, and city normalization.

This module provides standardization functions for handling various date, time,
and city formats encountered in different event sources.

Usage:
    from rules import utils

    # Normalize date to DD.MM.YYYY
    date = utils.normalize_date("2026-02-16")
    # Returns: "16.02.2026"

    # Normalize time to HH:MM
    time = utils.normalize_time("14:30 Uhr")
    # Returns: "14:30"

    # Normalize city to lowercase
    city = utils.normalize_city("Leverkusen", "Leverkusen")
    # Returns: "leverkusen"
"""

import re
from datetime import datetime, timedelta
from typing import Optional


def normalize_date(date_str: str) -> str:
    """Normalize any date format to DD.MM.YYYY format.

    Handles these formats:
    - DD.MM.YYYY (already standard)
    - D.M.YYYY (day without leading zero)
    - YYYY-MM-DD (ISO format)
    - DD. MonthName YYYY (e.g., "16. Februar 2026")
    - ISO 8601 datetime (e.g., "2026-02-16T14:30:00")

    Args:
        date_str: Date string in any supported format.

    Returns:
        Normalized date in DD.MM.YYYY format, or empty string if parsing fails.

    Examples:
        >>> normalize_date("2026-02-16")
        '16.02.2026'
        >>> normalize_date("16.02.2026")
        '16.02.2026'
        >>> normalize_date("5.3.2026")
        '05.03.2026'
        >>> normalize_date("16. Februar 2026")
        '16.02.2026'
        >>> normalize_date("2026-02-16T14:30:00")
        '16.02.2026'
        >>> normalize_date("")
        ''
    """
    if not date_str:
        return ""

    date_str = date_str.strip()

    # Check if already in DD.MM.YYYY or D.M.YYYY format
    ddmm_yyyy_pattern = r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$'
    match = re.match(ddmm_yyyy_pattern, date_str)
    if match:
        day, month, year = match.groups()
        return f"{day.zfill(2)}.{month.zfill(2)}.{year}"

    # Handle ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
    iso_pattern = r'^(\d{4})-(\d{2})-(\d{2})'
    iso_match = re.match(iso_pattern, date_str)
    if iso_match:
        year, month, day = iso_match.groups()
        return f"{day.zfill(2)}.{month.zfill(2)}.{year}"

    # Handle DD. MonthName YYYY format (German month names)
    month_names = {
        "januar": "01", "februar": "02", "märz": "03", "april": "04",
        "mai": "05", "juni": "06", "juli": "07", "august": "08",
        "september": "09", "oktober": "10", "november": "11", "dezember": "12",
    }
    day_monthname_pattern = r'^(\d{1,2})\.?\s+([a-zA-Zäöü]+)\s+(\d{4})$'
    dmy_match = re.match(day_monthname_pattern, date_str, re.IGNORECASE)
    if dmy_match:
        day, month_name, year = dmy_match.groups()
        month_lower = month_name.lower()
        month_num = month_names.get(month_lower, None)
        if month_num:
            return f"{day.zfill(2)}.{month_num}.{year}"

    # Return original if no format matched
    return date_str


def normalize_time(time_str: str) -> str:
    """Normalize any time format to HH:MM format.

    Handles these formats:
    - HH:MM (already standard)
    - HH.MM (dot separator)
    - HH:MM Uhr (with "Uhr" suffix)
    - HH.MM Uhr (dot separator with suffix)
    - HH:MM - HH:MM (time range)

    Args:
        time_str: Time string in any supported format.

    Returns:
        Normalized time in HH:MM format, or empty string if parsing fails.

    Examples:
        >>> normalize_time("14:30")
        '14:30'
        >>> normalize_time("14.30")
        '14:30'
        >>> normalize_time("14:30 Uhr")
        '14:30'
        >>> normalize_time("14.30 Uhr")
        '14:30'
        >>> normalize_time("14:30 - 16:30")
        '14:30 - 16:30'
        >>> normalize_time("")
        ''
    """
    if not time_str:
        return ""

    time_str = time_str.strip()

    # Remove "Uhr" suffix and normalize separators
    time_str = re.sub(r'\s*Uhr\b', '', time_str, flags=re.IGNORECASE)
    time_str = time_str.replace('.', ':').strip()

    # Handle time range (HH:MM - HH:MM)
    time_range_pattern = r'^(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})$'
    range_match = re.match(time_range_pattern, time_str)
    if range_match:
        start, end = range_match.groups()
        return f"{start} - {end}"

    # Handle single time (HH:MM)
    time_pattern = r'^(\d{1,2}):(\d{2})$'
    match = re.match(time_pattern, time_str)
    if match:
        hours, minutes = match.groups()
        return f"{hours.zfill(2)}:{minutes}"

    # Return original if no format matched
    return time_str


def is_within_14_days(date_str: str) -> bool:
    """Check if a date is within 14 days from today.

    Args:
        date_str: Date string in DD.MM.YYYY format.

    Returns:
        True if date is within 14 days from today, False otherwise.
        Returns True for invalid dates (to not filter out events with bad dates).

    Examples:
        >>> is_within_14_days("16.02.2026")  # Assuming today is 2026-02-16
        True
        >>> is_within_14_days("01.02.2026")  # 15 days ago
        False
    """
    if not date_str:
        return True  # Keep events without dates

    try:
        event_date = datetime.strptime(date_str, "%d.%m.%Y")
        today = datetime.now()
        date_range = timedelta(days=14)
        return today <= event_date <= today + date_range
    except ValueError:
        # Invalid date format, keep the event
        return True


def is_within_date_range(start_date: str, end_date: str, days: int = 14) -> bool:
    """Check if a date range is within specified days from today.

    Args:
        start_date: Start date string in DD.MM.YYYY format.
        end_date: End date string in DD.MM.YYYY format.
        days: Number of days to check from today. Defaults to 14.

    Returns:
        True if any date in range is within specified days from today.
    """
    if not start_date and not end_date:
        return True

    try:
        today = datetime.now()
        date_range = timedelta(days=days)

        if start_date:
            start = datetime.strptime(start_date, "%d.%m.%Y")
            if today <= start <= today + date_range:
                return True

        if end_date:
            end = datetime.strptime(end_date, "%d.%m.%Y")
            if today <= end <= today + date_range:
                return True

        return False
    except ValueError:
        return True


def extract_end_time(time_range: str) -> Optional[str]:
    """Extract end time from a time range string.

    Args:
        time_range: Time range string (e.g., "14:30 - 16:30").

    Returns:
        End time in HH:MM format, or None if not a range.
    """
    if not time_range:
        return None

    time_range_pattern = r'^\d{1,2}:\d{2}\s*-\s*(\d{1,2}:\d{2})$'
    match = re.match(time_range_pattern, time_range.strip())
    if match:
        return match.group(1)

    return None


def extract_start_time(time_range: str) -> Optional[str]:
    """Extract start time from a time range string.

    Args:
        time_range: Time range string (e.g., "14:30 - 16:30").

    Returns:
        Start time in HH:MM format, or None if not a range.
    """
    if not time_range:
        return None

    time_range_pattern = r'^(\d{1,2}:\d{2})\s*-\s*\d{1,2}:\d{2}$'
    match = re.match(time_range_pattern, time_range.strip())
    if match:
        return match.group(1)

    return None


def normalize_city(raw_city: str, default_city: str) -> str:
    """Normalize city name to standard format (lowercase).
    
    Handles these variations:
    - Case variations: "Leverkusen" → "leverkusen"
    - Numeric prefixes: "51379 Leverkusen" → "leverkusen"
    - Empty values: Returns default_city (lowercase)
    
    Args:
        raw_city: Raw city name from API or other source.
        default_city: Fallback city name (e.g., from folder hierarchy).
    
    Returns:
        Normalized lowercase city name.
    
    Examples:
        >>> normalize_city("Leverkusen", "Leverkusen")
        'leverkusen'
        >>> normalize_city("51379 Leverkusen", "Leverkusen")
        'leverkusen'
        >>> normalize_city("", "Leverkusen")
        'leverkusen'
        >>> normalize_city("leverkusen", "Leverkusen")
        'leverkusen'
    """
    if not raw_city:
        return default_city.lower()
    
    # Remove numeric prefixes (e.g., "51379 Leverkusen" → "Leverkusen")
    city_cleaned = re.sub(r'^\d+\s+', '', raw_city.strip())
    
    # Return lowercase version
    return city_cleaned.lower()


# City name mappings for aggregator sources (rausgegangen, etc.)
# Maps city names from aggregators to internal normalized names
AGGREGATOR_CITY_MAPPING = {
    "monheim am rhein": "monheim_am_rhein",
    "leverkusen": "leverkusen",
    "langenfeld": "langenfeld",
    "hilden": "hilden",
    "dormagen": "dormagen",
    "burscheid": "burscheid",
    "leichlingen": "leichlingen",
    "hitdorf": "hitdorf",
    "ratingen": "ratingen",
    "solingen": "solingen",
    "haan": "haan",
    "düsseldorf": "dusseldorf",
    "köln": "koeln",
}


# Standard city names (underscore format)
# All city names in the system must match this format
STANDARD_CITIES = {
    "monheim_am_rhein",
    "langenfeld",
    "leverkusen",
    "hilden",
    "dormagen",
    "hitdorf",
    "leichlingen",
    "burscheid",
    "solingen",
    "neuss",
    "koeln",
    "ratingen",
    "haan",
    "bergisch_gladbach",
    "grevenbroich",
    "pulheim",
    "wuppertal",
    "mettmann",
    "erkrath",
    "frechen",
}


def extract_city_from_address(address_locality: str, postal_code: str, default_city: str = "") -> str:
    """Extract city name from address fields, handling swapped postal codes.
    
    Some aggregators (like rausgegangen) may have swapped address fields:
    - addressLocality: "42719" (postal code)
    - postalCode: "Solingen" (city name)
    
    This function detects this situation and returns the correct city name.
    
    Args:
        address_locality: Value from addressLocality field.
        postal_code: Value from postalCode field.
        default_city: Fallback city name if both fields fail.
    
    Returns:
        Normalized lowercase city name.
    
    Examples:
        >>> extract_city_from_address("42719", "Solingen", "monheim_am_rhein")
        'solingen'
        >>> extract_city_from_address("Solingen", "42719", "monheim_am_rhein")
        'solingen'
        >>> extract_city_from_address("Leverkusen", "51379", "monheim_am_rhein")
        'leverkusen'
    """
    import re
    
    # Pattern to detect 5-digit postal codes (German format)
    postal_pattern = r'^\d{5}$'
    
    # Check if addressLocality is a postal code
    if address_locality and re.match(postal_pattern, address_locality.strip()):
        # addressLocality is a postal code, try postal_code for city
        if postal_code and not re.match(postal_pattern, postal_code.strip()):
            # postal_code looks like a city name
            return normalize_city(postal_code, default_city)
    
    # Use addressLocality as primary (standard case)
    if address_locality:
        return normalize_city(address_locality, default_city)
    
    # Try postal_code as fallback
    if postal_code:
        return normalize_city(postal_code, default_city)
    
    # No valid city found, use default
    return default_city.lower() if default_city else ""


def map_aggregator_city(raw_city: str, default_city: str = "") -> str:
    """Map aggregator city name to normalized internal city name.
    
    This function handles city mapping for aggregator sources like rausgegangen,
    which may return city names in different formats than our internal system.
    
    Args:
        raw_city: City name from aggregator source (e.g., "Monheim am Rhein").
        default_city: Fallback city name if mapping fails.
    
    Returns:
        Normalized lowercase city name matching internal system.
        Returns empty string if raw_city is empty and no default provided.
    
    Examples:
        >>> map_aggregator_city("Monheim am Rhein", "monheim_am_rhein")
        'monheim_am_rhein'
        >>> map_aggregator_city("Leverkusen", "monheim_am_rhein")
        'leverkusen'
        >>> map_aggregator_city("Düsseldorf", "")
        'dusseldorf'
    """
    if not raw_city:
        return default_city.lower() if default_city else ""
    
    city_lower = raw_city.lower().strip()
    
    # Direct mapping lookup
    if city_lower in AGGREGATOR_CITY_MAPPING:
        return AGGREGATOR_CITY_MAPPING[city_lower]
    
    # If not found in mapping, try normalize_city as fallback
    # This handles cases like "Leverkusen" → "leverkusen"
    return normalize_city(raw_city, default_city)


def validate_city(city: str) -> tuple[bool, str]:
    """Validate city name against standard format.
    
    Checks if city name matches standard underscore format (e.g., "monheim_am_rhein").
    
    Args:
        city: City name to validate.
    
    Returns:
        Tuple of (is_valid, normalized_city):
        - is_valid: True if city is in standard format
        - normalized_city: Normalized city name (if applicable)
    
    Examples:
        >>> validate_city("monheim_am_rhein")
        (True, 'monheim_am_rhein')
        >>> validate_city("monheim")
        (False, 'monheim_am_rhein')
        >>> validate_city("monheim am rhein")
        (False, 'monheim_am_rhein')
    """
    if not city:
        return False, ""
    
    city_lower = city.lower().strip()
    
    # Check if already in standard format
    if city_lower in STANDARD_CITIES:
        return True, city_lower
    
    # Try to normalize common variations
    # "monheim" -> "monheim_am_rhein"
    # "monheim am rhein" -> "monheim_am_rhein"
    if city_lower == "monheim":
        return False, "monheim_am_rhein"
    
    if city_lower in ["monheim am rhein", "monheim am rhein", "monheim am rhein"]:
        return False, "monheim_am_rhein"
    
    # Check other common patterns
    for standard_city in STANDARD_CITIES:
        if city_lower.replace(" ", "_") == standard_city:
            return False, standard_city
        if city_lower.replace("_", " ") == standard_city:
            return False, standard_city
    
    # City not in standard format and no normalization found
    return False, city_lower


def normalize_city_name(city: str) -> str:
    """Normalize city name to standard underscore format.
    
    Converts common city name variations to standard underscore format:
    - "Monheim am Rhein" -> "monheim_am_rhein"
    - "Düsseldorf" -> "dusseldorf"
    - "Köln" -> "koeln"
    - Already normalized names are returned unchanged
    
    Args:
        city: City name to normalize.
    
    Returns:
        Normalized city name in underscore format.
    
    Examples:
        >>> normalize_city_name("Monheim am Rhein")
        'monheim_am_rhein'
        >>> normalize_city_name("Düsseldorf")
        'dusseldorf'
        >>> normalize_city_name("monheim_am_rhein")
        'monheim_am_rhein'
    """
    if not city:
        return ""
    
    city_lower = city.lower().strip()
    
    # Direct mapping from AGGREGATOR_CITY_MAPPING
    if city_lower in AGGREGATOR_CITY_MAPPING:
        return AGGREGATOR_CITY_MAPPING[city_lower]
    
    # Already in standard format
    if city_lower in STANDARD_CITIES:
        return city_lower
    
    # Try common variations
    if city_lower == "monheim":
        return "monheim_am_rhein"
    
    if city_lower in ["monheim am rhein", "monheim am rhein", "monheim am rhein"]:
        return "monheim_am_rhein"
    
    # Return original if no normalization found
    return city_lower
