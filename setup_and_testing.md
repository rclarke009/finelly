# Verbiage — Setup and Testing

## Prerequisites: Ollama (LLM and embeddings)

The app uses **Ollama** for both the LLM (answer generation) and embeddings. Default config expects:

- **LLM:** `qwen3.5:9b` at `http://localhost:11434`
- **Embeddings:** `nomic-embed-text` at the same base URL

### Start Ollama and pull models

```bash
# Start the Ollama server (if not already running as a service)
ollama serve
```

In another terminal, pull the models so the API can load them:

```bash
# LLM used by POST /ask (see app/config.py: LLM_MODEL)
ollama pull qwen3.5:9b

# Embedding model used for ingest and ask (EMBED_MODEL)
ollama pull nomic-embed-text

# Vision model for POST /ask/image and POST /ingest/image (images → text; see app/config.py: LLAVA_MODEL)
ollama pull qwen2.5vl:7b
```

Optional: run the LLM interactively (also pulls if needed):

```bash
ollama run qwen3.5:9b
```

---

## App setup

```bash
cd verbiage
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and adjust if needed (e.g. `DATABASE_PATH`, `LLM_BASE_URL`). Defaults work for local Ollama. For Supabase/Postgres, set `DATABASE_URL` to the Postgres connection URI (Project Settings → Database → Connection string; see `supabase_migration.md`).

Start the API:

```bash
uvicorn app.main:app --reload
```

Default: `http://localhost:8000`. The same server serves the **web UI** at the root URL (see below).

---

## Run with Docker

The simplest way to run Verbiage (no Python or Ollama installed on the host) is with Docker. **No .env or secrets are required** for the default setup (SQLite + Ollama in containers).

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed (Windows, Mac, or Linux).

### Main path: launcher script

1. Open a terminal in the Verbiage project folder (the one that contains `docker-compose.yml`).
2. **Windows:** Double-click **`Start.bat`** or run `Start.bat` from a terminal. The script starts the containers, waits for Ollama, pulls the models (one-time), then opens http://localhost:8000/ in your browser.
3. **Mac/Linux:** Run `./start.sh`. Then open **http://localhost:8000/** in your browser.

First run may take several minutes while models download. Later runs are quick.

**To stop:** In the same folder run `docker compose down`. Data (SQLite DB and Ollama models) is kept in Docker volumes.

### Alternative: manual Compose

```bash
# From the project root (folder that contains docker-compose.yml)
docker compose up -d
```

Then one-time, pull the models:

```bash
docker compose exec ollama ollama pull llama3.1:8b
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull qwen2.5vl:7b
```

Open **http://localhost:8000/**.

### Optional: use your own .env

To override defaults (e.g. Supabase, OpenAI, Google Drive), create a `.env` from `.env.example` and add under the `verbiage` service in `docker-compose.yml`: `env_file: .env`. Do not commit real secrets to the repo.

---

## Web UI

After starting the API with `uvicorn app.main:app --reload`, open a browser at:

**http://localhost:8000/**

You get a single-page UI with **menu/tabs** so you can focus on one task at a time.

### Tabs

- **Ingest** — Paste or enter financial document text, or upload a PDF file; optionally set doc ID, title, and source. Submit to run ingest. Success or error message appears below the form. PDF upload uses the same chunk/embed pipeline as pasted text (requires the `pypdf` dependency from `pip install -r requirements.txt`). To ingest JPG or PNG images (e.g. bank screenshots), use **POST /ingest/image** (see curl below); the server uses LLaVA to extract visible text then ingests it like a text doc.
- **Ask** — Enter a question (e.g. What does this document say about early withdrawal? or Summarize the fees and rates.). Optionally limit the search to one document (dropdown). Submit to get an answer and expandable “Source chunks.” The document dropdown is filled from the list of ingested documents and is refreshed after each ingest.

The last selected tab is remembered in the browser (localStorage) for the next visit.

### Document review (Documents tab)

Click **Documents** in the header to open the Document review tab. Click **Load documents** (or switch to the tab) to fetch and show ingested documents: title, snippet, chunk count, tags, and linked account. Each row has an **Edit** button; use it to change the document’s tags (comma-separated) and which account it is linked to. Save updates the document via `PATCH /documents/{doc_id}`; omit a field in the API to leave it unchanged.

### Quick test flow

1. Open http://localhost:8000/.
2. Switch to the **Ingest** tab, paste some text (or upload a PDF), set a title and doc_id if you like, then submit.
3. Open the **Documents** tab and click **Load documents** to confirm the new doc appears; use **Edit** to set tags or linked account if you like.
4. Switch to the **Ask** tab, type a question that relates to the ingested text, then submit. Check the answer and “Source chunks.”

---

## curl commands

Base URL assumed: `http://localhost:8000`. Use `-s` for quieter output.

### Health check

```bash
curl -s "http://localhost:8000/health"
```

### List documents (GET)

Returns ingested documents (doc_id, title, source, created_at, num_chunks, snippet, tags, linked_account_ids). Same data used by the Web UI Documents tab.

```bash
curl -s "http://localhost:8000/documents"
```

### Update document (PATCH)

Update a document’s tags and/or linked account. Send only the fields you want to change. Use `account_id: null` to unlink all accounts from the document.

```bash
curl -s -X PATCH "http://localhost:8000/documents/cd-terms-2025" \
  -H "Content-Type: application/json" \
  -d '{"tags": ["2025", "CD"], "account_id": "some-account-uuid"}'
```

### Ingest (POST)

Requires a JSON body with at least `text`. Optional: `doc_id`, `title`, `source`, `chunking_options`.

```bash
curl -s -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{"text": "Certificate of Deposit terms: 12-month CD, 4.25% APY, $10,000 minimum. Early withdrawal incurs a penalty of 90 days interest. Maturity date: March 15, 2026.", "title": "CD terms 2025", "doc_id": "cd-terms-2025"}'
```

Minimal (server generates `doc_id`):

```bash
curl -s -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{"text": "Short document to ingest."}'
```

### Ingest image (POST /ingest/image)

Accepts JPG or PNG (e.g. bank screenshots). Uses LLaVA (Ollama) to extract all visible text, then runs the same chunk/embed pipeline as text and PDF. Requires LLaVA to be available (same as `/ask/image`). Multipart form: required `file`; optional `doc_id`, `title`, `source`, `chunk_size`, `chunk_overlap`, `tags`, `confirm_duplicate_content`. Max size 10 MB.

```bash
curl -s -X POST "http://localhost:8000/ingest/image" \
  -F "file=@screenshot.jpg" \
  -F "title=Bank statement screenshot" \
  -F "source=upload"
```

### Ask (POST)

Requires a JSON body with `question`. Optional: `top_k`, `doc_id`, `use_rag`.

After ingesting financial documents (e.g. statements, CD terms, or fee schedules), these questions verify RAG:

```bash
# Answerable from ingested docs: e.g. CD terms or statement
curl -s -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What does this document say about early withdrawal?"}'
```

```bash
# Answerable from ingested docs: fees, rates, or terms
curl -s -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Summarize the fees and rates mentioned."}'
```

With options (e.g. restrict to one document):

```bash
curl -s -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What does this document say about early withdrawal?", "top_k": 5, "doc_id": "cd-terms-2025"}'
```

**Note:** `GET /ask?question=...` is not supported; the endpoint expects **POST** with a JSON body.

### Ask image (POST /ask/image) — LLaVA vision

**POST /ask/image** sends an image to the vision model (Ollama) and returns descriptive text. No RAG. Requires `ollama pull qwen2.5vl:7b` and `LLAVA_MODEL` in config (default `qwen2.5vl:7b`); uses the same `LLM_BASE_URL` as the text LLM.

**Option 1: JSON body** — provide a URL to an image and an optional prompt:

```bash
curl -s -X POST "http://localhost:8000/ask/image" \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/photo.jpg", "prompt": "Describe what you see and summarize any financial details or terms."}'
```

**Option 2: multipart/form-data** — upload an image file and optional prompt:

```bash
curl -s -X POST "http://localhost:8000/ask/image" \
  -F "image=@/path/to/your/image.jpg" \
  -F "prompt=Describe this image and summarize any financial details or terms."
```

Response: `{"answer": "..."}` (text from LLaVA). Image size limit: 10 MB.

---

## Google Drive ingest (read-only)

You can ingest **Google Docs** from Drive by authorizing once with OAuth, then calling **POST /ingest/google-drive**. The app only requests read-only access (`drive.readonly`).

### 1. Google Cloud project and OAuth client

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or pick an existing one) and enable **Google Drive API** (APIs & Services → Library → search “Google Drive API” → Enable).
3. Create OAuth credentials: **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
4. If prompted, configure the **OAuth consent screen** (e.g. External, add your email as test user).
5. For **Application type** choose **Web application**.
6. Under **Authorized redirect URIs** add:  
   `http://localhost:8000/auth/google/callback`  
   (or the same URL with your host/port if you run the app elsewhere).
7. Copy the **Client ID** and **Client secret**.

### 2. Set env and run one-time OAuth

In your `.env` (or environment), set:

```bash
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
```

Optional: if the app is not on port 8000, set the callback URL to match what you registered:

```bash
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

Start the app (`uvicorn app.main:app --reload`), then in a browser open:

**http://localhost:8000/auth/google**

Sign in with the Google account that has access to the Drive files you want to ingest. After you approve, you are redirected to a page that shows a line like:

```bash
GOOGLE_REFRESH_TOKEN="1//0abc..."
```

Add that line to your `.env` (or set the env var), then restart the app.

### 3. Ingest from Drive

**POST /ingest/google-drive** lists and exports Google Docs, then ingests them (chunk + embed + store). Request body (all optional):

- **folder_id** — only list files in this Drive folder.
- **file_ids** — only these file IDs (Google Doc IDs). If set, `folder_id` is ignored.

If both are omitted, the app lists Google Docs from the root of the authenticated user’s Drive.

Example (ingest all Docs in a folder):

```bash
curl -s -X POST "http://localhost:8000/ingest/google-drive" \
  -H "Content-Type: application/json" \
  -d '{"folder_id": "YOUR_DRIVE_FOLDER_ID"}'
```

Example (ingest specific Docs by ID):

```bash
curl -s -X POST "http://localhost:8000/ingest/google-drive" \
  -H "Content-Type: application/json" \
  -d '{"file_ids": ["id1", "id2"]}'
```

Response shape: `{"ingested": N, "skipped": M, "errors": [...], "doc_ids": [...]}`. Duplicate `doc_id` (same file already ingested) is counted as skipped; other failures are listed in `errors`.
