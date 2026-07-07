import os

from supabase import Client, create_client

_client: Client | None = None


def get_supabase() -> Client | None:
    """Returns a Supabase client using the service role key, or None if not configured.

    The service role key bypasses row-level security so the backend can write
    sessions/messages/evaluations on behalf of authenticated users. Keep this
    key on the server only -- never expose it to the frontend.
    """
    global _client
    if _client is not None:
        return _client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None

    _client = create_client(url, key)
    return _client
