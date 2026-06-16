-- Run this in the Supabase SQL editor for your project.

create table if not exists sessions (
  id uuid primary key,
  user_id uuid references auth.users (id) on delete cascade,
  track text not null,
  role text,
  status text not null default 'active',
  overall_score int,
  summary text,
  created_at timestamptz not null default now(),
  ended_at timestamptz
);

create table if not exists messages (
  id bigint generated always as identity primary key,
  session_id uuid not null references sessions (id) on delete cascade,
  role text not null,
  content text not null,
  created_at timestamptz not null default now()
);

create table if not exists evaluations (
  id bigint generated always as identity primary key,
  session_id uuid not null references sessions (id) on delete cascade,
  category text not null,
  score int not null,
  feedback text
);

-- Row level security: users can only read their own sessions/messages/evaluations.
-- Writes are performed by the backend using the service role key, which bypasses RLS.

alter table sessions enable row level security;
alter table messages enable row level security;
alter table evaluations enable row level security;

create policy "Users can view their own sessions"
  on sessions for select
  using (auth.uid() = user_id);

create policy "Users can view messages from their sessions"
  on messages for select
  using (
    exists (
      select 1 from sessions
      where sessions.id = messages.session_id
        and sessions.user_id = auth.uid()
    )
  );

create policy "Users can view evaluations from their sessions"
  on evaluations for select
  using (
    exists (
      select 1 from sessions
      where sessions.id = evaluations.session_id
        and sessions.user_id = auth.uid()
    )
  );

create index if not exists idx_messages_session_id on messages (session_id);
create index if not exists idx_evaluations_session_id on evaluations (session_id);
create index if not exists idx_sessions_user_id on sessions (user_id);
