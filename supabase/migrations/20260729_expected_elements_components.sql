-- Adds the two columns DESIGN.md's schema documented but were never actually
-- migrated: expected_elements (behavioral, STAR components to surface) and
-- expected_components (system-design, architecture components for diagram
-- scoring). Without these, behavioral/system-design questions can be seeded
-- but the interviewer/evaluator has nothing to check answers/diagrams
-- against.
ALTER TABLE questions ADD COLUMN IF NOT EXISTS expected_elements JSONB;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS expected_components JSONB;
