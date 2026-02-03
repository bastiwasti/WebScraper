"""Rule parser registry - maps URLs to appropriate parsers."""

from typing import List, Type, Optional
import re

from .base import BaseRuleParser

# Import all rule parsers
from .cities.monheim import MonheimRuleParser
from .cities.solingen import SolingenRuleParser
from .cities.haan import HaanRuleParser
from .cities.langenfeld import LangenfeldRuleParser
from .cities.leverkusen import LeverkusenRuleParser
from .cities.hilden import HildenRuleParser
from .cities.dormagen import DormagenRuleParser
from .cities.ratingen import RatingenRuleParser

from .aggregators.rausgegangen import RausgegangenRuleParser
from .aggregators.meetup import MeetupRuleParser
from .aggregators.eventbrite import EventbriteRuleParser
from .aggregators.static import StaticRuleParser

# Ordered list of parser classes (higher priority = tried first)
_RULE_PARSER_CLASSES: List[Type[BaseRuleParser]] = [
    # City-specific parsers (high priority)
    MonheimRuleParser,
    SolingenRuleParser,
    HaanRuleParser,
    LangenfeldRuleParser,
    LeverkusenRuleParser,
    HildenRuleParser,
    DormagenRuleParser,
    RatingenRuleParser,

    # Aggregator parsers (medium priority)
    RausgegangenRuleParser,
    MeetupRuleParser,
    EventbriteRuleParser,

    # Fallback parser (lowest priority)
    StaticRuleParser,
]


def get_rule_parser(url: str) -> BaseRuleParser:
    """Return the appropriate rule parser instance for the given URL.

    Args:
        url: The URL to parse.

    Returns:
        A rule parser instance that can handle the URL.

    Raises:
        ValueError: If no parser found for the URL.
    """
    for parser_class in _RULE_PARSER_CLASSES:
        if parser_class.can_handle(url):
            return parser_class(url)

    raise ValueError(f"No rule parser found for URL: {url}")


def register_rule_parser(parser_class: Type[BaseRuleParser]) -> None:
    """Register a new rule parser class.

    Newer parsers take priority over older ones, so insert at the beginning.

    Args:
        parser_class: A BaseRuleParser subclass.
    """
    _RULE_PARSER_CLASSES.insert(0, parser_class)


def list_rule_parsers() -> List[str]:
    """Return list of registered rule parser class names."""
    return [cls.__name__ for cls in _RULE_PARSER_CLASSES]
