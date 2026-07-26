-- Autosaved Excalidraw scene elements for system-design sessions, so a
-- refresh/resume mid-session restores the candidate's diagram along with
-- the conversation (previously only the conversation was restored — the
-- canvas reset to blank on every refresh). See services/persistence.py
-- ::persist_diagram and routers/interview.py POST /interview/diagram.
ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS diagram_elements JSONB;
