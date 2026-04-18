"""Agent 3: Rates events based on family-friendliness for a family with 2 kids under 6 in Monheim am Rhein.

Supports two modes:
- Tool-calling mode (default): DeepSeek uses structured function calls to fetch events and submit ratings
- Legacy mode (--no-tools): Original prompt-in, JSON-out approach
"""

import json
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


SYSTEM_PROMPT = """Sie sind ein Elternpaar aus Monheim am Rhein mit zwei Kindern unter 6 Jahren. Sie bewerten lokale Veranstaltungen aus dieser Perspektive auf einer Skala von 1-5.

IHRE FAMILIE:
- 2 Erwachsene
- 2 Kinder (unter 6 Jahren)
- Wohnort: Monheim am Rhein
- Mobilität: Auto verfügbar, Bereitschaft bis 30km zu fahren

BEWERTUNGSKRITERIEN:

1. INHALTLICHE EIGNUNG (1-5):
   - Kindgerechte Themen (Tiere, Natur, Musik, Spielen, Basteln)
   - Angemessene Sprache (Deutsch, keine komplexen Themen)
   - Nicht zu überwältigend für Kleinkinder
   - 5 = Perfekt kindgerecht (Tiere, Spielplatz, Kindermusik)
   - 1 = Nicht kindgerecht (Politik, Wirtschaft, komplexe Vorträge)

2. ORT & ERREICHBARKEIT (1-5):
   - <= 10km: ideal (Monheim, Langenfeld, Leverkusen) → 5 Punkte
   - 10-20km: sehr gut (Hilden, Dormagen, Hitdorf) → 4 Punkte
   - 20-30km: akzeptabel (Leichlingen, Düsseldorf) → 3 Punkte
   - Parkplätze vorhanden? Kinderwagen-geeignet?
   - 5 = Parkplatz + kinderwagengeeignet + nahe
   - 1 = Weite Anfahrt + schlechte Parkmöglichkeiten

3. AUSSTATTUNG FÜR KLEINKINDER (1-5):
   - Wickelraum + Kinderwagen-geeignet + Spielbereich → 5 Punkte
   - Wickelraum + kinderwagengeeignet → 4 Punkte
   - Nur Wickelraum → 3 Punkte
   - Kinderwagen möglich, aber keine Extras → 2 Punkte
   - Keine kinderfreundliche Ausstattung → 1 Punkt
   WICHTIG: Mit 2 unter-6-Jährigen sind Wickelraum & Kinderwagen Pflicht!

4. INTERAKTIONSGRAD (1-5):
   - Kinder MITMACHEN (basteln, spielen, tanzen, etc.) → 5 Punkte
   - Stark interaktiv (Tierfüttern, Experimente) → 4 Punkte
   - Mittelmäßig (eher Zuschauen, aber ein bisschen aktiv) → 3 Punkte
   - Eher passiv (Konzert, Vorlesung) → 2 Punkte
   - Nur Zuschauen (Theater, Ausstellung ohne Aktiv) → 1 Punkt
   WICHTIG: Unter-6-Jährige können nicht stundenlang still sitzen!

5. KOSTEN FÜR FAMILIE (1-5):
   - Kostenlos → 5 Punkte
   - Kinder unter 6 kostenlos, Eltern günstig (< 20€) → 4 Punkte
   - Familienkarte/Gruppentarif verfügbar → 3 Punkte
   - Einzeltarif (50-100€ für Familie) → 2 Punkte
   - Teuer (> 100€ für Familie) → 1 Punkt
   FALLBACK: Wenn keine Preisinformation vorhanden → 3 Punkte (neutral)

GESAMTBEWERTUNG (1-5):
Bilden Sie einen Durchschnitt der 5 Kriterien und gewichten Sie nach Ihrem Eltern-Gefühl:
- 5 = PERFEKT für unsere Familie (würden wir auf jeden Fall hingehen)
- 4 = SEHR GUT (wahrscheinlich hin, würde uns freuen)
- 3 = GUT (in Betracht, vielleicht wenn nichts Besseres da ist)
- 2 = MÄßIG (eher nicht, nur in Ausnahmen)
- 1 = SCHLECHT (definitiv nicht, nicht geeignet)

Geben Sie NUR ein JSON-Array aus, mit den exakt folgenden Feldern:
event_id, rating, rating_inhaltlich, rating_ort, rating_ausstattung, rating_interaktion, rating_kosten, reason
"""

SYSTEM_PROMPT_TOOLS = SYSTEM_PROMPT + """
Sie haben zwei Werkzeuge zur Verfügung:
1. get_unrated_events - Holt unbewertete Veranstaltungen aus der Datenbank
2. submit_ratings - Speichert Ihre Bewertungen in der Datenbank

Arbeitsablauf:
1. Rufen Sie get_unrated_events auf, um eine Charge von Veranstaltungen zu erhalten
2. Bewerten Sie jede Veranstaltung nach den oben genannten Kriterien
3. Rufen Sie submit_ratings auf, um alle Bewertungen auf einmal zu speichern
4. Wiederholen Sie, bis keine unbewerteten Veranstaltungen mehr vorhanden sind
"""

USER_PROMPT = """Bewerten Sie die folgenden Veranstaltungen aus der Perspektive einer Familie mit 2 Kindern unter 6 Jahren aus Monheim am Rhein.

{events_json}
"""

# Simplified prompt for small models (e.g. Ollama gemma2:2b)
# Outputs only rating + reason, no sub-criteria. Max batch size: 3.
SIMPLE_PROMPT_SINGLE = """Bewerte diese Veranstaltung für eine Familie mit 2 Kleinkindern (unter 6 Jahre) aus Monheim am Rhein.

Skala:
5 = Perfekt für Kleinkinder (Spielen, Basteln, Tiere, Natur, kostenlos)
4 = Gut geeignet
3 = Geht so, vielleicht interessant
2 = Eher nicht für Kleinkinder
1 = Ungeeignet (Erwachsenenveranstaltung, weit weg, teuer)

WICHTIG: Prüfe start_datetime! Uhrzeit >= 18:00 = max. 2 (Kleinkinder schlafen). Veranstaltungen explizit für Kinder/Babys/Familien = 4-5.

Antworte NUR mit JSON, kein Text darum: {{"event_id": <id>, "rating": <1-5>, "reason": "<1 Satz auf Deutsch>"}}

Event:
{event_json}"""

SIMPLE_PROMPT_BATCH = """Bewerte diese Veranstaltungen für eine Familie mit 2 Kleinkindern (unter 6 Jahre) aus Monheim am Rhein.

Skala:
5 = Perfekt für Kleinkinder (Spielen, Basteln, Tiere, Natur, kostenlos)
4 = Gut geeignet
3 = Geht so, vielleicht interessant
2 = Eher nicht für Kleinkinder
1 = Ungeeignet (Erwachsenenveranstaltung, weit weg, teuer)

WICHTIG: Prüfe start_datetime! Uhrzeit >= 18:00 = max. 2 (Kleinkinder schlafen). Veranstaltungen explizit für Kinder/Babys/Familien = 4-5.

Antworte NUR mit JSON-Array, kein Text darum: [{{"event_id": <id>, "rating": <1-5>, "reason": "<1 Satz auf Deutsch>"}}]

Events:
{events_json}"""


# --- Tool schemas for DeepSeek function calling ---

GET_UNRATED_EVENTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_unrated_events",
        "description": "Fetch a batch of unrated events from the database. Returns event details including id, name, description, category, location, city, and start_datetime.",
        "parameters": {
            "type": "object",
            "title": "get_unrated_events",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of events to fetch (1-50)",
                    "default": 25
                }
            },
            "required": []
        }
    }
}

SUBMIT_RATINGS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "submit_ratings",
        "description": "Submit ratings for a batch of events. Each rating must include event_id, overall rating, 5 sub-criteria ratings, and a short reason.",
        "parameters": {
            "type": "object",
            "title": "submit_ratings",
            "properties": {
                "ratings": {
                    "type": "array",
                    "description": "Array of rating objects",
                    "items": {
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "integer", "description": "Event ID from get_unrated_events"},
                            "rating": {"type": "number", "description": "Overall rating 1.0-5.0"},
                            "rating_inhaltlich": {"type": "number", "description": "Content suitability 1.0-5.0"},
                            "rating_ort": {"type": "number", "description": "Location/accessibility 1.0-5.0"},
                            "rating_ausstattung": {"type": "number", "description": "Facilities for small children 1.0-5.0"},
                            "rating_interaktion": {"type": "number", "description": "Interaction level 1.0-5.0"},
                            "rating_kosten": {"type": "number", "description": "Cost for family 1.0-5.0"},
                            "reason": {"type": "string", "description": "Short explanation (max 200 chars)"}
                        },
                        "required": ["event_id", "rating", "rating_inhaltlich", "rating_ort",
                                     "rating_ausstattung", "rating_interaktion", "rating_kosten", "reason"]
                    }
                }
            },
            "required": ["ratings"]
        }
    }
}


class RatingAgent:
    """Rates events based on family-friendliness for a family with 2 kids under 6.

    Supports three modes:
    - Tool-calling (default): DeepSeek calls get_unrated_events/submit_ratings tools
    - Legacy (use_tools=False): Original prompt→JSON→parse approach
    - Simple (simple=True): Lightweight prompt for small models (Ollama), outputs rating+reason only, max batch 3
    """

    def __init__(self, model: str | None = None, use_tools: bool = True, run_id: int | None = None, simple: bool = False):
        from config import LLM_PROVIDER

        if LLM_PROVIDER == "deepseek" and DEEPSEEK_API_KEY:
            from langchain_openai import ChatOpenAI
            self.model_name = model or DEEPSEEK_MODEL
            self.llm = ChatOpenAI(
                model=self.model_name,
                api_key=lambda: DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                temperature=0.0,
                timeout=300,
            )
        elif LLM_PROVIDER == "ollama":
            from config import OLLAMA_BASE_URL, LLM_MODEL, OLLAMA_CLOUD_BASE_URL, OLLAMA_CLOUD_API_KEY, OLLAMA_CLOUD_MODEL
            from langchain_ollama import ChatOllama

            self.model_name = model or LLM_MODEL
            model_name = self.model_name
            base_url = OLLAMA_BASE_URL
            api_key = None

            # Check if using cloud model (models not available locally)
            cloud_models = ["gemma4", "qwen3.5", "ministral-3", "devstral-2", "nemotron-3", "glm-5", "minimax-m2", "kimi-k2", "cogito", "gemini-3", "deepseek-v3.2"]
            if any(cloud_model in model_name for cloud_model in cloud_models):
                base_url = OLLAMA_CLOUD_BASE_URL
                api_key = OLLAMA_CLOUD_API_KEY
                if not model:
                    model_name = OLLAMA_CLOUD_MODEL
                    self.model_name = OLLAMA_CLOUD_MODEL

            client_kwargs = {"timeout": 600}
            if api_key:
                client_kwargs["headers"] = {"Authorization": f"Bearer {api_key}"}

            self.llm = ChatOllama(
                model=model_name,
                base_url=base_url,
                temperature=0.0,
                client_kwargs=client_kwargs,
            )
            # Only disable tool calling for local Ollama models (not cloud models)
            # Cloud models like gemma4:31b, qwen3.5, etc. support function calling
            if base_url == OLLAMA_BASE_URL:  # Local Ollama
                use_tools = False
        else:
            raise ValueError(f"LLM_PROVIDER '{LLM_PROVIDER}' not configured or missing API key.")
        self.use_tools = use_tools
        self.simple = simple
        self.run_id = run_id
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ])

        # State for tool-calling mode
        self._filters: dict = {}
        self._total_rated: int = 0
        self._failed_events: list[int] = []
        self._no_more_events: bool = False
        self._verbose: bool = False
        # Token tracking
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0

    @staticmethod
    def _validate_ratings(ratings: list[dict]) -> list[dict]:
        """Validate that all ratings are decimals between 1 and 5."""
        valid_ratings = []

        for rating in ratings:
            if not isinstance(rating, dict):
                continue

            event_id = rating.get("event_id")
            if not isinstance(event_id, int):
                continue

            validated = {"event_id": event_id}

            rating_fields = [
                "rating", "rating_inhaltlich", "rating_ort",
                "rating_ausstattung", "rating_interaktion", "rating_kosten"
            ]

            valid = True
            for field in rating_fields:
                value = rating.get(field)
                if isinstance(value, (int, float)):
                    validated[field] = float(value)
                elif isinstance(value, str):
                    try:
                        validated[field] = float(value)
                    except ValueError:
                        valid = False
                        break
                else:
                    valid = False
                    break

                if validated[field] < 1:
                    validated[field] = 1.0
                elif validated[field] > 5:
                    validated[field] = 5.0

            if valid:
                validated["reason"] = rating.get("reason", "")[:200]
                valid_ratings.append(validated)

        return valid_ratings

    def _track_tokens(self, response):
        """Extract and accumulate token usage from a LangChain response."""
        try:
            usage = getattr(response, 'usage_metadata', None)
            if usage:
                self._total_input_tokens += usage.get('input_tokens', 0)
                self._total_output_tokens += usage.get('output_tokens', 0)
                return
            # Fallback: check response_metadata
            meta = getattr(response, 'response_metadata', {})
            token_usage = meta.get('token_usage', {})
            if token_usage:
                self._total_input_tokens += token_usage.get('prompt_tokens', 0)
                self._total_output_tokens += token_usage.get('completion_tokens', 0)
        except Exception:
            pass

    def _handle_get_unrated_events(self, args: dict) -> str:
        """Execute the get_unrated_events tool call."""
        from storage import get_unrated_events

        limit = min(args.get("limit", 25), 100)

        # Always offset=0: rated events drop out of the unrated query automatically
        events = get_unrated_events(
            limit=limit,
            offset=0,
            date_filter=self._filters.get("date_filter"),
            days_filter=self._filters.get("days_filter"),
            today_only=self._filters.get("today_only", False),
            tomorrow_only=self._filters.get("tomorrow_only", False),
            weekends_filter=self._filters.get("weekends_filter"),
            user_email=self.model_name,
        )

        if not events:
            self._no_more_events = True
            return json.dumps({"message": "Keine unbewerteten Veranstaltungen mehr vorhanden. Aufgabe abgeschlossen.", "events": []})

        # Serialize datetimes for JSON
        events_serializable = []
        for event in events:
            event_copy = event.copy()
            if 'start_datetime' in event_copy and event_copy['start_datetime']:
                event_copy['start_datetime'] = event_copy['start_datetime'].isoformat()
            events_serializable.append(event_copy)

        if self._verbose:
            print(f"\n  Fetched {len(events)} unrated events")

        return json.dumps(events_serializable, ensure_ascii=False)

    def _handle_submit_ratings(self, args: dict) -> str:
        """Execute the submit_ratings tool call."""
        from storage import insert_event_rating

        raw_ratings = args.get("ratings", [])
        validated = self._validate_ratings(raw_ratings)

        saved = 0
        for rating in validated:
            success = insert_event_rating(
                event_id=rating['event_id'],
                rating=rating['rating'],
                rating_inhaltlich=rating.get('rating_inhaltlich'),
                rating_ort=rating.get('rating_ort'),
                rating_ausstattung=rating.get('rating_ausstattung'),
                rating_interaktion=rating.get('rating_interaktion'),
                rating_kosten=rating.get('rating_kosten'),
                rating_reason=rating.get('reason', ''),
                user_email=self.model_name,
            )
            if success:
                saved += 1
            else:
                self._failed_events.append(rating['event_id'])

        self._total_rated += saved

        if self._verbose and validated:
            for r in validated:
                print(f"    ID {r['event_id']}: {r['rating']}/5 - {r.get('reason', '')}")

        skipped = len(raw_ratings) - len(validated)
        result = f"Saved {saved} ratings."
        if skipped > 0:
            result += f" Skipped {skipped} invalid ratings."
        return result

    def _execute_tool_call(self, tool_call: dict) -> str:
        """Route a tool call to the appropriate handler."""
        name = tool_call["name"]
        args = tool_call.get("args", {})

        if name == "get_unrated_events":
            return self._handle_get_unrated_events(args)
        elif name == "submit_ratings":
            return self._handle_submit_ratings(args)
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    def run(
        self,
        filters: dict | None = None,
        max_events: int | None = None,
        batch_size: int = 25,
        verbose: bool = False,
        progress_callback=None,
    ) -> dict:
        """Run the rating agent with tool-calling.

        Args:
            filters: Dict with date_filter, days_filter, today_only, tomorrow_only, weekends_filter
            max_events: Maximum events to rate (None = all)
            batch_size: Suggested batch size for fetches
            verbose: Print detailed output
            progress_callback: Optional callable(rated_count) for progress updates

        Returns:
            Dict with total_rated, failed_events
        """
        if self.simple:
            return self._run_simple(filters, max_events, batch_size, verbose, progress_callback)
        if not self.use_tools:
            return self._run_legacy(filters, max_events, batch_size, verbose, progress_callback)

        self._filters = filters or {}
        self._total_rated = 0
        self._failed_events = []
        self._no_more_events = False
        self._verbose = verbose
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        llm_with_tools = self.llm.bind_tools(
            [GET_UNRATED_EVENTS_SCHEMA, SUBMIT_RATINGS_SCHEMA]
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT_TOOLS),
            HumanMessage(content=f"Bitte bewerten Sie alle unbewerteten Veranstaltungen. "
                                 f"Holen Sie jeweils {batch_size} Veranstaltungen und bewerten Sie diese. "
                                 f"Wiederholen Sie bis keine mehr vorhanden sind."
                                 + (f" Maximal {max_events} Veranstaltungen." if max_events else "")),
        ]

        max_turns = 100
        for turn in range(max_turns):
            if max_events and self._total_rated >= max_events:
                break

            try:
                response: AIMessage = llm_with_tools.invoke(messages)
            except Exception as e:
                print(f"  ⚠ LLM error on turn {turn + 1}: {e}")
                break

            self._track_tokens(response)
            messages.append(response)

            if not response.tool_calls:
                # Model finished (returned text instead of tool call)
                if verbose and response.content:
                    print(f"  Agent: {response.content[:200]}")
                break

            submitted_in_turn = any(tc["name"] == "submit_ratings" for tc in response.tool_calls)

            for tool_call in response.tool_calls:
                result = self._execute_tool_call(tool_call)
                messages.append(ToolMessage(
                    content=result,
                    tool_call_id=tool_call["id"],
                ))

                if progress_callback:
                    progress_callback(self._total_rated)

            # Stop if get_unrated_events returned empty
            if self._no_more_events:
                break

            # Reset after each submit to prevent cross-batch context contamination
            # (model would otherwise reference earlier events by number: "Siehe Event 56")
            if submitted_in_turn:
                messages = [messages[0], messages[1]]
            elif len(messages) > 20:
                messages = [messages[0], messages[1]] + messages[-16:]

        # Update status if run_id is provided
        if self.run_id:
            from storage import update_rating_status_complete
            update_rating_status_complete(
                self.run_id,
                events_rated=self._total_rated,
                ratings_failed=len(self._failed_events),
                input_tokens=self._total_input_tokens,
                output_tokens=self._total_output_tokens,
            )

        return {
            "total_rated": self._total_rated,
            "failed_events": self._failed_events,
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
        }

    # --- Legacy mode (prompt-in, JSON-out) ---

    def _run_legacy(
        self,
        filters: dict | None = None,
        max_events: int | None = None,
        batch_size: int = 25,
        verbose: bool = False,
        progress_callback=None,
    ) -> dict:
        """Run the rating agent in legacy mode (no tool calling)."""
        from storage import get_unrated_events, insert_event_rating

        filters = filters or {}
        total_rated = 0
        failed_events = []
        offset = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        while True:
            if max_events and total_rated >= max_events:
                break

            limit = min(batch_size, max_events - total_rated) if max_events else batch_size
            events = get_unrated_events(
                limit=limit,
                offset=offset,
                date_filter=filters.get("date_filter"),
                days_filter=filters.get("days_filter"),
                today_only=filters.get("today_only", False),
                tomorrow_only=filters.get("tomorrow_only", False),
                weekends_filter=filters.get("weekends_filter"),
                user_email=self.model_name,
            )

            if not events:
                break

            if verbose:
                print(f"\n--- Batch {len(events)} events ---")
                for event in events:
                    print(f"  ID {event['id']}: {event['name'][:50]}")

            ratings = self.rate_events_batch(events)

            if not ratings:
                print(f"  ⚠ Failed to rate batch, skipping {len(events)} events")
                failed_events.extend([e['id'] for e in events])
                total_rated += len(events)
                offset += len(events)
                if progress_callback:
                    progress_callback(total_rated)
                continue

            for rating in ratings:
                insert_event_rating(
                    event_id=rating['event_id'],
                    rating=rating['rating'],
                    rating_inhaltlich=rating.get('rating_inhaltlich'),
                    rating_ort=rating.get('rating_ort'),
                    rating_ausstattung=rating.get('rating_ausstattung'),
                    rating_interaktion=rating.get('rating_interaktion'),
                    rating_kosten=rating.get('rating_kosten'),
                    rating_reason=rating.get('reason', ''),
                    user_email=self.model_name,
                )

            if verbose:
                print(f"  ✓ Rated {len(ratings)} events")
                for rating in ratings:
                    print(f"    ID {rating['event_id']}: {rating['rating']}/5 - {rating.get('reason', '')}")

            total_rated += len(ratings)
            offset += len(events)
            if progress_callback:
                progress_callback(total_rated)

        # Update status if run_id is provided
        if self.run_id:
            from storage import update_rating_status_complete
            update_rating_status_complete(
                self.run_id,
                events_rated=total_rated,
                ratings_failed=len(failed_events),
                input_tokens=self._total_input_tokens,
                output_tokens=self._total_output_tokens,
            )

        return {
            "total_rated": total_rated,
            "failed_events": failed_events,
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
        }

    def rate_events_batch(self, events: list[dict]) -> list[dict]:
        """Rate a batch of events using prompt mode (legacy).

        Args:
            events: List of event dicts with id, name, description, category, location, city, start_datetime

        Returns:
            List of rating dicts with event_id, rating, and individual criteria
        """
        events_serializable = []
        for event in events:
            event_copy = event.copy()
            if 'start_datetime' in event_copy and event_copy['start_datetime']:
                event_copy['start_datetime'] = event_copy['start_datetime'].isoformat()
            events_serializable.append(event_copy)

        events_json = json.dumps(events_serializable, ensure_ascii=False, indent=2)

        for attempt in range(3):
            try:
                messages = self._prompt.format_messages(events_json=events_json)
                response = self.llm.invoke(messages)
                self._track_tokens(response)
                out = response.content
                ratings = self._parse_json_array(out)
                validated_ratings = self._validate_ratings(ratings)

                if validated_ratings:
                    return validated_ratings
                else:
                    print(f"  ⚠ Attempt {attempt + 1}: No valid ratings parsed")

            except Exception as e:
                print(f"  ⚠ Attempt {attempt + 1}: Error - {str(e)}")

        return []

    @staticmethod
    def _parse_json_array(text: str) -> list[dict[str, Any]]:
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
            return [data] if isinstance(data, dict) else []
        except json.JSONDecodeError:
            return []

    # --- Simple mode (lightweight prompt for small Ollama models) ---

    def rate_events_batch_simple(self, events: list[dict]) -> list[dict]:
        """Rate up to 3 events using the simplified prompt (rating + reason only)."""
        if not events:
            return []

        events_serializable = []
        for ev in events:
            ev_copy = ev.copy()
            if ev_copy.get("start_datetime"):
                ev_copy["start_datetime"] = ev_copy["start_datetime"].isoformat()
            events_serializable.append(ev_copy)

        if len(events_serializable) == 1:
            prompt_text = SIMPLE_PROMPT_SINGLE.format(
                event_json=json.dumps(events_serializable[0], ensure_ascii=False, indent=2)
            )
        else:
            prompt_text = SIMPLE_PROMPT_BATCH.format(
                events_json=json.dumps(events_serializable, ensure_ascii=False, indent=2)
            )

        for attempt in range(3):
            try:
                from langchain_core.messages import HumanMessage
                response = self.llm.invoke([HumanMessage(content=prompt_text)])
                self._track_tokens(response)
                raw = response.content

                parsed = self._parse_json_array(raw)
                # Single-event response may come back as a dict, not a list
                if isinstance(parsed, dict):
                    parsed = [parsed]
                if not parsed and len(events_serializable) == 1:
                    # Try parsing as single object
                    try:
                        obj = json.loads(raw.strip().strip("```json").strip("```").strip())
                        if isinstance(obj, dict):
                            parsed = [obj]
                    except json.JSONDecodeError:
                        pass

                # Map to validated format (only rating + reason, no sub-criteria)
                validated = []
                for r in parsed:
                    event_id = r.get("event_id")
                    rating = r.get("rating")
                    if not isinstance(event_id, int) or not isinstance(rating, (int, float)):
                        continue
                    validated.append({
                        "event_id": event_id,
                        "rating": max(1.0, min(5.0, float(rating))),
                        "reason": str(r.get("reason", ""))[:200],
                    })

                if validated:
                    return validated
                print(f"  ⚠ Attempt {attempt + 1}: No valid ratings parsed")

            except Exception as e:
                print(f"  ⚠ Attempt {attempt + 1}: Error - {e}")

        return []

    def _run_simple(
        self,
        filters: dict | None = None,
        max_events: int | None = None,
        batch_size: int = 3,
        verbose: bool = False,
        progress_callback=None,
    ) -> dict:
        """Run simple rating mode for small Ollama models. Max batch size capped at 3."""
        from storage import get_unrated_events, insert_event_rating

        filters = filters or {}
        batch_size = min(batch_size, 3)  # hard cap
        total_rated = 0
        failed_events = []
        offset = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        while True:
            if max_events and total_rated >= max_events:
                break

            limit = min(batch_size, max_events - total_rated) if max_events else batch_size
            events = get_unrated_events(
                limit=limit,
                offset=offset,
                date_filter=filters.get("date_filter"),
                days_filter=filters.get("days_filter"),
                today_only=filters.get("today_only", False),
                tomorrow_only=filters.get("tomorrow_only", False),
                weekends_filter=filters.get("weekends_filter"),
                user_email=self.model_name,
            )

            if not events:
                break

            if verbose:
                print(f"\n--- Batch {len(events)} events (offset {offset}) ---")
                for ev in events:
                    print(f"  ID {ev['id']}: {ev['name'][:50]}")

            ratings = self.rate_events_batch_simple(events)

            if not ratings:
                print(f"  ⚠ Batch failed, skipping {len(events)} events")
                failed_events.extend([e["id"] for e in events])
                offset += len(events)
                total_rated += len(events)
                if progress_callback:
                    progress_callback(total_rated)
                continue

            for rating in ratings:
                insert_event_rating(
                    event_id=rating["event_id"],
                    rating=rating["rating"],
                    rating_inhaltlich=None,
                    rating_ort=None,
                    rating_ausstattung=None,
                    rating_interaktion=None,
                    rating_kosten=None,
                    rating_reason=rating.get("reason", ""),
                    user_email="ollama",
                )

            if verbose:
                for r in ratings:
                    print(f"    ID {r['event_id']}: {r['rating']}/5 — {r.get('reason', '')}")

            total_rated += len(ratings)
            offset += len(events)
            if progress_callback:
                progress_callback(total_rated)

        if self.run_id:
            from storage import update_rating_status_complete
            update_rating_status_complete(
                self.run_id,
                events_rated=total_rated,
                ratings_failed=len(failed_events),
                input_tokens=self._total_input_tokens,
                output_tokens=self._total_output_tokens,
            )

        return {
            "total_rated": total_rated,
            "failed_events": failed_events,
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
        }
