CREATE TABLE IF NOT EXISTS board(id INTEGER PRIMARY KEY, ats TEXT NOT NULL, slug TEXT NOT NULL, company TEXT NOT NULL, tier INTEGER DEFAULT 2, skip INTEGER DEFAULT 0, last_day TEXT, last_ok INTEGER, last_error TEXT, UNIQUE(ats,slug));
CREATE TABLE IF NOT EXISTS job(id TEXT PRIMARY KEY, board_id INTEGER NOT NULL, ext_id TEXT, title TEXT, location TEXT, loc_rank INTEGER, comp_min INTEGER, comp_max INTEGER, yoe_min INTEGER, url TEXT, first_seen TEXT, last_seen TEXT, status TEXT DEFAULT 'open', score INTEGER, apply_rank INTEGER, flags TEXT, detail_day TEXT);
CREATE INDEX IF NOT EXISTS job_seen ON job(last_seen, status);
CREATE INDEX IF NOT EXISTS job_board ON job(board_id);
CREATE TABLE IF NOT EXISTS job_event(job_id TEXT, day TEXT, change TEXT);
CREATE INDEX IF NOT EXISTS ev_day ON job_event(day);
CREATE TABLE IF NOT EXISTS alert(day TEXT, level TEXT, job_id TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS run(day TEXT PRIMARY KEY, ok INTEGER, error TEXT, boards_ok INTEGER, boards_failed INTEGER, jobs_new INTEGER, jobs_closed INTEGER, candidates INTEGER, finished_at TEXT);
