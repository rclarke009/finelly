# Finelly — Overview

Finelly is a **Private Cash & Document Assistant**: it tracks safe-income assets (CDs, money market), ingests financial documents, and provides trigger-based advice (e.g. maturity, obligations due). See **FINANCIAL-ASSISTANT.md** for principles, privacy, and API summary.

**Legacy (Verbiage):** The app still supports document ingest + RAG (storm report verbiage). **Ask** now also uses your financial data (accounts, positions, obligations) so you can ask e.g. "What's my total in CDs?" in addition to document questions.

---

## What It Does

- **Ingest** — Store hundreds or thousands of storm damage reports (text + metadata). Chunk, embed, and index for retrieval.
- **List documents** — See what’s already ingested: titles, doc_id, optional first N characters (snippet) so users know what’s in the system.
- **Ask** — Describe the current case (symptom, damage type, etc.). The app retrieves similar past report text and uses the LLM to suggest **overview** and **detailed image** verbiage.

Works “forward” (drafting from scratch) or “backward” (rewriting rough notes)—either way, AI turns rough input into report-ready verbiage.

---

cd verbiage && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

## Architecture (Phase 3 Style)

- **POST /ingest** — Accept a report (e.g. `doc_id`, `title`, `source`, `text`). Chunk, embed chunks, store in SQLite (documents, chunks, embeddings).
- **GET /documents** — Return a list of ingested documents (e.g. `doc_id`, `title`, `source`, `created_at`, `num_chunks`, and optional `snippet` = first N characters) so users can see what has been loaded.
- **POST /ask** — Accept a question or prompt (e.g. “This report has [symptom]. Give me overview and detailed image verbiage.”). Embed query → top-k similarity search → LLM with retrieved chunks as context → return suggested verbiage.

Same RAG flow as the learning project; domain = storm damage reports and reusable wording.

---

## Tech (Initial)

- FastAPI, Pydantic, async LLM + embedding client
- SQLite + chunk/embedding storage (pgvector later if needed)
- Chunking (e.g. by chars/sentences), cosine similarity retrieval
- **Data sources:** Ingest from PDF and .docx only (see `code-notes.md` for rationale and implementation).
- **Models (local, for client-name privacy):** **Llama 3.1 8B** via Ollama for text/RAG (POST /ask); **LLaVA** (Ollama) in the next phase for image → report.

---

## Roadmap

1. **Phase 3 clone** — Ingest + RAG (POST /ingest, POST /ask) for report text; verbiage-focused prompts. LLM: **Llama 3.1 8B** (Ollama, local).
2. **Phase 4** — Cache, observability, API key auth. Keep Llama 3.1 8B for text; add **LLaVA** (Ollama) for “look at this job’s images and write report text.”
3. **Later** — Optional: image-based damage comparison (vision/embeddings) as a separate feature; LLaVA remains the target vision model.
