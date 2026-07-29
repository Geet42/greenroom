"""
Replaces the "confirmed_unsupported" java/cpp questions (proven, not just
suspected, to fail — harness_generator's LLM path already exhausted
_GENERATION_ATTEMPTS on every one of them) with same-difficulty,
topic-matched candidates pulled straight from the neenza/leetcode-problems
dataset, pre-validated through the SAME deterministic import pipeline used
in import_neenza_boilerplate.py so a replacement only ever goes in once it's
proven to actually clear all 4 languages — never "swap and hope".

What's still needed per replacement (the one thing neenza doesn't ship):
verified test cases. Groq was rate-limited when this was built, so instead
of LLM-generating reference solutions, scripts/swap_solutions.py has
hand-authored Python solutions for each candidate (all standard, well-known
algorithms) — never trusted blind either: each is actually RUN through the
sandbox against the dataset's own official worked-example inputs, and only
accepted if its real output matches LeetCode's own stated example output.

Safety model: nothing is ever deleted before its replacement is fully built,
verified, and inserted. Any candidate that fails ANY step is skipped (old
question kept as-is, reported) rather than forcing a swap. This is a single
non-interactive pass — every accept/reject decision is deterministic given
the pre-validation, and the only inherently-variable part (LLM solution
correctness) is caught by sandbox cross-verification, not retried blindly.

Usage:
    cd backend && .venv/Scripts/python scripts/swap_unsupported_questions.py [--dry-run]
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from scripts.import_neenza_boilerplate import (  # noqa: E402
    _cpp_placeholder_return,
    _java_placeholder_return,
    _slugify,
    build_cpp_harness,
    build_java_harness,
    extract_cpp_signature,
    extract_java_signature,
    inject_placeholder_body,
    parse_neenza_examples,
    python_ensure_body,
)
from scripts.swap_solutions import SOLUTIONS as _SOLUTIONS_1  # noqa: E402
from scripts.swap_solutions_batch2 import SOLUTIONS_2 as _SOLUTIONS_2  # noqa: E402
from services import harness_generator, piston, question_bank  # noqa: E402
from services.question_generator import _run_solution  # noqa: E402
from services.supabase_client import get_supabase  # noqa: E402

DATASET_PATH = os.path.join(os.path.dirname(__file__), "_neenza_dataset.json")
SWAP_SOLUTIONS: dict[str, str] = {**_SOLUTIONS_1, **_SOLUTIONS_2}

_IDS_FILE = os.path.join(os.path.dirname(__file__), "_unsupported_ids.json")


def _load_target_ids() -> list[str]:
    if os.path.exists(_IDS_FILE):
        with open(_IDS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


_STRUCTURAL_UNSUPPORTED_IDS = _load_target_ids()

def _load_dataset() -> list[dict]:
    with open(DATASET_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["questions"] if isinstance(data, dict) else data


async def _piston_ok(piston_lang: str, version: str, source: str) -> bool:
    result = await piston.run_code(piston_lang, version, source, stdin="")
    raw = result.get("run", {})
    return not (raw.get("stderr") and raw.get("code", 0) != 0)


async def _structural_precheck(entry: dict) -> dict | None:
    """Validates a candidate WITHOUT needing test data yet — signature must
    parse for both java/cpp (our supported type vocabulary), and the
    boilerplate+placeholder-body must compile standalone when wrapped in a
    trivial synthetic main (a stand-in for the real driver, which needs real
    test data we don't have at this stage). Returns the parsed signatures if
    every check passes, else None."""
    snippets = entry.get("code_snippets") or {}
    java_code = snippets.get("java")
    cpp_code = snippets.get("cpp")
    py_code = snippets.get("python3")
    js_code = snippets.get("javascript")
    if not all([java_code, cpp_code, py_code, js_code]):
        return None

    java_sig = extract_java_signature(java_code)
    cpp_sig = extract_cpp_signature(cpp_code)
    if java_sig is None or cpp_sig is None:
        return None
    j_method, j_params, j_ret, j_body_start = java_sig
    c_method, c_params, c_ret, c_body_start = cpp_sig

    java_stub = inject_placeholder_body(java_code, j_body_start, f"return {_java_placeholder_return(j_ret)};")
    java_synth = harness_generator.merge_sources(
        "java", [java_stub, "class Main { public static void main(String[] a) { new Solution(); } }"],
    )
    if not await _piston_ok("java", "15.0.2", java_synth):
        return None

    cpp_stub = inject_placeholder_body(cpp_code, c_body_start, f"return {_cpp_placeholder_return(c_ret)};")
    cpp_synth = harness_generator.merge_sources("cpp", [cpp_stub, "int main() { Solution s; return 0; }"])
    if not await _piston_ok("gcc", "10.2.0", cpp_synth):
        return None

    py_stub = "from typing import List, Optional, Dict, Tuple\n\n" + python_ensure_body(py_code)
    if not await _piston_ok("python", "3.10.0", py_stub):
        return None
    if not await _piston_ok("node", "18.15.0", js_code):
        return None

    return {
        "java_sig": (j_method, j_params, j_ret, j_body_start), "cpp_sig": (c_method, c_params, c_ret, c_body_start),
        "java_stub": java_stub, "cpp_stub": cpp_stub, "py_stub": py_stub, "js_code": js_code,
    }


def _topic_score(our_topic: str, candidate_topics: list[str]) -> int:
    our_words = set(re.findall(r"[a-z]+", (our_topic or "").lower()))
    cand_words = set(w.lower() for t in candidate_topics for w in re.findall(r"[a-z]+", t))
    return len(our_words & cand_words)


def _values_equal(actual_repr: str, expected_text: str) -> bool:
    """actual_repr is a Python repr() string (from _run_solution's sandbox
    output); expected_text is the dataset's own free-text stated output
    (e.g. '2.50000', '"cbaabd"', '[0,1]', 'true'). Tolerant on formatting,
    strict on the pass/fail decision — this is checking a hand-authored
    solution against LeetCode's own official example output, not against
    another guess."""
    try:
        actual = ast.literal_eval(actual_repr)
    except Exception:
        return False
    et = expected_text.strip()
    candidates: list = []
    try:
        candidates.append(ast.literal_eval(et))
    except Exception:
        pass
    if len(et) >= 2 and et[0] == et[-1] and et[0] in "\"'":
        candidates.append(et[1:-1])
    candidates.append(et)
    if et.lower() == "true":
        candidates.append(True)
    if et.lower() == "false":
        candidates.append(False)
    for c in candidates:
        if isinstance(actual, float) or isinstance(c, (float, int)) and isinstance(actual, (int, float)):
            try:
                if abs(float(actual) - float(c)) < 1e-6:
                    return True
            except Exception:
                pass
        if actual == c:
            return True
    return False


async def build_replacement(old_id: str, old: dict, entry: dict, precheck: dict) -> dict | None:
    py_snippet = (entry.get("code_snippets") or {}).get("python3", "")
    m = re.search(r"def\s+(\w+)\s*\(", py_snippet)
    if not m:
        return None
    function_name = m.group(1)

    prompt_text = entry.get("description") or ""
    if not prompt_text.strip():
        return None

    solution = SWAP_SOLUTIONS.get(entry.get("problem_slug", ""))
    if not solution:
        return None  # no hand-authored solution available for this candidate

    # Seed calls + their OFFICIAL stated outputs from the dataset's own
    # worked examples (real LeetCode example data, not invented) — this is
    # what gets sandbox-verified against, not a second AI's opinion.
    seed_calls: list[str] = []
    official_outputs: list[str] = []
    for ex in entry.get("examples") or []:
        text = (ex.get("example_text") or "").strip()
        im = re.match(r"^Input:\s*(.*?)\nOutput:\s*(.*?)(?:\nExplanation:|$)", text, re.DOTALL)
        if not im:
            continue
        arg_text = im.group(1).strip()
        seed_calls.append(f"{function_name}({arg_text})")
        official_outputs.append(im.group(2).strip())
    if len(seed_calls) < 2:
        return None

    outputs = await _run_solution(solution, seed_calls)
    if outputs is None or len(outputs) != len(seed_calls):
        return None  # the hand-authored solution crashed on the official examples

    # The real verification bar: does our solution's SANDBOX-EXECUTED output
    # match LeetCode's own stated official output for every worked example?
    if any(not _values_equal(a, e) for a, e in zip(outputs, official_outputs)):
        return None

    tests = [{"call": c, "expected": o} for c, o in zip(seed_calls, outputs)]

    # Build real harnesses/signatures now that we have verified tests.
    j_method, j_params, j_ret, _ = precheck["java_sig"]
    c_method, c_params, c_ret, _ = precheck["cpp_sig"]
    java_driver = build_java_harness(j_method, j_params, j_ret, tests)
    cpp_driver = build_cpp_harness(c_method, c_params, c_ret, tests)
    if java_driver is None or cpp_driver is None:
        return None

    java_full = harness_generator.merge_sources("java", [precheck["java_stub"], java_driver])
    if not await _piston_ok("java", "15.0.2", java_full):
        return None
    cpp_full = harness_generator.merge_sources("cpp", [precheck["cpp_stub"], cpp_driver])
    if not await _piston_ok("gcc", "10.2.0", cpp_full):
        return None

    difficulty = (entry.get("difficulty") or old.get("difficulty") or "medium").lower()
    topic = (entry.get("topics") or [old.get("topic") or "general"])[0]
    examples = parse_neenza_examples(entry)
    new_id = _slugify(entry["title"])

    return {
        "id": new_id,
        "track": "technical",
        "topic": topic,
        "difficulty": difficulty,
        "title": entry["title"],
        "prompt": prompt_text,
        "function_name": f"Solution().{function_name}",
        "languages": ["python", "node", "java", "cpp"],
        "tests": tests,
        "constraints": entry.get("constraints") or [],
        "examples": examples,
        "signatures": {"python": precheck["py_stub"], "node": precheck["js_code"]},
        "harnesses": {
            "java": {"boilerplate": precheck["java_stub"], "harness": java_driver},
            "cpp": {"boilerplate": precheck["cpp_stub"], "harness": cpp_driver},
        },
    }


def _persist_swap(old_id: str, new_question: dict, dry_run: bool) -> None:
    if dry_run:
        return
    sb = get_supabase()
    if not sb:
        return
    sb.table("questions").insert({
        "id": new_question["id"], "track": new_question["track"], "topic": new_question["topic"],
        "difficulty": new_question["difficulty"], "title": new_question["title"], "prompt": new_question["prompt"],
        "function_name": new_question["function_name"], "languages": new_question["languages"],
        "tests": new_question["tests"], "constraints": new_question["constraints"], "examples": new_question["examples"],
        "signatures": new_question["signatures"], "harnesses": new_question["harnesses"],
    }).execute()
    sb.table("questions").delete().eq("id", old_id).execute()
    question_bank.refresh()


async def main(dry_run: bool) -> None:
    sb = get_supabase()
    if not sb:
        print("Supabase is not configured.")
        return

    dataset = _load_dataset()
    by_slug = {p.get("problem_slug"): p for p in dataset if p.get("problem_slug")}

    rows = sb.table("questions").select("id, track, title, topic, difficulty, tests, function_name").execute().data
    by_id = {r["id"]: r for r in rows}
    existing_slugs = {_slugify(r["title"]) for r in rows}

    print(f"Dataset: {len(dataset)} problems. {len(_STRUCTURAL_UNSUPPORTED_IDS)} questions targeted for swap.")
    if dry_run:
        print("DRY RUN — no writes will be made.\n")

    results = {"swapped": [], "skipped": []}
    used_candidate_slugs: set[str] = set()

    for old_id in _STRUCTURAL_UNSUPPORTED_IDS:
        old = by_id.get(old_id)
        if not old:
            results["skipped"].append((old_id, "not-found-in-db"))
            continue

        difficulty = (old.get("difficulty") or "").lower()
        our_topic = old.get("topic") or ""
        candidates = [
            p for slug, p in by_slug.items()
            if (p.get("difficulty") or "").lower() == difficulty
            and slug not in existing_slugs and slug not in used_candidate_slugs
        ]
        candidates.sort(key=lambda p: -_topic_score(our_topic, p.get("topics") or []))

        # Try candidates in ranked order until one clears BOTH the structural
        # precheck AND full test-verification — a candidate failing later
        # (e.g. no hand-authored solution available, or a genuine solution
        # bug) must not stop the search, or every later question in the same
        # difficulty bucket starves on that one bad candidate.
        new_question = None
        accepted = None
        tried_reasons = []
        for cand in candidates[:60]:
            pc = await _structural_precheck(cand)
            if pc is None:
                continue
            candidate_result = await build_replacement(old_id, old, cand, pc)
            if candidate_result is not None:
                new_question = candidate_result
                accepted = cand
                break
            tried_reasons.append(cand["problem_slug"])

        if new_question is None:
            reason = "no-structurally-clean-candidate-found" if not tried_reasons else (
                f"all-tried-candidates-failed-verification ({', '.join(tried_reasons)})"
            )
            results["skipped"].append((old_id, reason))
            print(f"[{old_id}] SKIP — {reason}")
            continue

        used_candidate_slugs.add(accepted["problem_slug"])
        _persist_swap(old_id, new_question, dry_run)
        results["swapped"].append((old_id, new_question["id"], new_question["title"]))
        print(f"[{old_id}] SWAPPED -> {new_question['id']} ({new_question['title']}), "
              f"{len(new_question['tests'])} verified tests, all 4 languages covered")

    print("\n=== Summary ===")
    print(f"Swapped: {len(results['swapped'])} / {len(_STRUCTURAL_UNSUPPORTED_IDS)}")
    for old_id, new_id, title in results["swapped"]:
        print(f"  {old_id}  ->  {new_id}  ({title})")
    print(f"\nSkipped (kept original): {len(results['skipped'])}")
    for old_id, reason in results["skipped"]:
        print(f"  {old_id}: {reason}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))
