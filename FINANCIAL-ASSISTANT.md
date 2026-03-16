# Finelly — Private Cash & Document Assistant

Finelly is a **private financial assistant** that helps manage safe-income assets (CDs, money market) and financial documents. It acts as a source-of-truth tracker, document analysis assistant, and decision-support tool for maturity and liquidity events.

## Principles

- **Database is the source of truth** — Structured tables (accounts, positions, obligations) are authoritative; the AI assists with extraction, explanation, and memos.
- **Table-driven decisions** — Decisions are driven from structured data; documents support and verify.
- **Trigger-based reasoning** — Recommendations only when meaningful triggers occur (e.g. CD maturity, obligation due); otherwise "No action required."
- **Privacy first** — Documents and data stay local or in private storage; document text is not sent to public APIs; reference-data lookups use only generic, non-personal parameters.

## Privacy

- **Documents:** Stored only in your local SQLite (or your own Supabase). No document text is sent to third-party APIs.
- **Embedding & LLM:** Defaults to local Ollama (`http://localhost:11434`). All embedding and generation can stay on your machine.
- **Reference data:** When the app fetches CD rates or fee info from the web, it sends only generic parameters (e.g. "6-month CD rates"). No account names, balances, or document content are ever included in those requests. **Public data in; no personal data out.**
- **Config:** Do not set API keys or external URLs for document/LLM flows if you want full local operation. See `.env.example` and `app/config.py`.

## Main features

- **GET /decision** — Run the trigger engine; get "No action required" or actionable triggers plus a memo and **sources** (user data refs and web links).
- **GET /decision/history** — List past decision results for the Past advice view.
- **POST /ask** — Ask questions over your **documents** (RAG) and over your **data** (accounts, positions, obligations). One place to ask anything.
- **CRUD** — Accounts, positions, obligations: `GET/POST/PATCH/DELETE /accounts`, `/positions`, `/obligations`.
- **Documents** — Ingest, list, and ask over ingested docs (existing RAG).

## Run

```bash
cd finelly && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
# Optional: set DATABASE_PATH, LLM_BASE_URL, EMBED_BASE_URL in .env
uvicorn app.main:app --reload
```

Open the UI (e.g. http://localhost:8000). Use **Status** to get current advice and **Past advice** to see history. Add accounts and positions via API or (later) UI forms; then **Ask** can answer questions about your data and documents.
