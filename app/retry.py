# retry.py
# Custom async retry wrapper with exponential backoff and jitter

### to do (if implementing from scratch)
# Implement with_retry(coro_fn, job, max_attempts): call coro_fn, on RateLimitedError or
# UpstreamTimeoutError retry with exponential backoff (e.g. 1s, 2s, 4s) plus random jitter.
# Increment job.attempts on each retry. Re-raise after max_attempts.
# Goal: make transient failures (rate limit, timeout) succeed without crashing.


## to do set up
import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.jobs import Job
from app.errors import LLMRateLimitedError, LLMUpstreamTimeoutError


RETRYABLE_EXCEPTIONS = (LLMRateLimitedError, LLMUpstreamTimeoutError)

T = TypeVar("T")            #preserves type from what calls the wrapper


## to do - create coroutine
async def with_retry(
    coro_fn: Callable[[], Awaitable[T]], 
    job: Job, 
    max_attempts: int,
    base_delay: float = 1.0,
    on_attempt: Callable[[Job], None] | None = None,
    ) -> T:
    """
    Execute coroutine with retry on retryable exceptions.
    coro_fn is called each attempt (creates fresh coroutine).
    Uses exponential backoff + jitter.
    Increments job.attempts on each attempt.
    """
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            result = await coro_fn()
            return result
        except RETRYABLE_EXCEPTIONS as e:
            last_exc = e
            job.attempts = attempt + 1
            if on_attempt:
                on_attempt(job)
            if attempt < max_attempts - 1:
                delay = base_delay * (2**attempt)
                jitter = random.uniform(0, delay * 0.5)
                await asyncio.sleep(delay + jitter)
            else:
                raise
    raise last_exc or RuntimeError("Retry exhausted")