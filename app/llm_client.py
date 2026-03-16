# llm_client.py
# has an async answer with context function
#
# OpenAI path: answer_openai() is called only with server-built, non-PII prompts
# (e.g. "what should someone do with $X in a CD?"). Never send user names,
# institution names, doc/chunk content, or raw user questions to OpenAI.

'''**Hint:** Reuse your ai-document LLM client or a minimal async caller; 
point it at **Ollama** (e.g. `http://localhost:11434`) and use 
**Llama 3.1 8B** (`llama3.1:8b`) so all generation stays local for 
client-name privacy. Keep the prompt template in one place so you can 
tune it later for “overview and detailed image verbiage.” Next phase: **LLaVA** 
(Ollama) for “look at this job’s images and write report text.”'''

import json
import random
import asyncio
from typing import AsyncIterator

import httpx

from app.config import (
    LLM_BASE_URL,
    LLAVA_MODEL,
    LLM_MAX_ATTEMPTS,
    LLM_MODEL,
    LLM_TIMEOUT_SECONDS,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MAX_ATTEMPTS,
    OPENAI_MODEL,
    OPENAI_TIMEOUT_SECONDS,
)
from app.errors import (
    LLMRateLimitedError,
    LLMServiceError,
    LLMUpstreamTimeoutError,
)



async def answer_with_context(prompt: str)->str:
    """Call OpenAI chat completions with the RAG prompt; return the assistant reply."""
    
    last_exc: BaseException | None = None
    for attempt in range(LLM_MAX_ATTEMPTS):
    
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    url = f"{LLM_BASE_URL.rstrip('/')}/api/chat",
                    json={
                        "model": LLM_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False
                    },
                )
            if resp.status_code == 429:
                raise LLMRateLimitedError("LLM rate limited")
            if resp.status_code >= 400:
                raise LLMServiceError(f"LLM API error {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            
            text = data.get("message", {}).get("content", "").strip()

            return text

        except LLMServiceError:
            raise
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise LLMServiceError(f"Ollama (LLM) connection failed: {e}") from e
        except httpx.TimeoutException as e:
            # last_exc = LLMUpstreamTimeoutError("Embedding request timed out") from e      # this version of python didn't like this exception chaining. We will figure that out later.
            last_exc = LLMUpstreamTimeoutError("Embedding request timed out")
            if attempt < LLM_MAX_ATTEMPTS - 1:
                delay = 1.0 * (2**attempt)
                jitter = random.uniform(0, delay * 0.5)
                await asyncio.sleep(delay + jitter)
            else:
                raise last_exc
            continue
        except (LLMRateLimitedError, LLMUpstreamTimeoutError) as e:
            last_exc = e
            if attempt < LLM_MAX_ATTEMPTS - 1:
                delay = 1.0 * (2**attempt)
                jitter = random.uniform(0, delay * 0.5)
                await asyncio.sleep(delay + jitter)
            else:
                raise
            continue



    else:
        if last_exc:
            raise last_exc
        raise RuntimeError("Embedding retries exhausted attempting to reach llm client")


# Timeout for streaming (generation can take minutes)
LLM_STREAM_TIMEOUT_SECONDS = 300


async def answer_with_context_stream(prompt: str) -> AsyncIterator[str]:
    """Call Ollama /api/chat with stream=True; yield content deltas as they arrive."""
    url = f"{LLM_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    last_exc: BaseException | None = None
    for attempt in range(LLM_MAX_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=LLM_STREAM_TIMEOUT_SECONDS) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    if resp.status_code == 429:
                        raise LLMRateLimitedError("LLM rate limited")
                    if resp.status_code >= 400:
                        body = await resp.aread()
                        raise LLMServiceError(
                            f"LLM API error {resp.status_code}: {body[:200]!r}"
                        )
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        content = data.get("message", {}).get("content") or data.get("response")
                        if content:
                            yield content
                        if data.get("done"):
                            return
        except (LLMServiceError, LLMRateLimitedError):
            raise
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise LLMServiceError(f"Ollama (LLM) connection failed: {e}") from e
        except httpx.TimeoutException:
            last_exc = LLMUpstreamTimeoutError("LLM stream timed out")
            if attempt < LLM_MAX_ATTEMPTS - 1:
                delay = 1.0 * (2**attempt)
                jitter = random.uniform(0, delay * 0.5)
                await asyncio.sleep(delay + jitter)
            else:
                raise last_exc
            continue
        except LLMUpstreamTimeoutError as e:
            last_exc = e
            if attempt < LLM_MAX_ATTEMPTS - 1:
                delay = 1.0 * (2**attempt)
                jitter = random.uniform(0, delay * 0.5)
                await asyncio.sleep(delay + jitter)
            else:
                raise
            continue
    if last_exc:
        raise last_exc
    raise RuntimeError("LLM stream retries exhausted")


async def answer_with_image(image_base64: str, prompt: str) -> str:
    """
    Call Ollama vision API (LLaVA) with one image and a text prompt.
    Uses LLAVA_MODEL and LLM_BASE_URL. No RAG; image-only path.
    """
    last_exc: BaseException | None = None
    for attempt in range(LLM_MAX_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    url=f"{LLM_BASE_URL.rstrip('/')}/api/chat",
                    json={
                        "model": LLAVA_MODEL,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt or "Describe this image and summarize any financial details or terms.",
                                "images": [image_base64],
                            }
                        ],
                        "stream": False,
                    },
                )
            if resp.status_code == 429:
                raise LLMRateLimitedError("LLM rate limited")
            if resp.status_code >= 400:
                raise LLMServiceError(
                    f"LLM API error {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
            text = data.get("message", {}).get("content", "").strip()
            return text
        except (LLMServiceError, LLMRateLimitedError):
            raise
        except httpx.TimeoutException:
            last_exc = LLMUpstreamTimeoutError("Vision request timed out")
            if attempt < LLM_MAX_ATTEMPTS - 1:
                delay = 1.0 * (2**attempt)
                jitter = random.uniform(0, delay * 0.5)
                await asyncio.sleep(delay + jitter)
            else:
                raise last_exc
            continue
    if last_exc:
        raise last_exc
    raise RuntimeError("Vision retries exhausted")


# Prompt for extracting text from bank/financial screenshots for RAG ingestion.
INGEST_IMAGE_EXTRACTION_PROMPT = (
    "This image is a financial or bank website screenshot. "
    "Extract and transcribe ALL visible text exactly as shown: numbers, labels, headings, "
    "table cells, account names, balances, dates, and any UI text. "
    "Preserve structure where possible (e.g. line breaks for separate lines). "
    "Output only the extracted text, with no extra commentary."
)


async def image_to_text_for_ingest(image_base64: str) -> str:
    """
    Call Ollama vision API (LLaVA) to extract all visible text from an image
    for RAG ingestion. Uses a fixed extraction prompt tuned for financial/bank
    screenshots. Same retry/timeout as answer_with_image.
    """
    return await answer_with_image(
        image_base64,
        INGEST_IMAGE_EXTRACTION_PROMPT,
    )


async def answer_openai(prompt: str) -> str | None:
    """
    Call OpenAI Chat Completions with a server-built prompt. Returns None if
    OPENAI_API_KEY is not set. Used only for non-PII prompts (e.g. CD advice
    with amount/term/rate only). Never send user names, doc content, or raw
    user questions here.
    """
    if not OPENAI_API_KEY:
        return None
    last_exc: BaseException | None = None
    for attempt in range(OPENAI_MAX_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=OPENAI_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    url=f"{OPENAI_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": OPENAI_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                )
            if resp.status_code == 429:
                raise LLMRateLimitedError("OpenAI rate limited")
            if resp.status_code >= 400:
                raise LLMServiceError(
                    f"OpenAI API error {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return (content or "").strip()
        except (LLMServiceError, LLMRateLimitedError):
            raise
        except httpx.TimeoutException:
            last_exc = LLMUpstreamTimeoutError("OpenAI request timed out")
            if attempt < OPENAI_MAX_ATTEMPTS - 1:
                delay = 1.0 * (2**attempt)
                jitter = random.uniform(0, delay * 0.5)
                await asyncio.sleep(delay + jitter)
            else:
                raise last_exc
            continue
    if last_exc:
        raise last_exc
    raise RuntimeError("OpenAI retries exhausted")

