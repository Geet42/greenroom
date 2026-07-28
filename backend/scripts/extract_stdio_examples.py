"""
Extracts "examples" for the CodeContests-imported (`cc-` prefixed) stdio-style
questions, which the LeetCode-oriented extract_constraints_examples.py
deliberately skips (its prompt assumes function-call-style examples, not
stdin/stdout blocks). These 77 questions already have constraints (imported
alongside the problem) but never had structured examples extracted — their
prompt text already states sample input/output (standard for competitive
programming problems), this just pulls it into the same {input, output,
explanation} shape the frontend already renders for every other question.

Reads/writes Supabase directly (these questions were imported straight into
Supabase via scripts/import_codecontests.py, not through the local JSON seed
reseed path), and is idempotent — skips any row that already has examples.

Usage:
    cd backend && .venv/Scripts/python scripts/extract_stdio_examples.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

from services.llm import _fallback_chat, _make_llm  # noqa: E402
from services.supabase_client import get_supabase  # noqa: E402

_SYSTEM = """\
You extract a structured "examples" field from a competitive-programming problem's prompt text. \
The prompt already states its own sample input/output (standard for this style of problem) — you \
are reformatting what's already there, not inventing new examples or behavior.

Reply with ONLY a JSON object, no markdown fences, no explanation, in this exact shape:
{
  "examples": [
    {"input": "<the sample input exactly as given, raw stdin text, preserve newlines as \\n>",
     "output": "<the corresponding sample output exactly as given, raw stdout text>",
     "explanation": "<short reason if the prompt gives one, else empty string>"}
  ]
}

Extract every sample input/output pair the prompt gives (usually 1-3). If the prompt gives no \
explicit sample I/O at all, return an empty list — do not invent one."""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _extract(prompt: str) -> list[dict] | None:
    user = f"Prompt:\n{prompt}"
    try:
        llm = _make_llm(temperature=0.1, max_tokens=1200)
        raw = _strip_fences(llm.invoke([SystemMessage(content=_SYSTEM), HumanMessage(content=user)]).content)
    except Exception:
        try:
            raw = _strip_fences(_fallback_chat(
                [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
                max_tokens=1200, temperature=0.1,
            ))
        except Exception as exc:
            print(f"    error: {exc}")
            return None
    try:
        data = json.loads(raw)
        examples = data.get("examples")
        return examples if isinstance(examples, list) else None
    except json.JSONDecodeError as exc:
        print(f"    parse error: {exc}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    sb = get_supabase()
    if not sb:
        print("Supabase is not configured.")
        return

    rows = sb.table("questions").select("id, prompt, examples").like("id", "cc-%").execute().data
    candidates = [r for r in rows if not r.get("examples")]
    if args.limit:
        candidates = candidates[: args.limit]

    print(f"Processing {len(candidates)} cc- questions missing examples...")
    done = 0
    for r in candidates:
        examples = _extract(r["prompt"])
        if examples:
            sb.table("questions").update({"examples": examples}).eq("id", r["id"]).execute()
            done += 1
            print(f"  OK: {r['id']} ({len(examples)} examples)")
        else:
            print(f"  SKIP: {r['id']}")

    print(f"\nDone: {done}/{len(candidates)} extracted.")


if __name__ == "__main__":
    main()
