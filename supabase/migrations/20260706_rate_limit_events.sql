-- Rate limiter events table — one row per API request, used for sliding-window
-- per-user rate limiting across all backend replicas.
-- Replaces the previous in-memory deque in services/rate_limit.py.

CREATE TABLE IF NOT EXISTS rate_limit_events (
    id      BIGSERIAL PRIMARY KEY,
    user_id UUID        NOT NULL,
    ts      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index used by both the count query (gte ts) and the prune delete (lt ts)
CREATE INDEX IF NOT EXISTS idx_rate_limit_events_user_ts
    ON rate_limit_events (user_id, ts);

-- RLS: backend uses the service-role key which bypasses RLS, but enable it
-- defensively so the anon key can never touch this table.
ALTER TABLE rate_limit_events ENABLE ROW LEVEL SECURITY;

-- No SELECT/INSERT policy for anon or authenticated role — only service role
-- (which bypasses RLS) can write here.
