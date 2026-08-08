"""Identity verification: email + client_id must match a users row."""
from __future__ import annotations

from typing import Optional, Dict

from src import db


def verify_user(email: str, client_id: str) -> Optional[Dict]:
    """Return the user record if email + client_id match, else None."""
    if not email or not client_id:
        return None
    conn = db.get_readonly_connection()
    try:
        row = conn.execute(
            "SELECT client_id, email, org_name, contact_name "
            "FROM users WHERE lower(email) = lower(?) AND client_id = ?",
            (email.strip(), client_id.strip()),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
