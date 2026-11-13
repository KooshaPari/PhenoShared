-- Migration: display_summaries (browser-facing reviewed projection for /projects/ + /parent/).
-- Source of truth for this table was missing from the repo; production D1 lost it
-- during the Oct 17 recovery and the display projection quarantined all 52 cards
-- (by design). Schema inferred from functions/api/display/[[path]].js reader +
-- web/tests/display.test.ts fixture + ask_display pattern.
CREATE TABLE IF NOT EXISTS display_summaries (
  project_id TEXT PRIMARY KEY REFERENCES projects(id),
  display_name TEXT,          -- approved copy of identity; canonical renames do NOT inherit approval
  display_grp TEXT,
  summary TEXT,
  next TEXT,
  blocker TEXT,
  blocker_state TEXT CHECK (blocker_state IN ('none','known','unknown') OR blocker_state IS NULL),
  reviewed INTEGER NOT NULL DEFAULT 0 CHECK (reviewed IN (0,1)),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
-- Restore path for the lost reviewed content: see report - pipeline seed or
-- D1 time-travel bookmark; do NOT bulk-set reviewed=1 without the review step.
