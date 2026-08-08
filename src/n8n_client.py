"""Client that routes a chat turn through the n8n webhook orchestrator.

The Streamlit UI uses this when N8N_WEBHOOK_URL is set. n8n then calls the
FastAPI engine for auth/intent/sql/rag and returns the composed answer.
Falls back to the in-process router if n8n is unreachable, so the UI never
hard-fails on the user.
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error

import config
from src.router import BotResponse


def ask(message: str, user: dict, timeout: float = 10.0) -> BotResponse:
    started = time.perf_counter()
    payload = json.dumps({
        "email": user["email"],
        "client_id": user["client_id"],
        "message": message,
    }).encode("utf-8")

    req = urllib.request.Request(
        config.N8N_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        # n8n unreachable -> graceful fallback to the direct engine path.
        from src import router
        print(f"[n8n_client] webhook failed ({exc}); falling back to direct engine.")
        return router.handle_message(message, user)

    latency = int((time.perf_counter() - started) * 1000)
    return BotResponse(
        text=data.get("answer", config.FALLBACK_MESSAGE),
        intent=data.get("intent", "n8n"),
        data_source=data.get("data_source", "N8N"),
        answered=bool(data.get("answered", False)),
        sources=data.get("sources", []) or [],
        latency_ms=latency,
    )
