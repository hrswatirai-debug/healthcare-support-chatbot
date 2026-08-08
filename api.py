"""FastAPI service exposing the chatbot engine as granular endpoints.

n8n orchestrates the flow by calling these over HTTP (all on localhost):
    POST /auth          -> verify identity
    POST /intent        -> classify intent
    POST /query/sql     -> run safe SQL + narrate
    POST /query/rag     -> RAG retrieve + grounded answer
    POST /chat          -> convenience: full pipeline in one call (fallback path)
    POST /reindex       -> rebuild the RAG index
    POST /events        -> receive async side-effect events (audit/notify hooks)
    GET  /health        -> liveness

An optional shared secret (ENGINE_API_KEY) can be required via the
`X-Engine-Key` header so only n8n (which holds the key) may call the engine.

Run with:  uvicorn api:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import os
import time

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

import config
from src import auth, db, intent as intent_mod, sql_engine, rag_engine, logger, router

ENGINE_API_KEY = os.getenv("ENGINE_API_KEY")  # optional shared secret

app = FastAPI(title="Healthcare Support Chatbot Engine", version="1.0.0")


@app.on_event("startup")
def _startup() -> None:
    db.init_db()
    # Warm the RAG index so the first request isn't slow.
    try:
        rag_engine._load_index()
    except Exception as exc:  # non-fatal
        print(f"[startup] index warm failed: {exc}")


def _check_key(x_engine_key: str | None) -> None:
    if ENGINE_API_KEY and x_engine_key != ENGINE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid engine key")


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class AuthIn(BaseModel):
    email: str
    client_id: str


class IntentIn(BaseModel):
    message: str


class QueryIn(BaseModel):
    message: str
    client_id: str | None = None


class ChatIn(BaseModel):
    message: str
    email: str
    client_id: str


class EventIn(BaseModel):
    type: str
    payload: dict = {}


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/health")
def health():
    return {"status": "ok", "provider": config.resolve_provider()}


@app.post("/auth")
def do_auth(body: AuthIn, x_engine_key: str | None = Header(default=None)):
    _check_key(x_engine_key)
    user = auth.verify_user(body.email, body.client_id)
    if not user:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user}


@app.post("/intent")
def do_intent(body: IntentIn, x_engine_key: str | None = Header(default=None)):
    _check_key(x_engine_key)
    label, confidence = intent_mod.classify(body.message)
    route = ("SQL" if label in config.SQL_INTENTS
             else "RAG" if label in config.RAG_INTENTS
             else "FALLBACK")
    return {"intent": label, "confidence": confidence, "route": route}


@app.post("/query/sql")
def do_sql(body: QueryIn, x_engine_key: str | None = Header(default=None)):
    _check_key(x_engine_key)
    if not body.client_id:
        raise HTTPException(status_code=400, detail="client_id required for SQL queries")
    try:
        rows, sql = sql_engine.run(body.message, body.client_id)
    except sql_engine.SQLGuardError:
        return {"answered": False, "answer": config.FALLBACK_MESSAGE,
                "rows": [], "sql": None}
    answer = sql_engine.narrate(body.message, rows)
    return {"answered": bool(rows), "answer": answer, "rows": rows, "sql": sql}


@app.post("/query/rag")
def do_rag(body: QueryIn, x_engine_key: str | None = Header(default=None)):
    _check_key(x_engine_key)
    answer, sources = rag_engine.answer(body.message)
    answered = answer.strip() != config.FALLBACK_MESSAGE
    return {"answered": answered, "answer": answer, "sources": sources}


@app.post("/chat")
def do_chat(body: ChatIn, x_engine_key: str | None = Header(default=None)):
    """Full pipeline in one call. Used as a fallback if n8n is unavailable."""
    _check_key(x_engine_key)
    user = auth.verify_user(body.email, body.client_id)
    if not user:
        raise HTTPException(status_code=401, detail="Identity not verified")
    resp = router.handle_message(body.message, user)
    return {
        "answer": resp.text, "intent": resp.intent, "data_source": resp.data_source,
        "answered": resp.answered, "sources": resp.sources, "latency_ms": resp.latency_ms,
    }


@app.post("/reindex")
def do_reindex(x_engine_key: str | None = Header(default=None)):
    _check_key(x_engine_key)
    rag_engine._INDEX_CACHE = None
    n = rag_engine.build_index()
    return {"reindexed": True, "chunks": n}


@app.post("/events")
def do_events(body: EventIn, x_engine_key: str | None = Header(default=None)):
    """Async side-effect sink (n8n posts audit/notify events here).

    Also used by n8n to record an audit row after it orchestrates a turn.
    """
    _check_key(x_engine_key)
    if body.type == "audit":
        p = body.payload
        logger.log_interaction(
            client_id=p.get("client_id"), intent=p.get("intent"),
            data_source=p.get("data_source", "N8N"),
            answered=bool(p.get("answered")),
            latency_ms=int(p.get("latency_ms", 0)),
            message=p.get("message", ""),
        )
        return {"logged": True}
    # Other event types (complaint_created, escalation, csat) are handled inside
    # n8n workflows; the engine just acknowledges receipt.
    return {"received": True, "type": body.type, "ts": time.time()}
