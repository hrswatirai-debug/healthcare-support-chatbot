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

    if intent in config.SQL_INTENTS:
        try:
            rows, sql = sql_engine.run(message, client_id)
            text = sql_engine.narrate(message, rows)
            answered = bool(rows)
            return BotResponse(text, intent, "SQL", answered, sql_used=sql)
        except sql_engine.SQLGuardError:
            return BotResponse(config.FALLBACK_MESSAGE, intent, "FALLBACK", False)

    if intent in config.RAG_INTENTS:
        text, sources = rag_engine.answer(message)
        answered = text.strip() != config.FALLBACK_MESSAGE
        return BotResponse(text, intent, "RAG" if answered else "FALLBACK",
                           answered, sources=sources)

    return BotResponse(config.FALLBACK_MESSAGE, intent, "FALLBACK", False)
