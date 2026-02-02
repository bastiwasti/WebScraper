"""Agent 2: Analyzes raw event text and structures it (name, description, location, date, source) for storage and next agent."""

import json
import re
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import LLM_MODEL, OLLAMA_BASE_URL, XAI_API_KEY, XAI_BASE_URL, XAI_MODEL, ZAI_API_KEY, ZAI_BASE_URL, ZAI_MODEL, GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


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
        elif LLM_PROVIDER == "groq" and GROQ_API_KEY:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model or GROQ_MODEL,
                api_key=GROQ_API_KEY,
                base_url=GROQ_BASE_URL,
                temperature=0.1,
            )
        elif LLM_PROVIDER == "xai" and XAI_API_KEY:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model or XAI_MODEL,
                api_key=XAI_API_KEY,
                base_url=XAI_BASE_URL,
                temperature=0.1,
            )
        elif LLM_PROVIDER == "zai" and ZAI_API_KEY:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model or ZAI_MODEL,
                api_key=ZAI_API_KEY,
                base_url=ZAI_BASE_URL,
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

    def run(self, raw_event_text: str) -> list[dict[str, Any]]:
        """Analyze raw event text and return a list of structured event dicts (name, description, location, date, time, source)."""
        chain = self._prompt | self.llm | StrOutputParser()
        out = chain.invoke({"raw_event_text": raw_event_text})
        return self._parse_json_array(out)
