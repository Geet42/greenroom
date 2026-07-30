"""
Backfills the `overall_score`/`summary`/evaluations for completed sessions
that were left with a null score.

Root cause (see docs/EVALUATION_METRICS.md, 2026-07-29 and the llm.py fix
alongside this script): two overlapping bugs.
  1. Sessions with zero candidate messages predate the has_candidate_answer
     guard added to routers/interview.py in commit a41ac59 (2026-07-27) — they
     hit the LLM eval path with an empty transcript and got back malformed
     JSON that was never validated.
  2. Sessions WITH real candidate answers still got a null score because
     JsonOutputParser(pydantic_object=EvaluationResult) only uses the schema
     for prompt formatting, not enforcement — a response missing
     overall_score passed straight through. Now fixed in llm.py via
     _validate_eval_result().

This script re-evaluates every affected session from its real, saved
transcript (never fabricates one) using the now-fixed evaluate_session(), and
persists the result the same way routers/interview.py's end_session does.
Nothing is invented: a session with genuinely zero candidate messages gets
the same explicit "no answers recorded" 0-score result the live endpoint
would give it today; a session with real answers gets a real LLM evaluation
run against that real transcript.

Usage: python scripts/backfill_missing_evaluations.py [--dry-run]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from services import llm
from services.supabase_client import get_supabase


def _persist(sb, session_id: str, result: dict) -> None:
    star = result.get("star_analysis")
    sb.table("sessions").update({
        "status": "completed",
        "overall_score": result.get("overall_score"),
        "summary": result.get("summary"),
        "star_analysis": star if star else None,
    }).eq("id", session_id).execute()
    # Clear any partial evaluation rows from the original failed attempt
    # before inserting the fresh ones, so categories are never duplicated.
    sb.table("evaluations").delete().eq("session_id", session_id).execute()
    for category in result.get("evaluations", []):
        sb.table("evaluations").insert({
            "session_id": session_id,
            "category": category.get("category"),
            "score": category.get("score"),
            "feedback": category.get("feedback"),
        }).execute()


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    sb = get_supabase()
    if not sb:
        print("Supabase not configured (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing).")
        return

    sessions = sb.table("sessions") \
        .select("id,track,role,status,overall_score") \
        .eq("status", "completed") \
        .is_("overall_score", "null") \
        .execute().data

    print(f"Found {len(sessions)} completed sessions with a null overall_score.\n")

    no_answer, evaluated, failed = 0, 0, 0

    for s in sessions:
        session_id = s["id"]
        track = s["track"]
        role = s.get("role") or "General"

        msgs = sb.table("messages").select("role,content,sequence_no") \
            .eq("session_id", session_id).order("sequence_no").execute().data
        history = [{"role": m["role"], "content": m["content"]} for m in msgs]

        has_candidate_answer = any(t["role"] == "candidate" for t in history)

        if not has_candidate_answer:
            result = {
                "overall_score": 0,
                "summary": "No answers were recorded in this session. Start a new session and answer at least one question to receive a score.",
                "star_analysis": None,
                "evaluations": [],
            }
            no_answer += 1
            print(f"[no-answer] {session_id} ({track}) -> score 0")
        else:
            try:
                result = llm.evaluate_session(track, role, history)
                print(f"[evaluated] {session_id} ({track}) -> score {result.get('overall_score')}")
                evaluated += 1
            except Exception as exc:
                print(f"[FAILED]    {session_id} ({track}) -> {exc}")
                failed += 1
                continue

        if not dry_run:
            _persist(sb, session_id, result)

    print(f"\nno-answer: {no_answer}  evaluated: {evaluated}  failed: {failed}")
    if dry_run:
        print("(dry run — nothing was written)")


if __name__ == "__main__":
    main()
