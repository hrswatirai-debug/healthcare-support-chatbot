"""SQLite helpers: initialization and safe read-only connections."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import config


def init_db() -> None:
    """Create the schema and load seed data (idempotent for a fresh file)."""
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    schema = (config.DATA_DIR / "schema.sql").read_text()
    seed = (config.DATA_DIR / "seed.sql").read_text()
    conn = sqlite3.connect(config.DB_PATH)
    try:
        conn.executescript(schema)
        # Only seed if empty, so re-running does not duplicate rows.
        cur = conn.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            conn.executescript(seed)
        conn.commit()
    finally:
        conn.close()


def get_readonly_connection() -> sqlite3.Connection:
    """Open the DB in read-only mode so no query can ever write."""
    uri = f"file:{config.DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_write_connection() -> sqlite3.Connection:
    """Writable connection — used only by the app for audit logging."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
