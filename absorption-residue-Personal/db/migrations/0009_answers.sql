-- 0009_answers: append-only ledger of the owner's answers to cockpit cards.
-- The table is created lazily by functions/api/answers/[[path]].js (CREATE TABLE IF NOT
-- EXISTS on each request) so capture does not wait on an operator migration window; this
-- file is the canonical schema record. Additive only per the immutable-ledger direction
-- (Oct 19): rows are never updated or deleted; superseded card revisions stay as history.
CREATE TABLE IF NOT EXISTS answers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id TEXT NOT NULL,
  revision TEXT NOT NULL,
  answer_type TEXT NOT NULL,
  choice TEXT,
  facts TEXT,
  identity TEXT NOT NULL,
  created_at TEXT NOT NULL,
  test INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS answers_card ON answers(card_id, id);
