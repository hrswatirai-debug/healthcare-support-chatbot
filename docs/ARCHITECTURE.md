# Architecture — AI-Powered Healthcare Support Chatbot (RAG + SQL)

## 1. High-level flow

```
                        ┌─────────────────────────────┐
   User (browser) ───▶  │   Streamlit chat interface   │
                        │  (app.py) — login + chat     │
                        └───────────────┬──────────────┘
                                        │ authenticated message
                                        ▼
                        ┌─────────────────────────────┐
                        │        Orchestrator          │
                        │        (src/router.py)       │
                        └───┬───────────┬───────────┬──┘
             intent detect  │           │           │  audit
                 ▼          │           │           ▼
        ┌────────────────┐  │           │   ┌────────────────┐
        │ intent.py      │  │           │   │ logger.py      │
        │ (LLM classify) │  │           │   │ audit log DB   │
        └────────────────┘  │           │   └────────────────┘
                            ▼           ▼
                 ┌──────────────┐  ┌──────────────┐
                 │ sql_engine   │  │ rag_engine   │
                 │ NL→SQL safe  │  │ TF-IDF search│
                 │ SQLite (RO)  │  │ + LLM answer │
                 └──────┬───────┘  └──────┬───────┘
                        ▼                 ▼
                 ┌──────────────┐  ┌──────────────┐
                 │ app.db       │  │ data/docs/*  │
                 │ (tables)     │  │ + index.pkl  │
                 └──────────────┘  └──────────────┘
```

## 2. Request lifecycle

1. **Authenticate** (`auth.py`): email + client_id validated against `users` table. A session is only created on success. Every downstream query is scoped to the authenticated `client_id`.
2. **Classify intent** (`intent.py`): the LLM maps the message to one of 9 intent categories (+ `unknown`) using a constrained, few-shot prompt that returns strict JSON.
3. **Route** (`router.py`):
   - Structured intents (orders, warranty/AMC, complaints, invoices, spare-part availability) → **SQL engine**.
   - Documentation intents (product specs, install/maintenance how-to, certifications, general policy) → **RAG engine**.
   - No confident intent / no data → deterministic fallback: *"I don't know the answer to that."*
4. **SQL path** (`sql_engine.py`): the LLM generates a **SELECT-only** query against a whitelisted schema. Guardrails then (a) reject non-SELECT, (b) reject queries touching non-whitelisted tables, (c) force a `client_id = ?` predicate bound to the session user, (d) run under a read-only SQLite connection with a row/time limit. Results are summarised into natural language by the LLM.
5. **RAG path** (`rag_engine.py`): the question is embedded with a TF-IDF vectorizer, top-k chunks are retrieved by cosine similarity, and the LLM answers **grounded only in the retrieved chunks**, citing the source document. If similarity is below a threshold, it returns the fallback.
6. **Respond & log** (`logger.py`): the answer is returned; an audit row (user, timestamp, intent, data source, latency, whether answered) is written.

## 3. Why these choices

| Concern | Decision | Rationale |
|---|---|---|
| LLM provider | Pluggable `llm.py` (Anthropic / OpenAI / Gemini) chosen by env vars | User supplies an existing key; no new signups. |
| Retrieval | TF-IDF + cosine (scikit-learn) | Zero external calls, deterministic, fast (<2s), no heavy model download; works even if the provider has no embeddings API. Swappable for vector embeddings later. |
| Database | SQLite | Self-contained, no server to provision; easy to seed and demo; read-only enforcement is simple. |
| UI | Streamlit | Single command to run; production-grade enough for a capstone demo. |
| Safety | SELECT-only + client_id scoping + read-only conn | Prevents data leakage across clients and any write/DROP — critical for healthcare (HIPAA-like). |
| Honesty | Similarity threshold + strict grounding | Meets the "I don't know" requirement; reduces hallucination. |

## 4. Security & compliance notes (HIPAA-like posture)

- **Least privilege data access:** all SQL is read-only and hard-scoped to the logged-in client. A user can never retrieve another client's rows even if the LLM tried.
- **No secrets in code:** API keys are read from environment (`.env`, git-ignored). Nothing is hard-coded or logged.
- **Auditability:** every interaction is logged with metadata; logs can be anonymized for analytics.
- **PII minimization:** the audit log stores a hashed user reference option and never stores raw message content unless enabled.
- **Injection defense:** LLM-generated SQL is parsed and validated, never blindly executed.

## 5. Meeting the evaluation targets

| Metric | Target | How this design supports it |
|---|---|---|
| Intent classification | 90%+ | Constrained JSON output + few-shot examples + `tests/` harness to measure it. |
| SQL query accuracy | 95%+ | Whitelisted schema in the prompt + validation + deterministic execution. |
| RAG answer precision | 90%+ | Grounded-only answering + similarity threshold + source citation. |
| Response latency | < 2s | Local TF-IDF retrieval; single LLM call per turn; SQLite in-process. |
| User satisfaction | 4.5+/5 | Concise natural answers, links to source docs, honest fallbacks. |

## 6. Extending to full production

- Swap TF-IDF for provider embeddings + a vector DB (pgvector / Chroma) via the same `rag_engine` interface.
- Move SQLite → managed Postgres; keep the read-only, client-scoped pattern.
- Put FastAPI in front of the engine and Streamlit/React as a separate frontend (interface is already decoupled from logic).
- Add SSO/MFA at the auth layer and encrypt the audit store.
