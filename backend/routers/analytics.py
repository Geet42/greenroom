from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from auth import AuthenticatedUser, get_current_user
from models import AnalyticsEventRequest
from services import metrics, question_bank
from services.persistence import persist_analytics_event
from services.rate_limit import check_rate_limit
from services.supabase_client import get_supabase

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Mirrors the frontend's route table (frontend/src/App.jsx). Anything outside
# this set is reported as "other" so a page_view event can never blow up
# page_view_total's label cardinality.
_KNOWN_PAGE_PATHS = {
    "/", "/auth/callback", "/login", "/signup",
    "/dashboard", "/interview", "/results/:sessionId", "/telemetry",
}


def _merge_plural_dupes(topics: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    """The question bank has a few genuine singular/plural duplicate topic
    tags (e.g. "array" and "arrays" as separate values on different rows —
    same for "stack"/"stacks", "string"/"strings") that otherwise show up as
    confusingly-near-identical duplicate rows in the dashboard's topic list.
    Only merges a plural into its singular when BOTH exist in this same
    dict — never blindly strips a trailing "s", which would incorrectly
    rewrite legitimately plural-only topics (e.g. "two-pointers",
    "bitmasks") that have no singular counterpart."""
    merged = dict(topics)
    for topic in list(merged):
        if not topic.endswith("s"):
            continue
        singular = topic[:-1]
        if singular in merged and singular != topic:
            for k, v in merged.pop(topic).items():
                merged[singular][k] += v
    return merged


@router.post("/event", status_code=202)
async def track_event(
    req: AnalyticsEventRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
):
    await run_in_threadpool(check_rate_limit, user.id, max_per_minute=60)
    background_tasks.add_task(
        persist_analytics_event, user.id, req.session_id, req.event, req.properties,
    )
    if req.event == "page_view":
        path = (req.properties or {}).get("path")
        metrics.PAGE_VIEW_TOTAL.labels(path=path if path in _KNOWN_PAGE_PATHS else "other").inc()
    return {"status": "accepted"}


@router.get("/stats")
async def get_stats(user: AuthenticatedUser = Depends(get_current_user)):
    await run_in_threadpool(check_rate_limit, user.id)
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        sessions = sb.table("sessions").select(
            "id,track,status,overall_score,created_at,ended_at,assigned_question_id"
        ).eq("user_id", user.id).execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"sessions query failed: {exc}") from exc

    try:
        events = sb.table("analytics_events").select(
            "event,properties,created_at"
        ).eq("user_id", user.id).execute().data or []
    except Exception:
        events = []

    completed = [s for s in sessions if s.get("status") == "completed"]
    scores = [s["overall_score"] for s in completed if s.get("overall_score") is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    tracks = ["behavioral", "technical", "system-design"]
    sessions_by_track = {}
    avg_score_by_track = {}
    completion_by_track = {}
    for track in tracks:
        ts = [s for s in sessions if s.get("track") == track]
        tc = [s for s in ts if s.get("status") == "completed"]
        ts_scores = [s["overall_score"] for s in tc if s.get("overall_score") is not None]
        sessions_by_track[track] = len(ts)
        avg_score_by_track[track] = round(sum(ts_scores) / len(ts_scores), 1) if ts_scores else 0
        completion_by_track[track] = round(len(tc) / len(ts) * 100) if ts else 0

    now_utc = datetime.now(timezone.utc)
    daily: dict[str, int] = {}
    for i in range(13, -1, -1):
        day = (now_utc - timedelta(days=i)).strftime("%Y-%m-%d")
        daily[day] = 0
    for s in sessions:
        if s.get("created_at"):
            day = s["created_at"][:10]
            if day in daily:
                daily[day] += 1

    lang_counts: dict[str, int] = {}
    for e in events:
        if e.get("event") == "code_run" and e.get("properties"):
            lang = e["properties"].get("language", "unknown")
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    # Score distribution buckets: 0-2, 3-4, 5-6, 7-8, 9-10
    buckets = {"0–2": 0, "3–4": 0, "5–6": 0, "7–8": 0, "9–10": 0}
    for sc in scores:
        if sc <= 2:
            buckets["0–2"] += 1
        elif sc <= 4:
            buckets["3–4"] += 1
        elif sc <= 6:
            buckets["5–6"] += 1
        elif sc <= 8:
            buckets["7–8"] += 1
        else:
            buckets["9–10"] += 1

    durations_min = []
    for s in completed:
        if not (s.get("created_at") and s.get("ended_at")):
            continue
        try:
            start = datetime.fromisoformat(s["created_at"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(s["ended_at"].replace("Z", "+00:00"))
        except ValueError:
            continue
        minutes = (end - start).total_seconds() / 60
        if minutes > 0:
            durations_min.append(minutes)
    avg_duration_minutes = round(sum(durations_min) / len(durations_min), 1) if durations_min else 0

    # Difficulty/topic mix of the questions actually assigned this user —
    # technical and system-design only (behavioral prompts aren't drawn from
    # a difficulty-tagged bank the same way). Looked up from the in-process
    # question bank cache (services.question_bank) rather than a second
    # Supabase round trip, since it's already loaded for the interview flow.
    question_tracks = ("technical", "system-design")
    difficulty_by_track = {t: {"easy": 0, "medium": 0, "hard": 0} for t in question_tracks}
    topic_counts: dict[str, dict[str, dict[str, int]]] = {t: {} for t in question_tracks}
    for s in sessions:
        track = s.get("track")
        qid = s.get("assigned_question_id")
        if track not in difficulty_by_track or not qid:
            continue
        q = question_bank.get_question(qid)
        if not q:
            continue
        difficulty = q.get("difficulty") or "medium"
        if difficulty not in difficulty_by_track[track]:
            difficulty = "medium"
        difficulty_by_track[track][difficulty] += 1
        topic = q.get("topic") or "general"
        bucket = topic_counts[track].setdefault(topic, {"easy": 0, "medium": 0, "hard": 0})
        bucket[difficulty] += 1

    topic_breakdown = {}
    for track, topics in topic_counts.items():
        rows = [{"topic": topic, "total": sum(c.values()), **c} for topic, c in _merge_plural_dupes(topics).items()]
        rows.sort(key=lambda r: r["total"], reverse=True)
        topic_breakdown[track] = rows[:8]

    return {
        "total_sessions": len(sessions),
        "completed_sessions": len(completed),
        "avg_score": avg_score,
        "avg_duration_minutes": avg_duration_minutes,
        "sessions_by_track": sessions_by_track,
        "avg_score_by_track": avg_score_by_track,
        "completion_rate_by_track": completion_by_track,
        "sessions_last_14_days": daily,
        "language_usage": lang_counts,
        "score_distribution": buckets,
        "difficulty_by_track": difficulty_by_track,
        "topic_breakdown": topic_breakdown,
    }
