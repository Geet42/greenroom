# Load test findings

## Run 1 — `health_baseline.js`, 2026-08-11

Local Docker Desktop backend (single container, 4 CPU / ~7.8 GB host — not
representative of the deployed Azure Container Apps sizing), ramping 0 → 20
→ 50 concurrent VUs over 3 minutes.

**Result: clean.** All thresholds passed:

| Metric | Result | Threshold |
|---|---|---|
| Requests | 17,226 total, 95.4 req/s | — |
| Error rate | 0.00% | <1% |
| `http_req_duration` p95 | 274ms | <500ms |
| `/api/health` p95 | 292ms | — |
| Max concurrent VUs | 50 | — |

No crashes, no dropped connections, no degraded responses at this load
level. This only exercises the lightweight unauthenticated path
(`/metrics`, `/api/health`) — it does **not** stress the actually expensive
path (Groq/Azure/Judge0 calls via the interview flow), which is where real
capacity limits are expected to show up first. That requires a real
Supabase auth token and hasn't been run yet (see `interview_flow.js` in
this directory — ready to run, just needs a token).

## Real bug found: this test itself hammered a third party

The first run of this script hit `/api/health` on every iteration. That
endpoint makes a **live, uncached external call** to Judge0's public API
(`ce.judge0.com`) on every single hit (`main.py`, pre-existing code). Over
the 3-minute run at ~50 concurrent VUs, that sent **~8,600 requests** to a
free, shared, third-party service with no SLA — not something a load test
(or, worse, a production liveness/readiness probe hitting the same
endpoint continuously) should be doing.

**Fixed, not just noted:**
- `main.py`: `/api/health`'s Judge0 reachability check is now cached for
  `_JUDGE0_HEALTH_CACHE_SECONDS` (30s) instead of re-checked on every hit.
  Covered by `tests/unit/test_main_health.py` (cache hit, cache expiry,
  failure path).
- `health_baseline.js`: repeated load now targets `/metrics` (pure
  in-process Prometheus state, no external dependency) instead of
  `/api/health`; the health endpoint is still sampled occasionally (every
  20th iteration) to prove it works under concurrent load without
  re-creating the same problem.

This is the one mitigation that came out of this round — deliberately not
adding speculative fixes (rate limiting, backpressure, etc.) for failure
modes this run didn't actually surface. The interview_flow.js run (once a
token is available) is what would surface those, if anything does.

## Next steps

- Run `interview_flow.js` with a real Supabase token to find the actual
  bottleneck (LLM call latency/cost under concurrency, Judge0 code-exec
  path, rate limiter behavior under genuine multi-user load).
- If/when run against the real Azure Container Apps deployment (not local
  Docker), re-run `health_baseline.js` there too — container CPU/memory
  limits and cold-start-from-zero (`minReplicas: 0`) behavior aren't
  reproducible locally.
