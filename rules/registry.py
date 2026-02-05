"""Rule registry - dynamically maps URLs to appropriate scrapers and regex parsers.

This registry auto-discovers all scraper.py and regex.py files from:
- rules/cities/*/subfolder/
- rules/aggregators/*

And provides a unified interface for getting rules by URL.
"""

import importlib
import os
from pathlib import Path
from typing import Dict, Type, Optional, Union

from .base import BaseRule, BaseScraper
from .urls import CITY_URLS


class RuleEntry:
    """Registry entry for a URL rule."""

    def __init__(self, url: str, scraper_class: Type[BaseScraper], regex_class: Type[BaseRule]):
        self.url = url
        self.scraper_class = scraper_class
        self.regex_class = regex_class

    def __repr__(self) -> str:
        return f"RuleEntry(url={self.url}, scraper={self.scraper_class.__name__}, regex={self.regex_class.__name__})"


def _import_module(module_path: str) -> Optional[object]:
    """Import a module by path.

    Args:
        module_path: Python module path (e.g., "rules.cities.monheim.terminkalender.scraper")

    Returns:
        Module object or None if import fails.
    """
    try:
        return importlib.import_module(module_path)
    except (ImportError, ModuleNotFoundError) as e:
        print(f"Warning: Failed to import {module_path}: {e}")
        return None


def _discover_rules() -> Dict[str, RuleEntry]:
    """Auto-discover all scraper.py and regex.py files from rules/ directory.

    Populates and returns global registry dict.
    """
    rules_dir = Path(__file__).parent
    registry = {}

    # Discover city rules
    for city_key, url_dict in CITY_URLS.items():
        for subfolder_key, url in url_dict.items():
            # Expected module paths:
            # With subfolder: rules.cities.{city}.{subfolder}.scraper
            # Without subfolder: rules.cities.{city}.scraper

            # Try with subfolder first
            base_path = f"rules.cities.{city_key}.{subfolder_key}"
            scraper_module = _import_module(f"{base_path}.scraper")
            regex_module = _import_module(f"{base_path}.regex")

            # If subfolder failed, try without subfolder
            if not scraper_module:
                base_path = f"rules.cities.{city_key}"
                scraper_module = _import_module(f"{base_path}.scraper")
            if not regex_module:
                base_path = f"rules.cities.{city_key}"
                regex_module = _import_module(f"{base_path}.regex")

            if scraper_module and regex_module:
                # Find rule classes in each module
                scraper_class = None
                regex_class = None

                for attr_name in dir(scraper_module):
                    attr = getattr(scraper_module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, BaseScraper) and
                        attr != BaseScraper and
                        attr_name.endswith("Scraper")):
                        scraper_class = attr
                        break

                for attr_name in dir(regex_module):
                    attr = getattr(regex_module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, BaseRule) and
                        attr != BaseRule and
                        attr_name.endswith("Rule") or attr_name.endswith("Regex")):
                        regex_class = attr
                        break

                if scraper_class and regex_class:
                    registry[url] = RuleEntry(url, scraper_class, regex_class)
                    print(f"Registered: {city_key}/{subfolder_key} -> {url}")
                else:
                    print(f"Warning: Could not find rule classes for {base_path}")
 
    return registry


# Global registry: URL -> RuleEntry
_RULE_REGISTRY: Dict[str, RuleEntry] = {}


def _ensure_initialized() -> None:
    """Ensure registry is initialized (lazy initialization)."""
    global _RULE_REGISTRY
    if not _RULE_REGISTRY:
        _RULE_REGISTRY = _discover_rules()


def get_rule(url: str) -> Optional[RuleEntry]:
    """Get rule entry for a given URL.

    Args:
        url: The URL to find a rule for.

    Returns:
        RuleEntry with scraper and regex classes, or None if not found.
    """
    _ensure_initialized()
    return _RULE_REGISTRY.get(url)


def get_rule_or_raise(url: str) -> RuleEntry:
    """Get rule entry for a given URL, raise error if not found.

    Args:
        url: The URL to find a rule for.

    Returns:
        RuleEntry with scraper and regex classes.

    Raises:
        ValueError: If no rule found for URL.
    """
    rule = get_rule(url)
    if not rule:
        raise ValueError(f"No rule found for URL: {url}")
    return rule


def list_registered_rules() -> Dict[str, RuleEntry]:
    """Return all registered rules.

    Returns:
        Dictionary mapping URLs to RuleEntry objects.
    """
    _ensure_initialized()
    return _RULE_REGISTRY.copy()


def list_registered_urls() -> list[str]:
    """Return list of all registered URLs.

    Returns:
        List of URL strings.
    """
    _ensure_initialized()
    return list(_RULE_REGISTRY.keys())


def get_scraper_for_url(url: str) -> Type[BaseScraper]:
    """Get scraper class for a given URL.

    Args:
        url: The URL to find a scraper for.

    Returns:
        Scraper class (subclass of BaseScraper).

    Raises:
        ValueError: If no scraper found for URL.
    """
    rule = get_rule_or_raise(url)
    return rule.scraper_class


def get_regex_for_url(url: str) -> Type[BaseRule]:
    """Get regex class for a given URL.

    Args:
        url: The URL to find a regex parser for.

    Returns:
        Regex class (subclass of BaseRule).

    Raises:
        ValueError: If no regex parser found for URL.
    """
    rule = get_rule_or_raise(url)
    return rule.regex_class


def create_scraper(url: str) -> BaseScraper:
    """Create a scraper instance for given URL.

    Args:
        url: The URL to create a scraper for.

    Returns:
        Scraper instance (BaseScraper subclass).
    """
    scraper_class = get_scraper_for_url(url)
    return scraper_class(url)


def create_regex(url: str) -> BaseRule:
    """Create a regex parser instance for given URL.

    Args:
        url: The URL to create a regex parser for.

    Returns:
        Regex parser instance (BaseRule subclass).
    """
    regex_class = get_regex_for_url(url)
    return regex_class(url)


def reinitialize_registry() -> None:
    """Force re-discovery and re-initialization of registry.

    This is useful for testing or when adding new rules dynamically.
    """
    global _RULE_REGISTRY
    _RULE_REGISTRY = {}
    _discover_rules()


# Initialize registry on module import
try:
    _ensure_initialized()
except Exception as e:
    print(f"Warning: Failed to initialize rule registry: {e}")
    _RULE_REGISTRY = {}
