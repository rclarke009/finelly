# worker.py
# Background worker loop for processing do_answer jobs

### to do (if implementing from scratch)
# Implement worker_loop(job_store, rate_limiter): infinite loop that:
# 1) Fetches pending jobs
# 2) For each job: mark RUNNING, call rate_limiter.acquire(), call LLM via with_retry,
#    set SUCCESS or FAILED
# 3) Sleep briefly (e.g. 0.5s) between iterations
# Wrap each job in try/except so one failure doesn't stop the worker.
# Goal: process jobs in the background instead of blocking the API.

### to do - set up
import asyncio
import logging

from app.job_store import JobStore
from app.rate_limit import TokenBucket
from app.jobs import Job, JobStatus
from app import llm_client
from app.config import LLM_TIMEOUT_SECONDS, LLM_MAX_ATTEMPTS
from app.errors import LLMUpstreamTimeoutError, LLMRateLimitedError
from app.retry import with_retry

logger = logging.getLogger(__name__)


### to do -  create function to process job
async def _process_job(
    job_store: JobStore,
    rate_limiter: TokenBucket,
    job: Job
) -> None:
    """Process a single job: rate limit, call LLM, update status."""

    async def _do_answer() -> str:
         
        while True:
            try:
                await rate_limiter.acquire()
                break
            except LLMRateLimitedError:
                await asyncio.sleep(1)  # wait then retry

            
        try:
            return await asyncio.wait_for(
                llm_client.answer_with_context(job.text),
                timeout=LLM_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as e:
            raise LLMUpstreamTimeoutError("LLM call timed out") from e

        
    try:
        result = await with_retry(
            _do_answer,
            job,
            max_attempts=LLM_MAX_ATTEMPTS,
        )
        job.status = JobStatus.SUCCESS
        job.result = result
    except (LLMUpstreamTimeoutError, Exception) as e:
        job.status = JobStatus.FAILED
        logger.error("Job %s failed after %d attempts: %s", job.id, job.attempts )
    await job_store.update_job(job)



### to do - create function worker loop to fetch pending jobs and process 
async def worker_loop(
    job_store: JobStore,
    rate_limiter: TokenBucket,
) -> None:
    """
    Background worker: fetch pending jobs, process one at a time.
    Does not crash on single job failure.
    """
    while True:
        try:
            pending = await job_store.list_pending()
            for job in pending[:1]:
                try:
                    job.status = JobStatus.RUNNING
                    await job_store.update_job(job)
                    await _process_job(job_store, rate_limiter, job)
                except Exception as e:
                    logger.error ("Unexpected error processing job %s: %s", job.id, e )
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    await job_store.update_job(job)
        except Exception as e:
            logger.error("Worker loop error: %s", e)
        await asyncio.sleep(0.5)



 