"""Configuration for WeeklyMail multi-agent pipeline."""

import os
from pathlib import Path

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# Local LLM via Ollama (use Mistral or compatible model)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "phi3")

# Location and focus for event scraping (Monheim 40789, family/children)
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", "Monheim 40789")
# Focus on family- and children-friendly events
FAMILY_FOCUS = os.getenv("FAMILY_FOCUS", "true").lower() in ("1", "true", "yes")

# SQLite DB for storing scraped events (for automation and next agents)
_data_dir = Path(__file__).resolve().parent / "data"
DB_PATH = os.getenv("DB_PATH", str(_data_dir / "events.db"))
