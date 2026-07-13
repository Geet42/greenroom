"""Unit tests for the Python/JS function-signature generation logic.

_verify_signature, _extract_kwarg_names, and _build_class_signature are all
pure and deterministic, so they're fully covered here. _generate_signature
(the LLM-inferred path, used only for the plain-function group where
parameter names are cosmetic) is exercised indirectly by the fail-open
contract: if verification rejects the output, callers fall back to the
generic starter code, same as an LLM/network failure.
"""
import pytest

from services.harness_generator import (
    _build_class_signature,
    _extract_kwarg_names,
    _verify_signature,
)

# ── Python ───────────────────────────────────────────────────────────────────

def test_python_valid_signature_passes():
    code = "def two_sum(nums, target):\n    pass\n"
    assert _verify_signature("python", code, "two_sum")


def test_python_wrong_function_name_fails():
    code = "def sum_two(nums, target):\n    pass\n"
    assert not _verify_signature("python", code, "two_sum")


def test_python_syntax_error_fails():
    code = "def two_sum(nums, target)\n    pass\n"  # missing colon
    assert not _verify_signature("python", code, "two_sum")


def test_python_method_inside_class_passes():
    code = "class LRUCache:\n    def __init__(self, capacity):\n        pass\n\n    def get(self, key):\n        pass\n"
    assert _verify_signature("python", code, "get")


def test_python_class_definition_matches_bare_class_name():
    # Stateful/constructor-based problems: function_name IS the class itself
    # (e.g. "LRUCache"), not one of its methods.
    code = (
        "class LRUCache:\n"
        "    def __init__(self, capacity):\n        pass\n\n"
        "    def get(self, key):\n        pass\n\n"
        "    def put(self, key, value):\n        pass\n"
    )
    assert _verify_signature("python", code, "LRUCache")


def test_node_class_definition_matches_bare_class_name():
    code = (
        "class LRUCache {\n"
        "  constructor(capacity) {}\n"
        "  get(key) {}\n"
        "  put(key, value) {}\n"
        "}\n"
    )
    assert _verify_signature("node", code, "LRUCache")


def test_python_empty_code_fails():
    assert not _verify_signature("python", "", "two_sum")


# ── JavaScript ("node") ──────────────────────────────────────────────────────

@pytest.mark.parametrize("code", [
    "function twoSum(nums, target) {\n  // TODO: implement\n}\n",
    "const twoSum = (nums, target) => {\n  // TODO: implement\n};\n",
    "const twoSum = function(nums, target) {\n  // TODO: implement\n};\n",
    "class Solution {\n  twoSum(nums, target) {\n    // TODO: implement\n  }\n}\n",
])
def test_node_valid_signature_passes(code):
    assert _verify_signature("node", code, "twoSum")


def test_node_wrong_function_name_fails():
    code = "function sumTwo(nums, target) {\n  // TODO: implement\n}\n"
    assert not _verify_signature("node", code, "twoSum")


def test_node_empty_code_fails():
    assert not _verify_signature("node", "", "twoSum")


def test_unsupported_language_fails():
    assert not _verify_signature("java", "class Solution {}", "twoSum")


# ── _extract_kwarg_names ─────────────────────────────────────────────────────

def test_extract_simple_kwargs():
    call = "Solution().kthCharacter(k=27)"
    assert _extract_kwarg_names(call, "kthCharacter") == ["k"]


def test_extract_multiple_kwargs_with_nested_list():
    call = "Solution().shortestDistanceAfterQueries(n=7, queries=[[0, 5], [1, 6], [2, 4]])"
    assert _extract_kwarg_names(call, "shortestDistanceAfterQueries") == ["n", "queries"]


def test_extract_kwargs_with_string_and_list_values():
    call = "Solution().finalPositionOfSnake(n=2, commands=['RIGHT', 'DOWN'])"
    assert _extract_kwarg_names(call, "finalPositionOfSnake") == ["n", "commands"]


def test_extract_kwargs_with_quoted_string_arg():
    call = "Solution().countKConstraintSubstrings(s='0101010101', k=5)"
    assert _extract_kwarg_names(call, "countKConstraintSubstrings") == ["s", "k"]


def test_extract_returns_none_for_positional_call():
    call = "two_sum([2, 7, 11, 15], 9)"
    assert _extract_kwarg_names(call, "two_sum") is None


def test_extract_returns_empty_list_for_no_args():
    call = "Solution().reset()"
    assert _extract_kwarg_names(call, "reset") == []


# ── _build_class_signature ───────────────────────────────────────────────────

def test_build_python_class_signature():
    code = _build_class_signature("python", "Solution", "kthCharacter", ["k"])
    assert _verify_signature("python", code, "kthCharacter")
    assert "class Solution:" in code
    assert "def kthCharacter(self, k):" in code


def test_build_node_class_signature():
    code = _build_class_signature("node", "Solution", "kthCharacter", ["k"])
    assert _verify_signature("node", code, "kthCharacter")
    assert "class Solution {" in code
