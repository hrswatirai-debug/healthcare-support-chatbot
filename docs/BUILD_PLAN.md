# Build Plan

A checklist mapping the capstone brief to what was built, so progress and
completeness are easy to verify.

## Phase 1 — Foundations ✅
- [x] Project scaffold, config via env vars, `.env.example`, `.gitignore`.
- [x] SQLite schema for users, equipment, orders, warranty/AMC, complaints,
      invoices, spare parts, and an audit log.
- [x] Seed data for 3 client hospitals (enables cross-client isolation testing).
- [x] Sample RAG documents: MRI & CT manuals, warranty/AMC policy,
      certifications/compliance, install & maintenance SOP, general FAQ.

## Phase 2 — Core engine ✅
- [x] Provider-agnostic LLM client (Anthropic / OpenAI / Gemini) + offline mock.
- [x] Identity verification (email + client_id).
- [x] Intent classifier → 9 categories + `unknown`.
- [x] Safe NL→SQL engine (SELECT-only, whitelist, client-scoped, read-only).
- [x] TF-IDF RAG engine with grounded answering + similarity threshold.
- [x] Audit logging (Step 5 of the brief).
- [x] Orchestrator that routes intent → SQL / RAG / fallback.

## Phase 3 — Interface ✅
- [x] Streamlit login + chat UI, showing intent / source / latency per answer.

## Phase 4 — Quality ✅
- [x] End-to-end test suite (auth, intent, SQL safety, client isolation,
      RAG retrieval, fallback, router).
- [x] README with quick-start, demo logins, and sample questions.
- [x] Architecture document with data flow and compliance notes.

## Deliverables (from the brief) — status
| Brief deliverable | Status | Where |
|---|---|---|
| Functional chatbot interface + GitHub repo | ✅ | `app.py`, whole repo |
| SQL schema for users, orders, equipment | ✅ | `data/schema.sql` |
| Sample documents for RAG | ✅ | `data/docs/` |
| Deployed backend with logging | ✅ (runnable locally) | `src/`, `chat_audit` table |

## Next steps to "deployed in the cloud"
1. Push the repo to GitHub (the folder is ready; add remote and push).
2. Add a `Dockerfile` (Streamlit base) or deploy to Streamlit Community Cloud.
3. Set the provider API key as a platform secret (not in the repo).
4. Swap SQLite → managed Postgres and TF-IDF → embeddings when scaling.

## Approval checkpoints (per your instructions)
- No external application was installed, subscribed to, or deleted.
- The design assumes **an API key you already have**; if you'd rather run fully
  free/local, say so and the LLM layer can point at a local model instead.
- Deploying to any hosting provider (Streamlit Cloud, a VM, etc.) will be done
  **only after your explicit approval**.
