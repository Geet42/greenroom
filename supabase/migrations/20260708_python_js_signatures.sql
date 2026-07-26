-- Lazily-generated Python/JS ("node") function-signature boilerplate, keyed by
-- language: {"python": "def two_sum(nums, target):\n    pass", "node": "..."}.
-- Mirrors the existing `harnesses` column (Java/C++), but there is no harness
-- here — the test runner already executes candidate code directly for these
-- languages, so this is purely editor scaffolding.
-- See services/harness_generator.py.
ALTER TABLE questions
  ADD COLUMN IF NOT EXISTS signatures JSONB;

-- All four ADD COLUMN IF NOT EXISTS below were previously only in the
-- untracked, ad-hoc supabase/migration_questions_bank.sql (not this
-- migrations/ folder), so there was no guarantee they'd applied everywhere.
-- Repeating them here — all idempotent (IF NOT EXISTS) — makes this single
-- migration the reliable source of truth for every per-question boilerplate
-- column: signatures (Python/JS), harnesses (Java/C++), constraints, examples.
ALTER TABLE questions
  ADD COLUMN IF NOT EXISTS harnesses JSONB;
ALTER TABLE questions
  ADD COLUMN IF NOT EXISTS constraints JSONB;
ALTER TABLE questions
  ADD COLUMN IF NOT EXISTS examples JSONB;
