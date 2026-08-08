"""Provider-agnostic LLM client.

Supports Anthropic, OpenAI, and Google Gemini, selected via environment
variables (see config.py). If no API key is present, falls back to a
deterministic offline "mock" so the whole pipeline still runs (used by the
test suite and for grading without incurring cost).

Public API:
    complete(system, user, task=None, temperature=0.0, max_tokens=1024) -> str
"""
from __future__ import annotations

import json
import re

import config


# --------------------------------------------------------------------------- #
# Real providers
# --------------------------------------------------------------------------- #
def _anthropic(system: str, user: str, temperature: float, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in resp.content if block.type == "text").strip()


def _openai(system: str, user: str, temperature: float, max_tokens: int) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content.strip()


def _gemini(system: str, user: str, temperature: float, max_tokens: int) -> str:
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(config.GEMINI_MODEL, system_instruction=system)
    resp = model.generate_content(
        user,
        generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
    )
    return (resp.text or "").strip()


# --------------------------------------------------------------------------- #
# Offline deterministic mock (no network / no key required)
# --------------------------------------------------------------------------- #
_INTENT_KEYWORDS = [
    ("order_delivery_status", ["order", "delivery", "deliver", "ship", "track", "arrive", "dispatch"]),
    ("warranty_amc", ["warranty", "amc", "maintenance contract", "coverage", "extend warranty"]),
    ("complaint_issue", ["complaint", "ticket", "broken", "fault", "not working", "issue", "escalate", "breakdown"]),
    ("payment_invoice", ["invoice", "payment", "refund", "overcharge", "receipt", "credit note", "bill"]),
    ("spare_parts", ["spare", "part", "replacement", "accessory", "probe", "cable", "in stock"]),
    ("installation_maintenance", ["install", "installation", "schedule", "book", "technician", "preventive"]),
    ("product_specs_docs", ["spec", "specification", "manual", "compatible", "compatibility", "how do i", "how to", "clean", "software"]),
    ("certifications_compliance", ["iso", "ce ", "fda", "certificate", "certification", "compliance", "regulation"]),
    ("general_query", ["business hours", "contact", "support hours", "open", "phone", "email", "policy"]),
]


def _mock_intent(user: str) -> str:
    # Only classify the actual message (the text after the last "Message:"),
    # never the few-shot examples that precede it.
    if "Message:" in user:
        text = user.rsplit("Message:", 1)[1]
    else:
        text = user
    text = text.replace("->", " ").lower()
    for intent, kws in _INTENT_KEYWORDS:
        if any(k in text for k in kws):
            return json.dumps({"intent": intent, "confidence": 0.9})
    return json.dumps({"intent": "unknown", "confidence": 0.2})


def _mock_sql(user: str) -> str:
    """Very small NL->SQL heuristic for offline mode. Real providers do better."""
    t = user.lower()
    if "order" in t or "deliver" in t or "track" in t or "ship" in t:
        return "SELECT order_id, status, est_delivery, tracking_no FROM orders WHERE client_id = :client_id;"
    if "warranty" in t or "amc" in t:
        return "SELECT contract_id, equipment_id, warranty_end, amc_plan, amc_status FROM warranty_amc WHERE client_id = :client_id;"
    if "complaint" in t or "ticket" in t or "fault" in t or "issue" in t:
        return "SELECT ticket_id, subject, priority, status FROM complaints WHERE client_id = :client_id;"
    if "invoice" in t or "payment" in t or "refund" in t or "bill" in t:
        return "SELECT invoice_id, amount_usd, status, due_date FROM invoices WHERE client_id = :client_id;"
    if "spare" in t or "part" in t or "stock" in t:
        return "SELECT part_id, part_name, in_stock, unit_price_usd FROM spare_parts;"
    return "SELECT order_id, status FROM orders WHERE client_id = :client_id;"


def _mock_answer(user: str, context: str) -> str:
    """Grounded summary for RAG/SQL result narration in offline mode."""
    if not context.strip():
        return config.FALLBACK_MESSAGE
    # Return the most relevant sentences from the provided context.
    sentences = re.split(r"(?<=[.!?])\s+", context.replace("\n", " "))
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    return " ".join(sentences[:3]) if sentences else context[:400]


def _mock(system: str, user: str, task: str | None) -> str:
    if task == "intent":
        return _mock_intent(user)
    if task == "sql":
        return _mock_sql(user)
    # task in {"rag_answer", "sql_answer", None}: 'user' holds question+context
    ctx = ""
    if "CONTEXT:" in user:
        ctx = user.split("CONTEXT:", 1)[1]
    return _mock_answer(user, ctx or user)


# --------------------------------------------------------------------------- #
# Dispatcher
# --------------------------------------------------------------------------- #
def complete(system: str, user: str, task: str | None = None,
             temperature: float = 0.0, max_tokens: int = 1024) -> str:
    provider = config.resolve_provider()
    try:
        if provider == "anthropic":
            return _anthropic(system, user, temperature, max_tokens)
        if provider == "openai":
            return _openai(system, user, temperature, max_tokens)
        if provider == "gemini":
            return _gemini(system, user, temperature, max_tokens)
    except Exception as exc:  # network/quota/auth failure -> safe degradation
        # Fall back to offline mock so the app never hard-crashes on the user.
        print(f"[llm] provider '{provider}' failed ({exc}); using offline mock.")
    return _mock(system, user, task)


def active_provider() -> str:
    return config.resolve_provider()
