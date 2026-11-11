#!/usr/bin/env python3
"""
jcode_extractor.py — Jcode/Kcode source extraction (4 sources).

Split out of extractors.py in round-4 to keep that file under the AGENTS.md
500-line hard limit. The 4 sources are:

  1. client_sessions/<pid>            FILE per PID, content = session_id
  2. client-input-session_*           FILES at jcode_root, mtime = activity
  3. state/swarm/session_<sid>.json   SESSION STATE FILES (rich metadata)
  4. ambient/transcripts/<ts>.json    AMBIENT transcripts (jcode only)

Filter: started_at >= 2025-04-01 UTC (epoch 1743465600).

Round-5 (W4-2): decomposed the 178-line extract_jcode monolith into 4
single-source helpers + a thin orchestrator. Each helper ≤50 lines. The
orchestrator owns the seen_sids set so the same session id is never double-
counted across sources.
"""
import json
import os
import sqlite3
from datetime import datetime

from extractors import APR_1_2025, _host, _read_text_file, _ts, insert_session


def _is_after_apr_2025(epoch_or_iso):
    """Return True if epoch (float) or ISO string is on/after 2025-04-01 UTC.

    Used by all 4 jcode source helpers to apply the round-3 filter rule.
    Returns True for unparseable timestamps (we err on the side of including).
    """
    if epoch_or_iso is None:
        return True
    try:
        if isinstance(epoch_or_iso, (int, float)):
            return epoch_or_iso >= APR_1_2025
        dt = datetime.fromisoformat(str(epoch_or_iso).replace("Z", "+00:00"))
        return dt.timestamp() >= APR_1_2025
    except (ValueError, TypeError):
        return True


def _extract_client_sessions(conn, device, jcode_root, harness, host, seen_sids):
    """Source 1: client_sessions/<pid> (file content = session_id). Returns n added."""
    cs_root = os.path.join(jcode_root, "client_sessions")
    if not os.path.isdir(cs_root):
        return 0
    n = 0
    for fname in os.listdir(cs_root):
        fpath = os.path.join(cs_root, fname)
        if not os.path.isfile(fpath):
            continue
        sid = _read_text_file(fpath, max_bytes=512)
        if not sid or not sid.startswith("session_"):
            continue
        try:
            mtime = os.path.getmtime(fpath)
        except OSError:
            continue
        if not _is_after_apr_2025(mtime):
            continue
        if sid in seen_sids:
            continue
        seen_sids.add(sid)
        insert_session(
            conn, harness=harness, session_id=sid, device=device, host=host,
            started_at=_ts(mtime), ended_at=None, title=None, model=None,
            provider=None, tokens_total=None, cwd=None, git_branch=None,
            path=fpath, extra_json=json.dumps({"source_kind": "client_session_pid"}),
        )
        n += 1
    return n


def _extract_client_input(conn, device, jcode_root, harness, host, seen_sids):
    """Source 2: client-input-session_* files at jcode_root (mtime = activity)."""
    if not os.path.isdir(jcode_root):
        return 0
    n = 0
    for fname in os.listdir(jcode_root):
        if not fname.startswith("client-input-session_"):
            continue
        fpath = os.path.join(jcode_root, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            mtime = os.path.getmtime(fpath)
        except OSError:
            continue
        if not _is_after_apr_2025(mtime):
            continue
        sid = fname[len("client-input-session_"):]
        if sid in seen_sids:
            continue
        seen_sids.add(sid)
        insert_session(
            conn, harness=harness, session_id=sid, device=device, host=host,
            started_at=_ts(mtime), ended_at=None, title=None, model=None,
            provider=None, tokens_total=None, cwd=None, git_branch=None,
            path=fpath, extra_json=json.dumps({"source_kind": "client_input"}),
        )
        n += 1
    return n


def _extract_state_swarm(conn, device, jcode_root, harness, host, seen_sids):
    """Source 3: state/swarm/session_<sid>.json (best metadata).

    Parses the JSON for started_at / model / provider / cwd / git_branch.
    Falls back to mtime if JSON parse fails or timestamps are missing.
    """
    swarm_root = os.path.join(jcode_root, "state", "swarm")
    if not os.path.isdir(swarm_root):
        return 0
    n = 0
    for fname in os.listdir(swarm_root):
        if not fname.startswith("session_") or not fname.endswith(".json"):
            continue
        fpath = os.path.join(swarm_root, fname)
        if not os.path.isfile(fpath):
            continue
        sid = fname[len("session_"):-len(".json")]
        if sid in seen_sids:
            continue
        seen_sids.add(sid)
        extra = {"source_kind": "state_swarm"}
        started_iso = model = provider = cwd = branch = None
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k in ("created_at", "createdAt", "started_at", "startedAt", "time_created"):
                    if k in data:
                        started_iso = data[k]
                        break
                m = data.get("model")
                model = m.get("id") if isinstance(m, dict) else m
                provider = data.get("provider") or data.get("model_provider")
                cwd = data.get("cwd") or data.get("directory")
                branch = data.get("git_branch") or data.get("gitBranch")
                extra["status"] = data.get("status")
                extra["role"] = data.get("role")
                if isinstance(data.get("tokens"), dict):
                    extra["tokens"] = data["tokens"]
        except (OSError, ValueError):
            pass
        if not started_iso:
            try:
                mtime = os.path.getmtime(fpath)
                started_iso = _ts(mtime)
                if not _is_after_apr_2025(mtime):
                    continue
            except OSError:
                pass
        elif not _is_after_apr_2025(started_iso):
            continue
        toks = extra.get("tokens", {})
        try:
            tokens_total = sum(int(v) for v in toks.values() if isinstance(v, (int, float))) or None
        except (ValueError, TypeError):
            tokens_total = None
        insert_session(
            conn, harness=harness, session_id=sid, device=device, host=host,
            started_at=started_iso, ended_at=None, title=None, model=model,
            provider=provider, tokens_total=tokens_total, cwd=cwd,
            git_branch=branch, path=fpath, extra_json=json.dumps(extra),
        )
        n += 1
    return n


def _extract_ambient(conn, device, jcode_root, harness, host, seen_sids):
    """Source 4: ambient/transcripts/<ts>.json (jcode only)."""
    amb_root = os.path.join(jcode_root, "ambient", "transcripts")
    if not os.path.isdir(amb_root):
        return 0
    n = 0
    for fname in os.listdir(amb_root):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(amb_root, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            mtime = os.path.getmtime(fpath)
        except OSError:
            continue
        if not _is_after_apr_2025(mtime):
            continue
        sid = "ambient-" + fname[:-5]
        if sid in seen_sids:
            continue
        seen_sids.add(sid)
        insert_session(
            conn, harness=harness, session_id=sid, device=device, host=host,
            started_at=_ts(mtime), ended_at=None, title=None, model=None,
            provider=None, tokens_total=None, cwd=None, git_branch=None,
            path=fpath, extra_json=json.dumps({"source_kind": "ambient"}),
        )
        n += 1
    return n


def extract_jcode(conn, device, jcode_root, harness_name="jcode"):
    """Jcode / Kcode orchestrator: runs all 4 source helpers in order.

    Filter: started_at >= 2025-04-01 UTC (round-3 invariant).
    Dedup: seen_sids set is shared across all 4 helpers so each session id
    is inserted at most once.
    """
    harness = harness_name
    host = _host() if device == "mac" else "kooshapari-desk"
    seen_sids = set()
    n = 0
    n += _extract_client_sessions(conn, device, jcode_root, harness, host, seen_sids)
    n += _extract_client_input(conn, device, jcode_root, harness, host, seen_sids)
    n += _extract_state_swarm(conn, device, jcode_root, harness, host, seen_sids)
    n += _extract_ambient(conn, device, jcode_root, harness, host, seen_sids)
    conn.commit()
    return n


# --------------------------------------------------------------- HELIOSLITE -
