import json
import random
from pathlib import Path

_PROBLEMS: list[dict] | None = None


def _load() -> list[dict]:
    global _PROBLEMS
    if _PROBLEMS is None:
        path = Path(__file__).parent.parent / "data" / "problems.json"
        with open(path, encoding="utf-8") as f:
            _PROBLEMS = json.load(f)
    return _PROBLEMS


def pick(difficulty: str | None = None) -> dict:
    problems = _load()
    pool = [p for p in problems if p["difficulty"] == difficulty] if difficulty else problems
    return random.choice(pool or problems)
