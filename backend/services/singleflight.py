"""
Per-key locks so concurrent callers generating the SAME thing (e.g. two
"Run Tests" clicks, or two open tabs, before a harness/test-case cache is
populated) coalesce into one LLM call instead of each paying for their own —
the existing caches in test_runner/harness_generator/adhoc_harness only
prevent repeat cost on a CACHE HIT; without this, two concurrent misses for
the same key both still hit the LLM.

Use with double-checked locking:
    if key in cache:
        return cache[key]
    with locks.get(key):          # or `async with` for the async variant
        if key not in cache:      # someone else may have finished while we waited
            cache[key] = generate(key)
        return cache[key]
"""

from __future__ import annotations

import asyncio
import threading
from typing import Hashable


class KeyedLocks:
    """Thread-safe per-key threading.Lock — for sync code (run_in_threadpool)."""

    def __init__(self):
        self._locks: dict[Hashable, threading.Lock] = {}
        self._guard = threading.Lock()

    def get(self, key: Hashable) -> threading.Lock:
        with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._locks[key] = lock
            return lock


class AsyncKeyedLocks:
    """Per-key asyncio.Lock — for async code awaited directly on the event loop."""

    def __init__(self):
        self._locks: dict[Hashable, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def get(self, key: Hashable) -> asyncio.Lock:
        async with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock
