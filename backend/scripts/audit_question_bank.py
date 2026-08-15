"""
Read-only audit of the LIVE Supabase `questions` table (never the local JSON
seed, which is known to be stale — it has no `harnesses`/`signatures` caches
and is missing 137 technical rows that were bulk-imported straight into
Supabase on 2026-07-28/29).

Classifies every row as:
  OK              — passes services.question_schema validation, nothing to fix.
  REPAIRABLE      — missing content with a known, human-authored fix path
                     (see docs/... none yet — tracked per-question in the report).
  DELETE-CANDIDATE — a structurally required field is missing with no possible
                     source to regenerate it from (e.g. no prompt/title at all).
                     NEVER auto-deleted by this script — see
                     scripts/delete_confirmed_questions.py.

For technical call/expected questions, also classifies each of
{python, node, java, cpp} into: native / verified-present / confirmed-unsupported
/ never-attempted, by reading `languages`/`harnesses`/`signatures` directly —
this script never calls harness_generator.get_or_generate*, which would mutate
Supabase as a side effect of a cache miss. Audit stays provably read-only:
no .insert()/.update()/.upsert()/.delete() call appears anywhere in this file.

Usage:
    cd backend && .venv/Scripts/python scripts/audit_question_bank.py [--track technical|system-design|behavioral] [--out path.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from services import question_schema  # noqa: E402
from services.supabase_client import get_supabase  # noqa: E402

ALL_LANGUAGES = ("python", "node", "java", "cpp")
UNSUPPORTED_MARKER = {"unsupported": True}

MIN_CALL_EXPECTED_TESTS = question_schema.MIN_CALL_EXPECTED_TESTS
MIN_STDIO_TESTS = question_schema.MIN_STDIO_TESTS
EXPECTED_ELEMENTS_COUNT = question_schema.EXPECTED_ELEMENTS_COUNT


def _is_stdio(row: dict) -> bool:
    tests = row.get("tests") or []
    return bool(tests) and isinstance(tests[0], dict) and "stdin" in tests[0]


def _language_status(row: dict) -> dict[str, str]:
    """Per-language classification for a technical call/expected question.
    Only meaningful for call/expected — stdio questions are language-agnostic
    by construction (raw source is the whole program) so this isn't called
    for them."""
    native = set(row.get("languages") or [])
    harnesses = row.get("harnesses") or {}
    signatures = row.get("signatures") or {}
    status = {}
    for lang in ALL_LANGUAGES:
        if lang in native:
            status[lang] = "native"
            continue
        cache = harnesses if lang in ("java", "cpp") else signatures
        cached = cache.get(lang)
        if cached == UNSUPPORTED_MARKER:
            status[lang] = "confirmed-unsupported"
        elif cached:
            status[lang] = "verified-present"
        else:
            status[lang] = "never-attempted"
    return status


def classify_row(row: dict) -> dict:
    """Returns a per-question audit record: {id, track, bucket, reasons: [...],
    fixes: [...], language_status: {...} (technical only)}."""
    qid = row.get("id", "<no id>")
    track = row.get("track")
    model, issues = question_schema.classify_and_validate(row)

    record = {
        "id": qid,
        "track": track,
        "title": row.get("title"),
        "bucket": "OK",
        "reasons": [],
        "fixes": [],
        "language_status": None,
    }

    # Structurally irreplaceable fields — nothing can regenerate these from
    # nothing, so a failure here is a delete-candidate regardless of anything
    # else. Everything else with an issue is REPAIRABLE (or, for fields with
    # literally no generator today — e.g. this is where a future field
    # without a repair script would also land — still REPAIRABLE but flagged
    # as "no generator available").
    irreplaceable_fields = {"id", "track", "title", "prompt"}

    if issues:
        hit_irreplaceable = any(iss.field.split(".")[0] in irreplaceable_fields for iss in issues)
        for iss in issues:
            record["reasons"].append(f"{iss.field}: {iss.message}")
        record["bucket"] = "DELETE-CANDIDATE" if hit_irreplaceable else "REPAIRABLE"
        record["fixes"] = _infer_fixes(row, issues)

    if track == "technical" and not _is_stdio(row):
        lang_status = _language_status(row)
        record["language_status"] = lang_status
        # Missing (never-attempted) java/cpp/node/python coverage is its own
        # REPAIRABLE reason, independent of schema validation — a question can
        # pass schema validation (has >=4 tests, function_name, etc.) yet still
        # be missing java/cpp boilerplate entirely.
        never_attempted = [l for l, s in lang_status.items() if s == "never-attempted"]
        if never_attempted:
            if record["bucket"] == "OK":
                record["bucket"] = "REPAIRABLE"
            record["reasons"].append(f"never-attempted languages: {', '.join(never_attempted)}")
            for lang in never_attempted:
                record["fixes"].append(f"author {lang} boilerplate+harness, verify via sandbox, persist")
        # Java/C++-only unsupported is NEVER a delete reason on its own — a
        # question usable in Python/JS is still a usable question. Only
        # note it, don't escalate the bucket.
        unsupported = [l for l, s in lang_status.items() if s == "confirmed-unsupported"]
        if unsupported:
            record["reasons"].append(f"confirmed-unsupported (already exhausted attempts): {', '.join(unsupported)}")

    return record


def _infer_fixes(row: dict, issues: list) -> list[str]:
    fixes = []
    for iss in issues:
        top = iss.field.split(".")[0]
        if top == "tests":
            n = len(row.get("tests") or [])
            floor = MIN_STDIO_TESTS if _is_stdio(row) else MIN_CALL_EXPECTED_TESTS
            fixes.append(f"top up tests from {n} to >= {floor}, each verified against a correct reference solution")
        elif top == "function_name":
            fixes.append("author function_name (or confirm this is genuinely a stdio problem)")
        elif top in ("functional_requirements", "non_functional_requirements", "scaling_constraints", "out_of_scope"):
            fixes.append(f"author {top} (structured system-design brief)")
        elif top == "expected_components":
            fixes.append("author expected_components (used by the diagram evaluator)")
        elif top == "expected_elements":
            fixes.append("author exactly 4 STAR-shaped expected_elements")
        elif top in ("prompt", "title", "id", "track"):
            fixes.append(f"NO GENERATOR — {top} is irreplaceable")
        else:
            fixes.append(f"author {top}")
    return fixes


def run_audit(track_filter: str | None) -> dict:
    sb = get_supabase()
    if not sb:
        print("Supabase is not configured (check SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY).")
        sys.exit(1)

    resp = sb.table("questions").select("*").execute()
    rows = resp.data or []
    if track_filter:
        rows = [r for r in rows if r.get("track") == track_filter]

    records = [classify_row(r) for r in rows]

    counts_by_track = Counter(r["track"] for r in records)
    bucket_by_track = Counter((r["track"], r["bucket"]) for r in records)
    fix_type_counts = Counter(f for r in records for f in r["fixes"])

    ok = [r["id"] for r in records if r["bucket"] == "OK"]
    repairable = [r for r in records if r["bucket"] == "REPAIRABLE"]
    delete_candidates = [r for r in records if r["bucket"] == "DELETE-CANDIDATE"]

    report = {
        "total_rows": len(rows),
        "counts_by_track": dict(counts_by_track),
        "bucket_by_track": {f"{t}/{b}": c for (t, b), c in bucket_by_track.items()},
        "fix_type_counts": dict(fix_type_counts),
        "ok_count": len(ok),
        "ok_ids": ok,
        "repairable": repairable,
        "delete_candidates": delete_candidates,
    }
    return report


def print_summary(report: dict) -> None:
    print(f"\n{'='*70}\nQUESTION BANK AUDIT — {report['total_rows']} total rows\n{'='*70}")
    print(f"By track: {report['counts_by_track']}")
    print(f"OK: {report['ok_count']}")
    print(f"REPAIRABLE: {len(report['repairable'])}")
    print(f"DELETE-CANDIDATE: {len(report['delete_candidates'])}")
    print("\nBucket breakdown by track:")
    for k, v in sorted(report["bucket_by_track"].items()):
        print(f"  {k}: {v}")
    print("\nFix types needed (across all REPAIRABLE/DELETE-CANDIDATE rows):")
    for k, v in sorted(report["fix_type_counts"].items(), key=lambda kv: -kv[1]):
        print(f"  {v:4d}  {k}")
    if report["delete_candidates"]:
        print("\nDELETE-CANDIDATES (need your review — nothing deleted by this script):")
        for r in report["delete_candidates"]:
            print(f"  {r['id']} ({r['track']}): {r['reasons']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", choices=["technical", "system-design", "behavioral"], default=None)
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "_audit_report.json"))
    args = parser.parse_args()

    report = run_audit(args.track)
    print_summary(report)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report written to {args.out}")


if __name__ == "__main__":
    main()
