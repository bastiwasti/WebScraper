"""Agent 3: Generates a well-structured email-ready document from structured event data."""

from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import LLM_MODEL, OLLAMA_BASE_URL


SYSTEM_PROMPT = """You are a newsletter writer for a family in Monheim 40789. You receive a list of local events (structured data with name, description, location, date, time, source).
Your task is to write a single, well-structured document that can be sent as an email. Requirements:
- Start with a short, friendly subject line (one line) and a one-sentence intro.
- List each event clearly with: name, date/time, location, brief description, and source (URL or site name) so readers can find more info.
- Use simple headings and bullet points or short paragraphs so it's easy to read in an email.
- Keep a professional but warm tone. Do not use markdown code blocks or JSON in the output.
- End with a short sign-off (e.g. "Have a great week!")."""

USER_PROMPT = """Turn this list of events into an email-ready document:

{structured_events}
"""


class WriterAgent:
    """Takes structured event list and produces a single email-ready text document."""

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.llm = ChatOllama(
            model=model or LLM_MODEL,
            base_url=base_url or OLLAMA_BASE_URL,
            temperature=0.5,
        )
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ])

    def run(self, structured_events: list[dict]) -> str:
        """Generate email-ready text from structured event list."""
        if not structured_events:
            return (
                "Subject: No events this week\n\n"
                "We couldn't find any local events to share this time. Check back next week!"
            )
        # Pass as readable text (e.g. JSON string) so the LLM can format it
        import json
        events_text = json.dumps(structured_events, indent=2, ensure_ascii=False)
        chain = self._prompt | self.llm | StrOutputParser()
        return chain.invoke({"structured_events": events_text})
