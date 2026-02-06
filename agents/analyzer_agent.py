"""Agent 2: Analyzes raw event text and structures it (name, description, location, date, source) for storage and next agent."""

import json
import re
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

from storage import create_run_status


SYSTEM_PROMPT = """Sie sind ein Datenanalyst. Sie erhalten einen Text, der lokale Veranstaltungen beschreibt (aus Websuche/Zusammenfassungen).
Ihre Aufgabe ist es, jedes Ereignis zu extrahieren und als einzelnes JSON-Array von Objekten auszugeben. Jedes Objekt muss genau diese Felder enthalten:
- "name": string (Ereignistitel) - Verwenden Sie EXAKT dieselben Wörter wie im Original
- "description": string (kurze Beschreibung oder Kategorie) - Verwenden Sie EXAKT dieselben Wörter wie im Original
- "location": string (Veranstaltungsort oder Ort) - Verwenden Sie EXAKT dieselben Wörter wie im Original
- "date": string (z.B. "2025-02-01" oder "Samstag 1. Februar") - Verwenden Sie EXAKT dieselben Wörter wie im Original
- "time": string (z.B. "14:00" oder "ganzen Tag") oder leere Zeichenkette, wenn unbekannt
- "source": string (URL oder Name der Website, wo das Ereignis gefunden wurde; erforderlich)
- "category": string - Kategorisieren Sie als einen dieser: "Bildende Kunst & Ausstellungen", "Live-Musik & Konzerte", "Darstellende Kunst & Theater", "Gemeinschaft & Kulturfeste", "Vorträge & Bildungsveranstaltungen", "Film & Kino", "Kulinarik & Gastronomie", "Club & Live-Musik-Abende", "Sonstige" (für alle anderen Events, die nicht in die anderen Kategorien passen)

KATEGORIEN:
- "Bildende Kunst & Ausstellungen": Ausstellungen, Kunstpräsentationen, Vernissagen, Finissagen, Malerei, Fotografie, Installationen
- "Live-Musik & Konzerte": Konzerte, Musikaufführungen, Orgelkonzerte, Jazz-Veranstaltungen, klassische Musik
- "Darstellende Kunst & Theater": Theateraufführungen, Komödien, Musicals, Kabarett, Schauspiel
- "Gemeinschaft & Kulturfeste": Feste, Märkte, Karneval, Umzüge, Open-Air-Veranstaltungen, Kulturfeste
- "Vorträge & Bildungsveranstaltungen": Vorträge, Lesungen, Workshops, Informationsveranstaltungen, Bildungsangebote
- "Film & Kino": Filmvorführungen, Kinoevents, Filmabende
- "Kulinarik & Gastronomie": Weinproben, Essen & Trinken Events, Gastronomieführungen, kulinarische Erlebnisse
- "Club & Live-Musik-Abende": Live-Musik in Clubs/Bars, Bandabende, Clubnights (oft mehrere Bands)
- "Sonstige": Alle anderen Veranstaltungen, die nicht in die obigen Kategorien passen

WICHTIG: Verwenden Sie EXAKT dieselben Wörter wie im Original - kein Übersetzen, kein Umformulieren, kein Hinzufügen oder Entfernen von Informationen.
Wenn der Text "Zeugniswochenende" enthält, schreiben Sie "Zeugniswochenende", nicht "Weekend of Zeugnisausgabe".
Wenn der Text "Jugendberufshilfe" enthält, schreiben Sie "Jugendberufshilfe", nicht "Local youth career assistance providers".

Geben Sie NUR das JSON-Array aus, kein Markdown-Code-Fence, kein zusätzlicher Text. Wenn keine Ereignisse vorhanden sind, geben Sie [] aus."""

USER_PROMPT = """Extrahieren Sie alle Ereignisse aus diesem Text in ein JSON-Array (enthält die Quelle für jedes Ereignis).

WICHTIG: Behalten Sie EXAKT dieselben Wörter wie im Original - kein Übersetzen, kein Umformulieren.
Wenn die JSON Felder in Deutsch sind (datum, uhrzeit, ort, beschreibung, quelle), behalten Sie diese Feldnamen.
Wenn die JSON Felder in Englisch sind (date, time, location, description, source), behalten Sie diese Feldnamen.

{raw_event_text}
"""


class AnalyzerAgent:
    """Takes raw event summary text and returns structured event list (list of dicts) with source."""

    def __init__(self, model: str | None = None, base_url: str | None = None):
        from config import LLM_PROVIDER

        if LLM_PROVIDER == "deepseek" and DEEPSEEK_API_KEY:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model or DEEPSEEK_MODEL,
                api_key=lambda: DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                temperature=0.0,
                timeout=600,
            )
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ])

    def _extract_pre_structured_events(self, text: str) -> list[dict[str, Any]]:
        """Extract JSON events from pre-structured text (from scraper LLM fallback)."""
        events = []
        
        # Pattern to find JSON content between "- Event:" and "  Date/Time:" or next event
        # This captures all text including markdown code fences
        event_blocks = re.findall(r'- Event:\s*([\s\S]*?)\n\s*(?:- Event:|Date/Time:)', text)
        
        for event_block in event_blocks:
            # Remove markdown code fences if present
            event_block = re.sub(r'```json\s*', '', event_block)
            event_block = re.sub(r'```\s*$', '', event_block)
            event_block = event_block.strip()
            
            if not event_block:
                continue
            
            try:
                data = json.loads(event_block)
                
                # Handle both formats:
                # 1. [{"name": "...", ...}, ...] (array of events)
                # 2. {"events": [...]} (wrapper with events key)
                # 3. {"name": "...", ...} (single event object)
                
                if isinstance(data, list):
                    events.extend(data)
                elif isinstance(data, dict):
                    if "events" in data:
                        events_data = data["events"]
                        if isinstance(events_data, list):
                            events.extend(events_data)
                    else:
                        # Single event object
                        events.append(data)
            except json.JSONDecodeError:
                continue
        
        return events

    def _parse_json_array(self, text: str) -> list[dict[str, Any]]:
        """Try to extract a JSON array from the model output."""
        text = text.strip()
        if "```" in text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if match:
                text = match.group(1).strip()
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "events" in data:
                return data["events"]
            return [data] if isinstance(data, dict) else []
        except json.JSONDecodeError:
            return []

    def _split_into_chunks(self, raw_event_text: str, events_per_chunk: int = 3, max_chars: int = 5000) -> list[str]:
        """Split raw event text into chunks with event and character limits."""
        events_pattern = r'\*\s+\*\*Event:\*\*'
        event_blocks = re.split(events_pattern, raw_event_text)
        
        if len(event_blocks) <= 1:
            return [raw_event_text]
        
        chunks = []
        current_chunk = ['']
        current_chars = 0
        
        for i in range(1, len(event_blocks)):
            block = event_blocks[i]
            block_text = '\n*   **Event:**' + block
            
            if current_chars + len(block_text) > max_chars and current_chunk != ['']:
                chunks.append('\n'.join(current_chunk).strip())
                current_chunk = ['']
                current_chars = 0
            
            current_chunk.append(block_text)
            current_chars += len(block_text)
            
            if len(current_chunk) > events_per_chunk + 1:
                chunks.append('\n'.join(current_chunk).strip())
                current_chunk = ['']
                current_chars = 0
        
        if current_chunk != ['']:
            chunks.append('\n'.join(current_chunk).strip())
        
        return chunks

    def _infer_category(self, description: str | None, name: str = "") -> str:
        """Infer category from event description and name."""
        description = description or ""
        text = (description + " " + name).lower()
        
        category_keywords = {
            "Bildende Kunst & Ausstellungen": ["kunst", "ausstellung", "vernissage", "finissage", "maler", "fotograf", "installation"],
            "Live-Musik & Konzerte": ["konzert", "musik", "jazz", "orgel", "band", "live", "orchester", "musikschule", "singt", "sänger", "musical"],
            "Darstellende Kunst & Theater": ["theater", "komöd", "kabarett", "schauspiel", "komödie", "bühne", "drama"],
            "Gemeinschaft & Kulturfeste": ["fest", "markt", "karneval", "umzug", "kulturfest", "weihnachtsmarkt", "volksfest", "straße", "kinderzug", "rosenmontag", "karnevalszug", "veedelszoch"],
            "Vorträge & Bildungsveranstaltungen": ["vortrag", "lesung", "workshop", "bildung", "seminar", "kurs", "referat", "info", "diskussion", "café", "tref", "begegnungsstätte", "bibliothek", "digitalcafé"],
            "Film & Kino": ["film", "kino", "vorführung", "movie", "cinema", "filmaufführung"],
            "Kulinarik & Gastronomie": ["wein", "ess", "trink", "prob", "gastronom", "koch", "kulinar", "restaurant", "gastros", "beer", "bier", "kaffee", "kuchen", "tapas", "proben"],
            "Club & Live-Musik-Abende": ["rockin'", "rooster", "club", "open mic", "pub", "live night", "kneipenabend"],
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in text for kw in keywords):
                return category
        
        return "Sonstige"

    def _normalize_field_names(self, event: dict) -> dict:
        """Normalize German field names to English database schema.
        
        Maps:
        - datum → date
        - uhrzeit → time
        - ort → location
        - beschreibung → description
        - quelle → source
        """
        normalized = {}
        field_mapping = {
            'datum': 'date',
            'uhrzeit': 'time',
            'ort': 'location',
            'beschreibung': 'description',
            'quelle': 'source',
            'name': 'name',
        }

        for key, value in event.items():
            if key in field_mapping:
                normalized[field_mapping[key]] = value
            else:
                normalized[key] = value

        return normalized

    def _infer_city_from_source(self, source: str, url_metrics: dict | None = None) -> str:
        """Infer city from event source URL."""
        if url_metrics:
            for url, metrics in url_metrics.items():
                if url in source or source in url:
                    city = metrics.get('city', '')
                    if city:
                        return city
        
        from rules import get_city_for_url
        city = get_city_for_url(source)
        if city:
            return city
        return ''

    def _deduplicate_events(self, events: list[dict]) -> list[dict]:
        """Remove duplicate events based on name, location, and source."""
        seen = set()
        unique_events = []
        for event in events:
            if not event or not isinstance(event, dict):
                continue
            key = (str(event.get('name', '')).lower().strip(), 
                    str(event.get('location', '')).lower().strip(),
                    str(event.get('source', '')).lower().strip())
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        return unique_events

    def run(self, run_id: int, raw_event_text: str, scraper_run_id: int | None = None, save_to_db: bool = False, chunk_size: int = 3, max_chars: int = 5000, url_metrics: dict | None = None) -> list[dict[str, Any]]:
        """Analyze raw event text and return a list of structured event dicts (name, description, location, date, time, source, city).

        Args:
            run_id: The pipeline run_id (from create_run). Required for tracking.
            raw_event_text: Raw text containing event information
            scraper_run_id: Run ID of the scraper agent (for linking)
            save_to_db: Whether to save events to database
            chunk_size: Number of events to process per LLM call (default: 3)
            max_chars: Maximum characters per chunk to prevent timeout (default: 5000)
            url_metrics: URL metrics from scraper containing city information

        Returns:
            List of structured event dicts.
        """
        all_events = []
        
        # First, try to extract pre-structured JSON events from scraper
        pre_structured = self._extract_pre_structured_events(raw_event_text)
        if pre_structured:
            print(f"Found {len(pre_structured)} pre-structured events from scraper")
            
            for event in pre_structured:
                # Normalize German field names to English database schema
                normalized_event = self._normalize_field_names(event)
                source = normalized_event.get("source", "")
                city = self._infer_city_from_source(source, url_metrics)
                normalized_event["city"] = city
                # Infer category
                category = self._infer_category(
                    description=normalized_event.get("description", ""),
                    name=normalized_event.get("name", "")
                )
                normalized_event["category"] = category
                all_events.append(normalized_event)
            
            # Deduplicate events based on name, location, and source
            before_dedup = len(all_events)
            all_events = self._deduplicate_events(all_events)
            after_dedup = len(all_events)
            if before_dedup != after_dedup:
                print(f"  Deduplicated: {before_dedup} -> {after_dedup} events (removed {before_dedup - after_dedup} duplicates)")
            
            return all_events
        
        # If no pre-structured events, use LLM analyzer
        chunks = self._split_into_chunks(raw_event_text, events_per_chunk=chunk_size, max_chars=max_chars)
        
        print(f"Processing {len(chunks)} chunk(s) with {chunk_size} events each...")
        
        for i, chunk in enumerate(chunks, 1):
            print(f"  Processing chunk {i}/{len(chunks)}...")
            chain = self._prompt | self.llm | StrOutputParser()
            out = chain.invoke({"raw_event_text": chunk})
            events = self._parse_json_array(out)
            
            for event in events:
                # Normalize German field names to English database schema
                normalized_event = self._normalize_field_names(event)
                source = normalized_event.get("source", "")
                city = self._infer_city_from_source(source, url_metrics)
                normalized_event["city"] = city
                # Infer category
                category = self._infer_category(
                    description=normalized_event.get("description", ""),
                    name=normalized_event.get("name", "")
                )
                normalized_event["category"] = category
                all_events.append(normalized_event)
            print(f"    Extracted {len(events)} events from chunk {i}")
        
        # Deduplicate events based on name, location, and source
        before_dedup = len(all_events)
        all_events = self._deduplicate_events(all_events)
        after_dedup = len(all_events)
        if before_dedup != after_dedup:
            print(f"  Deduplicated: {before_dedup} -> {after_dedup} events (removed {before_dedup - after_dedup} duplicates)")
        
        return all_events
