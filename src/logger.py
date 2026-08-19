"""Audit logging of every chatbot interaction (Step 5: Logging & Auditing)."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import config
from src import db

# When True, store a hashed client id instead of the raw value (privacy option).
ANONYMIZE = False


def _client_ref(client_id: str | None) -> str | None:
    if client_id is None:
        return None
    if ANONYMIZE:
        return "anon_" + hashlib.sha256(client_id.encode()).hexdigest()[:12]
    return client_id


def log_interaction(client_id: str | None, intent: str | None, data_source: str,
                    answered: bool, latency_ms: int, message: str) -> None:
    conn = db.get_write_connection()
    try:
        conn.execute(
            "INSERT INTO chat_audit "
            "(ts, client_id, intent, data_source, answered, latency_ms, message_preview) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                _client_ref(client_id),
                intent,
                data_source,
                1 if answered else 0,
                latency_ms,
                (message or "")[:120],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def log_error(payload: dict) -> None:
    """Persist a workflow/pipeline failure (posted by the n8n error handler)."""
    conn = db.get_write_connection()
    try:
        conn.execute(
            "INSERT INTO error_log "
            "(ts, workflow, failed_node, error_message, execution_url) "
            "VALUES (?,?,?,?,?)",
            (
                payload.get("timestamp")
                or datetime.now(timezone.utc).isoformat(timespec="seconds"),
                payload.get("workflow"),
                payload.get("failed_node"),
                payload.get("error_message"),
                payload.get("execution_url"),
            ),
        )
        conn.commit()
    finally:
        conn.close()
