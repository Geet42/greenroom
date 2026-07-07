"""
In-process job store for async code execution results.

When a candidate clicks "Run code", the backend starts the Piston call in a
BackgroundTask and returns a job_id immediately. The frontend polls
GET /api/interview/code/job/{job_id} until the job is done.

The store is intentionally simple: jobs live in memory, expire after 10
minutes, and are cleaned up lazily on each write. This is sufficient because:
  - Jobs are short-lived (Piston responds in seconds)
  - The frontend stops polling once it gets a result
  - A replica restart is acceptable (frontend retries the full run)
"""

from __future__ import annotations

import time
import uuid
from threading import Lock

_TTL_SECONDS = 600  # 10 minutes
_jobs: dict[str, dict] = {}
_lock = Lock()


def create_job() -> str:
    """Reserve a slot and return a new job_id."""
    job_id = str(uuid.uuid4())
    with _lock:
        _prune()
        _jobs[job_id] = {"status": "pending", "result": None, "created_at": time.monotonic()}
    return job_id


def set_result(job_id: str, result: dict) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = result


def set_error(job_id: str, message: str) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["result"] = {
                "run": {"stdout": "", "stderr": message, "code": -1}
            }


def get_job(job_id: str) -> dict | None:
    with _lock:
        return _jobs.get(job_id)


def _prune() -> None:
    """Remove jobs older than TTL. Must be called with _lock held."""
    cutoff = time.monotonic() - _TTL_SECONDS
    stale = [jid for jid, j in _jobs.items() if j["created_at"] < cutoff]
    for jid in stale:
        del _jobs[jid]
