#!/usr/bin/env python3
"""
extractors.py — Per-harness extractors for the session ledger.

Each extract_* function is a pure function of (sqlite connection, device, source_path)
that returns the count of rows written. No I/O outside the source path; no LLM.

Schema (open_db, insert_session) lives in extract_sessions.py — this file only
contains the 7 per-harness extractors and their text-reading helpers.

Constraints (round-1+ verified):
  s7  Read-only on sources. codex sqlite is opened with file:?mode=ro.
  s8  Apr 2025+ filter (epoch >= 1743465600).
  s9  No secrets: strip_secrets() truncates and redacts raw_line at write-time.
"""
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import zstandard as zstd
from datetime import datetime, timezone
from pathlib import Path

from ledger_db import open_db, insert_session

# Apr 1, 2025 in Unix epoch seconds (sqlite integer convention for codex)
APR_1_2025 = 1743465600
APR_1_2025_ISO = "2025-04-01T00:00:00+00:00"

# Output database (single file, both devices)
DEFAULT_DB = os.path.expanduser("~/Exports/analysis/session_ledger.sqlite")

# Round-4: _ts and _host moved here from extract_sessions.py
def _ts(epoch_sec):
    """epoch_sec -> ISO 8601 UTC string, or None."""
    if not epoch_sec:
        return None
    try:
        return datetime.fromtimestamp(int(epoch_sec), tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OSError):
        return None


def _host():
    return socket.gethostname()



def extract_codex(conn, device, codex_root):
    """
    Codex sources:
      state_5.sqlite:    threads table (rich metadata)
      sessions/*.jsonl.zst: rollouts (one per thread, jsonl inside zstd)
      session-archive/logs/codex-tui.log.*.zst: archived TUI logs (not rollouts)
    Filter: created_at >= 1743465600 (2025-04-01 UTC)
    """
    harness = "codex"
    state_db = os.path.join(codex_root, "state_5.sqlite")
    if not os.path.isfile(state_db):
        return 0
    # READ-ONLY URI mode
    uri = f"file:{state_db}?mode=ro"
    src = sqlite3.connect(uri, uri=True)
    src.row_factory = sqlite3.Row
    cur = src.execute(
        """
        SELECT id, created_at, updated_at, title, model, model_provider,
               tokens_used, cwd, git_branch, source
        FROM threads
        WHERE created_at >= ?
        ORDER BY created_at
        """,
        (APR_1_2025,),
    )
    n = 0
    for r in cur:
        sid = r["id"]
        started = _ts(r["created_at"])
        ended = _ts(r["updated_at"]) if r["updated_at"] and r["updated_at"] != r["created_at"] else None
        title = r["title"] or None
        # Titles are kept verbatim from source. No LLM reads this column; secrets
        # are stripped separately at write-time (see strip_secrets in insert_session).
        # Schema column is TEXT, no length cap. The 500-char truncation removed
        # in round-4 was a defensive default that destroyed data fidelity.
        insert_session(
            conn,
            harness=harness,
            session_id=sid,
            device=device,
            host=_host() if device == "mac" else "kooshapari-desk",
            started_at=started,
            ended_at=ended,
            title=title,
            model=r["model"],
            provider=r["model_provider"],
            tokens_total=r["tokens_used"] if r["tokens_used"] else None,
            cwd=r["cwd"],
            git_branch=r["git_branch"],
            path=state_db,
            extra_json=json.dumps({"source": r["source"]}) if r["source"] else None,
        )
        n += 1
    src.close()
    conn.commit()
    return n


# ----------------------------------------------------------------- CLAUDE ----
CLAUDE_USER_RE = re.compile(rb'"sessionId"\s*:\s*"([0-9a-f-]{36})"')
CLAUDE_TS_RE = re.compile(rb'"timestamp"\s*:\s*"([^"]+)"')
CLAUDE_CWD_RE = re.compile(rb'"cwd"\s*:\s*"([^"]+)"')
CLAUDE_MODEL_RE = re.compile(rb'"model"\s*:\s*"([^"]+)"')
CLAUDE_BRANCH_RE = re.compile(rb'"gitBranch"\s*:\s*"([^"]+)"')


def _first_jsonl_match(path, regex, max_bytes=8 * 1024 * 1024):
    """Read up to max_bytes of a jsonl file, return first regex match group(1)."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(max_bytes)
        m = regex.search(chunk)
        return m.group(1).decode("utf-8", errors="replace") if m else None
    except OSError:
        return None


def _all_jsonl_matches(path, regex, max_bytes=64 * 1024 * 1024, limit=10):
    """Yield up to `limit` regex matches from a jsonl file (first max_bytes)."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(max_bytes)
        for i, m in enumerate(regex.finditer(chunk)):
            if i >= limit:
                break
            try:
                yield m.group(1).decode("utf-8", errors="replace")
            except (IndexError, AttributeError):
                pass
    except OSError:
        return


def extract_claude(conn, device, claude_root):
    """
    Claude source: ~/.claude/projects/*/<sessionId>.jsonl
    Each file is a session. Extract sessionId, first timestamp, cwd, model.
    """
    harness = "claude"
    projects = os.path.join(claude_root, "projects")
    if not os.path.isdir(projects):
        return 0
    n = 0
    for project_dir in os.listdir(projects):
        pdir = os.path.join(projects, project_dir)
        if not os.path.isdir(pdir):
            continue
        for fname in os.listdir(pdir):
            if not fname.endswith(".jsonl"):
                continue
            fpath = os.path.join(pdir, fname)
            # sessionId is the filename (without .jsonl) for claude
            sid = os.path.splitext(fname)[0]  # .jsonl is 5 chars
            if not re.match(r"^[0-9a-f-]{36}$", sid):
                continue
            ts = _first_jsonl_match(fpath, CLAUDE_TS_RE)
            cwd = _first_jsonl_match(fpath, CLAUDE_CWD_RE)
            model = _first_jsonl_match(fpath, CLAUDE_MODEL_RE)
            # Branch can appear on multiple lines; take first
            branch = None
            for b in _all_jsonl_matches(fpath, CLAUDE_BRANCH_RE, limit=1):
                branch = b
                break
            # Apr 2025 filter: parse ts
            keep = True
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if dt.timestamp() < APR_1_2025:
                        keep = False
                except (ValueError, TypeError):
                    pass
            if not keep:
                continue
            insert_session(
                conn,
                harness=harness,
                session_id=sid,
                device=device,
                host=_host() if device == "mac" else "kooshapari-desk",
                started_at=ts,
                ended_at=None,
                title=None,
                model=model,
                provider=None,
                tokens_total=None,
                cwd=cwd,
                git_branch=branch,
                path=fpath,
                extra_json=json.dumps({"project": project_dir}),
            )
            n += 1
    conn.commit()
    return n


# ------------------------------------------------------------------ GEMINI --
def extract_gemini(conn, device, gemini_root):
    """
    Gemini: ~/<config>, no session data. The actual session data is in
    ~/Library/Application Support/Google/... or in Takeout exports. We
    record the config paths but no rows.
    """
    # Just check existence; no rows
    return 0


# ------------------------------------------------------------------- JCODE --
def _read_text_file(path, max_bytes=512):
    """Read up to max_bytes from a text file. Strips trailing whitespace."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(max_bytes).strip()
    except OSError:
        return ""


def extract_helioslite(conn, device, hl_root):
    """
    Helioslite: ~/.helioslite/logs/*.log (mostly empty in current install).
    Each non-empty log = 1 session.
    """
    harness = "helioslite"
    n = 0
    logs = os.path.join(hl_root, "logs")
    if not os.path.isdir(logs):
        return 0
    for fname in os.listdir(logs):
        fpath = os.path.join(logs, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            size = os.path.getsize(fpath)
            mtime = os.path.getmtime(fpath)
        except OSError:
            continue
        if size == 0:
            continue
        started = _ts(mtime)
        if started:
            try:
                dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                if dt.timestamp() < APR_1_2025:
                    continue
            except (ValueError, TypeError):
                pass
        sid = fname
        insert_session(
            conn,
            harness=harness,
            session_id=sid,
            device=device,
            host=_host() if device == "mac" else "kooshapari-desk",
            started_at=started,
            ended_at=None,
            title=None,
            model=None,
            provider=None,
            tokens_total=None,
            cwd=None,
            git_branch=None,
            path=fpath,
            extra_json=json.dumps({"size": size}),
        )
        n += 1
    conn.commit()
    return n


# ----------------------------------------------------------------- OPENCODE -
def extract_opencode(conn, device, opencode_log_dir, harness_name="opencode"):
    """
    Opencode source: ~/.local/share/opencode/log/opencode.log + dated logs.
    Each "message=created id=ses_..." line = 1 session.
    """
    harness = harness_name
    n = 0
    if not os.path.isdir(opencode_log_dir):
        return 0
    SID_RE = re.compile(rb'message=created\s+id=(ses_[A-Za-z0-9]+)')
    TS_RE = re.compile(rb'timestamp=(\S+)')
    MODEL_RE = re.compile(rb'model\.id=([^\s]+)')
    PROVIDER_RE = re.compile(rb'model\.providerID=([^\s]+)')
    TITLE_RE = re.compile(rb'title=("([^"]*)"|(\S+))')
    DIR_RE = re.compile(rb'directory=(\S+)')
    INPUT_TOK_RE = re.compile(rb'tokens\.input=(\d+)')
    OUTPUT_TOK_RE = re.compile(rb'tokens\.output=(\d+)')
    CACHE_READ_RE = re.compile(rb'tokens\.cache\.read=(\d+)')
    CACHE_WRITE_RE = re.compile(rb'tokens\.cache\.write=(\d+)')
    REASON_TOK_RE = re.compile(rb'tokens\.reasoning=(\d+)')
    for fname in sorted(os.listdir(opencode_log_dir)):
        fpath = os.path.join(opencode_log_dir, fname)
        if not os.path.isfile(fpath) or not fname.endswith(".log"):
            continue
        try:
            with open(fpath, "rb") as f:
                for line in f:
                    sid_m = SID_RE.search(line)
                    if not sid_m:
                        continue
                    sid = sid_m.group(1).decode("ascii")
                    ts_m = TS_RE.search(line)
                    started = ts_m.group(1).decode("ascii") if ts_m else None
                    if started:
                        try:
                            dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                            if dt.timestamp() < APR_1_2025:
                                continue
                        except (ValueError, TypeError):
                            pass
                    model_m = MODEL_RE.search(line)
                    provider_m = PROVIDER_RE.search(line)
                    title_m = TITLE_RE.search(line)
                    dir_m = DIR_RE.search(line)
                    in_tok_m = INPUT_TOK_RE.search(line)
                    out_tok_m = OUTPUT_TOK_RE.search(line)
                    cr_m = CACHE_READ_RE.search(line)
                    cw_m = CACHE_WRITE_RE.search(line)
                    rs_m = REASON_TOK_RE.search(line)
                    title = None
                    if title_m:
                        title = title_m.group(2).decode("utf-8", errors="replace") if title_m.group(2) else (title_m.group(3).decode("utf-8", errors="replace") if title_m.group(3) else None)
                    cwd = dir_m.group(1).decode("utf-8", errors="replace") if dir_m else None
                    tot = 0
                    for tm in (in_tok_m, out_tok_m, cr_m, cw_m, rs_m):
                        if tm:
                            try:
                                tot += int(tm.group(1))
                            except ValueError:
                                pass
                    extra = {
                        "cache_read": int(cr_m.group(1)) if cr_m else 0,
                        "cache_write": int(cw_m.group(1)) if cw_m else 0,
                    }
                    insert_session(
                        conn,
                        harness=harness,
                        session_id=sid,
                        device=device,
                        host=_host() if device == "mac" else "kooshapari-desk",
                        started_at=started,
                        ended_at=None,
                        title=title if title else None,
                        model=model_m.group(1).decode("ascii") if model_m else None,
                        provider=provider_m.group(1).decode("ascii") if provider_m else None,
                        tokens_total=tot if tot else None,
                        cwd=cwd,
                        git_branch=None,
                        path=fpath,
                        extra_json=json.dumps(extra),
                    )
                    n += 1
        except OSError:
            continue
    conn.commit()
    return n


# ---------------------------------------------------------------- DRIVER ----

# Re-export extract_jcode from jcode_extractor.py (round-4 split).
# Round-5 (W4-2): made lazy via __getattr__ to avoid the circular import
# that occurs when callers do `import jcode_extractor` before extractors has
# finished loading (jcode_extractor imports APR_1_2025 from extractors at
# module top, so extractors must complete first).
def __getattr__(name):  # PEP 562 module-level __getattr__
    if name == "extract_jcode":
        from jcode_extractor import extract_jcode
        return extract_jcode
    raise AttributeError(f"module 'extractors' has no attribute {name!r}")
