"""Unit test for scripts/benchmark_models.py's pure cost-math helper.
The rest of that script makes real network calls to LLM providers — like
every other one-off script in backend/scripts/, it has no test coverage
beyond what's testable without hitting a live API."""
import importlib.util
import os

import pytest

_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "benchmark_models.py")


@pytest.fixture(scope="module")
def benchmark_models():
    # Imported by path (not "from scripts import benchmark_models") since
    # scripts/ isn't a package and this module does network-touching imports
    # at call time only, not at import time — safe to load directly.
    spec = importlib.util.spec_from_file_location("benchmark_models", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cost_returns_na_when_model_not_in_rates(benchmark_models):
    assert benchmark_models._cost(None, 1000, 1000) == "n/a (model not in rates file)"


def test_cost_returns_na_when_rate_not_configured(benchmark_models):
    result = benchmark_models._cost({"input_per_1m_usd": None, "output_per_1m_usd": None}, 1000, 1000)
    assert result == "n/a (no rate configured)"


def test_cost_computes_when_rate_configured(benchmark_models):
    result = benchmark_models._cost(
        {"input_per_1m_usd": 1.0, "output_per_1m_usd": 2.0}, 1_000_000, 500_000,
    )
    assert result == "$2.000000"


def test_cost_partial_rate_still_na(benchmark_models):
    # Only input configured, output missing — don't compute a half-true cost.
    result = benchmark_models._cost({"input_per_1m_usd": 1.0, "output_per_1m_usd": None}, 1000, 1000)
    assert result == "n/a (no rate configured)"
