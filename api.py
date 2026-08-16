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
from fastapi.responses import HTMLResponse
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
    # Policy/how-to phrasings route to RAG even for structured topics.
    route = intent_mod.route_for(label, body.message)
    return {"intent": label, "confidence": confidence, "route": route}


@app.post("/query/sql")
def do_sql(body: QueryIn, x_engine_key: str | None = Header(default=None)):
    _check_key(x_engine_key)
    if not body.client_id:
        raise HTTPException(status_code=400, detail="client_id required for SQL queries")
    # Fast path: fixed templated query per intent (no LLM generation/narration).
    intent_label, _ = intent_mod.classify(body.message)
    rows, sql = sql_engine.run_templated(intent_label, body.client_id)
    if rows:
        return {"answered": True,
                "answer": sql_engine.format_templated(intent_label, rows),
                "rows": rows, "sql": sql}
    # No rows -> report unanswered so the workflow can cascade to RAG.
    return {"answered": False, "answer": config.FALLBACK_MESSAGE,
            "rows": [], "sql": sql}


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


def _fetch_history(limit: int, client_id: str | None):
    """Read recent audit rows from the DB. Read-only."""
    q = ("SELECT id, ts, client_id, intent, data_source, answered, latency_ms, "
         "message_preview FROM chat_audit")
    params: list = []
    if client_id:
        q += " WHERE client_id = ?"
        params.append(client_id)
    q += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    conn = db.get_readonly_connection()
    try:
        return [dict(r) for r in conn.execute(q, params).fetchall()]
    finally:
        conn.close()


@app.get("/history.json")
def history_json(limit: int = 50, client_id: str | None = None):
    """Raw chat history as JSON. Optional ?limit= and ?client_id= filters."""
    return {"count": None, "rows": _fetch_history(limit, client_id)}


@app.get("/history", response_class=HTMLResponse)
def history_page(limit: int = 50, client_id: str | None = None):
    """Human-friendly chat-history table you can open in a browser."""
    rows = _fetch_history(limit, client_id)
    body_rows = ""
    for r in rows:
        answered = "✅" if r["answered"] else "—"
        src = r["data_source"] or ""
        badge = {"SQL": "#2a9c68", "RAG": "#3c78d8", "FALLBACK": "#b65775"}.get(src, "#666")
        body_rows += (
            "<tr>"
            f"<td>{r['id']}</td>"
            f"<td class='mono'>{r['ts']}</td>"
            f"<td>{r['client_id'] or ''}</td>"
            f"<td>{r['intent'] or ''}</td>"
            f"<td><span class='badge' style='background:{badge}'>{src}</span></td>"
            f"<td style='text-align:center'>{answered}</td>"
            f"<td style='text-align:right'>{r['latency_ms']} ms</td>"
            f"<td>{(r['message_preview'] or '')}</td>"
            "</tr>"
        )
    if not rows:
        body_rows = ("<tr><td colspan='8' style='text-align:center;padding:24px'>"
                     "No chat history yet. Send a message through the chatbot first."
                     "</td></tr>")
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Chatbot History</title>
<meta http-equiv="refresh" content="10">
<style>
 :root {{ color-scheme: light }}
 body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; color:#1a1a1a }}
 h1 {{ font-size: 20px; margin: 0 0 4px }}
 .sub {{ color:#666; font-size: 13px; margin-bottom: 16px }}
 table {{ border-collapse: collapse; width: 100%; font-size: 13px }}
 th, td {{ padding: 8px 10px; border-bottom: 1px solid #eee; text-align: left; vertical-align: top }}
 th {{ background:#fafafa; position: sticky; top: 0; font-weight: 600 }}
 tr:hover td {{ background:#fafcff }}
 .mono {{ font-family: ui-monospace, Menlo, monospace; color:#555; white-space: nowrap }}
 .badge {{ color:#fff; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight:600 }}
</style></head><body>
 <h1>🩺 Chatbot Interaction History</h1>
 <div class="sub">Showing {len(rows)} most recent turns · auto-refreshes every 10s ·
   <a href="/history.json">JSON</a></div>
 <table>
  <thead><tr><th>#</th><th>Time (UTC)</th><th>Client</th><th>Intent</th>
   <th>Source</th><th>OK</th><th>Latency</th><th>Message</th></tr></thead>
  <tbody>{body_rows}</tbody>
 </table>
</body></html>"""
    return html
