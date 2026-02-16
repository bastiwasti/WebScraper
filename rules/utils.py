"""Utility functions for date and time normalization.

This module provides standardization functions for handling various date and time
formats encountered in different event sources.

Usage:
    from rules import utils

    # Normalize date to DD.MM.YYYY
    date = utils.normalize_date("2026-02-16")
    # Returns: "16.02.2026"

    # Normalize time to HH:MM
    time = utils.normalize_time("14:30 Uhr")
    # Returns: "14:30"
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
