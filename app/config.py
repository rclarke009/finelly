## Config and environment

# Small config module that reads from the environment: things like database path, 
# embedding model name and (if you use a remote API) base URL and API key. 
# Use sensible defaults where safe (e.g. a local SQLite path); never default secrets. 
# Keep config in one place so the rest of the app doesn’t touch `os.environ` directly.

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # Load .env into os.environ; no-op override if Docker already set vars

# Database: SQLite (local) or Postgres (Supabase)
# - For SQLite: set DATABASE_PATH (default verbiage.db). Leave DATABASE_URL unset/empty.
# - For Postgres/Supabase: set DATABASE_URL to the Postgres connection string from
#   Project Settings → Database → "Connection string" (choose URI). It looks like:
#   postgresql://postgres.[ref]:[PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres
#   (This is not the project URL https://xxx.supabase.co — that's for the JS client.)
#   Use pooler port 6543 for short-lived connections; use with psycopg2 or asyncpg.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()  # No default; empty = use SQLite

# SQLite path (used only when DATABASE_URL is empty)
DB_PATH = os.getenv("DATABASE_PATH", "verbiage.db")

EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
# EMBED_API_KEY = "" # optional for local Ollama; don’t default it. The client should only require it when you’re not using local (e.g. only require it when base URL is not localhost, or allow empty for local).
EMBED_TIMEOUT = int(os.getenv("EMBED_TIMEOUT", 30))
EMBED_MAX_ATTEMPTS = int(os.getenv("EMBED_MAX_ATTEMPTS", 3))

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
LLAVA_MODEL = os.getenv("LLAVA_MODEL", "qwen2.5vl:7b")
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", 60))
LLM_MAX_ATTEMPTS = int(os.getenv("LLM_MAX_ATTEMPTS", 3))
LLM_TOKEN_LIMIT = int(os.getenv("LLM_TOKEN_LIMIT", 10))
LLM_RATE_LIMIT_SECONDS = int(os.getenv("LLM_RATE_LIMIT_SECONDS", 60))

# OpenAI (general-path only: CD advice, rate summary; no PII in prompts).
# Safety: OpenAI is called only with server-built prompts (numbers, product types, fixed text).
# Never send user/institution names, doc content, or raw user questions. Required only when
# using GET /decision OpenAI advice or POST /ask/general.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_TIMEOUT_SECONDS = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
OPENAI_MAX_ATTEMPTS = int(os.getenv("OPENAI_MAX_ATTEMPTS", "3"))

# Google Drive (read-only ingest). No defaults for secrets.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "")
# Callback URL for one-time OAuth (must match value in Google Cloud Console).
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

# Remote log (Option B: Supabase Edge Function). When set, ERROR/WARNING are POSTed (no PII).
REMOTE_LOG_URL = os.getenv("REMOTE_LOG_URL", "").strip()
REMOTE_LOG_SECRET = os.getenv("REMOTE_LOG_SECRET", "").strip()
REMOTE_LOG_INSTANCE_ID = os.getenv("REMOTE_LOG_INSTANCE_ID", "").strip()
# Supabase anon key: sent as Authorization Bearer when calling Edge Functions (avoids 401 at gateway).
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()

# Re-ranker (two-stage retrieval). When enabled, first stage retrieves initial_k candidates,
# then a local cross-encoder re-ranks them and we keep the top top_k for context.
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "false").strip().lower() in ("true", "1", "yes")
RERANK_INITIAL_K_MULTIPLIER = int(os.getenv("RERANK_INITIAL_K_MULTIPLIER", "3"))
RERANK_INITIAL_K_MAX = int(os.getenv("RERANK_INITIAL_K_MAX", "50"))
RERANK_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2").strip()

# old settings if we want to switch to chatgpt:
# so the full embedding URL used by the client becomes http://localhost:11434/api/embeddings (base + path in code).
# EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "https://api.openai.com/v1").rstrip("/")
# EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
# EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
# EMBED_TIMEOUT = float(os.getenv("EMBED_TIMEOUT", "30"))
# EMBED_MAX_ATTEMPTS = int(os.getenv("EMBED_MAX_ATTEMPTS", "3"))
