# rate_limit.py
# Token bucket rate limiter - async-safe, in-memory

### to do (if implementing from scratch)
# Implement TokenBucket: X tokens per Y seconds, refill over time.
# acquire() consumes one token; if none available, raise RateLimitedError.
# Use asyncio.Lock so it's safe for concurrent workers.
# Goal: throttle LLM calls so you don't exceed upstream limits.

from app.config import LLM_RATE_LIMIT_SECONDS, LLM_TOKEN_LIMIT
from app.errors import LLMRateLimitedError
import time
import asyncio

class TokenBucket:
    """
    Token bucket: X tokens per Y seconds.
    Async-safe via asyncio.Lock.
    """

    def __init__(
        self,
        tokens: int = LLM_TOKEN_LIMIT,
        refill_seconds: int = LLM_RATE_LIMIT_SECONDS
        ) -> None:
        self._tokens = float(tokens)        # current tokens in bucket. this will fluctuate
        self._max_tokens = float(tokens)    # this gets set and doesn't change 
        self._refill_rate = tokens / refill_seconds
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()         #create a Lock instance
        


    async def acquire(self) -> None:
        """Consume one token. Raises RateLimitedError if no tokens available."""
        async with self._lock:              # uses lock object as an async context manager
            # get amount of time elapsed
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self._max_tokens, 
                self._tokens + elapsed * self._refill_rate
            )
            self._last_refill = now
            if self._tokens < 1:    
                raise LLMRateLimitedError("No tokens available")
            self._tokens -= 1


                