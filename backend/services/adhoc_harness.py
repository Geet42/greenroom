"""Java/C++ test-case support for ad-hoc problems — ones the interviewer
invents live in conversation rather than assigns from the curated question
bank (services.question_bank). Reuses the exact generate -> compile-verify ->
corrective-retry machinery from services.harness_generator (which was built
for the curated bank), just keyed by problem text instead of a bank question
id.

Cached in-memory only, not persisted to Supabase: ad-hoc problems are unique
per interview (the interviewer invents them fresh each time), so unlike bank
questions there's no cross-candidate reuse value that would justify the
storage — the in-memory cache only exists to avoid re-generating on repeated
"Run Tests" clicks or language switches within the same problem/session.
"""

from __future__ import annotations

import hashlib
import re

from services import harness_generator, singleflight

_cache: dict[tuple, dict | str | None] = {}
_locks = singleflight.AsyncKeyedLocks()

# Matches the function/method being called at the start of a "call" literal:
# "canJump(nums=[2,3,1,1,4])" -> "canJump", or the constructor being invoked
# in a stateful chain: "obj = LRUCache(2); obj.put(1,1)" -> "LRUCache".
_PLAIN_CALL = re.compile(r"^\s*(\w+)\s*\(")
_STATEFUL_CALL = re.compile(r"=\s*(\w+)\s*\(")


def _infer_method_name(call: str) -> str | None:
    m = _PLAIN_CALL.match(call)
    if m:
        return m.group(1)
    m = _STATEFUL_CALL.search(call)
    return m.group(1) if m else None


def _key(prefix: str, language: str, problem: str, cases: list[dict]) -> tuple:
    digest = hashlib.sha256((problem + repr(cases)).encode()).hexdigest()
    return (prefix, language, digest)


async def get_or_generate(language: str, problem: str, cases: list[dict]) -> dict | None:
    """Returns {"boilerplate": ..., "harness": ...} for this ad-hoc
    (problem, language) pair, generating and sandbox-verifying it against an
    LLM-produced reference solution on first use — same reliability bar as
    the curated bank (services.harness_generator.get_or_generate). Returns
    None if every attempt fails; callers should treat that like "this
    language isn't supported for this problem", same as the curated path."""
    if language not in ("java", "cpp"):
        return None
    if not cases:
        return None
    method_name = _infer_method_name(cases[0]["call"])
    if not method_name:
        return None

    key = _key("harness", language, problem, cases)
    if key in _cache:
        return _cache[key]

    import asyncio
    # Coalesces concurrent misses for the same key (e.g. two "Run Tests"
    # clicks before the first generation finishes) into one LLM+sandbox
    # round trip instead of each caller paying for its own.
    async with await _locks.get(key):
        if key in _cache:
            return _cache[key]

        question = {"title": "", "prompt": problem, "tests": cases, "function_name": method_name}
        feedback = None
        result = None
        for _attempt in range(harness_generator._GENERATION_ATTEMPTS):
            spec = await asyncio.to_thread(harness_generator._generate, language, question, feedback)
            if not spec:
                feedback = None  # generation itself failed — nothing useful to correct
                continue
            ok, err = await harness_generator._verify(language, spec, len(cases))
            if not ok:
                feedback = err
                continue
            result = {"boilerplate": spec["boilerplate"], "harness": spec["harness"]}
            break

        _cache[key] = result
        return result


async def get_or_generate_signature(language: str, problem: str, cases: list[dict]) -> str | None:
    """Returns a compile-checked starter signature for the candidate's editor
    — the same boilerplate `get_or_generate` would produce, without paying
    for full harness generation+verification if all that's needed right now
    is to show the editor something typed instead of a blank stub."""
    if language not in ("java", "cpp"):
        return None
    if not cases:
        return None
    method_name = _infer_method_name(cases[0]["call"])
    if not method_name:
        return None

    key = _key("signature", language, problem, cases)
    if key in _cache:
        return _cache[key]

    import asyncio
    async with await _locks.get(key):
        if key in _cache:
            return _cache[key]

        question = {"title": "", "prompt": problem, "tests": cases}
        code = None
        for _attempt in range(harness_generator._GENERATION_ATTEMPTS):
            code = await asyncio.to_thread(harness_generator._generate_signature, language, method_name, question)
            if code:
                break

        _cache[key] = code
        return code
