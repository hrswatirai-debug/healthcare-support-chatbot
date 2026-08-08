"""Natural-language -> SQL engine with strong safety guardrails.

Safety model:
  * The LLM may only produce a single SELECT statement.
  * Only whitelisted tables/views may be referenced.
  * Any client-scoped table MUST be filtered by :client_id (bound server-side).
  * Execution happens on a READ-ONLY connection with a row cap.
A user therefore can never read another client's rows, nor write/alter data.
"""
from __future__ import annotations

import re

import config
from src import db, llm

# Tables the model is allowed to touch.
CLIENT_SCOPED_TABLES = {"orders", "warranty_amc", "complaints", "invoices"}
GLOBAL_TABLES = {"equipment", "spare_parts"}
ALLOWED_TABLES = CLIENT_SCOPED_TABLES | GLOBAL_TABLES

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|"
    r"VACUUM|GRANT|TRIGGER|EXEC)\b",
    re.IGNORECASE,
)

_SCHEMA_DOC = """
Tables (SQLite):
  orders(order_id, client_id, equipment_id, quantity, order_date, status, est_delivery, tracking_no, notes)
  warranty_amc(contract_id, client_id, order_id, equipment_id, warranty_start, warranty_end, amc_plan, amc_status, amc_end)
  complaints(ticket_id, client_id, equipment_id, subject, priority, status, created_at, updated_at, assigned_team)
  invoices(invoice_id, client_id, order_id, amount_usd, issued_date, due_date, status, pdf_link)
  equipment(equipment_id, model_name, category, manufacturer, manual_doc, list_price_usd)   -- global, no client_id
  spare_parts(part_id, part_name, compatible_with, in_stock, unit_price_usd, lead_time_days) -- global, no client_id
"""

_SYSTEM = (
    "You translate a customer's question into ONE safe SQLite SELECT query.\n"
    "Rules:\n"
    "1. Output ONLY the SQL, no markdown, no explanation.\n"
    "2. SELECT statements only. Never modify data.\n"
    "3. Only use the tables/columns given. Do not invent columns.\n"
    "4. For the tables orders, warranty_amc, complaints, invoices you MUST include "
    "`client_id = :client_id` in the WHERE clause (use the exact placeholder :client_id).\n"
    "5. Keep it a single statement ending with a semicolon.\n"
    + _SCHEMA_DOC
)


class SQLGuardError(Exception):
    pass


def _clean(sql: str) -> str:
    sql = sql.strip()
    sql = re.sub(r"^```(?:sql)?", "", sql, flags=re.IGNORECASE).strip()
    sql = re.sub(r"```$", "", sql).strip()
    return sql


def _referenced_tables(sql: str) -> set[str]:
    found = set()
    for tbl in ALLOWED_TABLES:
        if re.search(rf"\b{tbl}\b", sql, re.IGNORECASE):
            found.add(tbl)
    return found


def validate(sql: str) -> str:
    """Raise SQLGuardError if the query is unsafe; return cleaned SQL if ok."""
    sql = _clean(sql)
    if sql.count(";") > 1 or (";" in sql and not sql.rstrip().endswith(";")):
        raise SQLGuardError("Only a single statement is allowed.")
    if not re.match(r"^\s*SELECT\b", sql, re.IGNORECASE):
        raise SQLGuardError("Only SELECT statements are allowed.")
    if FORBIDDEN.search(sql):
        raise SQLGuardError("Query contains a forbidden keyword.")

    used = _referenced_tables(sql)
    if not used:
        raise SQLGuardError("Query references no whitelisted table.")
    # Reject any unknown identifier that looks like a table via FROM/JOIN.
    for m in re.finditer(r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", sql, re.IGNORECASE):
        if m.group(1).lower() not in ALLOWED_TABLES:
            raise SQLGuardError(f"Table '{m.group(1)}' is not allowed.")
    # Enforce client scoping.
    if used & CLIENT_SCOPED_TABLES and ":client_id" not in sql:
        raise SQLGuardError("Missing required client_id scoping.")
    return sql


def run(message: str, client_id: str) -> tuple[list[dict], str]:
    """Generate + validate + execute. Returns (rows, sql_used)."""
    raw = llm.complete(system=_SYSTEM, user=message, task="sql",
                       temperature=0.0, max_tokens=300)
    sql = validate(raw)

    conn = db.get_readonly_connection()
    try:
        cur = conn.execute(sql, {"client_id": client_id})
        rows = [dict(r) for r in cur.fetchmany(config.SQL_MAX_ROWS)]
    finally:
        conn.close()
    return rows, sql


_ANSWER_SYSTEM = (
    "You are a concise, friendly medical-equipment support assistant. "
    "Answer the user's question using ONLY the data rows provided. "
    "If the rows are empty, say you couldn't find any matching records. "
    "Do not invent values. Keep it to 1-3 sentences."
)


def narrate(message: str, rows: list[dict]) -> str:
    if not rows:
        return "I couldn't find any records matching that in your account."
    context = "\n".join(str(r) for r in rows)
    user = f"QUESTION: {message}\nCONTEXT:\n{context}"
    return llm.complete(system=_ANSWER_SYSTEM, user=user, task="sql_answer",
                        temperature=0.1, max_tokens=300)
