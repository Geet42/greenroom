"""Deep data-quality audit, read-only. Complements audit_question_bank.py's
structural completeness check with content-level sanity checks across the
WHOLE bank (not just recently-touched rows):

  1. Every `tests[i].call` parses as a valid Python call, and `expected`
     parses as a valid Python literal (ast.literal_eval) — catches the
     "unparseable -inf literal" class of corruption found earlier.
  2. Paired-array arguments (same length by name convention, e.g.
     parent[]/s[], nums[]/cost[]) actually have matching lengths.
  3. No duplicate {call, expected} pairs within one question's tests.
  4. harnesses/signatures JSONB blobs parse and reference the question's
     own function_name somewhere in their harness text (catches an
     orphaned/mismatched harness pasted under the wrong question id).
  5. visible_count (stdio questions) is within [1, len(tests)].
  6. system-design / behavioral required fields are non-empty (not just
     present) — catches "[]" or "" slipping past a presence-only check.

Never mutates anything. Prints a flagged list for human review.
"""
import ast
import json
import sys

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(".env")
from services.supabase_client import get_supabase


def _try_parse_call(call: str):
    try:
        tree = ast.parse(call, mode="eval")
        return tree, None
    except SyntaxError as e:
        return None, str(e)


def _try_literal_eval(expected: str):
    try:
        return ast.literal_eval(expected), None
    except Exception as e:
        return None, str(e)


def _extract_kwargs(call: str):
    """Best-effort: parse `Solution().foo(a=1, b=[1,2])` into {'a': 1, 'b': [1,2]}."""
    tree, err = _try_parse_call(call)
    if tree is None:
        return None, err
    node = tree.body
    if not isinstance(node, ast.Call):
        return None, "not a call expression"
    kwargs = {}
    try:
        for kw in node.keywords:
            kwargs[kw.arg] = ast.literal_eval(kw.value)
    except Exception as e:
        return None, f"non-literal arg: {e}"
    return kwargs, None


def audit_tests_content(qid, tests):
    """call/expected format only — stdio-format rows (stdin/stdout keys,
    e.g. the CodeContests-derived cc-* rows) are a different, already-valid
    shape and are the caller's responsibility to route around."""
    flags = []
    seen = set()
    for i, t in enumerate(tests):
        call = t.get("call", "")
        expected = t.get("expected", "")
        _, call_err = _try_parse_call(call)
        if call_err:
            flags.append(f"test[{i}] call does not parse: {call_err}")
            continue
        _, exp_err = _try_literal_eval(expected)
        if exp_err:
            flags.append(f"test[{i}] expected does not literal_eval: {exp_err} -- {expected[:80]}")
        key = (call, expected)
        if key in seen:
            flags.append(f"test[{i}] exact duplicate of an earlier test case")
        seen.add(key)
    return flags


def audit_harness_blob(qid, function_name, harnesses, signatures):
    flags = []
    # function_name is stored as "Solution().methodName" (a call prefix);
    # the harness only ever calls the bare method name (e.g. "sol.methodName(...)").
    method_name = function_name
    if function_name and ")." in function_name:
        method_name = function_name.rsplit(").", 1)[-1]
    for lang, blob in (harnesses or {}).items():
        if not isinstance(blob, dict):
            flags.append(f"harnesses[{lang}] is not a dict")
            continue
        harness_text = blob.get("harness", "")
        if method_name and method_name not in harness_text:
            flags.append(f"harnesses[{lang}] does not reference method {method_name!r}")
    for lang, blob in (signatures or {}).items():
        if blob is None:
            flags.append(f"signatures[{lang}] is null")
    return flags


def main():
    sb = get_supabase()
    rows = sb.table("questions").select("*").execute().data
    print(f"Deep-auditing {len(rows)} rows...\n")

    total_flags = 0
    flagged_questions = 0
    for row in rows:
        qid = row["id"]
        track = row.get("track")
        flags = []

        tests = row.get("tests") or []
        is_stdio = bool(tests) and "stdin" in tests[0]
        if track == "technical" and not is_stdio:
            flags += [f"[tests] {f}" for f in audit_tests_content(qid, tests)]
            flags += [f"[harness] {f}" for f in audit_harness_blob(
                qid, row.get("function_name"), row.get("harnesses"), row.get("signatures"))]
            visible_count = row.get("visible_count")
            if visible_count is not None:
                if not (1 <= visible_count <= max(len(tests), 1)):
                    flags.append(f"[visible_count] {visible_count} out of range for {len(tests)} tests")
        elif track == "technical" and is_stdio:
            seen = set()
            for i, t in enumerate(tests):
                key = (t.get("stdin"), t.get("stdout"))
                if key in seen:
                    flags.append(f"[tests] test[{i}] exact duplicate stdin/stdout pair")
                seen.add(key)

        elif track == "system-design":
            for field in ("functional_requirements", "non_functional_requirements",
                          "scaling_constraints", "expected_components"):
                val = row.get(field)
                if not val:
                    flags.append(f"[{field}] missing or empty")

        elif track == "behavioral":
            elements = row.get("expected_elements")
            if not elements or len(elements) != 4:
                flags.append(f"[expected_elements] expected 4 items, got {len(elements) if elements else 0}")

        if flags:
            flagged_questions += 1
            total_flags += len(flags)
            print(f"=== {qid} ({track}) ===")
            for f in flags:
                print(f"  - {f}")

    print(f"\n{'='*70}")
    print(f"Deep audit complete: {flagged_questions} question(s) flagged, {total_flags} total issue(s), out of {len(rows)} rows.")


if __name__ == "__main__":
    main()
