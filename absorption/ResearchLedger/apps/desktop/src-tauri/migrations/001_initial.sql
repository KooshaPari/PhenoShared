PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  canonical_path TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  source_uri TEXT,
  content_hash TEXT NOT NULL,
  captured_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id TEXT NOT NULL REFERENCES documents(id),
  content_hash TEXT NOT NULL,
  raw_content TEXT NOT NULL,
  captured_at TEXT NOT NULL,
  UNIQUE(document_id, content_hash)
);

CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id TEXT NOT NULL REFERENCES documents(id),
  ordinal INTEGER NOT NULL,
  heading_path TEXT,
  text TEXT NOT NULL,
  UNIQUE(document_id, ordinal)
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
  text,
  heading_path,
  content='chunks',
  content_rowid='id'
);

CREATE TABLE IF NOT EXISTS provenance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id TEXT NOT NULL REFERENCES documents(id),
  source_uri TEXT,
  locator TEXT,
  quote TEXT,
  captured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL,
  claim TEXT NOT NULL,
  source_uri TEXT,
  citation_id TEXT NOT NULL DEFAULT '1',
  evidence_quote TEXT NOT NULL,
  span_start INTEGER NOT NULL,
  span_end INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(document_id, ordinal)
);

CREATE INDEX IF NOT EXISTS idx_claims_document ON claims(document_id, ordinal);

CREATE TABLE IF NOT EXISTS import_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_kind TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  error TEXT
);

INSERT OR IGNORE INTO schema_version(version) VALUES (1);

CREATE TABLE IF NOT EXISTS document_links (
  source_document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  target_url TEXT NOT NULL,
  relation TEXT NOT NULL DEFAULT 'mentioned',
  discovered_at TEXT NOT NULL,
  PRIMARY KEY (source_document_id, target_url)
);

CREATE INDEX IF NOT EXISTS idx_document_links_target ON document_links(target_url);

CREATE TABLE IF NOT EXISTS enrichment_jobs (
  document_id TEXT PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
  strategy TEXT NOT NULL,
  status TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  error TEXT
);

CREATE TABLE IF NOT EXISTS chunk_embeddings (
  chunk_id INTEGER PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
  model TEXT NOT NULL,
  embedding_version TEXT NOT NULL DEFAULT 'v1',
  input_hash TEXT NOT NULL DEFAULT '',
  dimensions INTEGER NOT NULL,
  vector_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- One durable row per discovered URL.  Raw responses live under the vault's
-- `.researchledger/references` directory; SQLite keeps the resumable job
-- state and the artifact fingerprint so a failed fetch never looks complete.
CREATE TABLE IF NOT EXISTS reference_fetches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  target_url TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  started_at TEXT,
  lease_expires_at INTEGER NOT NULL DEFAULT 0,
  artifact_path TEXT,
  content_type TEXT,
  http_status INTEGER,
  byte_count INTEGER,
  content_hash TEXT,
  fetched_at TEXT,
  error TEXT,
  run_id TEXT,
  parent_document_id TEXT,
  crawl_depth INTEGER NOT NULL DEFAULT 0,
  UNIQUE(source_document_id, target_url)
);

CREATE INDEX IF NOT EXISTS idx_reference_fetches_status
  ON reference_fetches(status, id);

CREATE TABLE IF NOT EXISTS reference_crawl_runs (
  id TEXT PRIMARY KEY,
  root_document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  max_depth INTEGER NOT NULL,
  max_documents INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'running',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consent_grants (
  id TEXT PRIMARY KEY,
  local_profile TEXT NOT NULL,
  provider TEXT NOT NULL,
  purpose TEXT NOT NULL,
  data_categories TEXT NOT NULL,
  url_scope TEXT NOT NULL,
  granted_at TEXT NOT NULL,
  expires_at TEXT,
  revoked_at TEXT,
  version INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_consent_grants_active
  ON consent_grants(purpose, url_scope, revoked_at, expires_at);

CREATE TABLE IF NOT EXISTS consent_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  grant_id TEXT NOT NULL,
  target_hash TEXT NOT NULL,
  decision TEXT NOT NULL,
  reason TEXT NOT NULL,
  decided_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_consent_audit_decided_at
  ON consent_audit(decided_at, id);
