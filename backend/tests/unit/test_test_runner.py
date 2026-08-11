"""Unit tests for services.test_runner harness generation."""
import threading
import time
from unittest.mock import patch

from services import test_runner
from services.test_runner import _node_harness, _pyliteral_to_js, get_or_generate_cases


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


def test_get_or_generate_cases_dedupes_concurrent_calls_for_same_problem():
    """Two "Run Tests" clicks (or two tabs) hitting the same not-yet-cached
    ad-hoc problem before the first LLM call returns must not each trigger
    their own generation — see services.singleflight."""
    problem = "unique-test-problem-for-dedup-test"
    test_runner._CASES_CACHE.pop(problem, None)
    call_count = {"n": 0}

    def fake_generate_cases(_problem):
        call_count["n"] += 1
        time.sleep(0.05)
        return [{"call": "f(1)", "expected": "1"}]

    results = []
    results_lock = threading.Lock()

    def worker():
        result = get_or_generate_cases(problem)
        with results_lock:
            results.append(result)

    with patch.object(test_runner, "_generate_cases", side_effect=fake_generate_cases):
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert call_count["n"] == 1
    assert all(r == [{"call": "f(1)", "expected": "1"}] for r in results)
