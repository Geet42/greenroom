-- Two gaps found by a full audit of the live `questions` table
-- (backend/scripts/audit_question_bank.py):
--
-- 1. visible_count never had a column. backend/data/question_bank.json's 77
--    stdio (CodeContests-style) questions each carry a real per-question
--    visible_count (1, 2, or 3 — how many of that question's test cases are
--    shown to the candidate vs. hidden), but nothing in Supabase ever stored
--    it, so routers/interview.py's `assigned["tests"], assigned.get("visible_count", 3)`
--    silently fell back to 3 for every stdio question served from Supabase —
--    45/77 questions have a seed value other than 3, meaning production was
--    quietly showing more test cases than each question's author intended.
--
-- 2. System-design questions previously had only a bare `prompt` string
--    (plus a diagram-evaluator-only `expected_components` list) — no
--    structured functional/non-functional requirements, scaling numbers, or
--    explicit out-of-scope boundaries, unlike a real system-design interview
--    brief. Adding four required-going-forward JSONB array columns for that.
ALTER TABLE questions ADD COLUMN IF NOT EXISTS visible_count INTEGER;

ALTER TABLE questions ADD COLUMN IF NOT EXISTS functional_requirements JSONB;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS non_functional_requirements JSONB;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS scaling_constraints JSONB;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS out_of_scope JSONB;
