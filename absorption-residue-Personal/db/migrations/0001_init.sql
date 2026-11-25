-- cockpit D1 schema v1
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,            -- slug of name
  name TEXT NOT NULL,
  grp TEXT NOT NULL,
  status TEXT,
  percent INTEGER,                -- NULL = not estimated
  detail TEXT, next TEXT, eta TEXT, blocker TEXT, usable TEXT,
  position INTEGER NOT NULL DEFAULT 0,
  archived INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  updated_by TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS subgoals (
  project_id TEXT NOT NULL REFERENCES projects(id),
  position INTEGER NOT NULL,
  name TEXT NOT NULL,
  state TEXT,
  PRIMARY KEY (project_id, position)
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (   -- append-only audit log
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
  project_id TEXT, before TEXT, after TEXT
);
CREATE INDEX IF NOT EXISTS events_project ON events(project_id, id);
CREATE TABLE IF NOT EXISTS tokens (   -- hashed per-agent write tokens
  actor TEXT PRIMARY KEY, sha256 TEXT NOT NULL, created_at TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0
);
