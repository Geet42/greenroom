import base64
import json
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

load_dotenv()

from routers import analytics, interview, tts  # noqa: E402
from services.logger import log  # noqa: E402
from services.persistence import persist_analytics_event  # noqa: E402

app = FastAPI(title="Greenroom API", version="0.1.0")

# Labeled by the matched route TEMPLATE (e.g. "/api/interview/{session_id}/message"),
# never the raw path — raw paths carry session/user ids, which would blow up
# Prometheus's label cardinality with one series per request.
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency in seconds", ["method", "path"],
)
REQUEST_ERRORS = Counter(
    "http_request_errors_total", "Unhandled exceptions raised while handling a request", ["method", "path"],
)

origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _unverified_user_id(request: Request) -> str | None:
    """Best-effort JWT `sub` extraction for error-log/analytics tagging only —
    signature is NOT verified, so this must never be used for authorization
    (routes still authenticate via auth.get_current_user)."""
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload.get("sub")
    except Exception:
        return None


def _route_template(request: Request) -> str:
    """The matched route's path TEMPLATE (e.g. "/api/interview/{session_id}"),
    set on request.scope once routing completes — falls back to the raw path
    (typically only reached for 404s, where no route matched)."""
    route = request.scope.get("route")
    return route.path if route else request.url.path


@app.middleware("http")
async def request_logger(request: Request, call_next):
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception as exc:
        latency_s = time.monotonic() - start
        path = _route_template(request)
        REQUEST_ERRORS.labels(method=request.method, path=path).inc()
        REQUEST_LATENCY.labels(method=request.method, path=path).observe(latency_s)
        log.error(
            "http.request_failed",
            method=request.method,
            path=request.url.path,
            latency_ms=round(latency_s * 1000),
            error=str(exc),
        )
        # Persisted (not just logged to stdout) so failures survive past the
        # container's log retention window and are queryable per-user — only
        # possible when the request carried a token, since analytics_events
        # requires a user_id.
        user_id = _unverified_user_id(request)
        if user_id:
            try:
                persist_analytics_event(
                    user_id, None, "backend_error",
                    {"path": request.url.path, "method": request.method, "error": str(exc)[:500]},
                )
            except Exception:
                pass
        raise
    latency_s = time.monotonic() - start
    path = _route_template(request)
    REQUEST_COUNT.labels(method=request.method, path=path, status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, path=path).observe(latency_s)
    log.info(
        "http.request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=round(latency_s * 1000),
    )
    return response


@app.get("/metrics")
async def metrics():
    """Prometheus scrape target — unauthenticated by convention (scraped
    in-cluster only; not linked from any public nav)."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(interview.router, prefix="/api")
app.include_router(tts.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")


@app.get("/api/health")
async def health():
    """
    Liveness + shallow readiness probe.
    Returns 200 with component status. Azure Container Apps health probes
    hit this endpoint — it must never block for more than a few seconds.
    """
    import httpx

    from services.supabase_client import get_supabase

    checks: dict[str, str] = {}

    # Supabase reachability (lightweight — just checks the client is configured)
    sb = get_supabase()
    checks["supabase"] = "ok" if sb else "unconfigured"

    # Judge0 reachability (fire-and-forget, 3 s timeout). Checks the public
    # instance only — RapidAPI's key-gated instance isn't cheap to probe
    # without burning a quota'd request, and the code path already falls
    # back to local subprocess execution if both are down.
    judge0_url = os.environ.get("JUDGE0_PUBLIC_URL", "https://ce.judge0.com")
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{judge0_url}/languages")
            checks["judge0"] = "ok" if r.status_code == 200 else f"http_{r.status_code}"
    except Exception:
        checks["judge0"] = "unreachable"

    # Groq key present (we can't call it cheaply; just assert it's configured)
    checks["groq"] = "configured" if os.environ.get("GROQ_API_KEY") else "unconfigured"

    overall = "ok" if all(v in ("ok", "configured") for v in checks.values()) else "degraded"
    log.info("health.check", overall=overall, **checks)
    return {"status": overall, "checks": checks}
