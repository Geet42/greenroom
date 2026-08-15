"""
Run once (or any time you want to reset Supabase's `questions` table back to
the bundled seed) to push backend/data/question_bank.json into Supabase:

    cd backend && .venv/Scripts/python scripts/seed_questions.py

After this, the question bank lives in Supabase and can be edited there
directly (add/edit/remove rows) without touching code or redeploying.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from services.supabase_client import get_supabase  # noqa: E402


def main():
    sb = get_supabase()
    if not sb:
        print("Supabase is not configured (check SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY).")
        return

    seed_path = os.path.join(os.path.dirname(__file__), "..", "data", "question_bank.json")
    with open(seed_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    for q in questions:
        row = {
            "id": q["id"],
            "track": q["track"],
            "topic": q.get("topic"),
            "difficulty": q.get("difficulty"),
            "title": q["title"],
            "prompt": q["prompt"],
            "function_name": q.get("function_name"),
            "languages": q["languages"],
            "tests": q["tests"],
            "constraints": q.get("constraints"),
            "examples": q.get("examples"),
            "scale_metadata": q.get("scale_metadata"),
            # Previously omitted — re-running this script silently nulled these
            # out for every behavioral/system-design row in Supabase, since
            # Supabase upsert sends exactly the given payload (missing keys
            # aren't "leave unchanged"). Found by audit_question_bank.py.
            "expected_elements": q.get("expected_elements"),
            "expected_components": q.get("expected_components"),
            "visible_count": q.get("visible_count"),
            "functional_requirements": q.get("functional_requirements"),
            "non_functional_requirements": q.get("non_functional_requirements"),
            "scaling_constraints": q.get("scaling_constraints"),
            "out_of_scope": q.get("out_of_scope"),
            #
            # harnesses/signatures: intentionally NEVER forwarded — those are
            # derived, sandbox-verified caches that only ever exist in
            # Supabase (never in this JSON seed, which has 0/357 populated).
            # Forwarding a field this seed never populates is a no-op today,
            # but it's a footgun if the seed is ever hand-edited or partially
            # stale: it would silently overwrite live-verified harnesses with
            # garbage. This script's job is resetting authored content, not
            # round-tripping generated artifacts.
        }
        sb.table("questions").upsert(row).execute()
        print(f"  upserted {q['id']}")

    print(f"Done — {len(questions)} questions seeded into Supabase.")


if __name__ == "__main__":
    main()
