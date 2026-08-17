"""
Benchmarks latency, token usage, and (where a rate is configured) $ cost for
each LLM this backend actually calls, across a handful of representative
prompt shapes sized like the real call sites (services/llm.py):

  - "opening"  — short system + role, like opening_message()
  - "followup" — a multi-turn conversation history, like next_question()
  - "eval"     — a full transcript + evaluation instructions, like
                 evaluate_session() (Azure-only in production)

These are representative-SIZED proxies, not the literal production prompt
templates (which need session-specific args) — good for relative
comparison and rough cost estimation, not an exact production-cost audit.

Cost math only runs for models with a rate configured in
data/model_rates.json — nothing is guessed. Fill those in with your actual
plan's pricing before trusting the $ column.

Usage:
    cd backend && .venv/Scripts/python scripts/benchmark_models.py [--iterations N]

Only benchmarks providers that are actually configured (checked via the
same env vars services/llm.py uses) — a provider with no key just gets
skipped with a note, not a fabricated result.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import httpx  # noqa: E402
from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

from services import llm as llm_service  # noqa: E402

_RATES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "model_rates.json")

_SCENARIOS = {
    "opening": {
        "system": "You are a friendly technical interviewer opening a mock interview for a "
                  "Senior Backend Engineer role. Greet the candidate and ask them to introduce themselves.",
        "user": "Begin the interview.",
        "max_tokens": 150,
    },
    "followup": {
        "system": "You are conducting a technical interview. The candidate is solving a coding "
                  "problem about finding the longest substring without repeating characters. Ask a "
                  "natural follow-up question based on their last answer, probing their understanding "
                  "of time complexity and edge cases. Do not reveal the answer.",
        "user": (
            "Candidate: I used a sliding window with a hash set to track characters currently in the "
            "window. When I see a duplicate, I shrink the window from the left until it's removed. "
            "I think this runs in O(n) time since each character is added and removed at most once."
        ),
        "max_tokens": 200,
    },
    "eval": {
        "system": "You are scoring a completed technical interview transcript. Return a JSON object "
                  "with overall_score (0-10), a 2-3 sentence summary, and per-category feedback for "
                  "problem-solving, communication, and code quality.",
        "user": (
            "Transcript:\n"
            "Interviewer: Tell me about your approach.\n"
            "Candidate: I'd use a sliding window with a hash set, giving O(n) time and O(min(n,26)) space "
            "for the visible ASCII range.\n"
            "Interviewer: What about edge cases?\n"
            "Candidate: Empty string returns 0, and a single repeated character returns 1.\n"
            "Interviewer: How would this scale to a streaming input you can't hold in memory?\n"
            "Candidate: I'd bound the window by a fixed byte budget and evict the oldest entries once "
            "over budget, trading exactness for a bounded memory footprint.\n"
        ) * 3,  # pad toward a realistic multi-turn transcript length
        "max_tokens": 400,
    },
}


def _rates() -> dict:
    with open(_RATES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _cost(model_rates: dict | None, input_tokens: int, output_tokens: int) -> str:
    if not model_rates:
        return "n/a (model not in rates file)"
    in_rate = model_rates.get("input_per_1m_usd")
    out_rate = model_rates.get("output_per_1m_usd")
    if in_rate is None or out_rate is None:
        return "n/a (no rate configured)"
    cost = (input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate
    return f"${cost:.6f}"


def _bench_groq(scenario_name: str, scenario: dict) -> dict | None:
    if not llm_service.GROQ_API_KEY:
        return None
    llm = llm_service._make_llm(temperature=0.3, max_tokens=scenario["max_tokens"])
    start = time.monotonic()
    result = llm.invoke([SystemMessage(content=scenario["system"]), HumanMessage(content=scenario["user"])])
    latency_ms = (time.monotonic() - start) * 1000
    usage = result.usage_metadata or {}
    return {
        "provider": "groq", "model": llm_service.GROQ_MODEL, "scenario": scenario_name,
        "latency_ms": round(latency_ms), "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
    }


def _bench_azure(scenario_name: str, scenario: dict) -> dict | None:
    if not llm_service.AZURE_OPENAI_API_KEY or not llm_service.AZURE_OPENAI_ENDPOINT:
        return None
    llm = llm_service._make_azure_llm(max_tokens=scenario["max_tokens"])
    start = time.monotonic()
    result = llm.invoke([SystemMessage(content=scenario["system"]), HumanMessage(content=scenario["user"])])
    latency_ms = (time.monotonic() - start) * 1000
    usage = result.usage_metadata or {}
    return {
        "provider": "azure-openai", "model": llm_service.AZURE_OPENAI_DEPLOYMENT, "scenario": scenario_name,
        "latency_ms": round(latency_ms), "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
    }


def _bench_fallback(scenario_name: str, scenario: dict) -> dict | None:
    if not llm_service.FALLBACK_BASE_URL or not llm_service.FALLBACK_API_KEY:
        return None
    payload = {
        "model": llm_service.FALLBACK_MODEL,
        "messages": [
            {"role": "system", "content": scenario["system"]},
            {"role": "user", "content": scenario["user"]},
        ],
        "temperature": 0.3,
        "max_tokens": scenario["max_tokens"],
    }
    start = time.monotonic()
    resp = httpx.post(
        f"{llm_service.FALLBACK_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {llm_service.FALLBACK_API_KEY}", "Content-Type": "application/json"},
        json=payload, timeout=60, follow_redirects=True,
    )
    latency_ms = (time.monotonic() - start) * 1000
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usage") or {}
    return {
        "provider": "ollama-cloud", "model": llm_service.FALLBACK_MODEL, "scenario": scenario_name,
        "latency_ms": round(latency_ms), "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
    }


_BENCHMARKS = [_bench_groq, _bench_fallback, _bench_azure]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=1, help="Repeat each scenario N times and average latency")
    args = ap.parse_args()

    rates = _rates()
    rows = []
    skipped_providers = set()

    for scenario_name, scenario in _SCENARIOS.items():
        for bench_fn in _BENCHMARKS:
            latencies = []
            last_result = None
            for _ in range(args.iterations):
                try:
                    result = bench_fn(scenario_name, scenario)
                except Exception as exc:
                    print(f"  ERROR {bench_fn.__name__} / {scenario_name}: {exc}")
                    result = None
                    break
                if result is None:
                    break
                latencies.append(result["latency_ms"])
                last_result = result
            if last_result is None:
                continue
            avg_latency = round(sum(latencies) / len(latencies))
            model_rates = rates.get(last_result["model"])
            rows.append({
                **last_result,
                "latency_ms": avg_latency,
                "cost_estimate": _cost(model_rates, last_result["input_tokens"], last_result["output_tokens"]),
            })

    for name, key_check in [
        ("groq", llm_service.GROQ_API_KEY), ("ollama-cloud", llm_service.FALLBACK_API_KEY),
        ("azure-openai", llm_service.AZURE_OPENAI_API_KEY),
    ]:
        if not key_check:
            skipped_providers.add(name)

    print(f"\n{'Provider':<14} {'Model':<26} {'Scenario':<10} {'Latency(ms)':>11} {'In tok':>7} {'Out tok':>8} {'Cost est.':>20}")
    print("-" * 100)
    for r in rows:
        print(f"{r['provider']:<14} {r['model']:<26} {r['scenario']:<10} {r['latency_ms']:>11} "
              f"{r['input_tokens']:>7} {r['output_tokens']:>8} {r['cost_estimate']:>20}")

    if skipped_providers:
        print(f"\nSkipped (not configured): {', '.join(sorted(skipped_providers))}")
    unrated = {r["model"] for r in rows if "no rate configured" in r["cost_estimate"]}
    if unrated:
        print(f"No $ rate configured for: {', '.join(sorted(unrated))} — fill in data/model_rates.json")


if __name__ == "__main__":
    main()
