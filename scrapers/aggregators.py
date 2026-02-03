"""Regional event aggregators scraper."""

from typing import Optional

from .base import BaseScraper, _clean_text


class RausgegangenScraper(BaseScraper):
    """Scraper for Rausgegangen.de event listings."""

    def _fetch_static(self) -> str:
        """Fetch static content with improved text extraction."""
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(
            self.url,
            timeout=15,
            headers={"User-Agent": "WeeklyMail/1.0"},
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "form"]):
            tag.decompose()

        divs_to_remove = []
        for tag in soup.find_all("div"):
            classes = tag.get("class")
            if classes and isinstance(classes, list):
                class_str = " ".join(str(c) for c in classes if c).lower()
                if any(kw in class_str for kw in ["nav", "menu", "pagination", "search", "filter", "cookie", "consent", "modal"]):
                    divs_to_remove.append(tag)

        for tag in divs_to_remove:
            tag.decompose()

        all_text = soup.get_text(separator="\n", strip=True)

        lines = []
        skip_sections = ["Imprint", "Terms and Conditions", "Team", "Jobs", "Hilfe & Kontakt", "For organizers", "For Brands", "Log in", "Deutsch", "English", "Geheimkonzerte", "Love at First Slide", "Discover", "Download", "App", "now", "PICK OF THE DAY", "PRESENTED", "Sponsored"]

        for line in all_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            if any(skip_word in line for skip_word in skip_sections):
                continue

            if len(line) < 3:
                continue

            if line in lines:
                continue

            lines.append(line)

        cleaned_text = "\n".join(lines)

        return _clean_text(cleaned_text, max_chars=25000)

    @property
    def needs_browser(self) -> bool:
        """Rausgegangen site may need browser for dynamic content."""
        return False

    def fetch(self) -> str:
        """Fetch content."""
        return self._fetch_static()

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Rausgegangen event pages."""
        return "rausgegangen.de" in url


class MeetupScraper(BaseScraper):
    """Scraper for Meetup.com event listings."""

    def _fetch_static(self) -> str:
        """Fetch static content with improved text extraction."""
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(
            self.url,
            timeout=15,
            headers={
                "User-Agent": "WeeklyMail/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "form", "button"]):
            tag.decompose()

        divs_to_remove = []
        for tag in soup.find_all("div"):
            classes = tag.get("class")
            if classes and isinstance(classes, list):
                class_str = " ".join(str(c) for c in classes if c).lower()
                if any(kw in class_str for kw in ["nav", "menu", "pagination", "search", "filter", "cookie", "modal", "signup", "login"]):
                    divs_to_remove.append(tag)

        for tag in divs_to_remove:
            tag.decompose()

        all_text = soup.get_text(separator="\n", strip=True)

        lines = []
        skip_sections = ["Startseite", "Deutsch", "Anmelden", "Registrieren", "Events", "Gruppen", "Alle Veranstaltungen", "Neue Gruppen", "Beliebiger Tag", "Beliebiger Typ", "Innerhalb von", "Teilnehmer", "Hybrid", "Online", "Soziale Aktivitäten", "Hobbys und Leidenschaften", "Sport und Fitness", "Reisen und Outdoor", "Karriere und Beruf", "Technologie", "Community und Umwelt", "Identität und Sprache", "Spiele", "Tanzen", "Hilfe", "Unterstützung und Coaching", "Musik", "Gesundheit und Wellness", "Kunst und Kultur", "Wissenschaft und Bildung", "Tiere und Haustiere", "Religion und Spiritualität", "Schreiben", "Eltern und Familie", "Bewegungen und Politik"]

        for line in all_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            if any(skip_word in line for skip_word in skip_sections):
                continue

            if len(line) < 3:
                continue

            if line in lines:
                continue

            lines.append(line)

        cleaned_text = "\n".join(lines)

        return _clean_text(cleaned_text, max_chars=25000)

    @property
    def needs_browser(self) -> bool:
        """Meetup site may need browser for dynamic content."""
        return False

    def fetch(self) -> str:
        """Fetch content."""
        return self._fetch_static()

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Meetup event pages."""
        return "meetup.com" in url


class EventbriteScraper(BaseScraper):
    """Scraper for Eventbrite.de event listings."""

    def _fetch_static(self) -> str:
        """Fetch static content - Eventbrite blocks automated requests."""
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(
            self.url,
            timeout=15,
            headers={
                "User-Agent": "WeeklyMail/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        if resp.status_code == 405:
            return "Eventbrite blocks automated requests. Consider using manual search or API access."
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "form"]):
            tag.decompose()

        all_text = soup.get_text(separator="\n", strip=True)

        return _clean_text(all_text, max_chars=25000)

    @property
    def needs_browser(self) -> bool:
        """Eventbrite may need browser."""
        return False

    def fetch(self) -> str:
        """Fetch content."""
        return self._fetch_static()

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Eventbrite event pages."""
        return "eventbrite.de" in url or "eventbrite.com" in url
