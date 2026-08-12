"""Unit tests for services.singleflight — the per-key lock utility used by
test_runner/adhoc_harness/harness_generator to stop concurrent cache misses
for the SAME key from each independently paying for an LLM call."""
import asyncio
import threading
import time

import pytest

from services.singleflight import AsyncKeyedLocks, KeyedLocks


def test_keyed_locks_dedupes_concurrent_generation_for_same_key():
    locks = KeyedLocks()
    cache: dict[str, int] = {}
    call_count = {"n": 0}

    def get_or_generate(key: str) -> int:
        if key in cache:
            return cache[key]
        with locks.get(key):
            if key in cache:
                return cache[key]
            call_count["n"] += 1
            time.sleep(0.05)  # simulate a slow LLM call — widens the race window
            cache[key] = call_count["n"]
            return cache[key]

    results = []
    results_lock = threading.Lock()

    def worker():
        result = get_or_generate("same-key")
        with results_lock:
            results.append(result)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All 5 concurrent callers for the SAME key got the one generated value,
    # and generation only happened once — this is the actual cost saving:
    # without the lock, several of these would have raced past the "if key
    # in cache" check and each triggered their own (expensive) generation.
    assert call_count["n"] == 1
    assert results == [1] * 5


def test_keyed_locks_different_keys_do_not_block_each_other():
    locks = KeyedLocks()
    order = []

    def hold(key: str, hold_seconds: float):
        with locks.get(key):
            order.append(f"start-{key}")
            time.sleep(hold_seconds)
            order.append(f"end-{key}")

    t1 = threading.Thread(target=hold, args=("a", 0.1))
    t2 = threading.Thread(target=hold, args=("b", 0.01))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # "b" (different key, shorter hold) should finish well before "a" —
    # proving the two locks don't serialize against each other.
    assert order.index("end-b") < order.index("end-a")


def test_keyed_locks_same_instance_returns_same_lock_object():
    locks = KeyedLocks()
    assert locks.get("k") is locks.get("k")


@pytest.mark.asyncio
async def test_async_keyed_locks_dedupes_concurrent_generation():
    locks = AsyncKeyedLocks()
    cache: dict[str, int] = {}
    call_count = {"n": 0}

    async def get_or_generate(key: str) -> int:
        if key in cache:
            return cache[key]
        async with await locks.get(key):
            if key in cache:
                return cache[key]
            call_count["n"] += 1
            await asyncio.sleep(0.05)
            cache[key] = call_count["n"]
            return cache[key]

    results = await asyncio.gather(
        get_or_generate("same-key"),
        get_or_generate("same-key"),
        get_or_generate("same-key"),
    )

    assert call_count["n"] == 1
    assert results == [1, 1, 1]


@pytest.mark.asyncio
async def test_async_keyed_locks_same_instance_returns_same_lock_object():
    locks = AsyncKeyedLocks()
    a = await locks.get("k")
    b = await locks.get("k")
    assert a is b
