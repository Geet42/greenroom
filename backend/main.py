import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from routers import analytics, interview, tts  # noqa: E402
from services.logger import log  # noqa: E402

app = FastAPI(title="Greenroom API", version="0.1.0")

origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    latency = round((time.monotonic() - start) * 1000)
    log.info(
        "http.request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=latency,
    )
    return response


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

    # Piston reachability (fire-and-forget, 3 s timeout)
    piston_url = os.environ.get("PISTON_URL", "http://localhost:2000/api/v2/execute")
    piston_base = piston_url.replace("/api/v2/execute", "")
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{piston_base}/api/v2/runtimes")
            checks["piston"] = "ok" if r.status_code == 200 else f"http_{r.status_code}"
    except Exception:
        checks["piston"] = "unreachable"

    # Groq key present (we can't call it cheaply; just assert it's configured)
    checks["groq"] = "configured" if os.environ.get("GROQ_API_KEY") else "unconfigured"

    overall = "ok" if all(v in ("ok", "configured") for v in checks.values()) else "degraded"
    log.info("health.check", overall=overall, **checks)
    return {"status": overall, "checks": checks}
