CREATE TABLE IF NOT EXISTS canonical_job (
  canonical_id TEXT PRIMARY KEY,
  company TEXT NOT NULL,
  title TEXT NOT NULL,
  official_url TEXT NOT NULL,
  geography TEXT NOT NULL DEFAULT 'unknown',
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  content_signature TEXT,
  state TEXT NOT NULL DEFAULT 'discovered'
);
CREATE TABLE IF NOT EXISTS canonical_source (
  source_kind TEXT NOT NULL,
  source_id TEXT NOT NULL,
  canonical_id TEXT NOT NULL,
  source_url TEXT NOT NULL,
  location TEXT,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  content_signature TEXT,
  PRIMARY KEY(source_kind,source_id)
);
CREATE INDEX IF NOT EXISTS idx_source_canonical ON canonical_source(canonical_id);
CREATE TABLE IF NOT EXISTS job_verification (
  canonical_id TEXT PRIMARY KEY,
  checked_at TEXT NOT NULL,
  source_signature TEXT NOT NULL,
  official_url TEXT NOT NULL,
  verification_status TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  decision_reasons TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_verification_status ON job_verification(verification_status,checked_at);
CREATE TABLE IF NOT EXISTS source_checkpoint (
  source_kind TEXT PRIMARY KEY,
  last_attempt TEXT,
  last_success TEXT,
  last_error TEXT,
  records_count INTEGER NOT NULL DEFAULT 0,
  last_snapshot_digest TEXT
);
