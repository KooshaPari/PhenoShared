-- Migration 0007: SSOT plane entity expansion + Dot relay surface + estimate ledger.
-- Spec: cockpit-dag-absorption spec section 7.1 (asks/tasks/agents/escalations),
-- section 15 (dot_status, dot_digest append-only, relay-writer write path),
-- section 16 (size_classes, estimates, actuals, velocity_log, dependency_edges).
-- All writes to these tables go through the sanctioned relay writer
-- (tools/dot-relay-writer) with the section 15-16 guards; ad-hoc wrangler stays
-- read-only. dot_* and ledger tables are append-only: corrections are new rows.

-- Entity expansion (spec 7.1): asks, tasks, agents, escalations alongside
-- projects/subgoals/events/meta.
CREATE TABLE IF NOT EXISTS asks (
  id TEXT PRIMARY KEY,
  verbatim TEXT NOT NULL,           -- his words, copied, never paraphrased in storage
  interpretation TEXT,              -- agent-authored until interpretation_state='confirmed'
  interpretation_state TEXT NOT NULL DEFAULT 'draft'
    CHECK (interpretation_state IN ('draft','confirmed','rejected','unknown')),
  source_ref TEXT,
  first_asked_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  updated_by TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,              -- kebab-case stable id
  project_id TEXT REFERENCES projects(id),
  title TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending',
  owner_lane TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  updated_by TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agents (
  id TEXT PRIMARY KEY,              -- lane/agent id, e.g. instinct:main, desk:jcode-pane-1
  lane TEXT NOT NULL,
  kind TEXT,
  last_seen_at TEXT
);
CREATE TABLE IF NOT EXISTS escalations (
  id TEXT PRIMARY KEY,
  task_id TEXT REFERENCES tasks(id),
  question TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open','answered','cancelled')),
  answer TEXT,
  created_at TEXT NOT NULL,
  answered_at TEXT
);

-- Dot relay surface (spec 15). Append-only; one events row per write;
-- updated_by='dot'. Dot cannot touch projects, subgoals,
-- display_summaries.reviewed, or tokens.
CREATE TABLE IF NOT EXISTS dot_status (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(id),
  status TEXT NOT NULL,             -- controlled vocab, enforced by the writer
  percent INTEGER CHECK (percent BETWEEN 0 AND 100),
  unknown_cause TEXT,               -- required with start_step when percent IS NULL
  start_step TEXT,
  text TEXT,                        -- length-capped, secret-scrubbed by the writer
  base_updated_at TEXT NOT NULL,    -- writer's last-read anchor for the stale-clobber check
  recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), -- NOSONAR: SQLite DDL has no constant mechanism; the ISO timestamp default is repeated per table by design
  updated_by TEXT NOT NULL DEFAULT 'dot'
);
CREATE INDEX IF NOT EXISTS dot_status_project ON dot_status(project_id, id);
CREATE INDEX IF NOT EXISTS dot_status_recorded ON dot_status(recorded_at);
CREATE TABLE IF NOT EXISTS dot_digest (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  period_start TEXT,
  period_end TEXT,
  format TEXT,                      -- 'pdf' | 'json' | 'markdown'
  uri TEXT,                         -- artifact location
  summary TEXT,
  recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), -- NOSONAR: SQLite DDL has no constant mechanism; the ISO timestamp default is repeated per table by design
  updated_by TEXT NOT NULL DEFAULT 'dot'
);

-- Estimate ledger (spec 16). Append-only: a re-estimate is a new row.
CREATE TABLE IF NOT EXISTS size_classes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  base_hours_p50 REAL NOT NULL,
  base_hours_p90 REAL NOT NULL,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS estimates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL,
  size_class_id INTEGER REFERENCES size_classes(id),
  est_hours_p50 REAL,
  est_hours_p90 REAL,
  basis TEXT,                       -- the historical-timing basis; 'unknown' where thin
  estimated_by TEXT NOT NULL,
  estimated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) -- NOSONAR: SQLite DDL has no constant mechanism; the ISO timestamp default is repeated per table by design
);
CREATE INDEX IF NOT EXISTS estimates_task ON estimates(task_id, id);
CREATE TABLE IF NOT EXISTS actuals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  actual_hours REAL,                -- measured from event timestamps, not guessed
  source TEXT,
  recorded_by TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS actuals_task ON actuals(task_id, id);
CREATE TABLE IF NOT EXISTS velocity_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_or_lane TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  tasks_done INTEGER NOT NULL,
  hours_actual REAL,
  hours_est REAL,
  ratio REAL                        -- hours_actual / hours_est; derived by the writer, never hand-entered
);
CREATE TABLE IF NOT EXISTS dependency_edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_task_id TEXT NOT NULL,
  to_task_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('blocks','soft')),
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), -- NOSONAR: SQLite DDL has no constant mechanism; the ISO timestamp default is repeated per table by design
  UNIQUE (from_task_id, to_task_id, kind)
);
