# AI-Powered Customer Support Chatbot — Healthcare Equipment (RAG + SQL)

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-engine-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)
![n8n](https://img.shields.io/badge/n8n-orchestration-EA4B71?logo=n8n&logoColor=white)
![Tests](https://img.shields.io/badge/tests-12%2F12%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

A real-time, chat-only customer-support assistant for a medical-equipment
manufacturer. It verifies the customer's identity, detects intent, and answers
by routing each question to either a **SQL** database (structured facts like
orders and warranties) or a **RAG** pipeline (documents like manuals, policies,
and certificates). When it can't find an answer, it says so honestly.

> New to the project? Read `docs/EXPLAIN_LIKE_IM_12.md` for a plain-language tour,
> and `docs/ARCHITECTURE.md` for the technical design.

## Features
- Chat-only web interface (Streamlit) with secure login (email + client ID).
- Intent detection across 9 support categories.
- **Hybrid engine:** safe NL→SQL for structured data + TF-IDF RAG for documents.
- Strong safety: SELECT-only SQL, per-client row scoping, read-only DB access.
- Honest fallback: *"I don't know the answer to that."*
- Full audit logging of every interaction (user, timestamp, intent, source, latency).
- Provider-agnostic LLM layer: Anthropic, OpenAI, or Gemini — chosen by env var.
  Runs fully offline in a deterministic `mock` mode when no key is set (used by tests).

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure your AI provider (use a key you already have)
cp .env.example .env
#   then edit .env and paste ONE key (ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY)

# 3. Initialize the database + build the RAG index
python scripts/init_db.py

# 4. Run the chatbot
streamlit run app.py
```

Then open the browser tab Streamlit prints (usually http://localhost:8501).

### Demo logins
| Organization | Email | Client ID |
|---|---|---|
| St. Mary Hospital | `admin@stmary-hospital.org` | `CLI-1001` |
| Green Valley Clinic | `ops@greenvalley-clinic.com` | `CLI-1002` |
| Lakeside Medical Center | `proc@lakeside-medical.org` | `CLI-1003` |

### Things to try
- "What's the status of my orders?"  → SQL
- "Is my warranty still active?"      → SQL
- "How do I book preventive maintenance?" → RAG
- "What's the field strength of the MagnaScan MRI?" → RAG
- "Can you send the FDA certificate?" → RAG
- "What's the weather tomorrow?"      → honest fallback

## Running with n8n orchestration (Docker)

Every chat turn can be routed through a self-hosted **n8n** workflow that calls
the FastAPI engine for auth → intent → SQL/RAG → response, and handles async
side-effects (ticketing, escalation, scheduled re-index). See
`docs/ARCHITECTURE_N8N.md` for the design and rationale.

```bash
cp .env.example .env          # set LLM key, ENGINE_API_KEY, N8N_PASSWORD
docker compose up --build     # starts engine (:8000) + n8n (:5678)
```
Then in n8n (http://localhost:5678): **Import from File** →
`n8n/workflow_chatbot_orchestrator.json` → **Activate**. Put the webhook URL it
gives you into `.env` as `N8N_WEBHOOK_URL`, then run `streamlit run app.py`.
The UI sidebar shows **Orchestration: n8n**; if n8n is down it falls back to the
in-process engine automatically.

> Self-host n8n only (not n8n Cloud) so patient data stays on your host.

## Running the tests
No API key required — tests use the offline `mock` provider:
```bash
python -m pytest -q
# or:
python tests/test_system.py
```

## Project layout
```
healthcare-support-chatbot/
├── app.py                  # Streamlit chat UI (login + chat)
├── config.py               # env-driven configuration & provider selection
├── requirements.txt
├── .env.example            # copy to .env and add your key
├── scripts/init_db.py      # create DB + build RAG index
├── src/
│   ├── llm.py              # provider-agnostic LLM client (+ offline mock)
│   ├── db.py               # SQLite init + read-only connections
│   ├── auth.py             # identity verification
│   ├── intent.py           # intent classification
│   ├── sql_engine.py       # safe NL→SQL (SELECT-only, client-scoped)
│   ├── rag_engine.py       # TF-IDF retrieval + grounded answering
│   ├── logger.py           # audit logging
│   └── router.py           # orchestrator
├── data/
│   ├── schema.sql          # users, orders, equipment, warranty, complaints, invoices, spares
│   ├── seed.sql            # demo data (3 client hospitals)
│   └── docs/               # sample RAG documents (manuals, policies, certs, SOPs)
├── tests/test_system.py    # end-to-end tests (offline)
└── docs/
    ├── EXPLAIN_LIKE_IM_12.md
    ├── ARCHITECTURE.md
    └── BUILD_PLAN.md
```

## Security & compliance (HIPAA-like posture)
- API keys are read from the environment; nothing secret is committed or logged.
- SQL is validated to be SELECT-only, restricted to whitelisted tables, and forced
  to filter by the logged-in `client_id`, executed on a read-only connection —
  a client can never read another client's data.
- Every interaction is written to an audit log; logging can be anonymized.

## Notes on production hardening
This repository is a complete, runnable reference implementation. For a real
deployment: move SQLite → managed Postgres, swap TF-IDF → embedding vectors +
a vector store, add SSO/MFA and encryption at rest, and place a FastAPI service
in front of the engine. See `docs/ARCHITECTURE.md` §6.

## License
Provided for the capstone project. Sample data and documents are fictional.
