"""Central configuration. All secrets come from environment variables (.env)."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # dotenv optional; env vars may be set another way
    pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "docs"
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "app.db"))
INDEX_PATH = str(DATA_DIR / "rag_index.pkl")

# ---- LLM provider selection -------------------------------------------------
# LLM_PROVIDER: "anthropic" | "openai" | "gemini" | "mock"
# The matching API key must be present in the environment.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def resolve_provider() -> str:
    """Pick a provider based on config + which key is present."""
    if LLM_PROVIDER != "auto":
        return LLM_PROVIDER
    if ANTHROPIC_API_KEY:
        return "anthropic"
    if OPENAI_API_KEY:
        return "openai"
    if GEMINI_API_KEY:
        return "gemini"
    return "mock"  # no key -> deterministic offline mode (used by tests)


# ---- Retrieval / routing knobs ---------------------------------------------
# n8n orchestration: if set, the UI routes turns through this webhook instead of
# calling the in-process router directly. Example:
#   http://localhost:5678/webhook/chat
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "").strip()
ENGINE_API_KEY = os.getenv("ENGINE_API_KEY", "").strip()

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_MIN_SIMILARITY = float(os.getenv("RAG_MIN_SIMILARITY", "0.05"))
SQL_MAX_ROWS = int(os.getenv("SQL_MAX_ROWS", "50"))
FALLBACK_MESSAGE = "I don't know the answer to that."

# Intents routed to the structured SQL engine
SQL_INTENTS = {
    "order_delivery_status",
    "warranty_amc",
    "complaint_issue",
    "payment_invoice",
    "spare_parts",
}
# Intents routed to the RAG document engine
RAG_INTENTS = {
    "product_specs_docs",
    "installation_maintenance",
    "certifications_compliance",
    "general_query",
}
