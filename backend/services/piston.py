import httpx
import os

# Primary: self-hosted Piston (docker run -p 2000:2000 ghcr.io/engineer-man/piston)
# Fallback: public instance (now requires auth — will fail gracefully)
PISTON_PRIMARY = os.environ.get("PISTON_URL", "http://localhost:2000/api/v2/execute")
PISTON_PUBLIC  = "https://emkc.org/api/v2/piston/execute"

_UNAVAILABLE = {
    "run": {
        "stdout": "",
        "stderr": (
            "Code execution is currently unavailable.\n"
            "The public sandbox requires authentication. "
            "To enable it, self-host Piston:\n"
            "  docker run -p 2000:2000 ghcr.io/engineer-man/piston\n"
            "Then set PISTON_URL=http://localhost:2000/api/v2/execute in backend/.env"
        ),
        "code": -1,
    }
}


async def run_code(language: str, version: str, source: str, stdin: str = "") -> dict:
    """Runs source code via Piston. Tries a local self-hosted instance first,
    then the public endpoint, and returns a friendly error dict if both fail."""
    payload = {
        "language": language,
        "version": version,
        "files": [{"content": source}],
        "stdin": stdin or "",
    }

    for url in [PISTON_PRIMARY, PISTON_PUBLIC]:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 401:
                    continue  # no auth — try next
                resp.raise_for_status()
                return resp.json()
        except (httpx.ConnectError, httpx.TimeoutException):
            continue  # instance not running — try next
        except httpx.HTTPStatusError:
            continue

    return _UNAVAILABLE
