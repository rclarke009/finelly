## 8. POST /ingest

# Wire the ingest endpoint: validate the request body with your Pydantic model;
#  chunk the `text` with your chunking function; insert one row into the documents
#  table; insert one row per chunk into the chunks table (build chunk id from docid:chunkindex); call your embedder for all
#  chunk texts; insert one row per chunk into the embeddings table; return your 
# ingest response. Decide and document: if `doc_id` already exists, do you return
#  an error (e.g. 409) or overwrite? If embedding fails after you’ve written 
# documents/chunks, do you roll back or leave partial data? Prefer “reject duplicate
#  doc_id” and “roll back or don’t persist on embed failure” so the DB stays 
# consistent.

# **Why now:** This is the first end-to-end flow: text in, chunks and embeddings 
# stored. Getting it right here makes the rest of the app usable.

# **Hint:** You can use a single transaction (begin, insert doc + chunks + embeddings,
#  commit) and roll back on any failure, or explicitly delete the document and its 
# chunks if embedding fails. Document your choice in a comment or in `code-notes.md`.

## 9. POST /ask

# Wire the ask endpoint: validate the request; embed the question with the same embedder 
# you use for chunks; call your retrieval function to get top-k chunks; build a prompt 
# that includes a short system instruction (e.g. “You suggest report verbiage based on 
# the following context”), the user’s question, and a “Context:” section with the 
# retrieved chunks (include doc_id and maybe chunk_id so the model can refer to sources). 
# Call your LLM with that prompt and return the model’s answer plus the list of top chunks 
# (and optionally scores/snippets). Cap the total context length (e.g. character or token
#  limit) so you don’t exceed model limits. If retrieval returns no chunks, either return 
# a message like “I don’t have relevant context” or call the LLM without context and say 
# so in the prompt.

# **Why now:** This completes the RAG loop: question → embed → retrieve → prompt 
# with context → LLM → answer. Verbiage’s value is “ask for overview/detail wording 
# and get it from similar reports.”

# **Hint:** Reuse your ai-document LLM client or a minimal async caller; point it at 
# **Ollama** (e.g. `http://localhost:11434`) and use **Llama 3.1 8B** (`llama3.1:8b`) 
# so all generation stays local for client-name privacy. Keep the prompt template in 
# one place so you can tune it later for “overview and detailed image verbiage.” 
# Next phase: **LLaVA** (Ollama) for “look at this job’s images and write report text.”

## 10. GET /documents (list ingested)

# Add an endpoint that returns a list of what has already been ingested so users can 
# see what’s in the system (confirm uploads, spot duplicates, scan by title). Implement
#  **GET /documents** (or **GET /ingest** if you prefer) that queries the documents table
#  and returns a list of items. Each item should include at least: `doc_id`, `title`, 
# `source`, `created_at`, and `num_chunks`. Optionally include a short `snippet` (e.g. 
# first 200–300 characters of the document text, or of the first chunk’s content) so users
#  get a quick preview. Define a Pydantic response model (e.g. `DocumentSummary` with those
#  fields) and a list response (e.g. `DocumentsListResponse` with `documents: 
# list[DocumentSummary]`). Add a DB helper that selects from `documents` and optionally 
# joins with the first chunk per doc for the snippet; keep the query simple (e.g. order 
# by `created_at` desc).


import base64
import hashlib
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
import uuid

from pypdf import PdfReader

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
import asyncio
import time
import logging
import json


from app.db import (
    create_db,
    delete_by_doc_id,
    get_doc_ids_by_tag,
    insert_chunk,
    insert_document,
    insert_embedding,
    set_document_tags,
    set_document_linked_account,
    doc_exist,
    find_doc_id_by_content_hash,
    list_documents,
    list_accounts,
    list_positions,
    list_obligations,
    get_position,
    get_obligation,
    get_account,
    insert_account,
    update_account,
    delete_account,
    insert_position,
    update_position,
    delete_position,
    insert_obligation,
    update_obligation,
    delete_obligation,
    insert_decision_history,
    list_decision_history,
    list_trigger_events,
)
from app.models import (
    AskGeneralRequest,
    AskGeneralResponse,
    AskImageResponse,
    AskRequest,
    AskResponse,
    ChunkingOptions,
    DocumentSummary,
    DocumentUpdateRequest,
    DocumentsListResponse,
    IngestRequest,
    IngestResponse,
    IngestGoogleDriveRequest,
    IngestGoogleDriveResponse,
    DecisionResponse,
    TriggerEventResponse,
    UserDataSource,
    WebSource,
    DecisionHistoryItem,
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    PositionCreate,
    PositionUpdate,
    PositionResponse,
    ObligationCreate,
    ObligationUpdate,
    ObligationResponse,
)
from app.triggers import evaluate_triggers
from app.reference_data import fetch_cd_rates, RateInfo
from app.rate_limit import TokenBucket
from app.chunking import chunk_text_chars
from app.embeddings import HttpEmbedder
from app.job_store import JobStore
from app.worker import worker_loop
from app.retrieval import retrieve_top_k
from app.reranker import rerank
from app.errors import LLMRateLimitedError, LLMServiceError, LLMTimeoutError, LLMUpstreamTimeoutError
from app.drive_client import list_and_export_docs, DriveClientError
from app.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    RERANK_ENABLED,
    RERANK_INITIAL_K_MAX,
    RERANK_INITIAL_K_MULTIPLIER,
)
from app import llm_client
from app.remote_log import send_remote_log

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class DuplicateContentError(Exception):
    """Raised when the same text/PDF content is already ingested (same content_hash)."""
    def __init__(self, existing_doc_id: str):
        self.existing_doc_id = existing_doc_id
        super().__init__(f"Content already ingested as doc_id={existing_doc_id!r}")


@asynccontextmanager
async def lifespan(app):

    # create db
    app.state.db_path = "documentsdb.sqlite"

    newdb = sqlite3.connect(app.state.db_path)
    # app.state.db_conn = create_db(newdb)      concurrency issues since the documents fetch is on a separate thread
    conn = create_db(newdb)
    conn.close()            # we don't need the connection right now, other areas will grab their conn based on the path 

    ### to do - create job store
    app.state.job_store = JobStore()
    job_store = app.state.job_store

    #create token bucket
    app.state.rate_limiter = TokenBucket()
    rate_limiter = app.state.rate_limiter

    #create task loop - worker will poll for pending jobs and process them.
    task = asyncio.create_task(worker_loop(job_store, rate_limiter))
    logger.info("Work Started")

    yield
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError as e:
        pass

    conn.close()
    logger.info("Work has stopped")


# create the web service and async life cycle thingy
app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def request_id_and_duration_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    request.state.trace_id = request_id
    request.state.start_time = time.perf_counter()
    request.state.route = f"{request.method} {request.url.path}"
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def _duration_ms(request: Request) -> int | None:
    if not getattr(request.state, "start_time", None):
        return None
    return int((time.perf_counter() - request.state.start_time) * 1000)


def _remote_log_error(request: Request, message: str, error_type: str) -> None:
    send_remote_log(
        level="ERROR",
        message=message,
        route=getattr(request.state, "route", None),
        request_id=getattr(request.state, "request_id", None),
        trace_id=getattr(request.state, "trace_id", None),
        duration_ms=_duration_ms(request),
        error_type=error_type,
    )


async def ingest_text(
    conn: sqlite3.Connection,
    doc_id: str,
    title: str | None,
    source: str | None,
    text: str,
    chunking_options: ChunkingOptions,
    confirm_duplicate_content: bool = False,
    tags: list[str] | None = None,
    account_id: str | None = None,
) -> IngestResponse:
    """
    Shared ingest: chunk text, insert document + chunks, embed, insert embeddings, commit.
    Raises ValueError('doc_id already exists') if doc_id is duplicate.
    Raises DuplicateContentError(existing_doc_id) if same content already ingested and not confirmed.
    Rollback (delete_by_doc_id) on embedding failure.
    """
    if doc_exist(conn, doc_id):
        raise ValueError("doc_id already exists")
    normalized = text.strip()
    content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    if not confirm_duplicate_content:
        existing_doc_id = find_doc_id_by_content_hash(conn, content_hash)
        if existing_doc_id is not None:
            raise DuplicateContentError(existing_doc_id)
    opts = chunking_options
    chunks = chunk_text_chars(normalized, opts.chunk_size, opts.chunk_overlap)
    insert_document(conn, doc_id, int(time.time()), title, source, content_hash=content_hash)
    for chunk in chunks:
        chunk_id = f"{doc_id}:{chunk.chunk_index}"
        insert_chunk(
            conn, chunk_id, doc_id, chunk.chunk_index, chunk.content,
            chunk.start_offset, chunk.end_offset,
        )
    embedder = HttpEmbedder()
    try:
        vectors = await embedder.embed_many([c.content for c in chunks])
    except Exception as e:
        delete_by_doc_id(conn, doc_id)
        logger.exception("embedding failed", exc_info=e)
        raise
    for chunk, vector in zip(chunks, vectors):
        chunk_id = f"{doc_id}:{chunk.chunk_index}"
        insert_embedding(conn, chunk_id, embedder.model, json.dumps(vector), embedder.dim)
    if tags:
        set_document_tags(conn, doc_id, tags)
    if account_id:
        set_document_linked_account(conn, doc_id, account_id)
    conn.commit()
    return IngestResponse(
        doc_id=doc_id,
        num_chunks=len(chunks),
        embedding_model=embedder.model,
        dim=embedder.dim,
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest(request: Request, ingest_request: IngestRequest):
    with sqlite3.connect(request.app.state.db_path) as conn:
        try:
            return await ingest_text(
                conn,
                ingest_request.doc_id,
                ingest_request.title,
                ingest_request.source,
                ingest_request.text,
                ingest_request.chunking_options,
                confirm_duplicate_content=ingest_request.confirm_duplicate_content,
                tags=ingest_request.tags or None,
                account_id=ingest_request.account_id,
            )
        except DuplicateContentError as e:
            raise HTTPException(
                status_code=409,
                detail={"code": "duplicate_content", "existing_doc_id": e.existing_doc_id},
            ) from e
        except ValueError as e:
            if "already exists" in str(e):
                raise HTTPException(
                    status_code=409,
                    detail="doc_id (document title) already exists. Use a different doc_id or delete the existing document first.",
                ) from e
            raise
        except Exception as e:
            raise HTTPException(status_code=503, detail="Embedding failed") from e


def _extract_text_from_pdf(data: bytes) -> str:
    """Extract text from PDF bytes. Returns concatenated text from all pages."""
    reader = PdfReader(BytesIO(data))
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts)


@app.post("/ingest/pdf", response_model=IngestResponse)
async def ingest_pdf(request: Request):
    """
    Ingest a PDF file: multipart/form-data with required 'file' (PDF),
    optional doc_id, title, source, chunk_size, chunk_overlap.
    Extracts text server-side then runs the same chunk/embed pipeline as POST /ingest.
    """
    form = await request.form()
    file = form.get("file")
    if file is None or not hasattr(file, "read"):
        raise HTTPException(
            status_code=400,
            detail="multipart form must include 'file' (PDF).",
        )
    raw = await file.read()
    if len(raw) > INGEST_PDF_MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"PDF too large (max {INGEST_PDF_MAX_BYTES // (1024*1024)} MB).",
        )
    if not raw.startswith(PDF_MAGIC):
        raise HTTPException(
            status_code=400,
            detail="File does not appear to be a PDF.",
        )
    try:
        text = _extract_text_from_pdf(raw)
    except Exception as e:
        logger.exception("PDF extraction failed", exc_info=e)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read PDF: {e!s}",
        ) from e
    text = (text or "").strip()
    if not text:
        raise HTTPException(
            status_code=400,
            detail="No text could be extracted; the PDF may be image-only or empty.",
        )
    filename = getattr(file, "filename", None) or "upload.pdf"
    doc_id_raw = form.get("doc_id")
    doc_id = str(doc_id_raw).strip() if isinstance(doc_id_raw, str) else None
    if not doc_id:
        doc_id = str(uuid.uuid4())
    title_raw = form.get("title")
    title = str(title_raw).strip() or None if isinstance(title_raw, str) else None
    source_raw = form.get("source")
    source = (str(source_raw).strip() or filename) if isinstance(source_raw, str) else filename
    chunk_size = 800
    chunk_overlap = 100
    cs = form.get("chunk_size")
    if cs is not None:
        try:
            chunk_size = int(cs) if isinstance(cs, str) else int(cs)
        except (TypeError, ValueError):
            pass
    co = form.get("chunk_overlap")
    if co is not None:
        try:
            chunk_overlap = int(co) if isinstance(co, str) else int(co)
        except (TypeError, ValueError):
            pass
    try:
        chunking_options = ChunkingOptions(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    confirm_duplicate = form.get("confirm_duplicate_content")
    confirm_duplicate_content = str(confirm_duplicate).strip().lower() in ("1", "true", "yes")
    tags_raw = form.get("tags")
    tags_list = None
    if tags_raw is not None and isinstance(tags_raw, str) and tags_raw.strip():
        tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
    account_id_raw = form.get("account_id")
    account_id = str(account_id_raw).strip() or None if isinstance(account_id_raw, str) else None
    with sqlite3.connect(request.app.state.db_path) as conn:
        try:
            return await ingest_text(
                conn, doc_id, title, source, text, chunking_options,
                confirm_duplicate_content=confirm_duplicate_content,
                tags=tags_list,
                account_id=account_id,
            )
        except DuplicateContentError as e:
            raise HTTPException(
                status_code=409,
                detail={"code": "duplicate_content", "existing_doc_id": e.existing_doc_id},
            ) from e
        except ValueError as e:
            if "already exists" in str(e):
                raise HTTPException(
                    status_code=409,
                    detail="doc_id (document title) already exists. Use a different doc_id or delete the existing document first.",
                ) from e
            raise
        except Exception as e:
            raise HTTPException(status_code=503, detail="Embedding failed") from e


def _is_supported_image(data: bytes) -> bool:
    """True if data looks like JPEG or PNG (magic bytes)."""
    return data.startswith(JPEG_MAGIC) or data.startswith(PNG_MAGIC)


@app.post("/ingest/image", response_model=IngestResponse)
async def ingest_image(request: Request):
    """
    Ingest an image file (JPG or PNG): multipart/form-data with required 'file',
    optional doc_id, title, source, chunk_size, chunk_overlap.
    Uses LLaVA to extract visible text (e.g. from bank screenshots), then runs
    the same chunk/embed pipeline as POST /ingest.
    """
    form = await request.form()
    file = form.get("file")
    if file is None or not hasattr(file, "read"):
        raise HTTPException(
            status_code=400,
            detail="multipart form must include 'file' (image).",
        )
    raw = await file.read()
    if len(raw) > INGEST_IMAGE_MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large (max {INGEST_IMAGE_MAX_BYTES // (1024*1024)} MB).",
        )
    if not _is_supported_image(raw):
        raise HTTPException(
            status_code=400,
            detail="File must be a JPEG or PNG image.",
        )
    try:
        image_base64 = base64.b64encode(raw).decode("ascii")
        text = await llm_client.image_to_text_for_ingest(image_base64)
    except (LLMServiceError, LLMRateLimitedError, LLMUpstreamTimeoutError) as e:
        logger.exception("Image text extraction failed", exc_info=e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    text = (text or "").strip()
    if len(text) < 10:
        raise HTTPException(
            status_code=400,
            detail="No text could be extracted from the image.",
        )
    filename = getattr(file, "filename", None) or "upload.jpg"
    doc_id_raw = form.get("doc_id")
    doc_id = str(doc_id_raw).strip() if isinstance(doc_id_raw, str) else None
    if not doc_id:
        doc_id = str(uuid.uuid4())
    title_raw = form.get("title")
    title = str(title_raw).strip() or None if isinstance(title_raw, str) else None
    source_raw = form.get("source")
    source = (str(source_raw).strip() or filename) if isinstance(source_raw, str) else filename
    chunk_size = 800
    chunk_overlap = 100
    cs = form.get("chunk_size")
    if cs is not None:
        try:
            chunk_size = int(cs) if isinstance(cs, str) else int(cs)
        except (TypeError, ValueError):
            pass
    co = form.get("chunk_overlap")
    if co is not None:
        try:
            chunk_overlap = int(co) if isinstance(co, str) else int(co)
        except (TypeError, ValueError):
            pass
    try:
        chunking_options = ChunkingOptions(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    confirm_duplicate = form.get("confirm_duplicate_content")
    confirm_duplicate_content = str(confirm_duplicate).strip().lower() in ("1", "true", "yes")
    tags_raw = form.get("tags")
    tags_list = None
    if tags_raw is not None and isinstance(tags_raw, str) and tags_raw.strip():
        tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
    account_id_raw = form.get("account_id")
    account_id = str(account_id_raw).strip() or None if isinstance(account_id_raw, str) else None
    with sqlite3.connect(request.app.state.db_path) as conn:
        try:
            return await ingest_text(
                conn, doc_id, title, source, text, chunking_options,
                confirm_duplicate_content=confirm_duplicate_content,
                tags=tags_list,
                account_id=account_id,
            )
        except DuplicateContentError as e:
            raise HTTPException(
                status_code=409,
                detail={"code": "duplicate_content", "existing_doc_id": e.existing_doc_id},
            ) from e
        except ValueError as e:
            if "already exists" in str(e):
                raise HTTPException(
                    status_code=409,
                    detail="doc_id (document title) already exists. Use a different doc_id or delete the existing document first.",
                ) from e
            raise
        except Exception as e:
            raise HTTPException(status_code=503, detail="Embedding failed") from e


@app.post("/ingest/google-drive", response_model=IngestGoogleDriveResponse)
async def ingest_google_drive(request: Request, body: IngestGoogleDriveRequest):
    """
    Ingest Google Docs from Drive (read-only). List/export then run shared ingest per doc.
    Duplicate doc_id is skipped and counted; other errors are recorded and processing continues.
    """
    try:
        docs = list_and_export_docs(folder_id=body.folder_id, file_ids=body.file_ids)
    except DriveClientError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    default_opts = ChunkingOptions()
    ingested = 0
    skipped = 0
    errors: list[str] = []
    doc_ids: list[str] = []
    with sqlite3.connect(request.app.state.db_path) as conn:
        for doc in docs:
            try:
                await ingest_text(
                    conn,
                    doc.doc_id,
                    doc.title,
                    doc.source,
                    doc.text,
                    default_opts,
                )
                ingested += 1
                doc_ids.append(doc.doc_id)
            except ValueError as e:
                if "already exists" in str(e):
                    skipped += 1
                else:
                    errors.append(f"{doc.doc_id} ({doc.title}): {e}")
            except Exception as e:
                errors.append(f"{doc.doc_id} ({doc.title}): {e}")
                logger.warning("Ingest failed for %s: %s", doc.doc_id, e)
    return IngestGoogleDriveResponse(
        ingested=ingested,
        skipped=skipped,
        errors=errors,
        doc_ids=doc_ids,
    )


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


@app.post("/ask", response_model=AskResponse)
async def ask(request: Request, ask_request: AskRequest):
    """RAG over documents plus optional Layer 2 (your data) summary so user can ask about CDs, obligations, etc."""
    t0 = time.perf_counter()
    logger.info("Ask: embedding question")
    with sqlite3.connect(request.app.state.db_path) as conn:
        rate_limiter = request.app.state.rate_limiter
        embedder = HttpEmbedder()
        query_vectors = await embedder.embed_many([ask_request.question])
        query_vec = query_vectors[0]
        embed_ms = _elapsed_ms(t0)
        logger.info("Ask: embedding done in %d ms, retrieving chunks", embed_ms)

        t1 = time.perf_counter()
        filter_doc_ids = None
        if ask_request.doc_ids:
            filter_doc_ids = ask_request.doc_ids
        elif ask_request.tag and ask_request.tag.strip():
            filter_doc_ids = get_doc_ids_by_tag(conn, ask_request.tag.strip())
        elif ask_request.doc_id and ask_request.doc_id.strip():
            filter_doc_ids = [ask_request.doc_id.strip()]
        initial_k = (
            min(RERANK_INITIAL_K_MULTIPLIER * ask_request.top_k, RERANK_INITIAL_K_MAX)
            if RERANK_ENABLED
            else ask_request.top_k
        )
        top_chunks = retrieve_top_k(conn, query_vec, initial_k, doc_id=None, doc_ids=filter_doc_ids)
        retrieval_ms = _elapsed_ms(t1)
        logger.info("Ask: retrieval done in %d ms (%d chunks)", retrieval_ms, len(top_chunks))

        rerank_ms = 0
        if RERANK_ENABLED and top_chunks:
            t_rerank = time.perf_counter()
            top_chunks = rerank(ask_request.question, top_chunks, ask_request.top_k)
            rerank_ms = _elapsed_ms(t_rerank)
            logger.info("Ask: re-rank done in %d ms (%d chunks)", rerank_ms, len(top_chunks))
        elif len(top_chunks) > ask_request.top_k:
            top_chunks = top_chunks[: ask_request.top_k]

        t2 = time.perf_counter()
        MAX_CONTEXT_CHARS = 8000
        context_parts = []
        total_len = 0
        data_summary = _build_data_summary(conn)
        if data_summary:
            block = "Your data (accounts, positions, obligations):\n" + data_summary + "\n\n"
            if total_len + len(block) <= MAX_CONTEXT_CHARS:
                context_parts.append(block)
                total_len += len(block)
        for c in top_chunks:
            block = f"[doc_id={c.doc_id} chunk_id={c.chunk_id}]\n{c.content_snippet}\n"
            if total_len + len(block) > MAX_CONTEXT_CHARS:
                break
            context_parts.append(block)
            total_len += len(block)
        context_str = "\n".join(context_parts) if context_parts else "(No documents or data loaded.)"
        data_summary_ms = _elapsed_ms(t2)
        logger.info("Ask: data summary + context build in %d ms (%d chars)", data_summary_ms, len(context_str))

        prompt = (
            "Answer using the context below (your data and/or document chunks). If the context doesn't contain enough information, say so.\n\n"
            "Context:\n" + context_str + "\n\n"
            "Question: " + ask_request.question
        )
        if not context_parts or (not top_chunks and not data_summary):
            total_ms = _elapsed_ms(t0)
            logger.info(
                "Ask: early return (no context) total=%d ms (embed=%d retrieval=%d rerank=%d data_summary+context=%d)",
                total_ms, embed_ms, retrieval_ms, rerank_ms, data_summary_ms,
            )
            return AskResponse(answer="I don't have relevant context or data to answer that question.", top_chunks=[])

        t3 = time.perf_counter()
        await rate_limiter.acquire()
        rate_limit_ms = _elapsed_ms(t3)
        if rate_limit_ms > 0:
            logger.info("Ask: rate limit wait %d ms", rate_limit_ms)

        t4 = time.perf_counter()
        answer = await llm_client.answer_with_context(prompt)
        llm_ms = _elapsed_ms(t4)
        total_ms = _elapsed_ms(t0)
        logger.info(
            "Ask: LLM done in %d ms | total=%d ms (embed=%d retrieval=%d rerank=%d data_summary+context=%d rate_limit=%d llm=%d)",
            llm_ms, total_ms, embed_ms, retrieval_ms, rerank_ms, data_summary_ms, rate_limit_ms, llm_ms,
        )
        return AskResponse(answer=answer, top_chunks=top_chunks)


async def _stream_ask_generator(prompt: str, top_chunks: list):
    """Yield NDJSON lines: first line has top_chunks, then deltas from LLM, then done."""
    meta = {"top_chunks": [c.model_dump() if hasattr(c, "model_dump") else c for c in top_chunks]}
    yield json.dumps(meta) + "\n"
    try:
        async for delta in llm_client.answer_with_context_stream(prompt):
            yield json.dumps({"delta": delta}) + "\n"
    except Exception:
        yield json.dumps({"error": "LLM stream failed"}) + "\n"
    yield json.dumps({"done": True}) + "\n"


@app.post("/ask/stream")
async def ask_stream(request: Request, ask_request: AskRequest):
    """RAG same as /ask but streams the LLM response as NDJSON: first line = {top_chunks}, then {delta}, then {done}."""
    with sqlite3.connect(request.app.state.db_path) as conn:
        rate_limiter = request.app.state.rate_limiter
        embedder = HttpEmbedder()
        query_vectors = await embedder.embed_many([ask_request.question])
        query_vec = query_vectors[0]

        filter_doc_ids = None
        if ask_request.doc_ids:
            filter_doc_ids = ask_request.doc_ids
        elif ask_request.tag and ask_request.tag.strip():
            filter_doc_ids = get_doc_ids_by_tag(conn, ask_request.tag.strip())
        elif ask_request.doc_id and ask_request.doc_id.strip():
            filter_doc_ids = [ask_request.doc_id.strip()]
        initial_k = (
            min(RERANK_INITIAL_K_MULTIPLIER * ask_request.top_k, RERANK_INITIAL_K_MAX)
            if RERANK_ENABLED
            else ask_request.top_k
        )
        top_chunks = retrieve_top_k(conn, query_vec, initial_k, doc_id=None, doc_ids=filter_doc_ids)

        if RERANK_ENABLED and top_chunks:
            top_chunks = rerank(ask_request.question, top_chunks, ask_request.top_k)
        elif len(top_chunks) > ask_request.top_k:
            top_chunks = top_chunks[: ask_request.top_k]

        MAX_CONTEXT_CHARS = 8000
        context_parts = []
        total_len = 0
        data_summary = _build_data_summary(conn)
        if data_summary:
            block = "Your data (accounts, positions, obligations):\n" + data_summary + "\n\n"
            if total_len + len(block) <= MAX_CONTEXT_CHARS:
                context_parts.append(block)
                total_len += len(block)
        for c in top_chunks:
            block = f"[doc_id={c.doc_id} chunk_id={c.chunk_id}]\n{c.content_snippet}\n"
            if total_len + len(block) > MAX_CONTEXT_CHARS:
                break
            context_parts.append(block)
            total_len += len(block)
        context_str = "\n".join(context_parts) if context_parts else "(No documents or data loaded.)"
        prompt = (
            "Answer using the context below (your data and/or document chunks). If the context doesn't contain enough information, say so.\n\n"
            "Context:\n" + context_str + "\n\n"
            "Question: " + ask_request.question
        )
        if not context_parts or (not top_chunks and not data_summary):
            async def no_context_stream():
                yield json.dumps({
                    "top_chunks": [],
                    "answer": "I don't have relevant context or data to answer that question.",
                    "done": True,
                }) + "\n"

            return StreamingResponse(
                no_context_stream(),
                media_type="application/x-ndjson",
            )

        await rate_limiter.acquire()

    return StreamingResponse(
        _stream_ask_generator(prompt, top_chunks),
        media_type="application/x-ndjson",
    )


# Max image size for POST /ask/image (file upload or URL fetch)
ASK_IMAGE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB

# Max PDF size for POST /ingest/pdf
INGEST_PDF_MAX_BYTES = 20 * 1024 * 1024  # 20 MB

# PDF magic bytes (simplified: %PDF)
PDF_MAGIC = b"%PDF"

# Image magic bytes for POST /ingest/image
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
INGEST_IMAGE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


@app.post("/ask/image", response_model=AskImageResponse)
async def ask_image(request: Request):
    """
    Image → report text via LLaVA (Ollama vision). No RAG.
    Accept either:
    - JSON: {"image_url": "https://...", "prompt": "optional"}
    - multipart/form-data: image=<file>, prompt=<optional>
    """
    rate_limiter = request.app.state.rate_limiter
    content_type = (request.headers.get("content-type") or "").lower()
    prompt = "Describe this image and summarize any financial details or terms."
    image_base64: str | None = None

    if "application/json" in content_type:
        body = await request.json()
        image_url = body.get("image_url")
        if not image_url or not isinstance(image_url, str):
            raise HTTPException(
                status_code=400,
                detail="JSON body must include 'image_url' (string).",
            )
        prompt = (body.get("prompt") or prompt).strip() or prompt
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(image_url)
                resp.raise_for_status()
                raw = resp.content
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to fetch image from URL: {e!s}",
            ) from e
        if len(raw) > ASK_IMAGE_MAX_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Image too large (max {ASK_IMAGE_MAX_BYTES // (1024*1024)} MB).",
            )
        image_base64 = base64.b64encode(raw).decode("ascii")
    else:
        form = await request.form()
        file = form.get("image")
        if file is None or not hasattr(file, "read"):
            raise HTTPException(
                status_code=400,
                detail="multipart form must include 'image' file.",
            )
        raw = await file.read()
        if len(raw) > ASK_IMAGE_MAX_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Image too large (max {ASK_IMAGE_MAX_BYTES // (1024*1024)} MB).",
            )
        p = form.get("prompt")
        if isinstance(p, str) and p.strip():
            prompt = p.strip()
        image_base64 = base64.b64encode(raw).decode("ascii")

    if not image_base64:
        raise HTTPException(status_code=400, detail="No image provided.")
    await rate_limiter.acquire()
    answer = await llm_client.answer_with_image(image_base64, prompt)
    return AskImageResponse(answer=answer)


@app.post("/ask/general", response_model=AskGeneralResponse)
async def ask_general(request: Request, body: AskGeneralRequest):
    """
    General-path only: templated prompts sent to OpenAI. No RAG, no user docs, no PII.
    Use template + optional amount/term_months; server builds a sanitized prompt.
    """
    if body.template == "cd_rates_summary":
        prompt = "Summarize the current US CD rate environment in 2-3 sentences."
    elif body.template == "cd_advice":
        amount_str = f"${body.amount:,.0f}" if body.amount is not None else "an amount"
        term_str = f" {body.term_months}-month" if body.term_months is not None else ""
        prompt = (
            f"What should someone do if they have {amount_str} in a{term_str} CD maturing now? "
            "Give 2-3 short options."
        )
    else:
        raise HTTPException(status_code=400, detail="Unknown template")
    answer = await llm_client.answer_openai(prompt)
    if answer is None:
        raise HTTPException(
            status_code=503,
            detail="OpenAI not configured (set OPENAI_API_KEY for general-path advice).",
        )
    return AskGeneralResponse(answer=answer)


@app.get("/documents", response_model=DocumentsListResponse)
def get_documents(request: Request):
    with sqlite3.connect(request.app.state.db_path) as conn:
        rows = list_documents(conn)
        documents = [
            DocumentSummary(
                doc_id=r[0],
                title=r[1],
                source=r[2],
                created_at=r[3],
                num_chunks=r[4],
                snippet=r[5],
                tags=r[6] if len(r) > 6 else [],
                linked_account_ids=r[7] if len(r) > 7 else [],
            )
            for r in rows
        ]
        return DocumentsListResponse(documents=documents)


@app.patch("/documents/{doc_id}", response_model=DocumentSummary)
def patch_document(request: Request, doc_id: str, body: DocumentUpdateRequest):
    """Update document tags and/or linked account. Omit a field to leave it unchanged."""
    with sqlite3.connect(request.app.state.db_path) as conn:
        if not doc_exist(conn, doc_id):
            raise HTTPException(status_code=404, detail="Document not found")
        if "tags" in body.model_fields_set:
            set_document_tags(conn, doc_id, body.tags if body.tags is not None else [])
        if "account_id" in body.model_fields_set:
            set_document_linked_account(conn, doc_id, body.account_id)
        conn.commit()
        rows = list_documents(conn)
        for r in rows:
            if r[0] == doc_id:
                return DocumentSummary(
                    doc_id=r[0],
                    title=r[1],
                    source=r[2],
                    created_at=r[3],
                    num_chunks=r[4],
                    snippet=r[5],
                    tags=r[6] if len(r) > 6 else [],
                    linked_account_ids=r[7] if len(r) > 7 else [],
                )
    raise HTTPException(status_code=404, detail="Document not found")


def _build_data_summary(conn: sqlite3.Connection, max_chars: int = 2000) -> str:
    """Build a short text summary of accounts, positions, obligations for Ask (data) context."""
    parts = []
    for row in list_accounts(conn):
        parts.append(f"Account: {row[1]} (type={row[2]}, institution={row[3]})")
    for row in list_positions(conn):
        pos_id, account_id, asset_type, desc, principal, rate_apr, maturity_date, doc_id, _, _ = row
        acc = get_account(conn, account_id)
        acc_name = acc[1] if acc else account_id
        line = f"Position: {asset_type}"
        if desc:
            line += f" {desc}"
        if principal is not None:
            line += f" principal={principal}"
        if rate_apr is not None:
            line += f" rate_apr={rate_apr}%"
        if maturity_date:
            line += f" maturity={maturity_date}"
        line += f" ({acc_name})"
        parts.append(line)
    for row in list_obligations(conn):
        obl_id, description, due_date, amount_estimate, priority, doc_id, _ = row
        line = f"Obligation: {description} due {due_date}"
        if amount_estimate is not None:
            line += f" amount_estimate={amount_estimate}"
        parts.append(line)
    s = "\n".join(parts) if parts else ""
    return s[:max_chars] + ("..." if len(s) > max_chars else "")


def _build_decision_sources(conn: sqlite3.Connection, trigger_rows: list[tuple]) -> list[UserDataSource | WebSource]:
    """Build sources list: user data refs for entities in triggers, plus optional web refs added by caller."""
    sources: list[UserDataSource | WebSource] = []
    seen: set[tuple[str, str]] = set()
    for row in trigger_rows:
        _id, trigger_type, entity_type, entity_id, event_date, evaluated_at, status = row
        key = (entity_type, entity_id)
        if key in seen:
            continue
        seen.add(key)
        if entity_type == "position":
            pos = get_position(conn, entity_id)
            if pos:
                _, account_id, asset_type, desc, principal, rate_apr, maturity_date, doc_id, _, _ = pos
                acc = get_account(conn, account_id)
                acc_name = acc[1] if acc else account_id
                label = f"Position: {asset_type}"
                if desc:
                    label += f" {desc}"
                if maturity_date:
                    label += f", matures {maturity_date}"
                label += f" ({acc_name})"
                sources.append(UserDataSource(entity_type="position", id=entity_id, label=label))
        elif entity_type == "obligation":
            obl = get_obligation(conn, entity_id)
            if obl:
                _, description, due_date, amount_estimate, priority, doc_id, _ = obl
                label = f"Obligation: {description}, due {due_date}"
                sources.append(UserDataSource(entity_type="obligation", id=entity_id, label=label))
    return sources


@app.get("/decision", response_model=DecisionResponse)
async def get_decision(request: Request):
    """
    Run trigger engine; return no_action_required or actionable with triggers, memo, and sources.
    Persists result to decision_history.
    """
    import uuid
    with sqlite3.connect(request.app.state.db_path) as conn:
        triggers = evaluate_triggers(conn, persist=True)
        now_ts = int(time.time())
        trigger_list = [
            TriggerEventResponse(
                id=r[0],
                trigger_type=r[1],
                entity_type=r[2],
                entity_id=r[3],
                event_date=r[4],
                evaluated_at=r[5],
                status=r[6],
            )
            for r in triggers
        ]
        sources = _build_decision_sources(conn, triggers)
        # Add web source for rate context when we have maturity triggers
        if any(t[1] == "maturity" for t in triggers):
            try:
                rate_infos = await fetch_cd_rates()
                for ri in rate_infos[:2]:
                    sources.append(
                        WebSource(
                            quote=ri.quote,
                            url=ri.source_url,
                            source_name=ri.source_name,
                        )
                    )
            except Exception as e:
                logger.warning("Reference data fetch failed: %s", e)

        # OpenAI path: sanitized CD advice per maturity trigger (no PII in prompt)
        openai_advice: list[str] = []
        for t in triggers:
            if t[1] != "maturity" or t[2] != "position":
                continue
            pos = get_position(conn, t[3])
            if not pos:
                continue
            _, _acc_id, asset_type, _desc, principal, rate_apr, maturity_date, *_ = pos
            principal_str = f"${principal:,.0f}" if principal is not None else "an amount"
            rate_str = f"{rate_apr}%" if rate_apr is not None else "unknown rate"
            prompt = (
                f"What should someone do if they have {principal_str} in a CD maturing now? "
                f"Current rate was {rate_str}. Give 2-3 short options."
            )
            try:
                advice = await llm_client.answer_openai(prompt)
                if advice:
                    openai_advice.append(advice)
            except Exception as e:
                logger.warning("OpenAI advice for maturity trigger failed: %s", e)

        if not triggers:
            status = "no_action_required"
            memo = "No action required. No CDs maturing soon and no obligations due in the next 30 days."
            # Include what we considered (positions/obligations) as sources
            positions = list_positions(conn)
            obligations = list_obligations(conn)
            for row in positions[:10]:
                pos_id, account_id, asset_type, desc, principal, rate_apr, maturity_date, doc_id, _, _ = row
                acc = get_account(conn, account_id)
                acc_name = acc[1] if acc else account_id
                label = f"Position: {asset_type}" + (f" {desc}" if desc else "") + (f", matures {maturity_date}" if maturity_date else "") + f" ({acc_name})"
                sources.append(UserDataSource(entity_type="position", id=pos_id, label=label))
            for row in obligations[:10]:
                obl_id, description, due_date, amount_estimate, priority, doc_id, _ = row
                sources.append(UserDataSource(entity_type="obligation", id=obl_id, label=f"Obligation: {description}, due {due_date}"))
        else:
            status = "actionable"
            memo = f"You have {len(triggers)} item(s) needing attention: " + "; ".join(
                f"{t[1]} ({t[2]} {t[3]})" for t in triggers[:5]
            ) + ". Review maturity and obligation dates; consider renewing or reallocating."
        history_id = str(uuid.uuid4())
        trigger_ids_str = json.dumps([r[0] for r in triggers])
        insert_decision_history(conn, history_id, now_ts, status, memo, trigger_ids_str)
        conn.commit()
        return DecisionResponse(
            status=status,
            triggers=trigger_list,
            memo=memo,
            sources=sources,
            openai_advice=openai_advice,
        )


@app.get("/decision/history", response_model=list[DecisionHistoryItem])
def get_decision_history(request: Request, since: int | None = None, limit: int = 50):
    """List past decision results (evaluated_at, status, memo) for the Past advice view."""
    with sqlite3.connect(request.app.state.db_path) as conn:
        rows = list_decision_history(conn, since=since, limit=limit)
        return [
            DecisionHistoryItem(id=r[0], evaluated_at=r[1], status=r[2], memo=r[3], trigger_ids=r[4])
            for r in rows
        ]


# --- Financial CRUD ---

@app.get("/accounts", response_model=list[AccountResponse])
def list_accounts_route(request: Request):
    with sqlite3.connect(request.app.state.db_path) as conn:
        rows = list_accounts(conn)
        return [AccountResponse(id=r[0], name=r[1], type=r[2], institution=r[3], document_id=r[4], created_at=r[5]) for r in rows]


@app.post("/accounts", response_model=AccountResponse)
def create_account(request: Request, body: AccountCreate):
    import uuid
    acc_id = str(uuid.uuid4())
    now = int(time.time())
    with sqlite3.connect(request.app.state.db_path) as conn:
        insert_account(conn, acc_id, body.name, now, body.type, body.institution, body.document_id)
        conn.commit()
    return AccountResponse(id=acc_id, name=body.name, type=body.type, institution=body.institution, document_id=body.document_id, created_at=now)


@app.get("/accounts/{account_id}", response_model=AccountResponse)
def get_account_route(request: Request, account_id: str):
    with sqlite3.connect(request.app.state.db_path) as conn:
        row = get_account(conn, account_id)
        if not row:
            raise HTTPException(status_code=404, detail="Account not found")
        return AccountResponse(id=row[0], name=row[1], type=row[2], institution=row[3], document_id=row[4], created_at=row[5])


@app.patch("/accounts/{account_id}", response_model=AccountResponse)
def patch_account(request: Request, account_id: str, body: AccountUpdate):
    with sqlite3.connect(request.app.state.db_path) as conn:
        row = get_account(conn, account_id)
        if not row:
            raise HTTPException(status_code=404, detail="Account not found")
        update_account(conn, account_id, body.name, body.type, body.institution, body.document_id)
        conn.commit()
        row = get_account(conn, account_id)
        return AccountResponse(id=row[0], name=row[1], type=row[2], institution=row[3], document_id=row[4], created_at=row[5])


@app.delete("/accounts/{account_id}", status_code=204)
def delete_account_route(request: Request, account_id: str):
    with sqlite3.connect(request.app.state.db_path) as conn:
        if not get_account(conn, account_id):
            raise HTTPException(status_code=404, detail="Account not found")
        delete_account(conn, account_id)
        conn.commit()
    return None


@app.get("/positions", response_model=list[PositionResponse])
def list_positions_route(request: Request, account_id: str | None = None):
    with sqlite3.connect(request.app.state.db_path) as conn:
        rows = list_positions(conn, account_id)
        return [
            PositionResponse(id=r[0], account_id=r[1], asset_type=r[2], description=r[3], principal=r[4], rate_apr=r[5], maturity_date=r[6], document_id=r[7], created_at=r[8], updated_at=r[9])
            for r in rows
        ]


@app.post("/positions", response_model=PositionResponse)
def create_position(request: Request, body: PositionCreate):
    import uuid
    pos_id = str(uuid.uuid4())
    now = int(time.time())
    with sqlite3.connect(request.app.state.db_path) as conn:
        if not get_account(conn, body.account_id):
            raise HTTPException(status_code=400, detail="Account not found")
        insert_position(conn, pos_id, body.account_id, body.asset_type, now, now, body.description, body.principal, body.rate_apr, body.maturity_date, body.document_id)
        conn.commit()
    return PositionResponse(id=pos_id, account_id=body.account_id, asset_type=body.asset_type, description=body.description, principal=body.principal, rate_apr=body.rate_apr, maturity_date=body.maturity_date, document_id=body.document_id, created_at=now, updated_at=now)


@app.get("/positions/{position_id}", response_model=PositionResponse)
def get_position_route(request: Request, position_id: str):
    with sqlite3.connect(request.app.state.db_path) as conn:
        row = get_position(conn, position_id)
        if not row:
            raise HTTPException(status_code=404, detail="Position not found")
        return PositionResponse(id=row[0], account_id=row[1], asset_type=row[2], description=row[3], principal=row[4], rate_apr=row[5], maturity_date=row[6], document_id=row[7], created_at=row[8], updated_at=row[9])


@app.patch("/positions/{position_id}", response_model=PositionResponse)
def patch_position(request: Request, position_id: str, body: PositionUpdate):
    now = int(time.time())
    with sqlite3.connect(request.app.state.db_path) as conn:
        row = get_position(conn, position_id)
        if not row:
            raise HTTPException(status_code=404, detail="Position not found")
        update_position(conn, position_id, now, body.description, body.principal, body.rate_apr, body.maturity_date, body.document_id)
        conn.commit()
        row = get_position(conn, position_id)
        return PositionResponse(id=row[0], account_id=row[1], asset_type=row[2], description=row[3], principal=row[4], rate_apr=row[5], maturity_date=row[6], document_id=row[7], created_at=row[8], updated_at=row[9])


@app.delete("/positions/{position_id}", status_code=204)
def delete_position_route(request: Request, position_id: str):
    with sqlite3.connect(request.app.state.db_path) as conn:
        if not get_position(conn, position_id):
            raise HTTPException(status_code=404, detail="Position not found")
        delete_position(conn, position_id)
        conn.commit()
    return None


@app.get("/obligations", response_model=list[ObligationResponse])
def list_obligations_route(request: Request):
    with sqlite3.connect(request.app.state.db_path) as conn:
        rows = list_obligations(conn)
        return [
            ObligationResponse(id=r[0], description=r[1], due_date=r[2], amount_estimate=r[3], priority=r[4], document_id=r[5], created_at=r[6])
            for r in rows
        ]


@app.post("/obligations", response_model=ObligationResponse)
def create_obligation(request: Request, body: ObligationCreate):
    import uuid
    obl_id = str(uuid.uuid4())
    now = int(time.time())
    with sqlite3.connect(request.app.state.db_path) as conn:
        insert_obligation(conn, obl_id, body.description, body.due_date, now, body.amount_estimate, body.priority, body.document_id)
        conn.commit()
    return ObligationResponse(id=obl_id, description=body.description, due_date=body.due_date, amount_estimate=body.amount_estimate, priority=body.priority, document_id=body.document_id, created_at=now)


@app.get("/obligations/{obligation_id}", response_model=ObligationResponse)
def get_obligation_route(request: Request, obligation_id: str):
    with sqlite3.connect(request.app.state.db_path) as conn:
        row = get_obligation(conn, obligation_id)
        if not row:
            raise HTTPException(status_code=404, detail="Obligation not found")
        return ObligationResponse(id=row[0], description=row[1], due_date=row[2], amount_estimate=row[3], priority=row[4], document_id=row[5], created_at=row[6])


@app.patch("/obligations/{obligation_id}", response_model=ObligationResponse)
def patch_obligation(request: Request, obligation_id: str, body: ObligationUpdate):
    with sqlite3.connect(request.app.state.db_path) as conn:
        row = get_obligation(conn, obligation_id)
        if not row:
            raise HTTPException(status_code=404, detail="Obligation not found")
        update_obligation(conn, obligation_id, body.description, body.due_date, body.amount_estimate, body.priority, body.document_id)
        conn.commit()
        row = get_obligation(conn, obligation_id)
        return ObligationResponse(id=row[0], description=row[1], due_date=row[2], amount_estimate=row[3], priority=row[4], document_id=row[5], created_at=row[6])


@app.delete("/obligations/{obligation_id}", status_code=204)
def delete_obligation_route(request: Request, obligation_id: str):
    with sqlite3.connect(request.app.state.db_path) as conn:
        if not get_obligation(conn, obligation_id):
            raise HTTPException(status_code=404, detail="Obligation not found")
        delete_obligation(conn, obligation_id)
        conn.commit()
    return None


@app.get("/health")
def health():
    return {"healthy": True}


@app.exception_handler(LLMTimeoutError)
async def llm_timeout_handler(request: Request, exc: LLMTimeoutError):
    _remote_log_error(request, "LLM request timed out", "LLMTimeoutError")
    return JSONResponse(
        status_code=504,
        content={"detail": "LLM request timed out"},
    )


@app.exception_handler(LLMUpstreamTimeoutError)
async def llm_upstream_timeout_handler(request: Request, exc: LLMUpstreamTimeoutError):
    _remote_log_error(request, "LLM upstream timed out", "LLMUpstreamTimeoutError")
    return JSONResponse(
        status_code=504,
        content={"detail": "LLM request timed out"},
    )


@app.exception_handler(LLMServiceError)
async def llm_service_error_handler(request: Request, exc: LLMServiceError):
    _remote_log_error(request, "LLM service unavailable", "LLMServiceError")
    return JSONResponse(
        status_code=503,
        content={"detail": "LLM service unavailable"},
    )


@app.exception_handler(LLMRateLimitedError)
async def llm_rate_limit_handler(request: Request, exc: LLMRateLimitedError):
    _remote_log_error(request, "LLM rate limit", "LLMRateLimitedError")
    return JSONResponse(
        status_code=429,
        content={"detail": "LLM rate limit issue."},
    )


@app.exception_handler(Exception)
async def catch_all_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException) and exc.status_code < 500:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    _remote_log_error(
        request,
        f"{type(exc).__name__}: {str(exc)[:500]}",
        type(exc).__name__,
    )
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
        logger.warning("Ollama connection failed: %s", exc)
    elif isinstance(exc, LLMServiceError) and "connection failed" in str(exc).lower():
        logger.warning("Ollama connection failed: %s", exc)
    else:
        logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


def _google_flow():
    """Build OAuth flow for Drive read-only (state will be set per-request)."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")
    from google_auth_oauthlib.flow import Flow

    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
        redirect_uri=GOOGLE_REDIRECT_URI,
    )


@app.get("/auth/google")
async def auth_google(request: Request):
    """
    Start one-time OAuth: redirect to Google consent (Drive read-only).
    After approval, user is sent to /auth/google/callback.
    """
    try:
        flow = _google_flow()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="false",
    )
    response = RedirectResponse(url=auth_url, status_code=302)
    response.set_cookie(key="oauth_state", value=state, max_age=600, httponly=True)
    return response


@app.get("/auth/google/callback", response_class=HTMLResponse)
async def auth_google_callback(request: Request):
    """
    OAuth callback: exchange code for tokens, show refresh token to set in .env.
    """
    state_cookie = request.cookies.get("oauth_state")
    state_query = request.query_params.get("state")
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code in callback")
    if not state_cookie or state_cookie != state_query:
        raise HTTPException(status_code=400, detail="Invalid or missing state")
    try:
        flow = _google_flow()
        flow._state = state_query
        flow.fetch_token(authorization_response=str(request.url))
    except Exception as e:
        logger.exception("OAuth fetch_token failed: %s", e)
        raise HTTPException(status_code=503, detail="Token exchange failed") from e
    refresh_token = flow.credentials.refresh_token
    if not refresh_token:
        raise HTTPException(
            status_code=503,
            detail="No refresh token; try revoking app access and re-authorizing with prompt=consent",
        )
    response = HTMLResponse(
        content=f"""
        <html><body style="font-family: sans-serif; padding: 2rem;">
        <h1>Google Drive auth complete</h1>
        <p>Add this to your <code>.env</code> (or set the env var):</p>
        <pre style="background: #eee; padding: 1rem; overflow-x: auto;">GOOGLE_REFRESH_TOKEN={refresh_token!r}</pre>
        <p>You already have <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code> set (required for this flow).</p>
        <p>Then restart the app and use <b>POST /ingest/google-drive</b> to sync.</p>
        </body></html>
        """
    )
    response.delete_cookie("oauth_state")
    return response


# Serve frontend (tabs + documents drawer); 
# mount last so API routes take precedence
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

