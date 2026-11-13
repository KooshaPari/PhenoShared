-- PROPOSAL ONLY: no execution before quota reset and explicit approval.
-- Keep source originals/private import outside this display table until reviewed.
CREATE TABLE IF NOT EXISTS ask_display (
 id INTEGER PRIMARY KEY,
 original_text TEXT, interpretation TEXT NOT NULL,
 first_asked_at TEXT, reported_state TEXT NOT NULL,
 verified_state TEXT NOT NULL DEFAULT 'needs_reconciliation',
 task_links_json TEXT NOT NULL DEFAULT '[]', source_refs_json TEXT NOT NULL DEFAULT '[]',
 reconciled_at TEXT, updated_at TEXT NOT NULL,
 reviewed INTEGER NOT NULL DEFAULT 0 CHECK(reviewed IN (0,1))
);
CREATE INDEX IF NOT EXISTS ask_display_reviewed_id ON ask_display(reviewed,id);
-- Future writer must atomically update canonical ask + reviewed display projection,
-- using authenticated existing write path, revision checks and audit provenance.
-- Do not expose a new unauthenticated writer or mint credentials for this patch.
