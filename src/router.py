"""Orchestrator: intent -> route to SQL or RAG -> answer -> audit log."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import config
from src import intent as intent_mod
from src import sql_engine, rag_engine, logger


@dataclass
class BotResponse:
    text: str
    intent: str
    data_source: str          # SQL | RAG | FALLBACK
    answered: bool
    sources: list[str] = field(default_factory=list)
    sql_used: str | None = None
    latency_ms: int = 0


def handle_message(message: str, user: dict) -> BotResponse:
    """Main entry point. `user` must be an authenticated users-row dict."""
    started = time.perf_counter()
    client_id = user["client_id"]

    intent, confidence = intent_mod.classify(message)

    resp = _dispatch(message, client_id, intent, confidence)
    resp.latency_ms = int((time.perf_counter() - started) * 1000)

    logger.log_interaction(
        client_id=client_id,
        intent=resp.intent,
        data_source=resp.data_source,
        answered=resp.answered,
        latency_ms=resp.latency_ms,
        message=message,
    )
    return resp


def _dispatch(message: str, client_id: str, intent: str, confidence: float) -> BotResponse:
    # Unknown / low confidence -> honest fallback.
    if intent == "unknown":
        return BotResponse(config.FALLBACK_MESSAGE, intent, "FALLBACK", False)

    # Route policy/how-to phrasings to documents, lookups to structured data.
    route = intent_mod.route_for(intent, message)

    if route == "SQL":
        # Fast path: fixed templated query + templated formatting (no LLM calls).
        rows, sql = sql_engine.run_templated(intent, client_id)
        if rows:
            text = sql_engine.format_templated(intent, rows)
            return BotResponse(text, intent, "SQL", True, sql_used=sql)
        # Nothing structured to return -> cascade to documents before fallback.
        return _rag_or_fallback(message, intent)

    if route == "RAG":
        return _rag_or_fallback(message, intent)

    return BotResponse(config.FALLBACK_MESSAGE, intent, "FALLBACK", False)


def _rag_or_fallback(message: str, intent: str) -> BotResponse:
    text, sources = rag_engine.answer(message)
    answered = text.strip() != config.FALLBACK_MESSAGE
    return BotResponse(text, intent, "RAG" if answered else "FALLBACK",
                       answered, sources=sources)
