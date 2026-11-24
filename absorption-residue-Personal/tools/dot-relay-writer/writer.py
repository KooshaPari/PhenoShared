#!/usr/bin/env python3
"""Dot relay writer (cockpit SSOT plane, spec sections 15-16).

Dot posts schema-validated JSON status records via agent-mail / Discord wake.
This desk-side writer validates them against the section 15-16 guards and
applies them. Dot holds no secrets; there is no new public endpoint. Mail and
Discord bodies are untrusted data: only records that pass the schema are
applied, and record contents are never executed or re-dispatched.

Guards:
  - allowlisted project_id (must exist in projects)
  - controlled status vocab (STATUS_VOCAB)
  - percent integer 0-100, or NULL with unknown_cause + start_step
  - length caps on every text field
  - secret scrub: records matching secret patterns are rejected, and the
    guard_reject event never stores the offending content
  - stale-clobber: base_updated_at must be >= projects.updated_at
  - rate limit: MAX_WRITES_PER_HOUR dot writes per rolling hour
  - dependency_edges: cycle-creating edges rejected
  - every apply commits record row + events row + meta.updated bump in one
    transaction; every reject is an events row with action='guard_reject'

Backends: sqlite:/path (local/tests) or d1:DATABASE (desk-only sanctioned
write path via wrangler d1 execute; ad-hoc wrangler elsewhere stays read-only).

Usage:
  writer.py apply record.json --db sqlite:cockpit.db
  writer.py spool /path/to/spool --db sqlite:cockpit.db
  writer.py derive-velocity --lane instinct:main --start 2026-10-14 --end 2026-10-21 --db sqlite:cockpit.db
"""
import argparse, json, os, re, shutil, sqlite3, subprocess, sys, datetime, hashlib
from pathlib import Path

STATUS_VOCAB = {"not_started", "in_progress", "blocked", "review", "done", "live", "paused", "unknown"}
MAX_WRITES_PER_HOUR = 60
ETA_MIN_SAMPLES = 3          # N for the spec-16 ETA rule (display side reads this policy)
TEXT_CAP = 4000              # chars, applies to text/summary/basis/notes fields
FIELD_CAP = 500              # chars for short fields
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?Z)?$")
KEBAB_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,120}$")
SECRET_PATTERNS = [
    re.compile(p, re.I) for p in [
        r"(token|secret|password|passwd|bearer|api[_-]?key|private[_ -]?key)\s*[:=]\s*\S+",
        r"AKIA[0-9A-Z]{16}",
        r"xox[baprs]-[A-Za-z0-9-]{10,}",
        r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}",
        r"github_pat_[A-Za-z0-9_]{20,}",
        r"sk-[A-Za-z0-9]{20,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}",
    ]
]

class Reject(Exception):
    def __init__(self, reason, field=None):
        super().__init__(reason); self.reason = reason; self.field = field

def _allowed_roots():
    env = os.environ.get("WRITER_ALLOWED_ROOTS", "")
    roots = [Path(p).expanduser().resolve() for p in env.split(os.pathsep) if p.strip()]
    return roots or [Path.cwd(), Path.home()]

def resolve_cli_path(arg, field="path"):
    """Confine an LLM/CLI-supplied path to an allowed root
    (WRITER_ALLOWED_ROOTS, os.pathsep-separated; default: cwd and home).
    resolve() collapses '..' and follows symlinks, so both traversal and
    symlink escapes fail the is_relative_to check."""
    p = Path(arg).expanduser().resolve()
    if not any(p.is_relative_to(root) for root in _allowed_roots()):
        raise Reject("path escapes allowed roots", field=field)
    return p

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

def scrub_check(value, field):
    if not isinstance(value, str):
        return
    for pat in SECRET_PATTERNS:
        if pat.search(value):
            raise Reject("secret-pattern", field)

def bounded(value, cap, field):
    if value is None:
        return None
    if not isinstance(value, str):
        raise Reject("wrong-type", field)
    if len(value) > cap:
        raise Reject("over-length-cap", field)
    scrub_check(value, field)
    return value

def iso(value, field):
    if not isinstance(value, str) or not ISO_RE.match(value):
        raise Reject("bad-timestamp", field)
    return value

# ---------- backends ----------

class SqliteBackend:
    def __init__(self, path): self.conn = sqlite3.connect(path)
    def execute(self, sql, params): return self.conn.execute(sql, params)
    def query(self, sql, params=()): return self.conn.execute(sql, params).fetchall()
    def one(self, sql, params=()):
        r = self.conn.execute(sql, params).fetchone()
        return r[0] if r else None
    def commit(self): self.conn.commit()
    def rollback(self): self.conn.rollback()
    def close(self): self.conn.close()

def _lit(v):
    if v is None: return "NULL"
    if isinstance(v, bool): raise ValueError("bool not supported")
    if isinstance(v, int): return str(v)
    if isinstance(v, float): return repr(v)
    s = str(v)
    if len(s) > TEXT_CAP * 2: raise ValueError("literal too long")
    if any(ord(c) < 32 for c in s): raise ValueError("control character in literal")
    return "'" + s.replace("'", "''") + "'"

class D1Backend:
    """Desk-only sanctioned write path: wrangler d1 execute. Values have all
    passed validation (vocab, caps, ISO/kebab regexes) before reaching _lit."""
    def __init__(self, database): self.database = database; self._stmts = []
    def _render(self, sql, params):
        parts = sql.split("?")
        out = parts[0]
        for part in parts[1:]:
            if not params: raise ValueError("param underflow")
            out += _lit(params.pop(0)) + part
        if params: raise ValueError("param overflow")
        # NOSONAR python:S3649 -- SQL text is static code, never derived from record
        # content; the wrangler CLI exposes no parameter binding, so values pass
        # through _lit (quote-doubling, type, length, and control-char checks).
        return out
    def execute(self, sql, params):
        p = list(params); self._stmts.append(self._render(sql, p))
    def query(self, sql, params=()):
        p = list(params); stmt = self._render(sql, p)
        r = subprocess.run(["wrangler", "d1", "execute", self.database, "--remote",
                            "--json", "--command", stmt],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError("wrangler query failed: " + r.stderr[:200])
        data = json.loads(r.stdout)
        rows = data[0].get("results", []) if isinstance(data, list) else data.get("results", [])
        return [tuple(row.values()) for row in rows]
    def one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0][0] if rows else None
    def commit(self):
        if not self._stmts: return
        # NOSONAR python:S3649 -- statements were built by _render from static SQL
        # with _lit-escaped values only (see above).
        # D1 rejects explicit BEGIN/COMMIT; a --file execute applies the statements as one atomic batch.
        script = " ".join(s.rstrip(";") + ";" for s in self._stmts)
        self._stmts = []
        r = subprocess.run(["wrangler", "d1", "execute", self.database, "--remote",
                            "--command", script],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError("wrangler commit failed: " + r.stderr[:200])
    def rollback(self): self._stmts = []
    def close(self):
        pass  # D1Backend is stateless: each commit spawns a wrangler CLI call, so there is no connection to close.

def open_db(spec):
    kind, _, rest = spec.partition(":")
    if kind == "sqlite": return SqliteBackend(rest)
    if kind == "d1": return D1Backend(rest)
    raise SystemExit("unknown --db backend: " + kind)

# ---------- guards ----------

def check_rate_limit(db):
    n = db.one("SELECT COUNT(*) FROM dot_status WHERE recorded_at >= strftime('%Y-%m-%dT%H:%M:%fZ','now','-1 hour')")
    n = (n or 0) + (db.one("SELECT COUNT(*) FROM dot_digest WHERE recorded_at >= strftime('%Y-%m-%dT%H:%M:%fZ','now','-1 hour')") or 0)
    if n >= MAX_WRITES_PER_HOUR:
        raise Reject("rate-limit")

def check_project(db, project_id):
    if not isinstance(project_id, str) or not KEBAB_RE.match(project_id):
        raise Reject("bad-project-id", "project_id")
    row = db.one("SELECT updated_at FROM projects WHERE id=?", (project_id,))
    if row is None:
        raise Reject("project-not-allowlisted", "project_id")
    return row

def check_fresh(db, project_id, base_updated_at):
    current = check_project(db, project_id)
    if base_updated_at < current:
        raise Reject("stale-clobber", "base_updated_at")

def log_reject(db, kind, reason, project_id=None, detail=None):
    # Never stores record content: a reject triggered by a secret pattern must
    # not copy the secret into the events ledger.
    safe = json.dumps({"kind": kind, "reason": reason, "field": detail})[:FIELD_CAP]
    try:
        db.execute("INSERT INTO events(ts,actor,action,project_id,before,after) VALUES (?,?,?,?,NULL,?)",
                   (now_iso(), "dot", "guard_reject", project_id, safe))
        db.commit()
    except Exception:
        db.rollback()
        raise

def bump_meta(db):
    db.execute("INSERT INTO meta(k,v) VALUES ('updated',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (now_iso(),))

def log_event(db, action, project_id, after, actor="dot"):
    db.execute("INSERT INTO events(ts,actor,action,project_id,before,after) VALUES (?,?,?,?,NULL,?)",
               (now_iso(), actor, action, project_id, after))

# ---------- record appliers ----------

def apply_status(db, rec):
    project_id = rec.get("project_id")
    status = rec.get("status")
    percent = rec.get("percent")
    unknown_cause = rec.get("unknown_cause")
    start_step = rec.get("start_step")
    text = rec.get("text")
    base = rec.get("base_updated_at")
    check_rate_limit(db)
    check_project(db, project_id)
    if status not in STATUS_VOCAB:
        raise Reject("status-vocab", "status")
    if percent is not None:
        if not isinstance(percent, int) or isinstance(percent, bool) or not (0 <= percent <= 100):
            raise Reject("percent-range", "percent")
    else:
        if not unknown_cause or not start_step:
            raise Reject("unknown-needs-cause-and-start-step", "percent")
        bounded(unknown_cause, FIELD_CAP, "unknown_cause")
        bounded(start_step, FIELD_CAP, "start_step")
    bounded(text, TEXT_CAP, "text")
    iso(base, "base_updated_at")
    check_fresh(db, project_id, base)
    after = json.dumps({"project_id": project_id, "status": status, "percent": percent})[:FIELD_CAP]
    db.execute("INSERT INTO dot_status(project_id,status,percent,unknown_cause,start_step,text,base_updated_at,updated_by) VALUES (?,?,?,?,?,?,?,'dot')",
               (project_id, status, percent, unknown_cause, start_step, text, base))
    log_event(db, "dot_status", project_id, after)
    bump_meta(db)
    db.commit()

def apply_digest(db, rec):
    check_rate_limit(db)
    fmt = rec.get("format")
    if fmt not in ("pdf", "json", "markdown", None):
        raise Reject("digest-format", "format")
    period_start, period_end = rec.get("period_start"), rec.get("period_end")
    if period_start is not None: iso(period_start, "period_start")
    if period_end is not None: iso(period_end, "period_end")
    bounded(rec.get("uri"), FIELD_CAP, "uri")
    bounded(rec.get("summary"), TEXT_CAP, "summary")
    db.execute("INSERT INTO dot_digest(period_start,period_end,format,uri,summary,updated_by) VALUES (?,?,?,?,?,'dot')",
               (period_start, period_end, fmt, rec.get("uri"), rec.get("summary")))
    log_event(db, "dot_digest", None, json.dumps({"format": fmt, "uri": rec.get("uri")})[:FIELD_CAP])
    bump_meta(db)
    db.commit()

def _creates_cycle(db, from_id, to_id, kind):
    # Reject if to_id can already reach from_id via same-kind edges.
    seen, stack = set(), [to_id]
    while stack:
        cur = stack.pop()
        if cur == from_id:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        rows = db.query("SELECT to_task_id FROM dependency_edges WHERE from_task_id=? AND kind=?", (cur, kind))
        stack.extend(r[0] for r in rows)
    return False

def apply_edge(db, rec):
    frm, to, kind = rec.get("from_task_id"), rec.get("to_task_id"), rec.get("kind")
    for f, v in (("from_task_id", frm), ("to_task_id", to)):
        if not isinstance(v, str) or not KEBAB_RE.match(v):
            raise Reject("bad-task-id", f)
    if kind not in ("blocks", "soft"):
        raise Reject("edge-kind", "kind")
    if frm == to or _creates_cycle(db, frm, to, kind):
        raise Reject("dependency-cycle", "from_task_id")
    created_by = bounded(rec.get("created_by") or "dot", FIELD_CAP, "created_by")
    try:
        db.execute("INSERT INTO dependency_edges(from_task_id,to_task_id,kind,created_by) VALUES (?,?,?,?)",
                   (frm, to, kind, created_by))
    except sqlite3.IntegrityError:
        raise Reject("duplicate-edge", "from_task_id")
    log_event(db, "dependency_edge", None, json.dumps({"from": frm, "to": to, "kind": kind})[:FIELD_CAP])
    bump_meta(db)
    db.commit()

def apply_estimate(db, rec):
    task_id = rec.get("task_id")
    if not isinstance(task_id, str) or not KEBAB_RE.match(task_id):
        raise Reject("bad-task-id", "task_id")
    size_class_id = rec.get("size_class_id")
    if size_class_id is not None:
        if not isinstance(size_class_id, int) or db.one("SELECT COUNT(*) FROM size_classes WHERE id=?", (size_class_id,)) != 1:
            raise Reject("unknown-size-class", "size_class_id")
    p50, p90 = rec.get("est_hours_p50"), rec.get("est_hours_p90")
    for f, v in (("est_hours_p50", p50), ("est_hours_p90", p90)):
        if v is not None and (not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0):
            raise Reject("bad-hours", f)
    bounded(rec.get("basis"), TEXT_CAP, "basis")
    estimated_by = bounded(rec.get("estimated_by") or "dot", FIELD_CAP, "estimated_by")
    db.execute("INSERT INTO estimates(task_id,size_class_id,est_hours_p50,est_hours_p90,basis,estimated_by) VALUES (?,?,?,?,?,?)",
               (task_id, size_class_id, p50, p90, rec.get("basis"), estimated_by))
    log_event(db, "estimate", None, json.dumps({"task_id": task_id})[:FIELD_CAP])
    bump_meta(db)
    db.commit()

def apply_actual(db, rec):
    task_id = rec.get("task_id")
    if not isinstance(task_id, str) or not KEBAB_RE.match(task_id):
        raise Reject("bad-task-id", "task_id")
    started, finished = rec.get("started_at"), rec.get("finished_at")
    if started is not None: iso(started, "started_at")
    if finished is not None: iso(finished, "finished_at")
    hours = rec.get("actual_hours")
    if hours is not None and (not isinstance(hours, (int, float)) or isinstance(hours, bool) or hours < 0):
        raise Reject("bad-hours", "actual_hours")
    bounded(rec.get("source"), FIELD_CAP, "source")
    recorded_by = bounded(rec.get("recorded_by") or "dot", FIELD_CAP, "recorded_by")
    db.execute("INSERT INTO actuals(task_id,started_at,finished_at,actual_hours,source,recorded_by) VALUES (?,?,?,?,?,?)",
               (task_id, started, finished, hours, rec.get("source"), recorded_by))
    log_event(db, "actual", None, json.dumps({"task_id": task_id})[:FIELD_CAP])
    bump_meta(db)
    db.commit()

# ---------- lane actions on Dot status rows (spec 18/19) ----------
# Confirm, flag-stale and note are written by a lane, never by Dot: Dot cannot
# confirm its own report. They append events rows only; dot_status stays
# append-only and the UI stays read-only. Confirm shape (matches the display DTO):
#   events(action='dot_status_confirm', actor=<lane>, project_id, after={"confirm_ref": <dot_status.id>})
LANE_RE = re.compile(r"^[a-z0-9][a-z0-9:._-]{0,60}$")
NOTE_CAP = 1000
MAX_LANE_ACTIONS_PER_HOUR = 60

def _lane(rec):
    actor = rec.get("actor")
    if not isinstance(actor, str) or not LANE_RE.match(actor) or actor.split(":")[0] == "dot":
        raise Reject("actor-not-a-lane", "actor")
    return actor

def _lane_rate_limit(db, actor):
    n = db.one("SELECT COUNT(*) FROM events WHERE actor=? AND action LIKE 'dot_status_%' AND ts >= strftime('%Y-%m-%dT%H:%M:%fZ','now','-1 hour')", (actor,))
    if (n or 0) >= MAX_LANE_ACTIONS_PER_HOUR:
        raise Reject("rate-limit", "actor")

def _status_ref(db, project_id, ref, required=True):
    if ref is None and not required:
        return None
    if not isinstance(ref, int) or isinstance(ref, bool):
        raise Reject("bad-confirm-ref", "confirm_ref")
    if db.one("SELECT 1 FROM dot_status WHERE id=? AND project_id=?", (ref, project_id)) is None:
        raise Reject("unknown-status-ref", "confirm_ref")
    return ref

def _lane_action(db, rec, action, ref_required, payload):
    actor = _lane(rec)
    project_id = rec.get("project_id")
    _lane_rate_limit(db, actor)
    check_project(db, project_id)
    ref = _status_ref(db, project_id, rec.get("confirm_ref"), ref_required)
    after = json.dumps(payload(ref), ensure_ascii=True)
    log_event(db, action, project_id, after, actor)
    bump_meta(db)
    db.commit()

def apply_confirm(db, rec):
    _lane_action(db, rec, "dot_status_confirm", True, lambda ref: {"confirm_ref": ref})

def apply_flag_stale(db, rec):
    reason = bounded(rec.get("reason"), FIELD_CAP, "reason")
    _lane_action(db, rec, "dot_status_flag_stale", True, lambda ref: {"confirm_ref": ref, "reason": reason})

def apply_note(db, rec):
    text = bounded(rec.get("text"), NOTE_CAP, "text")
    if not text or not text.strip():
        raise Reject("empty-note", "text")
    _lane_action(db, rec, "dot_status_note", False, lambda ref: {"confirm_ref": ref, "text": text})

# ---------- ask proofs (lane-only, handoff v2; events-row form until migration 0009) ----------
ASK_PROOF_RESULTS = {"pass", "fail", "partial"}
ASK_PROOF_EVIDENCE_KINDS = {"pr", "ci_run", "test_run", "deploy_sha", "screenshot", "probe"}
ASK_PROOF_MAX_EVIDENCE = 20
ISO_OFFSET_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")

def iso_offset(value, field):
    if not isinstance(value, str) or not ISO_OFFSET_RE.match(value):
        raise Reject("bad-timestamp", field)
    return value

def _ask_proof_rate_limit(db, actor):
    n = db.one("SELECT COUNT(*) FROM events WHERE actor=? AND action='ask_proof' AND ts >= strftime('%Y-%m-%dT%H:%M:%fZ','now','-1 hour')", (actor,))
    if (n or 0) >= MAX_LANE_ACTIONS_PER_HOUR:
        raise Reject("rate-limit", "actor")

def apply_ask_proof(db, rec):
    """Lane proof that an ask was verified (handoff v2). Until migration 0009
    lands the proofs table, the proof is an events row: action='ask_proof',
    project_id NULL, after={ask_id,result,unit_ref,evidence,dedupe_sha}.
    verified_state stays 'needs_reconciliation'; reviewed is never touched."""
    actor = _lane(rec)
    _ask_proof_rate_limit(db, actor)
    ask_id = rec.get("ask_id")
    if not isinstance(ask_id, int) or isinstance(ask_id, bool):
        raise Reject("bad-ask-id", "ask_id")
    current_updated_at = db.one("SELECT updated_at FROM ask_display WHERE id=?", (ask_id,))
    if current_updated_at is None:
        raise Reject("unknown-ask", "ask_id")
    result = rec.get("result")
    if result not in ASK_PROOF_RESULTS:
        raise Reject("bad-result", "result")
    unit_ref = bounded(rec.get("unit_ref"), NOTE_CAP, "unit_ref")
    if not unit_ref or not unit_ref.strip():
        raise Reject("empty-unit-ref", "unit_ref")
    evidence = rec.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise Reject("empty-evidence", "evidence")
    if len(evidence) > ASK_PROOF_MAX_EVIDENCE:
        raise Reject("too-much-evidence", "evidence")
    norm_evidence = []
    for item in evidence:
        if not isinstance(item, dict):
            raise Reject("bad-evidence-item", "evidence")
        kind = item.get("kind")
        if kind not in ASK_PROOF_EVIDENCE_KINDS:
            raise Reject("bad-evidence-kind", "evidence.kind")
        ref = bounded(item.get("ref"), FIELD_CAP, "evidence.ref")
        if not ref or not ref.strip():
            raise Reject("empty-evidence-ref", "evidence.ref")
        observed_at = iso_offset(item.get("observed_at"), "evidence.observed_at")
        norm_evidence.append({"kind": kind, "ref": ref, "observed_at": observed_at})
    base = iso_offset(rec.get("base_updated_at"), "base_updated_at")
    if base < current_updated_at:
        raise Reject("stale-clobber", "base_updated_at")
    dedupe = hashlib.sha256(json.dumps(
        {"ask_id": ask_id, "unit_ref": unit_ref,
         "refs": sorted(e["ref"] for e in norm_evidence)},
        sort_keys=True).encode()).hexdigest()[:32]
    for (prior_json,) in db.query("SELECT after FROM events WHERE action='ask_proof'"):
        try:
            prior = json.loads(prior_json)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(prior, dict) and prior.get("dedupe_sha") == dedupe:
            raise Reject("duplicate-proof", "evidence")
    after = json.dumps({"ask_id": ask_id, "result": result, "unit_ref": unit_ref,
                        "evidence": norm_evidence, "dedupe_sha": dedupe}, ensure_ascii=True)
    log_event(db, "ask_proof", None, after, actor)
    bump_meta(db)
    db.commit()

APPLIERS = {"status": apply_status, "digest": apply_digest, "edge": apply_edge,
            "estimate": apply_estimate, "actual": apply_actual,
            "confirm": apply_confirm, "flag_stale": apply_flag_stale, "note": apply_note, "ask_proof": apply_ask_proof}

def apply_record(db, rec):
    # Record type lives in "type" (default "status"); "kind" stays free for
    # dependency_edges' blocks|soft field.
    if not isinstance(rec, dict):
        log_reject(db, "unknown", "not-an-object")
        return {"applied": False, "reason": "not-an-object"}
    rtype = rec.get("type", "status")
    applier = APPLIERS.get(rtype)
    pid = rec.get("project_id") if isinstance(rec.get("project_id"), str) else None
    if not applier:
        log_reject(db, str(rtype)[:40], "unknown-type")
        return {"applied": False, "reason": "unknown-type"}
    try:
        applier(db, rec)
    except Reject as r:
        db.rollback()
        log_reject(db, rtype, r.reason, pid, r.field)
        return {"applied": False, "reason": r.reason, "field": r.field}
    return {"applied": True}

def derive_velocity(db, lane, period_start, period_end):
    """Append one derived velocity_log row from estimates+actuals. Never hand-entered.
    Single-column queries only: D1 JSON rows do not guarantee column order."""
    task_ids = [r[0] for r in db.query(
        "SELECT DISTINCT task_id FROM actuals WHERE finished_at >= ? AND finished_at < ? AND actual_hours IS NOT NULL",
        (period_start, period_end))]
    hours_actual = 0.0
    hours_est = 0.0
    for tid in task_ids:
        hours_actual += db.one(
            "SELECT SUM(actual_hours) FROM actuals WHERE task_id=? AND finished_at >= ? AND finished_at < ?",
            (tid, period_start, period_end)) or 0.0
        est = db.one("SELECT est_hours_p50 FROM estimates WHERE task_id=? ORDER BY id DESC LIMIT 1", (tid,))
        if est is not None:
            hours_est += est
    done = len(task_ids)
    ha = hours_actual if done else None
    he = hours_est if done else None
    ratio = (ha / he) if (ha is not None and he) else None
    db.execute("INSERT INTO velocity_log(agent_or_lane,period_start,period_end,tasks_done,hours_actual,hours_est,ratio) VALUES (?,?,?,?,?,?,?)",
               (lane, period_start, period_end, done, ha, he, ratio))
    log_event(db, "velocity_log", None, json.dumps({"lane": lane, "tasks_done": done})[:FIELD_CAP])
    db.commit()
    return {"lane": lane, "tasks_done": done, "hours_actual": ha,
            "hours_est": he, "ratio": ratio, "eta_samples_ok": done >= ETA_MIN_SAMPLES}

# ---------- CLI ----------

def cmd_apply(db, path):
    path = resolve_cli_path(path)
    with open(path) as f:
        rec = json.load(f)
    return apply_record(db, rec)

def cmd_spool(db, spool):
    spool = resolve_cli_path(spool, "spool")
    applied = os.path.join(spool, "applied"); rejected = os.path.join(spool, "rejected")
    os.makedirs(applied, exist_ok=True); os.makedirs(rejected, exist_ok=True)
    results = []
    for name in sorted(os.listdir(spool)):
        if not name.endswith(".json"):
            continue
        src = os.path.join(spool, name)
        # listdir names cannot contain '/', but a symlinked entry can point
        # outside the spool root - resolve and confine before opening.
        if not Path(src).resolve().is_relative_to(spool):
            res = {"applied": False, "reason": "symlink escape"}
            results.append((name, res))
            continue
        try:
            res = cmd_apply(db, src)
        except (json.JSONDecodeError, OSError):
            res = {"applied": False, "reason": "unparseable"}
        dest = applied if res.get("applied") else rejected
        shutil.move(src, os.path.join(dest, name))
        if not res.get("applied"):
            with open(os.path.join(rejected, name + ".reason"), "w") as f:
                f.write(str(res.get("reason")))
        results.append((name, res))
    return results

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("apply", "spool"):
        p = sub.add_parser(name); p.add_argument("path"); p.add_argument("--db", required=True)
    p = sub.add_parser("derive-velocity")
    p.add_argument("--lane", required=True); p.add_argument("--start", required=True)
    p.add_argument("--end", required=True); p.add_argument("--db", required=True)
    args = ap.parse_args(argv)
    db = open_db(args.db)
    try:
        if args.cmd == "apply":
            res = cmd_apply(db, args.path)
        elif args.cmd == "spool":
            res = cmd_spool(db, args.path)
        else:
            iso(args.start, "start"); iso(args.end, "end")
            res = derive_velocity(db, args.lane, args.start, args.end)
    except Reject as r:
        print(json.dumps({"applied": False, "reason": r.reason, "field": r.field}, indent=2))
        return 1
    finally:
        db.close()
    print(json.dumps(res, indent=2, default=str))
    if isinstance(res, dict) and not res.get("applied", True):
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
