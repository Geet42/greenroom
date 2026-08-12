"""Unit tests for GET /api/health's Judge0 reachability caching.

Found via infra/loadtest/health_baseline.js: a 3-minute local load test at
~50 concurrent req/s sent ~8,600 requests to Judge0's public API (no SLA,
not ours to hammer) purely from health checks, since the endpoint made a
fresh external call on every single hit. main.py doesn't import cleanly
without real-looking env vars (it calls load_dotenv() at import time), so
this stubs the minimum required before import — same reason no other test
file imports main directly.
"""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def main_module(monkeypatch):
    # main.py registers Prometheus collectors at module import time —
    # re-importing (e.g. via importlib.reload) would try to register them a
    # second time into the same global CollectorRegistry and blow up with
    # "Duplicated timeseries". Import ONCE (Python caches it in sys.modules
    # after that), just reset the cache dict this test cares about.
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    import main as main_mod
    main_mod._judge0_health_cache["status"] = None
    main_mod._judge0_health_cache["checked_at"] = 0.0
    return main_mod


class _FakeResponse:
    status_code = 200


class _FakeAsyncClient:
    def __init__(self, call_count):
        self._call_count = call_count

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, _url):
        self._call_count["n"] += 1
        return _FakeResponse()


@pytest.mark.asyncio
async def test_health_caches_judge0_check_across_calls(main_module):
    call_count = {"n": 0}

    with patch("httpx.AsyncClient", return_value=_FakeAsyncClient(call_count)), \
         patch("services.supabase_client.get_supabase", return_value=MagicMock()):
        first = await main_module.health()
        second = await main_module.health()

    assert call_count["n"] == 1  # second call served from cache, no new HTTP request
    assert first["checks"]["judge0"] == "ok"
    assert second["checks"]["judge0"] == "ok"


@pytest.mark.asyncio
async def test_health_rechecks_judge0_after_cache_expires(main_module):
    call_count = {"n": 0}

    with patch("httpx.AsyncClient", return_value=_FakeAsyncClient(call_count)), \
         patch("services.supabase_client.get_supabase", return_value=MagicMock()):
        await main_module.health()
        # Simulate the cache window having elapsed instead of sleeping in a test.
        main_module._judge0_health_cache["checked_at"] -= main_module._JUDGE0_HEALTH_CACHE_SECONDS + 1
        await main_module.health()

    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_health_reports_unreachable_on_judge0_error(main_module):
    class _FailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, _url):
            raise ConnectionError("boom")

    with patch("httpx.AsyncClient", return_value=_FailingClient()), \
         patch("services.supabase_client.get_supabase", return_value=MagicMock()):
        result = await main_module.health()

    assert result["checks"]["judge0"] == "unreachable"
    assert result["status"] == "degraded"
