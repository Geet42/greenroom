"""
Filters Leetcode.csv into backend/data/problems.json.

Keeps: non-premium, Algorithm, Easy or Medium, classic interview topics,
       likes >= 1000 (well-known problems the LLM can describe accurately).
"""

import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).parent.parent

INTERVIEW_TOPICS = {
    "Array", "String", "Hash Table", "Dynamic Programming",
    "Greedy", "Binary Search", "Depth-First Search", "Breadth-First Search",
    "Tree", "Binary Tree", "Two Pointers", "Sliding Window",
    "Stack", "Linked List", "Graph", "Backtracking",
    "Heap (Priority Queue)", "Sorting", "Recursion",
    "Matrix", "Bit Manipulation", "Prefix Sum", "Union Find", "Trie",
}

def parse_topics(raw: str) -> list[str]:
    return [t.strip() for t in raw.split(",") if t.strip()]

def is_interview_problem(row: dict) -> bool:
    if row["Premium Only"] != "False":
        return False
    if row["Category"] != "Algorithms":
        return False
    if row["Difficulty"] not in ("Easy", "Medium"):
        return False
    try:
        if int(row["Likes"]) < 1000:
            return False
    except (ValueError, KeyError):
        return False
    topics = parse_topics(row["Topics"])
    return any(t in INTERVIEW_TOPICS for t in topics)

def build():
    csv_path = ROOT / "Leetcode.csv"
    out_path = ROOT / "backend" / "data" / "problems.json"

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    filtered = [r for r in rows if is_interview_problem(r)]

    problems = []
    for r in filtered:
        topics = parse_topics(r["Topics"])
        interview_topics = [t for t in topics if t in INTERVIEW_TOPICS]
        problems.append({
            "id":           int(r["ID"]),
            "title":        r["Title"].strip(),
            "difficulty":   r["Difficulty"],
            "topics":       interview_topics,
            "acceptance":   float(r["Acceptance Rate (%)"] or 0),
            "link":         r["Link"].strip(),
        })

    # Sort by ID so the file is deterministic
    problems.sort(key=lambda p: p["id"])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(problems, f, indent=2)

    easy   = sum(1 for p in problems if p["difficulty"] == "Easy")
    medium = sum(1 for p in problems if p["difficulty"] == "Medium")
    print(f"Saved {len(problems)} problems → {out_path}")
    print(f"  Easy: {easy}  Medium: {medium}")

    # Show 5 random samples
    print("\nSample problems:")
    for p in random.sample(problems, min(5, len(problems))):
        print(f"  [{p['difficulty']:6}] {p['id']:4d}. {p['title']}  |  {', '.join(p['topics'][:3])}")

if __name__ == "__main__":
    build()
