-- Minimal usage/click analytics: one row per tracked frontend/backend event,
-- used to spot real user counts, activity, usage spikes, and drop-off points.

CREATE TABLE IF NOT EXISTS analytics_events (
    id         BIGSERIAL PRIMARY KEY,
    user_id    UUID        NOT NULL,
    session_id UUID,
    event      TEXT        NOT NULL,
    properties JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Supports both "activity over time" and "activity per user" queries.
CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events (created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id    ON analytics_events (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_events_event      ON analytics_events (event, created_at);

-- RLS: backend uses the service-role key which bypasses RLS, but enable it
-- defensively so the anon key can never touch this table.
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;

-- No SELECT/INSERT policy for anon or authenticated role — only service role
-- (which bypasses RLS) can write here.
