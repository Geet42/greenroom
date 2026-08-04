-- Fix data-integrity gaps: analytics_events.session_id and
-- rate_limit_events.user_id were created with no foreign keys, unlike every
-- other user/session-owned table in schema.sql. In practice this means:
--   1. analytics_events rows outlive the session they describe forever.
--      routers/interview.py::delete_session explicitly deletes evaluations
--      and messages but has no way to clean up analytics_events, since there
--      is no FK to cascade from.
--   2. rate_limit_events has no link back to auth.users at all.

-- Drop any analytics_events rows whose session no longer exists so the new
-- FK constraint can be added without failing on pre-existing orphans.
delete from analytics_events
where session_id is not null
  and not exists (select 1 from sessions where sessions.id = analytics_events.session_id);

alter table analytics_events drop constraint if exists analytics_events_session_id_fkey;
alter table analytics_events add constraint analytics_events_session_id_fkey
  foreign key (session_id) references sessions (id) on delete cascade;

create index if not exists idx_analytics_events_session_id on analytics_events (session_id);

-- Same treatment for rate_limit_events.user_id -> auth.users.
delete from rate_limit_events
where not exists (select 1 from auth.users where auth.users.id = rate_limit_events.user_id);

alter table rate_limit_events drop constraint if exists rate_limit_events_user_id_fkey;
alter table rate_limit_events add constraint rate_limit_events_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;
