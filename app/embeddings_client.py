# Part C — Embeddings (chunk → vector)
# Real embedding API (best, if you have it)
# Implement embeddings_client.py:
# async def embed_texts(texts: list[str]) -> list[list[float]]
# Use env vars:
# EMBED_BASE_URL
# EMBED_API_KEY
# EMBED_MODEL
# Add timeout, retries (reuse Phase 2 patterns)
# In-memory cache (TTLCache): same text + model → same vector; avoids duplicate Ollama calls.

import asyncio
import logging
import random

import httpx
from cachetools import TTLCache

from app.config import (
    EMBED_BASE_URL,
    EMBED_MAX_ATTEMPTS,
    EMBED_MODEL,
    EMBED_TIMEOUT,
)
from app.errors import (
    LLMRateLimitedError,
    LLMServiceError,
    LLMUpstreamTimeoutError,
)

logger = logging.getLogger(__name__)

# Per-text cache: key (model, text) → list[float]. TTL 1 hour; max 10k entries.
_EMBED_CACHE_TTL = 3600
_EMBED_CACHE_MAXSIZE = 10_000
_embed_cache: TTLCache[tuple[str, str], list[float]] = TTLCache(
    maxsize=_EMBED_CACHE_MAXSIZE,
    ttl=_EMBED_CACHE_TTL,
)
_embed_cache_lock = asyncio.Lock()


def _parse_embed_response(data: dict) -> list[list[float]]:
    """Parse Ollama embed response into list of vectors, same order as input."""
    if data.get("embeddings"):
        return data["embeddings"]
    if data.get("embedding") is not None:
        return [data["embedding"]]
    raise LLMServiceError("Unexpected embed response shape")


async def _call_embed_api(texts: list[str]) -> list[list[float]]:
    """
    Call Ollama embed API for the given texts. Retries on rate limit / timeout.
    Returns one vector per text, same order.
    """
    last_exc: BaseException | None = None
    for attempt in range(EMBED_MAX_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=EMBED_TIMEOUT) as client:
                response = await client.post(
                    f"{EMBED_BASE_URL}/api/embed",
                    headers={"Content-Type": "application/json"},
                    json={"model": EMBED_MODEL, "input": texts},
                )
            if response.status_code == 429:
                raise LLMRateLimitedError("Embedding API rate limited")
            if response.status_code >= 400:
                raise LLMServiceError(
                    f"Embedding API error {response.status_code}: {response.text[:200]}"
                )
            data = response.json()
            return _parse_embed_response(data)
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise LLMServiceError(f"Ollama (embed) connection failed: {e}") from e
        except httpx.TimeoutException:
            last_exc = LLMUpstreamTimeoutError("Embedding request timed out")
            if attempt < EMBED_MAX_ATTEMPTS - 1:
                delay = 1.0 * (2**attempt)
                jitter = random.uniform(0, delay * 0.5)
                await asyncio.sleep(delay + jitter)
            else:
                raise last_exc
            continue
        except (LLMRateLimitedError, LLMUpstreamTimeoutError) as e:
            last_exc = e
            if attempt < EMBED_MAX_ATTEMPTS - 1:
                delay = 1.0 * (2**attempt)
                jitter = random.uniform(0, delay * 0.5)
                await asyncio.sleep(delay + jitter)
            else:
                raise
            continue
        except LLMServiceError:
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("Embedding retries exhausted")


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts. Returns one vector per text, same order.
    Uses an in-memory TTLCache so identical (model, text) pairs skip the API.
    Only texts missing from the cache are sent to Ollama in one batched request.
    """
    if not texts:
        return []

    results: list[list[float] | None] = [None] * len(texts)
    need_fetch: list[tuple[int, str]] = []

    async with _embed_cache_lock:
        for i, text in enumerate(texts):
            key = (EMBED_MODEL, text)
            if key in _embed_cache:
                results[i] = _embed_cache[key]
            else:
                need_fetch.append((i, text))

    if not need_fetch:
        return list(results)

    texts_to_fetch = [t for _, t in need_fetch]
    vectors = await _call_embed_api(texts_to_fetch)

    async with _embed_cache_lock:
        for (idx, text), vec in zip(need_fetch, vectors):
            results[idx] = vec
            _embed_cache[(EMBED_MODEL, text)] = vec

    return list(results)



