"""Identity verification: email + client_id must match a users row."""
from __future__ import annotations

from typing import Optional, Dict

from src import db


def _sanitize(v) -> str:
    """Strip whitespace and a stray leading '=' or quotes from upstream input."""
    if v is None:
        return ""
    return str(v).strip().lstrip("=").strip().strip('"\'').strip()


def verify_user(email: str, client_id: str) -> Optional[Dict]:
    """Return the user record if email + client_id match, else None."""
    email = _sanitize(email)
    client_id = _sanitize(client_id)
    if not email or not client_id:
        return None
    conn = db.get_readonly_connection()
    try:
        row = conn.execute(
            "SELECT client_id, email, org_name, contact_name "
            "FROM users WHERE lower(email) = lower(?) AND client_id = ?",
            (email, client_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
