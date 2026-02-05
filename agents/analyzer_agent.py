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
- "category": string - Kategorisieren Sie als einen dieser: "family" (familienfreundlich), "adult" (für Erwachsene), "sport" (Sportveranstaltung), "other" (alle anderen)

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
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                temperature=0.0,
            )
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ])

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

    def _split_into_chunks(self, raw_event_text: str, events_per_chunk: int = 5) -> list[str]:
        """Split raw event text into chunks of events."""
        events_pattern = r'\*\s+\*\*Event:\*\*'
        event_blocks = re.split(events_pattern, raw_event_text)
        
        if len(event_blocks) <= 1:
            return [raw_event_text]
        
        chunks = []
        for i in range(1, len(event_blocks), events_per_chunk):
            batch = event_blocks[i:i+events_per_chunk]
            chunk = '\n*   **Event:**'.join([''] + batch)
            chunks.append(chunk.strip())
        
        return chunks

    def _infer_category(self, description: str, name: str = "") -> str:
        """Infer category from event description and name."""
        text = (description + " " + name).lower()
        
        category_keywords = {
            "family": ["familie", "kinder", "jugend", "kind", "baby", "schule", "eltern", "familien"],
            "adult": ["erwachsen", "adult", "senior", "abend", "nacht", "bar", "club", "party"],
            "sport": ["sport", "fitness", "laufen", "schwimmen", "rad", "fußball", "tennis", "yoga"],
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in text for kw in keywords):
                return category
        
        return "other"

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

    def run(self, run_id: int, raw_event_text: str, scraper_run_id: int | None = None, save_to_db: bool = False, chunk_size: int = 5, url_metrics: dict | None = None) -> list[dict[str, Any]]:
        """Analyze raw event text and return a list of structured event dicts (name, description, location, date, time, source, city).

        Args:
            run_id: The pipeline run_id (from create_run). Required for tracking.
            raw_event_text: Raw text containing event information
            scraper_run_id: Run ID of the scraper agent (for linking)
            save_to_db: Whether to save events to database
            chunk_size: Number of events to process per LLM call (default: 5)
            url_metrics: URL metrics from scraper containing city information

        Returns:
            List of structured event dicts.
        """
        all_events = []
        chunks = self._split_into_chunks(raw_event_text, events_per_chunk=chunk_size)
        
        print(f"Processing {len(chunks)} chunk(s) with {chunk_size} events each...")
        
        for i, chunk in enumerate(chunks, 1):
            print(f"  Processing chunk {i}/{len(chunks)}...")
            chain = self._prompt | self.llm | StrOutputParser()
            out = chain.invoke({"raw_event_text": chunk})
            events = self._parse_json_array(out)
            
            for event in events:
                # Normalize German field names to English database schema
                event = self._normalize_field_names(event)
                source = event.get("source", "")
                city = self._infer_city_from_source(source, url_metrics)
                event["city"] = city
            
            all_events.extend(events)
            print(f"    Extracted {len(events)} events from chunk {i}")

        if save_to_db and all_events:
            from storage import insert_events, update_run_status_analyzed

            # Use provided run_id or scraper_run_id
            target_run_id = run_id if run_id else scraper_run_id

            # Calculate totals
            events_found = len(all_events)
            valid_events = 0
            for e in all_events:
                if e.get("name") and e.get("date") and e.get("location") and e.get("source"):
                    valid_events += 1

            # Update status with ADD (not REPLACE)
            update_run_status_analyzed(
                target_run_id,
                events_found,
                valid_events,
                linked_run_id=scraper_run_id,
            )
            insert_events(all_events, target_run_id)

        return all_events
