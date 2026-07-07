-- Stores the structured diagram evaluation for system-design sessions.
-- Separate column from star_analysis (which is used by behavioral sessions).
ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS diagram_evaluation JSONB;
