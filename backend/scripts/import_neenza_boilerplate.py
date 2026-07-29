"""
Imports real LeetCode starter code from the neenza/leetcode-problems dataset
(https://github.com/neenza/leetcode-problems, 2,913 problems, MIT-style free
dataset) as boilerplate for our own question bank, matched by slugified
title. This replaces the LLM-generation half of harness_generator's job for
every matched question:

- python/node: the dataset's own `code_snippets["python3"]` / `["javascript"]`
  are written straight into `signatures[lang]` — these are real official
  LeetCode stubs, nothing to generate.
- java/cpp: the dataset's own `code_snippets["java"]` / `["cpp"]` become the
  candidate-facing boilerplate half of `harnesses[lang]`, but a harness still
  needs a driver/main that calls the candidate's method and prints our
  {id,label,input,expected,passed} JSON schema per test — that part IS
  generated here, deterministically (no LLM), by parsing the official
  method's declared parameter/return types straight out of the dataset's own
  signature and translating our bank's Python test literals into typed
  Java/C++ literals of the matching shape.

Deliberately scoped, not "handles every LeetCode problem ever": only
primitives, strings, and (possibly nested) arrays/Lists/vectors of those are
supported, since that covers the overwhelming majority of this bank. Anything
using a custom type (ListNode, TreeNode, NestedInteger, ...), or a
stateful/constructor-based problem (multi-statement test calls), is left
untouched — those stay on harness_generator's existing LLM path.

Unlike harness_generator.get_or_generate, there is no reference solution to
verify against here (the dataset only ships an empty stub), so this can only
sanity-check that the boilerplate+driver actually COMPILES (same technique as
harness_generator._compiles), not that the driver's comparison logic is
correct against real solved output. Given the driver logic itself is a fixed,
reviewed template rather than LLM-generated prose, that compile check is the
meaningful risk to catch (a wrong type mapping, a syntax slip) — logical
correctness follows directly from the template, not from a per-problem guess.

Usage:
    cd backend && .venv/Scripts/python scripts/import_neenza_boilerplate.py [--dataset PATH] [--limit N] [--dry-run]

PATH defaults to downloading https://raw.githubusercontent.com/neenza/leetcode-problems/master/merged_problems.json
to a temp file if not already present locally.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import asyncio  # noqa: E402

from services import harness_generator, question_bank  # noqa: E402
from services.supabase_client import get_supabase  # noqa: E402

DATASET_URL = "https://raw.githubusercontent.com/neenza/leetcode-problems/master/merged_problems.json"

_UNSUPPORTED_MARKER = harness_generator._UNSUPPORTED_MARKER


# ── slug matching ────────────────────────────────────────────────────────────

def _slugify(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# ── type model: ('prim', 'int'|'long'|'double'|'float'|'boolean'|'char')
#              | ('string',)
#              | ('array', inner)      -- java only
#              | ('list', inner)       -- java only (List<...>)
#              | ('vector', inner)     -- cpp only

_JAVA_PRIM = {"int", "long", "double", "float", "boolean", "char"}
_JAVA_BOXED_TO_PRIM = {
    "Integer": "int", "Long": "long", "Double": "double",
    "Float": "float", "Boolean": "boolean", "Character": "char",
}
_JAVA_PRIM_TO_BOXED = {v: k for k, v in _JAVA_BOXED_TO_PRIM.items()}

_CPP_PRIM = {"int", "long", "long long", "double", "float", "bool", "char"}


def parse_java_type(s: str) -> tuple | None:
    s = s.strip()
    m = re.match(r"^(int|long|double|float|boolean|char|String)((?:\s*\[\s*\])*)$", s)
    if m:
        base, brackets = m.group(1), m.group(2)
        depth = brackets.count("[")
        t: tuple = ("string",) if base == "String" else ("prim", base)
        for _ in range(depth):
            t = ("array", t)
        return t
    m = re.match(r"^List<(.+)>$", s)
    if m:
        inner_raw = m.group(1).strip()
        if inner_raw in _JAVA_BOXED_TO_PRIM:
            return ("list", ("prim", _JAVA_BOXED_TO_PRIM[inner_raw]))
        if inner_raw == "String":
            return ("list", ("string",))
        inner = parse_java_type(inner_raw)
        if inner is None:
            return None
        return ("list", inner)
    if s in _JAVA_BOXED_TO_PRIM:
        return ("prim", _JAVA_BOXED_TO_PRIM[s])
    if s == "String":
        return ("string",)
    return None


def parse_cpp_type(s: str) -> tuple | None:
    s = s.strip()
    s = re.sub(r"^const\s+", "", s)
    s = re.sub(r"\s*&\s*$", "", s).strip()
    if s in _CPP_PRIM:
        return ("prim", s)
    if s == "string":
        return ("string",)
    m = re.match(r"^vector<(.+)>$", s)
    if m:
        inner = parse_cpp_type(m.group(1).strip())
        if inner is None:
            return None
        return ("vector", inner)
    return None


# ── signature extraction from the dataset's own code_snippets ───────────────

def _split_top_level(s: str) -> list[str]:
    parts, depth, cur = [], 0, []
    for ch in s:
        if ch in "<[(":
            depth += 1
            cur.append(ch)
        elif ch in ">])":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def extract_java_signature(code: str) -> tuple | None:
    m = re.search(r"public\s+(.+?)\s+(\w+)\s*\((.*?)\)\s*\{", code, re.DOTALL)
    if not m:
        return None
    ret_str, method_name, params_str = m.group(1).strip(), m.group(2), m.group(3)
    ret_type = parse_java_type(ret_str)
    if ret_type is None:
        return None
    params: list[tuple[tuple, str]] = []
    for p in _split_top_level(params_str):
        if not p.strip():
            continue
        if " " not in p.strip():
            return None
        type_str, name = p.strip().rsplit(None, 1)
        pt = parse_java_type(type_str.strip())
        if pt is None:
            return None
        params.append((pt, name))
    return method_name, params, ret_type, m.end()


def extract_cpp_signature(code: str) -> tuple | None:
    m = re.search(r"public:\s*(.+?)\s+(\w+)\s*\((.*?)\)\s*\{", code, re.DOTALL)
    if not m:
        return None
    ret_str, method_name, params_str = m.group(1).strip(), m.group(2), m.group(3)
    ret_type = parse_cpp_type(ret_str)
    if ret_type is None:
        return None
    params: list[tuple[tuple, str]] = []
    for p in _split_top_level(params_str):
        if not p.strip():
            continue
        p = p.strip()
        if " " not in p:
            return None
        type_str, name = p.rsplit(None, 1)
        name = name.lstrip("&").strip()
        pt = parse_cpp_type(type_str.strip())
        if pt is None:
            return None
        params.append((pt, name))
    return method_name, params, ret_type, m.end()


# ── call-string -> python values ─────────────────────────────────────────────

def parse_call_args(call: str) -> list | None:
    """"twoSum([2,7,11,15], 9)" -> [[2,7,11,15], 9]. Handles the bank's
    keyword-call style too ("Solution().foo(nums=[1,2], k=3)"). Returns None
    for multi-statement (stateful/constructor) calls — those are out of scope
    here."""
    if ";" in call:
        return None
    call = re.sub(r"^\w+\(\)\.", "", call)  # strip a leading "Solution()." constructor prefix
    idx = call.find("(")
    if idx == -1:
        return None
    depth = 0
    end = -1
    in_str: str | None = None
    i = idx
    while i < len(call):
        ch = call[i]
        if in_str:
            if ch == "\\":
                i += 1  # skip the escaped character too (e.g. \" inside the literal)
            elif ch == in_str:
                in_str = None
        elif ch in ("'", '"'):
            in_str = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end = i
                break
        i += 1
    if end == -1:
        return None
    inner = call[idx + 1:end]
    if not inner.strip():
        return []
    values = []
    for part in _split_top_level(inner):
        part = part.strip()
        m = re.match(r"^\w+\s*=\s*(.*)$", part, re.DOTALL)
        literal_text = m.group(1) if m else part
        try:
            values.append(ast.literal_eval(literal_text))
        except (ValueError, SyntaxError):
            return None
    return values


# ── literal builders ─────────────────────────────────────────────────────────

def _java_scalar_literal(value, t: tuple) -> str:
    kind = t[0]
    if kind == "prim":
        p = t[1]
        if p == "int":
            return str(int(value))
        if p == "long":
            return f"{int(value)}L"
        if p in ("double", "float"):
            return repr(float(value))
        if p == "boolean":
            return "true" if value else "false"
        if p == "char":
            return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"
    if kind == "string":
        return json.dumps(str(value))
    raise ValueError(f"unsupported scalar type {t}")


def _java_array_body(value, elem_t: tuple) -> str:
    if elem_t[0] == "array":
        return "{" + ", ".join(_java_array_body(v, elem_t[1]) for v in value) + "}"
    return "{" + ", ".join(_java_scalar_literal(v, elem_t) for v in value) + "}"


def java_base_and_depth(t: tuple) -> tuple[str, int]:
    depth = 0
    cur = t
    while cur[0] == "array":
        depth += 1
        cur = cur[1]
    base = "String" if cur[0] == "string" else cur[1]
    return base, depth


def java_type_decl(t: tuple) -> str:
    if t[0] == "prim":
        return t[1]
    if t[0] == "string":
        return "String"
    if t[0] == "array":
        base, depth = java_base_and_depth(t)
        return base + "[]" * depth
    if t[0] == "list":
        return f"List<{java_boxed_decl(t[1])}>"
    raise ValueError(f"unsupported type {t}")


def java_boxed_decl(t: tuple) -> str:
    if t[0] == "prim":
        return _JAVA_PRIM_TO_BOXED[t[1]]
    if t[0] == "string":
        return "String"
    if t[0] == "list":
        return f"List<{java_boxed_decl(t[1])}>"
    raise ValueError(f"unsupported boxed type {t}")


def java_literal(value, t: tuple) -> str:
    if t[0] == "array":
        base, depth = java_base_and_depth(t)
        body = _java_array_body(value, t[1])
        return f"new {base}{'[]' * depth}{body}"
    if t[0] == "list":
        inner = t[1]
        elems = [java_literal(v, inner) if inner[0] in ("list", "array") else _java_scalar_literal(v, inner) for v in value]
        return "Arrays.asList(" + ", ".join(elems) + ")"
    return _java_scalar_literal(value, t)


def java_compare_expr(a: str, b: str, t: tuple) -> str:
    if t[0] == "array":
        base, depth = java_base_and_depth(t)
        if depth == 1 and base in _JAVA_PRIM:
            return f"Arrays.equals({a}, {b})"
        return f"Arrays.deepEquals({a}, {b})"
    if t[0] == "list":
        return f"{a}.equals({b})"
    if t[0] == "string":
        return f"{a}.equals({b})"
    return f"{a} == {b}"


def _cpp_scalar_literal(value, t: tuple) -> str:
    kind = t[0]
    if kind == "prim":
        p = t[1]
        if p == "int":
            return str(int(value))
        if p in ("long", "long long"):
            return f"{int(value)}LL"
        if p in ("double", "float"):
            return repr(float(value))
        if p == "bool":
            return "true" if value else "false"
        if p == "char":
            return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"
    if kind == "string":
        return json.dumps(str(value))
    raise ValueError(f"unsupported scalar type {t}")


def cpp_type_decl(t: tuple) -> str:
    if t[0] == "prim":
        return t[1]
    if t[0] == "string":
        return "string"
    if t[0] == "vector":
        return f"vector<{cpp_type_decl(t[1])}>"
    raise ValueError(f"unsupported type {t}")


def cpp_literal(value, t: tuple) -> str:
    if t[0] == "vector":
        inner = t[1]
        elems = [cpp_literal(v, inner) for v in value]
        return f"{cpp_type_decl(t)}{{{', '.join(elems)}}}"
    return _cpp_scalar_literal(value, t)


# ── driver generation ────────────────────────────────────────────────────────

def _visible_json_line(i: int, call_text: str, expected_text: str) -> tuple[str, str]:
    """Returns (java_source_literal_for_prefix, runtime_full_text_on_error) —
    both built via json.dumps so arbitrary characters in call/expected text
    (quotes, backslashes) round-trip safely through the JSON+Java escaping
    layers rather than being hand-escaped ad hoc."""
    input_esc = json.dumps(call_text)[1:-1]
    expected_esc = json.dumps(expected_text)[1:-1]
    prefix = f'{{"id":{i},"label":"Case {i}","input":"{input_esc}","expected":"{expected_esc}","passed":'
    return json.dumps(prefix), json.dumps(prefix + "false}")


def _hidden_json_line(i: int) -> tuple[str, str]:
    prefix = f'{{"id":{i},"hidden":true,"passed":'
    return json.dumps(prefix), json.dumps(prefix + "false}")


def _java_placeholder_return(t: tuple) -> str:
    if t[0] == "prim":
        return "false" if t[1] == "boolean" else "0"
    return "null"  # string, array, list


def _cpp_placeholder_return(t: tuple) -> str:
    if t[0] == "prim":
        return "false" if t[1] == "bool" else "0"
    if t[0] == "string":
        return '""'
    return "{}"  # vector


def python_ensure_body(code: str) -> str:
    """Same problem as the Java/C++ placeholder-return case: the dataset's
    Python stub body is genuinely empty (just trailing whitespace after the
    ':'), which is a syntax error standalone (Python needs an indented
    block). Finds the method's own 'def' line and appends a 'pass' at the
    right indent, discarding whatever trailing whitespace was there."""
    try:
        ast.parse(code)
        return code
    except SyntaxError:
        pass
    lines = code.splitlines()
    def_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if re.match(r"^(\s*)def\s+\w+\(", lines[i]):
            def_idx = i
            break
    if def_idx is None:
        return code
    indent = len(lines[def_idx]) - len(lines[def_idx].lstrip())
    body_indent = " " * (indent + 4)
    return "\n".join(lines[: def_idx + 1]) + "\n" + body_indent + "pass\n"


def inject_placeholder_body(code: str, body_start: int, placeholder_stmt: str) -> str:
    """The dataset's stub method body is truly empty ('{ }') — fine for
    LeetCode's own editor, but our contract (matching harness_generator's LLM
    path) requires the boilerplate to compile standalone before a candidate
    types anything, which an empty non-void method body can't do. Splices a
    single placeholder return right after the method's opening brace."""
    return code[:body_start] + f"\n        {placeholder_stmt}\n" + code[body_start:]


def build_java_harness(method_name: str, params: list[tuple[tuple, str]], ret_type: tuple, tests: list[dict]) -> str | None:
    lines = ["import java.util.*;", "", "class Main {", "    public static void main(String[] args) {", "        Solution sol = new Solution();"]
    ret_decl = java_type_decl(ret_type)
    for i, t in enumerate(tests, start=1):
        arg_values = parse_call_args(t["call"])
        if arg_values is None or len(arg_values) != len(params):
            return None
        try:
            expected_value = ast.literal_eval(t["expected"])
            arg_literals = [java_literal(v, pt) for v, (pt, _n) in zip(arg_values, params)]
            expected_literal = java_literal(expected_value, ret_type)
        except (ValueError, SyntaxError):
            return None
        visible = i <= 3
        cmp_expr = java_compare_expr("actual", "expected", ret_type)
        if visible:
            ok_lit, err_lit = _visible_json_line(i, t["call"], t["expected"])
        else:
            ok_lit, err_lit = _hidden_json_line(i)
        lines += [
            "        {",
            "            try {",
            f"                {ret_decl} actual = sol.{method_name}({', '.join(arg_literals)});",
            f"                {ret_decl} expected = {expected_literal};",
            f"                boolean passed = {cmp_expr};",
            f"                System.out.println({ok_lit} + passed + \"}}\");",
            "            } catch (Exception e) {",
            f"                System.out.println({err_lit});",
            "            }",
            "        }",
        ]
    lines += ["    }", "}"]
    return "\n".join(lines)


def build_cpp_harness(method_name: str, params: list[tuple[tuple, str]], ret_type: tuple, tests: list[dict]) -> str | None:
    lines = ["int main() {", "    Solution sol;"]
    ret_decl = cpp_type_decl(ret_type)
    for i, t in enumerate(tests, start=1):
        arg_values = parse_call_args(t["call"])
        if arg_values is None or len(arg_values) != len(params):
            return None
        try:
            expected_value = ast.literal_eval(t["expected"])
            arg_literals = [cpp_literal(v, pt) for v, (pt, _n) in zip(arg_values, params)]
            expected_literal = cpp_literal(expected_value, ret_type)
        except (ValueError, SyntaxError):
            return None
        visible = i <= 3
        if visible:
            ok_lit, err_lit = _visible_json_line(i, t["call"], t["expected"])
        else:
            ok_lit, err_lit = _hidden_json_line(i)
        # LeetCode C++ signatures commonly take non-const T& params — an
        # rvalue temporary literal can't bind to that, so declare a named
        # local for each argument (an lvalue) and pass those instead.
        arg_decls = [
            f"            {cpp_type_decl(pt)} arg{k} = {lit};"
            for k, (lit, (pt, _n)) in enumerate(zip(arg_literals, params))
        ]
        arg_names = ", ".join(f"arg{k}" for k in range(len(params)))
        lines += [
            "    {",
            "        try {",
            *arg_decls,
            f"            {ret_decl} actual = sol.{method_name}({arg_names});",
            f"            {ret_decl} expected = {expected_literal};",
            "            bool passed = (actual == expected);",
            f"            cout << {ok_lit} << (passed ? \"true\" : \"false\") << \"}}\" << endl;",
            "        } catch (...) {",
            f"            cout << {err_lit} << endl;",
            "        }",
            "    }",
        ]
    lines += ["    return 0;", "}"]
    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────────

def _load_dataset(path: str) -> list[dict]:
    if not os.path.exists(path):
        print(f"Downloading dataset to {path} ...")
        urllib.request.urlretrieve(DATASET_URL, path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["questions"] if isinstance(data, dict) else data


async def _piston_compiles(language: str, source: str) -> tuple[bool, str]:
    return await harness_generator._compiles(language, source)


async def _piston_runs_cleanly(piston_lang: str, version: str, source: str) -> tuple[bool, str]:
    """Generic sanity check for languages outside harness_generator's java/cpp
    scope (python/node) — just confirms the bare boilerplate (no invocation)
    doesn't error out when run as-is."""
    from services import piston
    result = await piston.run_code(piston_lang, version, source, stdin="")
    raw = result.get("run", {})
    if raw.get("stderr") and raw.get("code", 0) != 0:
        return False, raw["stderr"][:500]
    return True, ""


_EXAMPLE_RE = re.compile(
    r"^Input:\s*(?P<input>.*?)\nOutput:\s*(?P<output>.*?)(?:\nExplanation:\s*(?P<explanation>.*))?$",
    re.DOTALL,
)


def parse_neenza_examples(entry: dict) -> list[dict]:
    """Dataset's example_text is a single blob, e.g. 'Input: nums = [2,7,11,15],
    target = 9\\nOutput: [0,1]\\nExplanation: ...' — reshape into our
    {input, output, explanation} schema. Skips any example that doesn't match
    the expected Input:/Output: shape rather than guessing."""
    out = []
    for ex in entry.get("examples") or []:
        text = (ex.get("example_text") or "").strip()
        m = _EXAMPLE_RE.match(text)
        if not m:
            continue
        out.append({
            "input": m.group("input").strip(),
            "output": m.group("output").strip(),
            "explanation": (m.group("explanation") or "").strip(),
        })
    return out


def _persist_metadata(question_id: str, constraints: list[str] | None, examples: list[dict] | None) -> None:
    from services import question_bank
    sb = get_supabase()
    if not sb:
        return
    update: dict = {}
    if constraints is not None:
        update["constraints"] = constraints
    if examples is not None:
        update["examples"] = examples
    if not update:
        return
    try:
        sb.table("questions").update(update).eq("id", question_id).execute()
        question_bank.refresh()
    except Exception:
        pass


async def process_question(q: dict, entry: dict, dry_run: bool) -> dict:
    outcome = {"id": q["id"], "python": None, "node": None, "java": None, "cpp": None,
               "constraints": None, "examples": None}
    snippets = entry.get("code_snippets") or {}

    # constraints/examples: direct from the dataset, no LLM needed — only
    # fills gaps, never overwrites what's already there.
    want_constraints = not q.get("constraints") and entry.get("constraints")
    parsed_examples = parse_neenza_examples(entry) if not q.get("examples") else []
    want_examples = not q.get("examples") and parsed_examples
    if want_constraints or want_examples:
        if not dry_run:
            _persist_metadata(
                q["id"],
                entry["constraints"] if want_constraints else None,
                parsed_examples if want_examples else None,
            )
        outcome["constraints"] = "imported" if want_constraints else "no-data"
        outcome["examples"] = "imported" if want_examples else ("no-data" if not q.get("examples") else "skipped-already-cached")
    else:
        outcome["constraints"] = "skipped-already-cached" if q.get("constraints") else "no-data"
        outcome["examples"] = "skipped-already-cached" if q.get("examples") else "no-data"

    # python / node: straight copy, no driver needed (test_runner calls the
    # function directly), just a shape sanity check.
    for bank_lang, dataset_key, piston_lang, piston_version in [
        ("python", "python3", "python", "3.10.0"),
        ("node", "javascript", "node", "18.15.0"),
    ]:
        if (q.get("signatures") or {}).get(bank_lang):
            outcome[bank_lang] = "skipped-already-cached"
            continue
        code = snippets.get(dataset_key)
        if not code or not code.strip():
            outcome[bank_lang] = "no-snippet"
            continue
        if bank_lang == "python":
            code = "from typing import List, Optional, Dict, Tuple\n\n" + python_ensure_body(code)
        ok, err = await _piston_runs_cleanly(piston_lang, piston_version, code)
        if not ok:
            outcome[bank_lang] = f"compile-check-failed: {err[:200]}"
            continue
        if not dry_run:
            harness_generator._persist_signature(q["id"], bank_lang, code)
        outcome[bank_lang] = "imported"

    # java / cpp: need a generated driver on top of the dataset's boilerplate.
    for bank_lang, dataset_key, extractor, builder, piston_lang, piston_version in [
        ("java", "java", extract_java_signature, build_java_harness, "java", "15.0.2"),
        ("cpp", "cpp", extract_cpp_signature, build_cpp_harness, "gcc", "10.2.0"),
    ]:
        if (q.get("harnesses") or {}).get(bank_lang):
            outcome[bank_lang] = "skipped-already-cached"
            continue
        code = snippets.get(dataset_key)
        if not code or not code.strip():
            outcome[bank_lang] = "no-snippet"
            continue
        sig = extractor(code)
        if sig is None:
            outcome[bank_lang] = "unsupported-signature"
            continue
        method_name, params, ret_type, body_start = sig
        driver = builder(method_name, params, ret_type, q["tests"])
        if driver is None:
            outcome[bank_lang] = "unsupported-test-shape"
            continue
        placeholder = (_java_placeholder_return if bank_lang == "java" else _cpp_placeholder_return)(ret_type)
        stub_code = inject_placeholder_body(code, body_start, f"return {placeholder};")
        full_source = harness_generator.merge_sources(bank_lang, [stub_code, driver])
        ok, err = await _piston_compiles(bank_lang, full_source)
        if not ok:
            outcome[bank_lang] = f"compile-check-failed: {err[:300]}"
            continue
        if not dry_run:
            harness_generator._persist(q["id"], bank_lang, {"boilerplate": stub_code, "harness": driver})
        outcome[bank_lang] = "imported"

    return outcome


async def main(dataset_path: str, limit: int | None, dry_run: bool) -> None:
    sb = get_supabase()
    if not sb:
        print("Supabase is not configured.")
        return

    dataset = _load_dataset(dataset_path)
    by_slug = {p.get("problem_slug"): p for p in dataset if p.get("problem_slug")}
    print(f"Dataset: {len(dataset)} problems ({len(by_slug)} unique slugs)")

    all_questions = question_bank._all_questions()

    def is_stdio(qq: dict) -> bool:
        tests = qq.get("tests") or []
        return bool(tests and "stdin" in tests[0])

    technical = [q for q in all_questions if q.get("track") == "technical" and not is_stdio(q)]

    matched = []
    for q in technical:
        entry = by_slug.get(_slugify(q["title"]))
        if entry:
            matched.append((q, entry))
    if limit:
        matched = matched[:limit]

    print(f"{len(matched)} / {len(technical)} non-stdio technical questions matched by title")
    if dry_run:
        print("DRY RUN — no writes will be made.\n")

    fields = ("python", "node", "java", "cpp", "constraints", "examples")
    tally: dict[str, dict[str, int]] = {f: {} for f in fields}
    for i, (q, entry) in enumerate(matched, 1):
        result = await process_question(q, entry, dry_run)
        for f in fields:
            status = result[f] or "n/a"
            bucket = status.split(":")[0]
            tally[f][bucket] = tally[f].get(bucket, 0) + 1
        print(f"[{i}/{len(matched)}] {q['id']}: "
              f"py={result['python']} node={result['node']} java={result['java']} cpp={result['cpp']} "
              f"constraints={result['constraints']} examples={result['examples']}")

    print("\nSummary:")
    for f in fields:
        print(f"  {f}: {tally[f]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, default=os.path.join(os.path.dirname(__file__), "_neenza_dataset.json"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.dataset, args.limit, args.dry_run))
