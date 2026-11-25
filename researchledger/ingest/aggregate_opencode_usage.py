#!/usr/bin/env python3
"""
aggregate_opencode_usage.py — OpenCode Go usage-log aggregator.

Walks the opencode log files (and any log file the operator names) and writes
one row per usage event into the `opencode_usage` table of the session
ledger. Captures:
  - cached / uncached / reasoning token counts
  - 401 responses (with session-header presence as the waste indicator)
  - retries (count, reason)
  - per-profile / per-session attribution for the spend-agent one-profile proof

Schema columns (must match extract_sessions.opencode_usage):
  timestamp, profile, session_id, model, cached_tokens, uncached_tokens,
  reasoning_tokens, retry_count, http_status, session_header_present,
  quota_window, raw_line, source_path

No LLM, no secrets in raw_line. The "raw_line" is the original log line,
truncated to 8 KiB and stripped of any obvious bearer/key patterns.

Usage:
  python3 aggregate_opencode_usage.py [--db PATH] [--log-dir DIR] [--device mac|desk]
  # Also called automatically by extract_sessions.py after extract_opencode().
"""
import argparse
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# Same default db as extract_sessions
DEFAULT_DB = os.path.expanduser("~/Exports/analysis/session_ledger.sqlite")
DEFAULT_LOG_DIR_MAC = os.path.expanduser("~/.local/share/opencode/log")

# Logfmt key=value (with optional quoted strings) used by opencode.
KVAL_RE = re.compile(
    r'(?P<key>[a-zA-Z][a-zA-Z0-9._-]*)=(?:"(?P<qstr>(?:[^"\\]|\\.)*)"|(?P<bare>\S+))'
)
TS_RE = re.compile(r'timestamp=(?P<v>\S+)')
PROFILE_RE = re.compile(r'profile=(?P<v>\S+)')
HTTP_STATUS_RE = re.compile(r'http[._]status=(?P<v>\d{3})|status(?:_code)?=(?P<v2>\d{3})')
RETRY_RE = re.compile(r'\bretry(?:_count)?=(?P<v>\d+)|(?P<v3>\d+)\s+retries', re.IGNORECASE)
QUOTA_WINDOW_RE = re.compile(r'quota[._]?window=(?P<v>\S+)', re.IGNORECASE)
QUOTA_LIMITED_RE = re.compile(r'quota[._]?(?:limited|exceeded|exhausted)=(?P<v>true|1)', re.IGNORECASE)
SESSION_HEADER_RE = re.compile(r'x-opencode-session[_-]?(?:header|present)?=(?P<v>true|false|1|0)', re.IGNORECASE)
# Cached token block: "tokens.input=123 tokens.output=456 tokens.reasoning=0 tokens.cache.read=789 tokens.cache.write=12"
TOK_INPUT = re.compile(r'tokens\.input=(?P<v>\d+)')
TOK_OUTPUT = re.compile(r'tokens\.output=(?P<v>\d+)')
TOK_REASON = re.compile(r'tokens\.reasoning=(?P<v>\d+)')
TOK_CACHE_READ = re.compile(r'tokens\.cache\.read=(?P<v>\d+)')
TOK_CACHE_WRITE = re.compile(r'tokens\.cache\.write=(?P<v>\d+)')
COST_RE = re.compile(r'\bcost=(?P<v>\d+(?:\.\d+)?)')
SESSION_ID_RE = re.compile(r'\bid=(?P<v>ses_[A-Za-z0-9_]+)')
MODEL_ID_RE = re.compile(r'model\.id=(?P<v>\S+)')
PROVIDER_ID_RE = re.compile(r'model\.providerID=(?P<v>\S+)')

# Patterns that look like API keys / bearer tokens — strip from raw_line
SECRET_PATTERNS = [
    re.compile(r'(?i)bearer\s+[A-Za-z0-9_\-\.=]{8,}'),
    re.compile(r'sk-[A-Za-z0-9]{20,}'),
    re.compile(r'sk_[A-Za-z0-9]{20,}'),
    re.compile(r'ghp_[A-Za-z0-9]{20,}'),
    re.compile(r'xox[baprs]-[A-Za-z0-9-]{10,}'),
    re.compile(r'eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+'),  # JWT
]


def parse_kv(line: str):
    """Parse a logfmt-style line into a dict."""
    out = {}
    for m in KVAL_RE.finditer(line):
        k = m.group("key")
        v = m.group("qstr")
        if v is None:
            v = m.group("bare")
        out[k] = v
    return out


def strip_secrets(line: str) -> str:
    """Remove any obvious secret patterns from a log line. Truncate to 8 KiB."""
    s = line
    for pat in SECRET_PATTERNS:
        s = pat.sub("***REDACTED***", s)
    if len(s) > 8192:
        s = s[:8192] + "...[truncated]"
    return s


def detect_session_header(kv: dict) -> int:
    """0 = not present, 1 = present. Default to 0 if unknown (conservative)."""
    v = kv.get("x-opencode-session")
    if v is None:
        v = kv.get("x-opencode-session-header")
    if v is None:
        return 0  # unknown → conservative: assume missing (this is the "waste" case)
    return 1 if str(v).lower() in ("true", "1", "yes") else 0


def process_log_file(conn, log_path, profile=None):
    """Walk one opencode log file, emit rows into opencode_usage table."""
    n = 0
    if not os.path.isfile(log_path):
        return 0
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            if not raw_line.strip():
                continue
            line = raw_line.rstrip("\n")
            kv = parse_kv(line)
            if not kv:
                continue
            # Only consider lines that carry usage signals: token counts,
            # 401, retry, quota, or session-header. Skip pure trace logs.
            has_tokens = any(k.startswith("tokens.") for k in kv)
            # 401 detection MUST be structured. Raw `401 in line` matches
            # timestamps like `2026-07-30T10:34:48.401Z` (false positive on the
            # spend-agent's "78 401s" claim, corrected 2026-10-12 round-2).
            http_m_inner = HTTP_STATUS_RE.search(line)
            has_401 = (kv.get("http_status") == "401"
                       or kv.get("status") == "401"
                       or kv.get("response.status") == "401"
                       or (http_m_inner is not None
                           and (http_m_inner.group("v") == "401"
                                or http_m_inner.group("v2") == "401")))
            # retry: only when an explicit retry key or count is present
            has_retry = any(k in kv for k in ("retry", "retry_count", "attempt", "attempts", "retries"))
            has_quota = QUOTA_LIMITED_RE.search(line) is not None or QUOTA_WINDOW_RE.search(line) is not None
            if not (has_tokens or has_401 or has_retry or has_quota):
                continue
            ts_m = TS_RE.search(line)
            timestamp = ts_m.group("v") if ts_m else None
            # Skip pre-Apr-2025
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if dt.timestamp() < 1743465600:
                        continue
                except (ValueError, TypeError):
                    pass
            sid_m = SESSION_ID_RE.search(line)
            session_id = sid_m.group("v") if sid_m else kv.get("id")
            model_m = MODEL_ID_RE.search(line)
            provider_m = PROVIDER_ID_RE.search(line)
            # Profile: explicit profile= kwarg or "opencode-go" default for opencode logs
            prof = profile or (kv.get("profile") if kv.get("profile") else "opencode-go")
            cached = int(TOK_CACHE_READ.search(line).group("v")) if TOK_CACHE_READ.search(line) else None
            uncached = None
            in_tok = TOK_INPUT.search(line)
            if in_tok:
                uncached = int(in_tok.group("v"))
            reason = int(TOK_REASON.search(line).group("v")) if TOK_REASON.search(line) else None
            retry_m = RETRY_RE.search(line)
            retry_count = int(retry_m.group("v") or retry_m.group("v3") or 0) if retry_m else 0
            http_m = HTTP_STATUS_RE.search(line)
            http_status = int(http_m.group("v") or http_m.group("v2")) if http_m else (401 if has_401 else None)
            qwin_m = QUOTA_WINDOW_RE.search(line)
            quota_window = qwin_m.group("v") if qwin_m else None
            sess_header = detect_session_header(kv)
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO opencode_usage
                    (timestamp, profile, session_id, model, cached_tokens,
                     uncached_tokens, reasoning_tokens, retry_count,
                     http_status, session_header_present, quota_window,
                     raw_line, source_path)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        timestamp, prof, session_id,
                        model_m.group("v") if model_m else None,
                        cached, uncached, reason, retry_count, http_status,
                        sess_header, quota_window,
                        strip_secrets(line), log_path,
                    ),
                )
                n += 1
            except sqlite3.Error as e:
                print(f"[warn] insert failed for {log_path}: {e}", file=sys.stderr)
                continue
    conn.commit()
    return n


def main_with_args(db, log_dir, device="mac", profile="opencode-go"):
    """Programmatic entry point (used by extract_sessions.py)."""
    if not os.path.isfile(db):
        print(f"[warn] db not found, skipping opencode aggregation: {db}", file=sys.stderr)
        return 0
    if not os.path.isdir(log_dir):
        print(f"[warn] log dir not found, skipping opencode aggregation: {log_dir}",
              file=sys.stderr)
        return 0
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS opencode_usage (
            rowid INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, profile TEXT, session_id TEXT, model TEXT,
            cached_tokens INTEGER, uncached_tokens INTEGER, reasoning_tokens INTEGER,
            retry_count INTEGER, http_status INTEGER, session_header_present INTEGER,
            quota_window TEXT, raw_line TEXT, source_path TEXT,
            UNIQUE (timestamp, profile, session_id, raw_line)
        )
    """
    )
    # Re-aggregation safety: DELETE prior rows for this device/profile so the
    # re-run replaces instead of duplicating. (sessions table uses INSERT OR
    # REPLACE on its PK; opencode_usage had no PK so re-runs doubled rows.)
    cur = conn.execute(
        "DELETE FROM opencode_usage WHERE profile = ? AND source_path LIKE ?",
        (profile, log_dir.replace("\\", "\\\\") + "%"),
    )
    n_purged = cur.rowcount
    if n_purged:
        print(f"  [opencode] purged {n_purged} prior rows for re-run safety", file=sys.stderr)
    t0 = time.time()
    total = 0
    files = sorted([f for f in os.listdir(log_dir) if f.endswith(".log")])
    for fname in files:
        fpath = os.path.join(log_dir, fname)
        n = process_log_file(conn, fpath, profile=profile)
        if n:
            print(f"  [{device}/opencode] {fname}: {n} usage events")
        total += n
    conn.commit()
    print(f"=== opencode_usage: {total} rows in {time.time()-t0:.1f}s ===")
    # Spend-agent one-profile proof summary
    summary = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN http_status = 401 THEN 1 ELSE 0 END) AS n_401,
            SUM(CASE WHEN http_status = 401 AND session_header_present = 0 THEN 1 ELSE 0 END) AS n_401_no_header,
            SUM(retry_count) AS total_retries,
            SUM(cached_tokens) AS sum_cached,
            SUM(uncached_tokens) AS sum_uncached
        FROM opencode_usage
        """
    ).fetchone()
    print(f"  total events: {summary[0]}")
    print(f"  401 responses: {summary[1]}")
    print(f"  401 + missing session-header (waste): {summary[2]}")
    print(f"  total retries: {summary[3]}")
    print(f"  cached tokens: {summary[4] or 0}")
    print(f"  uncached tokens: {summary[5] or 0}")
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--log-dir", default=DEFAULT_LOG_DIR_MAC,
                    help="Directory of *.log files")
    ap.add_argument("--device", default="mac", choices=["mac", "desk"])
    ap.add_argument("--profile", default="opencode-go")
    args = ap.parse_args()

    if not os.path.isfile(args.db):
        print(f"[err] db not found: {args.db}", file=sys.stderr)
        return 1
    if not os.path.isdir(args.log_dir):
        print(f"[err] log dir not found: {args.log_dir}", file=sys.stderr)
        return 0
    conn = sqlite3.connect(args.db)
    # Ensure opencode_usage table exists
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS opencode_usage (
            rowid INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            profile TEXT,
            session_id TEXT,
            model TEXT,
            cached_tokens INTEGER,
            uncached_tokens INTEGER,
            reasoning_tokens INTEGER,
            retry_count INTEGER,
            http_status INTEGER,
            session_header_present INTEGER,
            quota_window TEXT,
            raw_line TEXT,
            source_path TEXT
        )
    """
    )
    t0 = time.time()
    main_with_args(db=args.db, log_dir=args.log_dir, device=args.device,
                    profile=args.profile)
    return 0


if __name__ == "__main__":
    sys.exit(main())
