"""End-to-end tests. Run with:  python -m pytest -q   (or: python tests/test_system.py)

These run in offline 'mock' mode (no API key) so they are free and deterministic.
They exercise auth, intent routing, SQL safety, RAG grounding, and the fallback.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["LLM_PROVIDER"] = "mock"  # force offline deterministic mode

from src import db, rag_engine, auth, intent, sql_engine, router  # noqa: E402


def setup_module(_):
    db.init_db()
    rag_engine.build_index()


# ---- Auth -----------------------------------------------------------------
def test_valid_login():
    u = auth.verify_user("admin@stmary-hospital.org", "CLI-1001")
    assert u and u["client_id"] == "CLI-1001"


def test_invalid_login():
    assert auth.verify_user("admin@stmary-hospital.org", "CLI-9999") is None
    assert auth.verify_user("nobody@nowhere.com", "CLI-1001") is None


# ---- Intent ---------------------------------------------------------------
def test_intent_routing():
    assert intent.classify("Where is my order?")[0] == "order_delivery_status"
    assert intent.classify("Is my warranty active?")[0] == "warranty_amc"
    assert intent.classify("Send me the FDA certificate")[0] == "certifications_compliance"
    assert intent.classify("What are your business hours?")[0] == "general_query"


# ---- SQL safety -----------------------------------------------------------
def test_sql_rejects_non_select():
    for bad in ["DELETE FROM orders;", "DROP TABLE users;",
                "UPDATE orders SET status='x' WHERE client_id=:client_id;"]:
        try:
            sql_engine.validate(bad)
            assert False, f"should have rejected: {bad}"
        except sql_engine.SQLGuardError:
            pass


def test_sql_requires_client_scope():
    try:
        sql_engine.validate("SELECT * FROM orders;")
        assert False, "should require client scoping"
    except sql_engine.SQLGuardError:
        pass
    # global table without client_id is allowed
    assert sql_engine.validate("SELECT * FROM spare_parts;")


def test_sql_rejects_unknown_table():
    try:
        sql_engine.validate("SELECT * FROM users WHERE client_id=:client_id;")
        assert False, "users table must not be queryable"
    except sql_engine.SQLGuardError:
        pass


def test_sql_client_isolation():
    # Running St. Mary's session must never return another client's orders.
    rows, _ = sql_engine.run("show my orders", "CLI-1001")
    assert rows, "expected St. Mary orders"
    assert all(r.get("order_id", "").startswith("ORD-440") for r in rows)
    rows2, _ = sql_engine.run("show my orders", "CLI-1002")
    ids1 = {r["order_id"] for r in rows}
    ids2 = {r["order_id"] for r in rows2}
    assert ids1.isdisjoint(ids2), "clients must not share orders"


# ---- RAG ------------------------------------------------------------------
def test_rag_finds_answer():
    ans, sources = rag_engine.answer("What is the field strength of the MagnaScan MRI?")
    assert sources, "should retrieve a source doc"
    assert ans.strip() != "I don't know the answer to that."


def test_rag_fallback_on_irrelevant():
    ans, sources = rag_engine.answer("What is the capital of France zxqweqwe?")
    assert ans.strip() == "I don't know the answer to that."


# ---- End-to-end router ----------------------------------------------------
def test_router_sql_path():
    user = auth.verify_user("admin@stmary-hospital.org", "CLI-1001")
    resp = router.handle_message("What's my order status?", user)
    assert resp.data_source == "SQL"
    assert resp.latency_ms >= 0


def test_router_rag_path():
    user = auth.verify_user("admin@stmary-hospital.org", "CLI-1001")
    resp = router.handle_message("How do I book preventive maintenance?", user)
    assert resp.data_source in ("RAG", "FALLBACK")


def test_router_unknown_fallback():
    user = auth.verify_user("admin@stmary-hospital.org", "CLI-1001")
    resp = router.handle_message("asdkjfh qwoieu zxcmnv", user)
    assert resp.text.strip() == "I don't know the answer to that."


# ---- allow direct execution ----------------------------------------------
if __name__ == "__main__":
    setup_module(None)
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print(f"PASS  {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed.")
