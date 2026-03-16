# job_store.py
# In-memory job store with async-safe concurrent access

import asyncio
from app.jobs import Job, JobStatus
import uuid
from datetime import datetime, timezone

class JobStore:
    """
    In-memory job store. Safe for concurrent access via asyncio.Lock.
    Idempotency: each submission creates a new job (no duplicate text detection).
    """

    ### to do
    # Implement create_job(text) -> Job: generate unique id (e.g. uuid), create Job with PENDING,
    # store in dict, return it.
    # Implement get_job(job_id) -> Job | None: lookup in dict.
    # Implement update_job(job): update dict entry, refresh updated_at.  ** this requires 
    # Implement list_pending() -> list[Job]: return jobs where status is PENDING, sorted by created_at.
    # Use asyncio.Lock around dict access so it's safe for concurrent requests.

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, text: str) -> Job:
        """Create a new job with unique ID. Each submission gets a new job_id."""
        job_id = uuid.uuid4().hex
        newjob = Job(
            id=job_id,
            text=text,
            status=JobStatus.PENDING,
            )
        async with self._lock:
            if job_id in self._jobs:
                #it's a duplicate
                raise ValueError(f"Duplicate id: {job_id}")
            self._jobs[job_id] = newjob
        return newjob


    async def get_job(self, job_id) -> Job:
        current_job = self._jobs.get(job_id)
        return current_job

    async def update_job(self, job: Job) -> Job | None:
        job.updated_at = datetime.now(timezone.utc)
        async with self._lock:
            if job.id in self._jobs:
                self._jobs[job.id] = job
                return job
            else: 
                return None

        
    async def list_pending(self) -> list[Job]:
        """Return jobs with status PENDING, ordered by created_at."""
        async with self._lock:
            pending = [j for j in self._jobs.values() if j.status == JobStatus.PENDING]
        return sorted(pending, key= lambda j: j.created_at)