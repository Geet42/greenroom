import httpx

PISTON_URL = "https://emkc.org/api/v2/piston/execute"


async def run_code(language: str, version: str, source: str, stdin: str = "") -> dict:
    """Runs source code in a sandboxed environment via the public Piston API.

    Piston (https://github.com/engineer-man/piston) is open source and the public
    instance is free to use. For higher reliability or rate limits, self-host Piston
    with Docker and point PISTON_URL at your own instance.
    """
    payload = {
        "language": language,
        "version": version,
        "files": [{"content": source}],
        "stdin": stdin or "",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(PISTON_URL, json=payload)
        response.raise_for_status()
        return response.json()
