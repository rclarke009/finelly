# jobs.py
# Job model and JobStatus enum for Phase 2 background job system

### to do
# Define JobStatus enum with: PENDING, RUNNING, SUCCESS, FAILED.
# Define Job dataclass with: id, text, status, result, error, attempts, created_at, updated_at.
# This is the core data shape for the job queue.

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

class JobStatus(str,Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

@dataclass
class Job:
    id: str
    text: str
    status: JobStatus = JobStatus.PENDING 
    result: str | None = None 
    error: str | None = None
    attempts: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))






# without dataclass decorator from module
# class Job:
#     def __init__(self, id: str, text: str, status: str = "pending"):
#         self.id = id
#         self.text = text
#         self.status = status
    
#     def __eq__(self, other):
#         if not isinstance(other, Job):
#             return NotImplemented
#         return (self.id, self.text, self.status) == (other.id, other.text, other.status)
#     # ... __repr__, etc.
