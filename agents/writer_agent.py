"""Agent 3: Generates a well-structured email-ready document from structured event data."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import LLM_MODEL, OLLAMA_BASE_URL, XAI_API_KEY, XAI_BASE_URL, XAI_MODEL, ZAI_API_KEY, ZAI_BASE_URL, ZAI_MODEL, GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


SYSTEM_PROMPT = """You are a newsletter writer for a family in Monheim 40789. You receive a list of local events (structured data with name, description, location, date, time, category, source).
Your task is to write a single, well-structured document that can be sent as an email. Requirements:
- Start with a short, friendly subject line (one line) and a one-sentence intro.
- Group events by category (family, adult, sport, other) if multiple events exist.
- List each event clearly with: name, date/time, location, brief description, category, and source (URL or site name) so readers can find more info.
- Use simple headings and bullet points or short paragraphs so it's easy to read in an email.
- Keep a professional but warm tone. Do not use markdown code blocks or JSON in the output.
- End with a short sign-off (e.g. "Have a great week!")."""

USER_PROMPT = """Turn this list of events into an email-ready document:

{structured_events}
"""


class WriterAgent:
    """Takes structured event list and produces a single email-ready text document."""

    def __init__(self, model: str | None = None, base_url: str | None = None):
        from config import LLM_PROVIDER

        if LLM_PROVIDER == "deepseek" and DEEPSEEK_API_KEY:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model or DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                temperature=0.5,
            )
        elif LLM_PROVIDER == "groq" and GROQ_API_KEY:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model or GROQ_MODEL,
                api_key=GROQ_API_KEY,
                base_url=GROQ_BASE_URL,
                temperature=0.5,
            )
        elif LLM_PROVIDER == "xai" and XAI_API_KEY:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model or XAI_MODEL,
                api_key=XAI_API_KEY,
                base_url=XAI_BASE_URL,
                temperature=0.5,
            )
        elif LLM_PROVIDER == "zai" and ZAI_API_KEY:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model or ZAI_MODEL,
                api_key=ZAI_API_KEY,
                base_url=ZAI_BASE_URL,
                temperature=0.5,
            )
        else:
            from langchain_ollama import ChatOllama
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
