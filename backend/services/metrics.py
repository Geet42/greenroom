"""
Prometheus metrics for LLM calls, guardrail activity, code execution, and
session lifecycle.

Kept separate from main.py (which owns the generic HTTP request/latency/error
metrics) so services can import this without importing the FastAPI app —
main.py already imports from routers, which import from services, so a
services -> main import would be circular.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from pathlib import Path

from prometheus_client import Counter, Histogram

# ── LLM provider calls ──────────────────────────────────────────────────────
# provider values in use: "groq", "azure_openai", "ollama_fallback"

LLM_PROVIDER_REQUESTS = Counter(
    "llm_provider_requests_total", "LLM calls by provider and outcome",
    ["provider", "status"],  # status: "success" | "error"
)
LLM_PROVIDER_LATENCY = Histogram(
    "llm_provider_latency_seconds", "LLM call latency in seconds, by provider",
    ["provider"],
)
# source values: "interviewer" (opening/next_question), "evaluation"
# (evaluate_session), "guardrail" (guardrail.py's own leak-detection judge)
LLM_FALLBACK_TOTAL = Counter(
    "llm_fallback_total", "Times the Ollama-cloud fallback was invoked, by call site",
    ["source"],
)
LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total", "LLM tokens consumed, by provider and direction",
    ["provider", "direction"],  # direction: "input" | "output"
)
LLM_COST_DOLLARS_TOTAL = Counter(
    "llm_cost_dollars_total", "Estimated LLM spend in USD, by provider",
    ["provider"],
)


@contextmanager
def track_llm_call(provider: str):
    """Wrap a single LLM invocation to record latency and success/error
    outcome. Re-raises whatever the wrapped call raises — this only observes,
    it never changes error-handling behavior."""
    start = time.monotonic()
    try:
        yield
    except Exception:
        LLM_PROVIDER_REQUESTS.labels(provider=provider, status="error").inc()
        raise
    else:
        LLM_PROVIDER_REQUESTS.labels(provider=provider, status="success").inc()
    finally:
        LLM_PROVIDER_LATENCY.labels(provider=provider).observe(time.monotonic() - start)


def record_fallback(source: str) -> None:
    LLM_FALLBACK_TOTAL.labels(source=source).inc()


_RATES_PATH = Path(__file__).resolve().parent.parent / "data" / "model_rates.json"
_rates_cache: dict | None = None


def _load_rates() -> dict:
    """Cached read of data/model_rates.json. Missing/unreadable file just
    means no cost math happens anywhere — never raises."""
    global _rates_cache
    if _rates_cache is None:
        try:
            _rates_cache = json.loads(_RATES_PATH.read_text())
        except Exception:
            _rates_cache = {}
    return _rates_cache


def record_usage(provider: str, model: str, usage_metadata: dict | None) -> None:
    """Records token counts, and — only when a verified $/1M rate exists for
    this exact model in data/model_rates.json — estimated cost. Tokens are
    still recorded even with no configured rate; cost is silently skipped,
    matching scripts/benchmark_models.py's own "never fabricate a number"
    policy rather than guessing a price."""
    if not usage_metadata:
        return
    input_tokens = usage_metadata.get("input_tokens") or 0
    output_tokens = usage_metadata.get("output_tokens") or 0
    if input_tokens:
        LLM_TOKENS_TOTAL.labels(provider=provider, direction="input").inc(input_tokens)
    if output_tokens:
        LLM_TOKENS_TOTAL.labels(provider=provider, direction="output").inc(output_tokens)

    rate = _load_rates().get(model)
    if not rate:
        return
    in_rate = rate.get("input_per_1m_usd")
    out_rate = rate.get("output_per_1m_usd")
    cost = 0.0
    if in_rate is not None:
        cost += (input_tokens / 1_000_000) * in_rate
    if out_rate is not None:
        cost += (output_tokens / 1_000_000) * out_rate
    if cost:
        LLM_COST_DOLLARS_TOTAL.labels(provider=provider).inc(cost)


# ── Guardrail ────────────────────────────────────────────────────────────────

GUARDRAIL_LEAK_DETECTED = Counter(
    "guardrail_leak_detected_total",
    "Times the guardrail caught and rewrote a bad interviewer response, by track and reason",
    ["track", "reason"],  # reason: "answer_leak" | "new_problem"
)

# ── Code execution (Judge0 / local subprocess fallback) ─────────────────────

CODE_EXECUTION_TOTAL = Counter(
    "code_execution_total", "Code execution attempts, by backend and outcome",
    ["backend", "status"],  # backend: "judge0_public" | "judge0_rapidapi" | "subprocess" | "unavailable"
)
CODE_EXECUTION_LATENCY = Histogram(
    "code_execution_latency_seconds", "Code execution total latency in seconds (all backends attempted)",
)

# ── Sessions ─────────────────────────────────────────────────────────────────

SESSIONS_STARTED = Counter(
    "sessions_started_total", "Interview sessions started, by track", ["track"],
)
SESSIONS_COMPLETED = Counter(
    "sessions_completed_total", "Interview sessions completed (evaluation generated), by track", ["track"],
)
EVALUATION_SCORE = Histogram(
    "evaluation_score", "Distribution of overall evaluation scores (0-10), by track",
    ["track"],
    buckets=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
)
