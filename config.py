"""Configuration for WeeklyMail multi-agent pipeline."""

import os
from pathlib import Path

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# LLM Provider: "ollama", "xai", "zai", "groq", or "deepseek"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

# Local LLM via Ollama (use Mistral or compatible model)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "phi3")

# xAI API (Grok models)
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
XAI_MODEL = os.getenv("XAI_MODEL", "grok-beta")

# z.AI API (GLM models)
ZAI_API_KEY = os.getenv("ZAI_API_KEY", "")
ZAI_BASE_URL = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4")
ZAI_MODEL = os.getenv("ZAI_MODEL", "glm-4.7")

# Groq API (Llama models)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Location and focus for event scraping (Monheim 40789, family/children)
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", "Monheim 40789")
# Focus on family- and children-friendly events
FAMILY_FOCUS = os.getenv("FAMILY_FOCUS", "true").lower() in ("1", "true", "yes")

# SQLite DB for storing scraped events (for automation and next agents)
_data_dir = Path(__file__).resolve().parent / "data"
DB_PATH = os.getenv("DB_PATH", str(_data_dir / "events.db"))
