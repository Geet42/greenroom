"""Unit tests for services.test_runner harness generation."""
from services.test_runner import _node_harness, _pyliteral_to_js


def test_pyliteral_to_js_translates_booleans_and_none():
    assert _pyliteral_to_js("True") == "true"
    assert _pyliteral_to_js("False") == "false"
    assert _pyliteral_to_js("None") == "null"
    assert _pyliteral_to_js("canJump(nums=[2,3,1,1,4])") == "canJump(nums=[2,3,1,1,4])"


def test_pyliteral_to_js_does_not_mangle_substrings():
    # "Truesdale" contains "True" but isn't the literal — word boundary must hold.
    assert _pyliteral_to_js("Truesdale") == "Truesdale"


def test_node_harness_uses_js_literals_not_python_ones():
    cases = [{"call": "canJump([2,3,1,1,4])", "expected": "True"}]
    harness = _node_harness("function canJump(n){return true;}", cases)
    assert '"expected": "true"' in harness or '"expected":"true"' in harness
    assert "True" not in harness
