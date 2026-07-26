import time
from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from services.supabase_client import get_supabase


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str | None = None


def get_current_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token")

    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is not configured")

    # A transient network error talking to Supabase looks identical to an
    # actually-invalid token if we don't retry — which would otherwise log a
    # candidate out (or fail an unrelated request, e.g. bulk delete) for a
    # blip that had nothing to do with their token.
    user = None
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            response = supabase.auth.get_user(token)
            user = response.user
            last_exc = None
            break
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                time.sleep(0.3)
    if last_exc is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from last_exc

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return AuthenticatedUser(id=str(user.id), email=user.email)
