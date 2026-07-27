"""
Backfills per-language boilerplate for every non-stdio technical question in
the bank, so candidates get real LeetCode-style starter code on first load
instead of paying the generation latency (and risking a rate-limited LLM
failing silently mid-interview) the first time each (question, language)
pair is requested.

Idempotent and safe to re-run: every question/language pair already cached
in Supabase (harnesses/signatures columns) is skipped. Only fills gaps.

Usage:
    cd backend && .venv/Scripts/python scripts/seed_boilerplate.py [--limit N] [--languages java,cpp,python,node]

Requires the `signatures` column to exist on `questions` — apply
supabase/migrations/20260708_python_js_signatures.sql first (this script
will tell you and skip python/node if it's missing, rather than silently
losing that work every run).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from services import harness_generator, question_bank  # noqa: E402
from services.supabase_client import get_supabase  # noqa: E402

ALL_LANGUAGES = ["python", "node", "java", "cpp"]
CONCURRENCY = 4


def _is_stdio(q: dict) -> bool:
    tests = q.get("tests") or []
    return bool(tests and "stdin" in tests[0])


def _has_signatures_column(sb) -> bool:
    try:
        sb.table("questions").select("signatures").limit(1).execute()
        return True
    except Exception:
        return False


async def _fill_one(q: dict, lang: str, sem: asyncio.Semaphore) -> str:
    async with sem:
        try:
            if lang in ("python", "node"):
                result = await harness_generator.get_or_generate_signature(q, lang)
            else:
                result = await harness_generator.get_or_generate(q, lang)
            return "ok" if result else "unsupported"
        except Exception as exc:
            return f"error: {exc}"


async def main(limit: int | None, languages: list[str]) -> None:
    sb = get_supabase()
    if not sb:
        print("Supabase is not configured (check SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY).")
        return

    has_signatures = _has_signatures_column(sb)
    if not has_signatures and any(lang in ("python", "node") for lang in languages):
        print(
            "WARNING: 'signatures' column doesn't exist yet on `questions` — "
            "python/node signature generation will run but CANNOT persist, so "
            "it'll redo this work every time it's requested. Apply "
            "supabase/migrations/20260708_python_js_signatures.sql first.\n"
            "Skipping python/node for this run."
        )
        languages = [lang for lang in languages if lang not in ("python", "node")]

    all_questions = question_bank._all_questions()
    technical = [q for q in all_questions if q.get("track") == "technical" and not _is_stdio(q)]
    if limit:
        technical = technical[:limit]

    print(f"{len(technical)} non-stdio technical questions, languages: {languages}")

    sem = asyncio.Semaphore(CONCURRENCY)
    results = {"ok": 0, "unsupported": 0, "error": 0, "skipped": 0}

    for i, q in enumerate(technical, 1):
        tasks = []
        task_langs = []
        for lang in languages:
            cache_key = "signatures" if lang in ("python", "node") else "harnesses"
            cached = (q.get(cache_key) or {}).get(lang)
            if cached:
                results["skipped"] += 1
                continue
            # java/cpp: on-demand full harness generation when not natively listed.
            # node: on-demand signature-only generation (same function as the
            # native case) — previously this was skipped for any question that
            # didn't already list node, which is nearly all of them, so node
            # was never actually attempted in practice.
            if lang not in (q.get("languages") or []) and lang not in ("java", "cpp", "node"):
                continue
            if lang in ("java", "cpp") and lang in (q.get("languages") or []):
                continue  # native support already, no on-demand harness needed
            tasks.append(_fill_one(q, lang, sem))
            task_langs.append(lang)

        if not tasks:
            continue

        outcomes = await asyncio.gather(*tasks)
        for lang, outcome in zip(task_langs, outcomes):
            bucket = "ok" if outcome == "ok" else ("unsupported" if outcome == "unsupported" else "error")
            results[bucket] += 1
            status = outcome if bucket == "error" else outcome
            print(f"[{i}/{len(technical)}] {q['id']} | {lang} | {status}")

    print(f"\nDone. {results}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N questions")
    parser.add_argument("--languages", type=str, default=",".join(ALL_LANGUAGES))
    args = parser.parse_args()
    asyncio.run(main(args.limit, args.languages.split(",")))
