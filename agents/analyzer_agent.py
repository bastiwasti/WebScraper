"""Agent 2: Analyzes raw event text and structures it (name, description, location, date, source) for storage and next agent."""

import json
import re
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import LLM_MODEL, OLLAMA_BASE_URL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


SYSTEM_PROMPT = """You are a data analyst. You receive a text that describes local events (from web search/summaries).
Your task is to extract every event and output a single JSON array of objects. Each object must have exactly these fields:
- "name": string (event title)
- "description": string (short summary or category)
- "location": string (venue or place)
- "date": string (e.g. "2025-02-01" or "Samstag 1. Februar")
- "time": string (e.g. "14:00" or "all day") or empty string if unknown
- "source": string (URL or website name where the event was found; required)
- "category": string - Categorize as one of: "family", "adult", "sport", "other" (based on event type, target audience, and content)
Output only the JSON array, no markdown code fence, no extra text. If there are no events, output []."""

USER_PROMPT = """Extract all events from this text into a JSON array (include source for each event):

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
                temperature=0.1,
            )
        else:
            from langchain_ollama import ChatOllama
            self.llm = ChatOllama(
                model=model or LLM_MODEL,
                base_url=base_url or OLLAMA_BASE_URL,
                temperature=0.1,
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

    def run(self, raw_event_text: str, scraper_run_id: int | None = None, save_to_db: bool = False, chunk_size: int = 5) -> list[dict[str, Any]]:
        """Analyze raw event text and return a list of structured event dicts (name, description, location, date, time, source).
        
        Args:
            raw_event_text: Raw text containing event information
            scraper_run_id: Run ID of the scraper agent (for linking)
            save_to_db: Whether to save events to database
            chunk_size: Number of events to process per LLM call (default: 5)
        """
        all_events = []
        chunks = self._split_into_chunks(raw_event_text, events_per_chunk=chunk_size)
        
        print(f"Processing {len(chunks)} chunk(s) with {chunk_size} events each...")
        
        for i, chunk in enumerate(chunks, 1):
            print(f"  Processing chunk {i}/{len(chunks)}...")
            chain = self._prompt | self.llm | StrOutputParser()
            out = chain.invoke({"raw_event_text": chunk})
            events = self._parse_json_array(out)
            all_events.extend(events)
            print(f"    Extracted {len(events)} events from chunk {i}")

        if save_to_db and all_events:
            from storage import create_run, insert_events, update_run_status_analyzed, create_run_status, update_run_status_complete
            run_id = create_run("analyzer", linked_run_id=scraper_run_id)
            create_run_status(run_id, [])
            insert_events(all_events, run_id)
            
            valid_events = 0
            for e in all_events:
                if e.get("name") and e.get("date") and e.get("location") and e.get("source"):
                    valid_events += 1
            
            update_run_status_complete(run_id)
            update_run_status_analyzed(run_id, len(all_events), valid_events, linked_run_id=scraper_run_id)

        return all_events
