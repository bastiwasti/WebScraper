"""Configuration for WeeklyMail multi-agent pipeline."""

import os
from pathlib import Path

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# LLM Provider: "deepseek" (ONLY)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek").lower()

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Location and focus for event scraping (Monheim 40789, family/children)
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", "Monheim 40789")
# Focus on family- and children-friendly events
FAMILY_FOCUS = os.getenv("FAMILY_FOCUS", "true").lower() in ("1", "true", "yes")

# PostgreSQL connection (shared with JobSearch project)
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DATABASE = os.getenv("PG_DATABASE", "vmpostgres")
PG_USER = os.getenv("PG_USER", "webscraper")
PG_PASSWORD = os.getenv("PG_PASSWORD", "webscraper")
PG_SCHEMA = os.getenv("PG_SCHEMA", "webscraper")

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma2:2b")

# Legacy SQLite path (used by migration script only)
_data_dir = Path(__file__).resolve().parent / "data"
SQLITE_DB_PATH = str(_data_dir / "events.db")

# Locations/Ausflüge feature — center point and radius
MONHEIM_LAT = 51.0917
MONHEIM_LNG = 6.8873
LOCATIONS_RADIUS_KM = 30

# Google Places API (optional, for future restaurant enrichment)
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
