"""
Persistence + bookkeeping shell for question-bank repairs — reused by ME
(Claude) as a library of verified-write primitives while hand-authoring
content per question in-session. This file contains NO LLM calls and NO
content-generation logic; every function here takes already-written content
as input, runs it through real sandbox verification
(services.harness_verify / services.piston), and only persists to Supabase
on a confirmed pass. Nothing here ever deletes a row — see
scripts/delete_confirmed_questions.py for that, which requires a prior audit
flag plus explicit --ids confirmation.

Three distinct repair shapes, because the app's runtime test-execution
routing genuinely differs per gap (see routers/interview.py):

  1. Java/C++ harness (never-attempted in audit_question_bank.py's language_status):
     runtime always uses services.harness_generator.get_or_generate's cache
     (the `harnesses` column) regardless of the `languages` array — so
     persist_and_verify_harness() only needs to write `harnesses[lang]`.

  2. Node signature (never-attempted node): the runtime test-execution path
     (services.test_runner.generate_harness) ONLY uses the bank's own
     verified tests when "node" is listed in the question's `languages`
     array — otherwise it falls back to LLM-generated, sandbox-UNVERIFIED
     ad-hoc test cases at request time, even if a `signatures.node`
     boilerplate already exists (that cache is display-only, for the
     /boilerplate route). So a correct node repair must verify the bank's
     own tests actually pass in JS (via the same translation
     test_runner._node_harness/_pyliteral_to_js/_add_js_new_keywords does at
     runtime) AND add "node" to `languages` — persist_and_verify_node() does
     both, atomically from the caller's perspective (language is only added
     after verification passes).

  3. Test-case top-up (insufficient_test_count): appends new {call, expected}
     pairs to `tests`, where `expected` is computed by actually EXECUTING a
     reference Python solution against `call` in the sandbox — never a
     claimed/guessed value. append_verified_test_case() does this.

Every persist call re-reads the row uses the same read-merge-write pattern as
harness_generator._persist_question_field, then calls question_bank.refresh()
to bust the in-process cache — imported directly from harness_generator
rather than reimplemented.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from services import (  # noqa: E402
    harness_generator,
    harness_verify,
    piston,
    question_bank,
    test_runner,
)
from services.supabase_client import get_supabase  # noqa: E402

_LOG_PATH = os.path.join(os.path.dirname(__file__), "_repair_log.json")


def _load_log() -> dict:
    if os.path.exists(_LOG_PATH):
        with open(_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_log(log_data: dict) -> None:
    with open(_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2)


def _record(question_id: str, key: str, outcome: str, detail: str = "") -> None:
    data = _load_log()
    data.setdefault(question_id, {})[key] = {"outcome": outcome, "detail": detail[:500]}
    _save_log(data)


def _persist_flat_field(question_id: str, field: str, value) -> None:
    """For plain (non-per-language-dict) fields, e.g. `tests`, `languages`.
    Unlike harness_generator._persist_question_field (which merges into a
    {language: data} dict), this overwrites the whole field — the caller is
    responsible for having read-merged first if that's the semantics needed
    (see append_verified_test_case / _add_language_if_missing)."""
    sb = get_supabase()
    if not sb:
        raise RuntimeError("Supabase is not configured")
    sb.table("questions").update({field: value}).eq("id", question_id).execute()
    question_bank.refresh()


def _get_question(question_id: str) -> dict:
    sb = get_supabase()
    row = sb.table("questions").select("*").eq("id", question_id).execute()
    if not row.data:
        raise ValueError(f"question {question_id!r} not found")
    return row.data[0]


# ── 1. Java/C++ harness ───────────────────────────────────────────────────

async def persist_and_verify_harness(
    question_id: str, language: str, boilerplate: str, harness: str, reference_solution: str,
) -> tuple[bool, str]:
    """language in ('java', 'cpp'). Verifies via the real sandbox, persists
    to `harnesses[language]` ONLY on pass (never a partial/best-effort
    write) — same all-or-nothing contract as harness_generator.get_or_generate."""
    question = _get_question(question_id)
    n_tests = len(question["tests"])
    ok, err = await harness_verify.verify_against_tests(
        language, boilerplate, harness, reference_solution, n_tests, harness_generator.merge_sources,
    )
    if not ok:
        _record(question_id, f"harness:{language}", "failed", err)
        return False, err

    harness_data = {"boilerplate": boilerplate, "harness": harness}
    await asyncio.to_thread(harness_generator._persist_question_field, question_id, "harnesses", language, harness_data)
    _record(question_id, f"harness:{language}", "verified_and_persisted")
    return True, ""


# ── 2. Node signature + languages ─────────────────────────────────────────

async def persist_and_verify_node(
    question_id: str, boilerplate: str, reference_solution: str,
) -> tuple[bool, str]:
    """Verifies the question's OWN canonical tests actually pass when the
    reference_solution is run through the exact translation
    (test_runner._node_harness/_pyliteral_to_js/_add_js_new_keywords) the
    live runtime uses, THEN persists signatures.node and adds "node" to
    `languages` — only after verification, so a question is never marked
    node-capable with unverified test behavior."""
    question = _get_question(question_id)
    cases = question["tests"]

    harness_source = test_runner._node_harness(reference_solution, cases)
    result = await piston.run_code("node", "18.15.0", harness_source, stdin="")
    raw = result.get("run", {})
    if raw.get("stderr") and raw.get("code", 0) != 0:
        err = raw["stderr"][:1500]
        _record(question_id, "node", "failed", err)
        return False, f"reference solution + node harness failed to run:\n{err}"

    parsed = test_runner.parse_results(raw.get("stdout", ""), raw.get("stderr", ""))
    if parsed["status"] != "accepted":
        err = json.dumps(parsed)[:1500]
        _record(question_id, "node", "failed", err)
        return False, f"reference solution did not pass all of the question's own tests in JS: {err}"

    ok_stub, stub_err = await harness_verify.compiles("node", boilerplate)
    if not ok_stub:
        _record(question_id, "node", "failed", stub_err)
        return False, f"boilerplate stub failed to compile standalone:\n{stub_err}"

    await asyncio.to_thread(harness_generator._persist_question_field, question_id, "signatures", "node", boilerplate)
    languages = list(question.get("languages") or [])
    if "node" not in languages:
        languages.append("node")
        await asyncio.to_thread(_persist_flat_field, question_id, "languages", languages)
    _record(question_id, "node", "verified_and_persisted")
    return True, ""


# ── 3. Test-case top-up ───────────────────────────────────────────────────

async def append_verified_test_case(question_id: str, reference_solution: str, call: str) -> tuple[bool, str]:
    """Executes `call` against `reference_solution` (Python) in the real
    sandbox and uses the ACTUAL produced value as `expected` — never a
    claimed/guessed one — then appends {call, expected} to `tests`. Skips
    (returns False) if the call raises, since that means either the call
    string or the reference solution itself is wrong, not something to
    silently paper over."""
    script = f'''{reference_solution}

import json as _j
try:
    _result = {call}
    print(_j.dumps({{"ok": True, "value": _result}}))
except Exception as _e:
    print(_j.dumps({{"ok": False, "error": str(_e)}}))
'''
    result = await piston.run_code("python", "3.10.0", script, stdin="")
    raw = result.get("run", {})
    if raw.get("stderr") and raw.get("code", 0) != 0:
        err = raw["stderr"][:1500]
        _record(question_id, f"testcase:{call[:60]}", "failed", err)
        return False, err

    try:
        parsed = json.loads((raw.get("stdout") or "").strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        _record(question_id, f"testcase:{call[:60]}", "failed", str(exc))
        return False, f"could not parse execution result: {exc}"

    if not parsed.get("ok"):
        _record(question_id, f"testcase:{call[:60]}", "failed", parsed.get("error", ""))
        return False, f"call raised: {parsed.get('error')}"

    expected_repr = repr(parsed["value"])
    question = _get_question(question_id)
    tests = list(question["tests"])
    tests.append({"call": call, "expected": expected_repr})
    await asyncio.to_thread(_persist_flat_field, question_id, "tests", tests)
    _record(question_id, f"testcase:{call[:60]}", "verified_and_persisted", expected_repr)
    return True, expected_repr


# ── System-design structured brief (flat JSONB fields, structural-only check) ──

def persist_system_design_brief(
    question_id: str,
    functional_requirements: list[str],
    non_functional_requirements: list[str],
    scaling_constraints: list[str],
    out_of_scope: list[str],
) -> None:
    """No sandbox verification is possible for prose fields — only the
    structural check services.question_schema already enforces (non-empty
    lists). Persists all four fields in one update call."""
    for name, value in (
        ("functional_requirements", functional_requirements),
        ("non_functional_requirements", non_functional_requirements),
        ("scaling_constraints", scaling_constraints),
        ("out_of_scope", out_of_scope),
    ):
        if not value:
            raise ValueError(f"{name} must be non-empty for {question_id}")

    sb = get_supabase()
    if not sb:
        raise RuntimeError("Supabase is not configured")
    sb.table("questions").update({
        "functional_requirements": functional_requirements,
        "non_functional_requirements": non_functional_requirements,
        "scaling_constraints": scaling_constraints,
        "out_of_scope": out_of_scope,
    }).eq("id", question_id).execute()
    question_bank.refresh()
    _record(question_id, "system_design_brief", "persisted")
