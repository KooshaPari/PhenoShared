-- Economics page schema (stage 1: inventory + usage). Reference design: economics-page-codex-design.txt
CREATE TABLE IF NOT EXISTS econ_models (
  id TEXT PRIMARY KEY,            -- e.g. 'minimax-mimo-2.6-flash'
  family TEXT, version TEXT,
  released TEXT,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS econ_reference_versions (
  id TEXT PRIMARY KEY,
  baseline_model_id TEXT NOT NULL REFERENCES econ_models(id),
  description TEXT,
  calibration_hash TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS econ_lanes (
  id TEXT PRIMARY KEY,            -- e.g. 'openrouter:free:acct-01'
  model_id TEXT REFERENCES econ_models(id),
  provider TEXT NOT NULL,
  access_type TEXT NOT NULL,      -- 'subscription' | 'api' | 'free-proxy' | 'plan-pool'
  plan TEXT,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS econ_connections (
  id TEXT PRIMARY KEY,            -- sanitized, no credentials
  lane_id TEXT REFERENCES econ_lanes(id),
  provider TEXT NOT NULL,
  auth_type TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  last_sync TEXT,
  source TEXT                     -- e.g. 'omniroute-snapshot'
);
CREATE TABLE IF NOT EXISTS econ_plan_terms (
  id TEXT PRIMARY KEY,
  plan TEXT NOT NULL,             -- 'MiniMax Ultra', 'OpenCode Go', 'GPT Pro', 'Cursor Pro+'
  fee_cents INTEGER NOT NULL,
  period TEXT NOT NULL DEFAULT 'monthly',
  state TEXT NOT NULL,            -- 'confirmed' | 'planned'
  effective TEXT NOT NULL,        -- ISO date the term governs from
  notes TEXT
);
CREATE TABLE IF NOT EXISTS econ_price_observations (
  id TEXT PRIMARY KEY,
  lane_id TEXT REFERENCES econ_lanes(id),
  observed_at TEXT NOT NULL,
  input_per_1m_cents INTEGER,
  cached_per_1m_cents INTEGER,
  output_per_1m_cents INTEGER,
  source TEXT
);
CREATE TABLE IF NOT EXISTS econ_usage_ledger (
  request_id TEXT PRIMARY KEY,    -- canonical; gateway+harness enrich one row
  occurred_at TEXT NOT NULL,
  lane_id TEXT,
  connection_id TEXT,
  model TEXT,
  status INTEGER,
  input_tokens INTEGER, cached_tokens INTEGER, output_tokens INTEGER, reasoning_tokens INTEGER,
  elapsed_ms INTEGER,
  cost_cents REAL,
  mfu REAL,                       -- MiMo-flash units, NULL until calibrated
  provenance TEXT
);
CREATE INDEX IF NOT EXISTS econ_usage_occurred ON econ_usage_ledger(occurred_at, lane_id);
CREATE TABLE IF NOT EXISTS econ_daily_usage (
  day TEXT NOT NULL,
  lane_id TEXT,
  requests INTEGER NOT NULL DEFAULT 0,
  accepted INTEGER,
  spend_cents REAL,
  mfu REAL,
  coverage REAL,                  -- fraction of traffic resolved to a lane
  PRIMARY KEY (day, lane_id)
);
CREATE TABLE IF NOT EXISTS econ_sync_runs (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  started_at TEXT NOT NULL, finished_at TEXT,
  status TEXT, watermark TEXT, detail TEXT
);
