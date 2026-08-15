-- Draft only — NOT applied automatically. Adds CHECK constraints to the
-- questions table mirroring the existing sessions_track_check pattern
-- (see supabase/schema.sql). Confirmed against live data before drafting:
-- track values in use = {behavioral, technical, system-design},
-- difficulty values in use = {easy, medium, hard} — zero violating rows.
--
-- Apply only with explicit user sign-off (schema migration on a shared DB).

alter table questions drop constraint if exists questions_track_check;
alter table questions add constraint questions_track_check
  check (track in ('behavioral', 'technical', 'system-design'));

alter table questions drop constraint if exists questions_difficulty_check;
alter table questions add constraint questions_difficulty_check
  check (difficulty is null or difficulty in ('easy', 'medium', 'hard'));
