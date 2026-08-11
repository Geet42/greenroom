"""
Extracts structured "scale_metadata" tags from each system-design question's
existing `prompt`/`constraints` text — same idea as
scripts/extract_constraints_examples.py: the numbers (daily active users,
writes/reads per second, latency targets, storage estimates, etc.) already
exist in prose (e.g. "100M writes/day (~1,200/sec)" inside `constraints`),
this just pulls them into a separate structured field the frontend can
render as distinct tags instead of leaving them buried in a string array.

Low-risk by construction: extraction/reformatting of numbers already stated
in the problem's own text, not new claims about scale requirements — a
spot-check against a handful of known problems is enough, no sandboxed
verification needed (there's nothing computational to verify).

Usage:
    cd backend && .venv/Scripts/python scripts/backfill_scale_metadata.py [--limit N] [--dry-run]

After running, re-seed Supabase so the durable copy picks up the new field:
    cd backend && .venv/Scripts/python scripts/seed_questions.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

from services.llm import _fallback_chat, _make_llm  # noqa: E402

_BANK_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "question_bank.json")

_SYSTEM = """\
You extract structured scale/metadata tags from a system-design interview problem's prompt and \
constraints text. The numbers are already stated in that text — you are reformatting what's \
already there into short label/value tags, not inventing new requirements.

Reply with ONLY a JSON object, no markdown fences, no explanation, in this exact shape:
{
  "scale_metadata": [
    {"label": "<short label, e.g. 'Writes/day', 'Reads/sec', 'Latency (p99)', 'Storage'>",
     "value": "<the number/range as stated, e.g. '100M (~1,200/sec)', '< 100ms', '500 TB/year'>"}
  ]
}

Extract every distinct scale-relevant number the text gives (throughput, storage, latency, \
concurrency, data volume, retention, etc.) — typically 2-5 tags. If the text gives no concrete \
numbers at all, return an empty list — do not invent plausible-sounding ones."""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _extract(question: dict) -> list[dict] | None:
    constraints_preview = "\n".join(f"  - {c}" for c in (question.get("constraints") or []))
    user = f"Prompt:\n{question['prompt']}\n\nConstraints:\n{constraints_preview or '(none stated)'}"

    try:
        llm = _make_llm(temperature=0.1, max_tokens=500)
        result = llm.invoke([SystemMessage(content=_SYSTEM), HumanMessage(content=user)])
        raw = _strip_fences(result.content)
    except Exception:
        try:
            raw = _strip_fences(_fallback_chat(
                [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
                max_tokens=500, temperature=0.1,
            ))
        except Exception as exc:
            print(f"    error: {exc}")
            return None

    try:
        data = json.loads(raw)
        tags = data.get("scale_metadata")
        if isinstance(tags, list) and all(
            isinstance(t, dict) and "label" in t and "value" in t for t in tags
        ):
            return tags
    except json.JSONDecodeError as exc:
        print(f"    parse error: {exc}")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true", help="Print extracted tags without writing the seed file")
    args = ap.parse_args()

    with open(_BANK_PATH, "r", encoding="utf-8") as f:
        bank = json.load(f)

    candidates = [q for q in bank if q.get("track") == "system-design" and not q.get("scale_metadata")]
    if args.limit:
        candidates = candidates[: args.limit]

    print(f"Processing {len(candidates)} system-design questions...")
    done = 0
    for q in candidates:
        tags = _extract(q)
        if tags:
            q["scale_metadata"] = tags
            done += 1
            tag_preview = ", ".join(f'{t["label"]}={t["value"]}' for t in tags)
            print(f"  OK: {q['id']}: {tag_preview}")
        else:
            print(f"  SKIP: {q['id']}")

    if args.dry_run:
        print(f"\n[dry run] Would have extracted {done}/{len(candidates)} — not writing {_BANK_PATH}")
        return

    with open(_BANK_PATH, "w", encoding="utf-8") as f:
        json.dump(bank, f, indent=2)

    print(f"\nDone: {done}/{len(candidates)} extracted. Saved to {_BANK_PATH}")
    print("Run scripts/seed_questions.py to push this into Supabase.")


if __name__ == "__main__":
    main()
