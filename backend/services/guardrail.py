"""
Guardrail layer — stops the interviewer from leaking the answer inside its own
question. Two concrete leaks we must never let through:

  technical       — stating the time/space complexity of the candidate's (or the
                     optimal) solution instead of asking the candidate to derive it.
  system-design   — declaring a specific architectural decision (which database,
                     caching layer, scaling pattern, etc.) instead of asking the
                     candidate to propose and defend one.

Defense in depth, three layers:
  1. Prompt hardening (see TRACK_PERSONAS in llm.py) — primary defense, cheapest.
  2. Regex detector — catches known patterns with near-zero latency.
  3. LLM judge — fires only when regex passes; fast YES/NO call (max_tokens=3)
     that catches novel phrasing the regex doesn't know about. Fails open (returns
     False) if Groq is unavailable, keeping the guardrail non-blocking.
"""

from __future__ import annotations

import os
import random
import re

_COMPLEXITY_PATTERNS = [
    re.compile(r"O\(\s*[a-zA-Z0-9log\s\*\+\^,]+\s*\)"),
    re.compile(r"\b(time|space)\s+complexity\s+(is|would be)\s+O\(", re.IGNORECASE),
    re.compile(r"\b(time|space)\s+complexity\s+(of (your|this|the)\s+\w+\s+is)\b", re.IGNORECASE),
    re.compile(r"\bruns?\s+in\s+(linear|constant|logarithmic|log[- ]?linear|quadratic|exponential|polynomial)\s+time\b", re.IGNORECASE),
    re.compile(r"\b(optimal|best|ideal)\s+(time|space)\s+complexity\b", re.IGNORECASE),
    re.compile(r"\byour solution (is|runs)\s+O\(", re.IGNORECASE),
]

_ARCHITECTURE_LEAK_PATTERNS = [
    re.compile(r"\byou should (use|implement|add|build|adopt)\b", re.IGNORECASE),
    re.compile(r"\bi('d| would) (recommend|suggest)\b", re.IGNORECASE),
    re.compile(r"\bthe (best|right|correct|optimal) (approach|architecture|design|way|solution) (is|would be) to\b", re.IGNORECASE),
    re.compile(r"\byou('ll| will) (need|want) to (use|implement|add)\b", re.IGNORECASE),
    re.compile(r"\bthe (key|main) (architectural\s+)?decision (is|here is|would be) to\b", re.IGNORECASE),
]

_LEAK_PATTERNS = {
    "technical": _COMPLEXITY_PATTERNS,
    "system-design": _ARCHITECTURE_LEAK_PATTERNS,
}

_FALLBACK_QUESTIONS = {
    "technical": [
        "Before we move on — how would you characterize the efficiency of your solution, and could it be improved?",
        "What trade-offs did you weigh when you picked this approach over the alternatives?",
        "Are there any edge cases your current solution might not handle correctly?",
        "Walk me through what happens to your solution as the input grows much larger.",
    ],
    "system-design": [
        "What are the main trade-offs of the approach you're describing?",
        "How would this design hold up if traffic increased by 10x overnight?",
        "What would you reconsider first if one of these components failed in production?",
        "Where do you expect this design to break down first, and why?",
    ],
}


def violates(text: str, track: str) -> bool:
    """Layer 2: fast regex check. True if `text` matches a known leak pattern."""
    patterns = _LEAK_PATTERNS.get(track)
    if not patterns:
        return False
    return any(p.search(text) for p in patterns)


def _llm_judge(text: str, track: str) -> bool:
    """Layer 3: LLM judge. Only called when regex passes. Fails open (returns False) on any error."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return False
    prompts = {
        "technical": (
            "Does the following interviewer message reveal the time or space complexity "
            "of any solution (e.g. O(n), O(1), linear time, constant space), or state "
            "that a solution is optimal without asking the candidate to verify? "
            "Reply YES or NO only.\n\n" + text
        ),
        "system-design": (
            "Does the following interviewer message recommend a specific architectural "
            "component (a named database, cache, queue, load balancer, or scaling strategy) "
            "to the candidate instead of asking them to propose and defend one? "
            "Reply YES or NO only.\n\n" + text
        ),
    }
    prompt = prompts.get(track)
    if not prompt:
        return False
    try:
        import httpx
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 3,
                "temperature": 0,
            },
            timeout=5,
        )
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"].strip().upper()
        return answer.startswith("YES")
    except Exception:
        return False


def sanitize(draft: str, track: str, regenerate_fn) -> str:
    """
    Returns a safe version of `draft` to show the candidate.

    draft:          the interviewer's first-pass question/response
    track:          interview track — only "technical" and "system-design" are checked
    regenerate_fn:  zero-arg callable that asks the LLM to rewrite `draft` without
                     leaking; may raise, in which case we just fall back

    Detection order: regex (Layer 2) first for speed; LLM judge (Layer 3) only
    when regex is clean, to catch novel phrasing at low cost.
    """
    layer1 = violates(draft, track)
    layer2 = not layer1 and _llm_judge(draft, track)

    if not layer1 and not layer2:
        return draft

    try:
        retry = regenerate_fn()
        if not violates(retry, track) and not _llm_judge(retry, track):
            return retry
    except Exception:
        pass

    return random.choice(_FALLBACK_QUESTIONS[track])
