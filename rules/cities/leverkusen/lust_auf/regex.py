"""HTML parser for Leverkusen Lust-Auf website.

The site no longer exposes the calendar REST API (wp-json/tribe/events 404s).
It renders "eventhub" cards server-side on /veranstaltungen/ with WordPress
pagination (/veranstaltungen/page/2/ — page 2 verified different from page 1).

This parser extracts events from the eventhub card markup (Level 1) and
enriches them from detail pages (Level 2): full description, end time,
categories and price.
"""

import re
import requests
from datetime import datetime, timedelta
from typing import List
from bs4 import BeautifulSoup
from rules.base import BaseRule, Event
from rules import categories

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
WINDOW_DAYS = 30


class LustAufRegex(BaseRule):
    """Eventhub-card parser for Lust-Auf Leverkusen.

    Level 1: server-rendered cards on /veranstaltungen/ (with /page/N/ pagination)
    Level 2: detail pages /veranstaltung/<slug>/ with description, end time,
             categories, price and organizer.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Lust-Auf pages."""
        return "lust-auf-leverkusen.de" in url

    def __init__(self, url: str):
        super().__init__(url)
        self.today = datetime.now()
        self.cutoff = self.today + timedelta(days=WINDOW_DAYS)

    def get_regex_patterns(self) -> List:
        """Empty - eventhub parsing uses BeautifulSoup instead."""
        return []

    @staticmethod
    def fetch_page(url: str, timeout: int = 25) -> str:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def parse_cards(raw_html: str) -> list[dict]:
        """Extract event data from eventhub cards.

        Returns list of dicts with keys: name, event_url, datetime_iso, venue.
        """
        soup = BeautifulSoup(raw_html, "html.parser")
        cards = soup.select("article.eventhub-card")
        result = []
        for card in cards:
            try:
                title_link = card.select_one(".eventhub-event-card__title a[href]")
                if not title_link:
                    continue
                name = title_link.get_text(strip=True)
                href = title_link.get("href", "").strip()
                if not name or not href:
                    continue

                time_elem = card.select_one("time[datetime]")
                dt_iso = time_elem.get("datetime", "").strip() if time_elem else ""

                venue_elem = card.select_one(".eventhub-event-card__venue-name")
                venue = venue_elem.get_text(strip=True) if venue_elem else ""

                if card.has_attr("aria-label"):
                    aria = card["aria-label"]
                    if aria.startswith("Event:") and not name:
                        name = aria[len("Event:"):].strip()

                result.append({
                    "name": name,
                    "event_url": href,
                    "datetime_iso": dt_iso,
                    "venue": venue,
                })
            except Exception as e:
                print(f"[LustAuf] Card parse failed: {e}")
                continue
        return result

    @staticmethod
    def parse_detail_page(detail_html: str) -> dict | None:
        """Parse event detail page (Level 2).

        Returns dict with detail_full_description, detail_end_time,
        detail_price, detail_categories or None.
        """
        soup = BeautifulSoup(detail_html, "html.parser")
        content = soup.select_one(".eventhub-hero-editorial__content")
        if not content:
            return None

        detail = {}

        paragraphs = [p.get_text(strip=True) for p in content.find_all("p")]
        descriptions = [p for p in paragraphs if len(p) > 50]
        if descriptions:
            detail["detail_full_description"] = "\n\n".join(descriptions[:4])
        elif content.get_text(strip=True):
            detail["detail_full_description"] = content.get_text(strip=True)[:2000]

        rows = content.select(".eventhub-hero-editorial__event-teaser, dl, table")
        details_text = " | ".join(r.get_text(" ", strip=True) for r in rows)

        raw = BeautifulSoup(re.sub(r"<[^>]*>", "|", details_text), "html.parser").get_text("|", strip=True)
        compressed = re.sub(r"\|+", "|", raw)

        time_row = re.search(r"Zeit:?\s*\|?\s*(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})", compressed)
        if time_row:
            detail["detail_time"] = time_row.group(1)
            detail["detail_end_time"] = time_row.group(2)

        price_row = re.search(r"Preis:?\s*\|?\s*([^|\n]{1,60})", compressed)
        if price_row:
            detail["detail_price"] = price_row.group(1).strip()

        cat_row = re.search(r"Kategorien:?\s*\|?\s*([^|\n]{1,80})", compressed)
        if cat_row:
            detail["detail_categories"] = cat_row.group(1).strip()

        return detail if detail else None

    def build_event_from_card(self, card: dict) -> Event | None:
        dt_iso = card.get("datetime_iso", "")
        if not dt_iso:
            return None
        try:
            dt = datetime.fromisoformat(dt_iso)
        except ValueError:
            return None

        date_str = dt.strftime("%d.%m.%Y")
        time_str = dt.strftime("%H:%M")
        if not (self.today.date() <= dt.date() <= self.cutoff.date()):
            return None

        return Event(
            name=card["name"],
            description="",
            location=card.get("venue", ""),
            date=date_str,
            time=time_str,
            source=self.url,
            category="other",
            city="Leverkusen",
            event_url=card["event_url"],
            origin=self.get_origin(),
        )

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse list page HTML into events (single page scheduling fallback)."""
        cards = self.parse_cards(raw_content)
        print(f"[LustAuf] Found {len(cards)} cards on page")
        events = []
        for card in cards:
            event = self.build_event_from_card(card)
            if event:
                events.append(event)
        print(f"[LustAuf] {len(events)} events within {WINDOW_DAYS}-day window")
        return events

    def fetch_level2_data(self, events: List[Event], raw_html: str | None = None) -> List[Event]:
        """Fetch detail pages: description, end time, categories, price."""
        if not events:
            return events

        print(f"[LustAuf Level 2] Fetching detail pages for {len(events)} events...")

        for event in events:
            if not event.event_url:
                continue

            try:
                print(f"  Fetching: {event.name[:50]}")
                detail_html = self.fetch_page(event.event_url, timeout=15)
                detail_data = self.parse_detail_page(detail_html)

                if detail_data:
                    event.raw_data = detail_data

                    full_desc = detail_data.get("detail_full_description", "")
                    if full_desc and not event.description:
                        event.description = full_desc

                    end_time = detail_data.get("detail_end_time", "")
                    if end_time:
                        event.end_time = end_time

                    cat_raw = detail_data.get("detail_categories", "")
                    if cat_raw:
                        event.category = categories.normalize_category(
                            categories.infer_category(cat_raw, event.name)
                        )

                    event.source = event.event_url
                    print(f"  ✓ Fetched details for: {event.name[:50]}")
                else:
                    print(f"  ✗ Failed to parse details for: {event.name[:50]}")

            except Exception as e:
                print(f"  ✗ Failed to fetch detail page {event.event_url}: {e}")
                continue

        print(f"[LustAuf Level 2] Completed: {sum(1 for e in events if e.raw_data)}/{len(events)} events with detail data")
        return events
