"""Agent 2: Analyzes raw event text and structures it (name, description, location, date, source) for storage and next agent."""

import json
import re
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

from storage import create_run_status
from rules import categories


SYSTEM_PROMPT = """Sie sind ein Datenanalyst. Sie erhalten einen Text, der lokale Veranstaltungen beschreibt (aus Websuche/Zusammenfassungen).
Ihre Aufgabe ist es, jedes Ereignis zu extrahieren und als einzelnes JSON-Array von Objekten auszugeben. Jedes Objekt muss genau diese Felder enthalten:
- "name": string (Ereignistitel) - Verwenden Sie EXAKT dieselben Wörter wie im Original
- "description": string (kurze Beschreibung oder Kategorie) - Verwenden Sie EXAKT dieselben Wörter wie im Original
- "location": string (Veranstaltungsort oder Ort) - Verwenden Sie EXAKT dieselben Wörter wie im Original
- "date": string (z.B. "2025-02-01" oder "Samstag 1. Februar") - Verwenden Sie EXAKT dieselben Wörter wie im Original
- "time": string (z.B. "14:00" oder "ganzen Tag") oder leere Zeichenkette, wenn unbekannt
- "source": string (URL oder Name der Website, wo das Ereignis gefunden wurde; erforderlich)
- "category": string - Kategorisieren Sie als einen dieser: "family", "education", "sport", "culture", "market", "festival", "adult", "community", "other" (für alle anderen Events, die nicht in die anderen Kategorien passen)

KATEGORIEN:
- "family": Familienveranstaltungen, Kinder, Jugend, Eltern, Familientage, Kindertage
- "education": Kurse, Workshops, VHS, Volkshochschule, Bildung, Schulungen, Seminare, Vorträge, Bibliothek
- "sport": Sport, Fitness, Laufen, Schwimmen, Rad, Fußball, Tennis, Yoga, Wandern, Turniere, Jogging, Radfahren
- "culture": Ausstellungen, Konzerte, Theater, Film, Kino, Lesungen, Führungen, Kunst, Museum, Musik, Galerie, Oper, Orchester
- "market": Märkte, Flohmärkte, Verkaufsmärkte, Weihnachtsmärkte, Bauernmärkte, Handwerkermärkte
- "festival": Feste, Festivals, Karneval, Fastnacht, Kirmes, Volksfeste, Stadtfeste, Sommerfeste
- "adult": Erwachsene, Senioren, Abend, Nacht, Bar, Club, Party, Frauen, Damen, Nachtleben, Diskothek
- "community": Treffen, Vereine, Gruppen, Nachbarschaft, Soziales, Gemeinschaft, Bürgerverein, Sportvereine, Musikvereine
- "other": Alle anderen Veranstaltungen, die nicht in die obigen Kategorien passen

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
        
        # Pattern to find event blocks
        # Matches: "- Event:" followed by event name (first line)
        # Then captures all indented lines until next event or end
        event_blocks = re.findall(r'- Event:\s*([^\n]+(?:\n\s{2}[^\n]+)*)(?=\n\s*- Event:|\Z)', text)
        
        for event_block in event_blocks:
            event_block = event_block.strip()
            
            if not event_block:
                continue
            
            # Extract event name from first line
            lines = event_block.split('\n')
            if not lines:
                continue
            
            event_name = lines[0].strip()
            
            # Extract other fields from remaining lines
            event_data = {
                "name": event_name,
                "date": "",
                "time": "",
                "location": "",
                "description": "",
                "source": "",
                "raw_data": None,
            }
            
            for line in lines[1:]:  # Skip first line (name)
                line = line.strip()
                
                # Date (separate line)
                date_match = re.match(r'^Date:\s*(.+)', line)
                if date_match:
                    event_data["date"] = date_match.group(1).strip()
                    continue
                
                # Time (separate line)
                time_match = re.match(r'^Time:\s*(.+)', line)
                if time_match:
                    event_data["time"] = time_match.group(1).strip()
                    continue
                
                # Location/Venue
                loc_match = re.match(r'^Location/Venue:\s*(.+)', line)
                if loc_match:
                    event_data["location"] = loc_match.group(1).strip()
                    continue
                
                # Description/Category
                desc_match = re.match(r'^Description/Category:\s*(.+)', line)
                if desc_match:
                    event_data["description"] = desc_match.group(1).strip()
                    continue
                
                # Source
                source_match = re.match(r'^Source:\s*(.+)', line)
                if source_match:
                    event_data["source"] = source_match.group(1).strip()
                    continue
                
                # Level2_Data
                level2_match = re.match(r'^Level2_Data:\s*(.+)', line)
                if level2_match:
                    try:
                        level2_json = level2_match.group(1).strip()
                        event_data["raw_data"] = json.loads(level2_json)
                    except json.JSONDecodeError:
                        pass
                    continue
            
            # Build event object from parsed data
            if event_data["date"] or event_data["location"]:
                events.append(event_data)
        
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
        name = name or ""
        
        category = categories.infer_category(description, name)
        category = categories.normalize_category(category)
        
        return category

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
        
        # Special handling for datefix.de external event system
        # Dormagen uses datefix.de (dfxid parameter in URL)
        # Infer city from datefix domain to maintain correct mapping
        if 'datefix' in source.lower():
            return 'dormagen'
        
        return ''

    def _deduplicate_events(self, events: list[dict]) -> list[dict]:
        """Remove duplicate events based on event ID if available, otherwise name, location, date, and source."""
        seen = set()
        unique_events = []
        
        for event in events:
            if not event or not isinstance(event, dict):
                continue
            
            # Try to use event ID first (if provided by scraper)
            event_id = event.get('id', '')
            name = str(event.get('name', '')).lower().strip()
            location = str(event.get('location', '')).lower().strip()
            date = str(event.get('date', '')).lower().strip()
            source = str(event.get('source', '')).lower().strip()
            
            # Create unique key:
            # - If event has ID: use source + ID
            # - Otherwise: use (name, location, date, source) tuple to distinguish same event on different dates
            if event_id:
                key = f"{source}::{event_id}"
            else:
                key = (name, location, date, source)
            
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

    def analyze_events(self, events: list, url_metrics: dict | None = None) -> list[dict[str, Any]]:
        """Analyze structured Event objects from a single URL and return structured dicts.
        
        Args:
            events: List of Event objects from scraper
            url_metrics: URL metrics from scraper containing city information
        
        Returns:
            List of structured event dicts ready for database insertion.
        """
        all_events = []
        
        for event in events:
            if not event:
                continue
            
            event_dict = {
                "name": event.name,
                "description": event.description,
                "location": event.location,
                "date": event.date,
                "time": event.time,
                "source": event.source,
                "end_time": event.end_time,
                "city": event.city,
                "event_url": event.event_url,
                "raw_data": event.raw_data,
                "category": event.category if hasattr(event, 'category') else "other",
                "origin": event.origin,
            }
            
            infer_city = event.city or self._infer_city_from_source(event.source, url_metrics)
            event_dict["city"] = infer_city
            
            if not event_dict.get("category") or event_dict["category"] == "other":
                category = self._infer_category(event.description, event.name)
                event_dict["category"] = category
            
            all_events.append(event_dict)
        
        return all_events
