"""Speed infrastructure for the technical java/cpp/node backlog: infers
Java/C++ parameter & return types automatically from the bank's own existing
(verified) Python test literals, so authoring a repair only requires writing
the algorithm itself (java/cpp/node solution source) — not hand-declaring
every type tuple. Everything still runs through the same real sandbox
verification as the pilot batch (services.harness_verify /
services.piston) before persisting; type inference only removes toil, not
verification."""
import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import repair_question_bank as rqb  # noqa: E402
from import_neenza_boilerplate import (  # noqa: E402
    build_cpp_harness,
    build_java_harness,
    cpp_type_decl,
    java_type_decl,
    parse_call_args,
)

from services.supabase_client import get_supabase  # noqa: E402

_INT32_MAX = 2_147_483_647
_INT32_MIN = -2_147_483_648


def _infer_scalar(values: list) -> tuple:
    """values: all observed values for one argument/return position across
    every test case (so an empty-list-in-case-1 doesn't blind inference)."""
    flat = _flatten(values)
    if not flat:
        return ("prim", "int")  # nothing to go on — default, verification will catch a wrong guess
    if all(isinstance(v, bool) for v in flat):
        return ("prim", "boolean")
    if all(isinstance(v, str) for v in flat):
        return ("string",)
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in flat):
        if any(isinstance(v, float) for v in flat):
            return ("prim", "double")
        if any(v > _INT32_MAX or v < _INT32_MIN for v in flat):
            return ("prim", "long")
        return ("prim", "int")
    raise ValueError(f"cannot infer scalar type from mixed values: {flat[:5]}")


def _flatten(v):
    if isinstance(v, list):
        out = []
        for x in v:
            out.extend(_flatten(x))
        return out
    return [v]


def _depth(v) -> int:
    d = 0
    while isinstance(v, list):
        d += 1
        v = v[0] if v else None
    return d


def infer_java_type(values: list) -> tuple:
    """values: this argument's value across every test case (list of raw
    python values, some possibly lists/nested lists)."""
    max_depth = max((_depth(v) for v in values), default=0)
    if max_depth == 0:
        return _infer_scalar(values)
    scalar = _infer_scalar(values)
    t = scalar
    for _ in range(max_depth):
        t = ("array", t)
    return t


def _to_cpp_scalar(scalar: tuple) -> tuple:
    if scalar == ("prim", "long"):
        return ("prim", "long long")
    if scalar == ("prim", "boolean"):
        return ("prim", "bool")
    return scalar


def infer_cpp_type(values: list) -> tuple:
    max_depth = max((_depth(v) for v in values), default=0)
    scalar = _to_cpp_scalar(_infer_scalar(values))
    if max_depth == 0:
        return scalar
    t = scalar
    for _ in range(max_depth):
        t = ("vector", t)
    return t


def infer_signature(tests: list[dict]) -> tuple[list, list, tuple, tuple]:
    """Returns (java_params, cpp_params, java_ret, cpp_ret) — java_params/
    cpp_params are list[(type_tuple, arg_name)] as build_java_harness/
    build_cpp_harness expect. Argument names are positional (arg0, arg1, ...)
    since only the CALL matters at runtime, not the declared name."""
    parsed = [parse_call_args(t["call"]) for t in tests]
    if any(p is None for p in parsed):
        raise ValueError("could not parse call args for one or more tests")
    n_args = len(parsed[0])
    if any(len(p) != n_args for p in parsed):
        raise ValueError("inconsistent arg count across tests")

    java_params, cpp_params = [], []
    for i in range(n_args):
        values = [p[i] for p in parsed]
        java_params.append((infer_java_type(values), f"arg{i}"))
        cpp_params.append((infer_cpp_type(values), f"arg{i}"))

    expected_values = [ast.literal_eval(t["expected"]) for t in tests]
    java_ret = infer_java_type(expected_values)
    cpp_ret = infer_cpp_type(expected_values)
    return java_params, cpp_params, java_ret, cpp_ret


def _java_placeholder(t: tuple) -> str:
    if t[0] == "prim":
        return "false" if t[1] == "boolean" else "0"
    return "null"


def _cpp_placeholder(t: tuple) -> str:
    if t[0] == "prim":
        return "false" if t[1] == "bool" else "0"
    if t[0] == "string":
        return '""'
    return "{}"


def build_java_boilerplate(method_name: str, params: list, ret_type: tuple) -> str:
    args = ", ".join(f"{java_type_decl(pt)} {name}" for pt, name in params)
    return f"class Solution {{\n    public {java_type_decl(ret_type)} {method_name}({args}) {{\n        return {_java_placeholder(ret_type)};\n    }}\n}}\n"


def build_cpp_boilerplate(method_name: str, params: list, ret_type: tuple) -> str:
    args = ", ".join(f"{cpp_type_decl(pt)}& {name}" if pt[0] in ("vector", "string") else f"{cpp_type_decl(pt)} {name}" for pt, name in params)
    return f"class Solution {{\npublic:\n    {cpp_type_decl(ret_type)} {method_name}({args}) {{\n        return {_cpp_placeholder(ret_type)};\n    }}\n}};\n"


async def repair_technical_question(
    qid: str, method_name: str, java_solution: str, cpp_solution: str, node_solution: str,
) -> dict:
    """One-call repair: infers types from the bank's own tests, builds
    boilerplate+harness deterministically, verifies java/cpp/node against the
    REAL sandbox using the solutions I authored, persists only on pass.
    Returns {"java": (ok, err), "cpp": (ok, err), "node": (ok, err)}."""
    sb = get_supabase()
    tests = sb.table("questions").select("tests").eq("id", qid).execute().data[0]["tests"]

    java_params, cpp_params, java_ret, cpp_ret = infer_signature(tests)

    java_boiler = build_java_boilerplate(method_name, java_params, java_ret)
    cpp_boiler = build_cpp_boilerplate(method_name, cpp_params, cpp_ret)

    java_harness = build_java_harness(method_name, java_params, java_ret, tests)
    cpp_harness = build_cpp_harness(method_name, cpp_params, cpp_ret, tests)

    results = {}
    if java_harness is None:
        results["java"] = (False, "build_java_harness failed (unsupported literal shape)")
    else:
        results["java"] = await rqb.persist_and_verify_harness(qid, "java", java_boiler, java_harness, java_solution)

    if cpp_harness is None:
        results["cpp"] = (False, "build_cpp_harness failed (unsupported literal shape)")
    else:
        results["cpp"] = await rqb.persist_and_verify_harness(qid, "cpp", cpp_boiler, cpp_harness, cpp_solution)

    node_boiler = f"class Solution {{\n    {method_name}({', '.join(n for _, n in java_params)}) {{\n\n    }}\n}}\n"
    results["node"] = await rqb.persist_and_verify_node(qid, node_boiler, node_solution)

    return results
