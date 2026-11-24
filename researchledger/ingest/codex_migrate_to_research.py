"""
codex_migrate_to_research.py — pump ~/.codex/sessions/**/rollout-*.jsonl → migrated_codex_*

Codex is the OpenAI Codex CLI. Session format is COMPLETELY different from
jcode/kcode (and from each session having one .json file):

  - One .jsonl file per snapshot; many snapshots per session_id
  - One LINE per event (not per message)
  - 8 line types: session_meta, event_msg, response_item, world_state,
    turn_context, token_usage_record, inter_agent_communication_metadata,
    compacted
  - response_item.payload.type discriminates: "message" (user/assistant/
    developer text), "reasoning", "function_call", "function_call_output",
    "custom_tool_call", "agent_message"
  - Model name lives in turn_context.payload.model (one per turn, may vary
    across turns in the same session)
  - Token totals in token_usage_record lines (per-response usage field)

We use the LARGEST .jsonl per session_id as the canonical snapshot
(smaller files are intermediate states; the largest is most complete).

Snapshot files come in THREE forms and all are accepted:
  - rollout-*.jsonl            plain text (older installs)
  - rollout-*.jsonl.zst        zstd-compressed (modern installs, the majority)
  - rollout-*.jsonl.zst.zst    double-compressed (a handful of files)
`rollout-*.jsonl*` is matched and every `.zst` layer is decompressed while
streaming (via the `zstandard` module when importable, else `zstd -dc`).

Older 2025-07 snapshots are single-line stubs of the form
`{"id": "<uuid>", "timestamp": "..."}` with no `type` field. For those the
session id falls back to that top-level `id`, so the session is still
recorded (with zero parsed messages) instead of being silently dropped.

Encrypted inter-agent messages (4,588 lines with `encrypted_content`) are
skipped — we can't decrypt them. They're a small fraction of the corpus.

Default --since 2026-09-01; pass --since 2000-01-01 for the full store
(the on-disk corpus starts 2025-07-16).

Idempotent: 2nd run inserts 0 rows. Source row check-then-insert (avoids
the auto-increment INSERT OR IGNORE bug discovered in jcode W9).
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sqlite3
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from migrator_base import add_common_args, register_source
import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from researchledger import corpus_guard  # noqa: E402
from researchledger.corpus_guard import guard_write_target  # noqa: E402

# Re-export the response-item parser so callers can still write
# `from codex_migrate_to_research import parse_response_item`.
from codex_response_parser import (
    LEGACY_TOP_LEVEL_TYPES,
    adapt_legacy_line,
    parse_message_content,
    parse_response_item,
)

DEFAULT_DB = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"
DEFAULT_SESSIONS_DIR = Path.home() / ".codex" / "sessions"
DEFAULT_SINCE = "2026-09-01T00:00:00Z"

SESSION_UUID_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.I
)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def zst_depth(path: Path) -> int:
    """Number of trailing `.zst` layers on a file name (0, 1 or 2)."""
    name = path.name
    depth = 0
    while name.endswith(".zst"):
        depth += 1
        name = name[: -len(".zst")]
    return depth


@contextmanager
def open_rollout(path: Path):
    """Open a rollout file as text, decompressing any `.zst` layers.

    Streams; never reads a whole file into memory to decompress it.
    """
    depth = zst_depth(path)
    if depth == 0:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            yield fh
        return

    try:
        import zstandard  # type: ignore
    except ImportError:
        zstandard = None

    if zstandard is not None:
        raw = open(path, "rb")
        stream = raw
        try:
            for _ in range(depth):
                stream = zstandard.ZstdDecompressor().stream_reader(
                    stream, read_across_frames=True
                )
            yield io.TextIOWrapper(stream, encoding="utf-8", errors="replace")
        finally:
            stream.close()
            raw.close()
        return

    # Fallback: one `zstd -dc` process per layer.
    procs = []
    stdin = None
    for i in range(depth):
        cmd = ["zstd", "-dc", str(path)] if i == 0 else ["zstd", "-dc"]
        p = subprocess.Popen(
            cmd,
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        procs.append(p)
        stdin = p.stdout
    try:
        yield io.TextIOWrapper(stdin, encoding="utf-8", errors="replace")
    finally:
        if stdin is not None:
            stdin.close()
        for p in procs:
            try:
                p.wait(timeout=30)
            except subprocess.TimeoutExpired:
                p.kill()


def peek_session_id(path: Path) -> str | None:
    """Session id for a rollout file, read from the head of the stream.

    Prefers a `session_meta` line. Falls back to a top-level `id` on a line
    with no `type` (the 2025-07 single-line snapshot stubs), then to the first
    UUID in the file name.
    """
    first_obj = None
    try:
        with open_rollout(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(d, dict):
                    continue
                if first_obj is None:
                    first_obj = d
                if d.get("type") == "session_meta":
                    sid = d.get("payload", {}).get("session_id")
                    if sid:
                        return sid
                elif "type" not in d and isinstance(d.get("id"), str):
                    return d["id"]
    except OSError:
        return None

    if isinstance(first_obj, dict) and isinstance(first_obj.get("id"), str):
        return first_obj["id"]
    m = SESSION_UUID_RE.search(path.name)
    return m.group(1) if m else None


def find_largest_per_session(files: list[Path]) -> dict[str, tuple[Path, int]]:
    """
    Group files by session_id (extracted from first session_meta line).
    Return {session_id: (largest_file, snapshot_count)}.
    """
    from collections import defaultdict
    sid_to_files: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        sid = peek_session_id(f)
        if not sid:
            continue
        sid_to_files[sid].append(f)

    return {
        sid: (
            max(group, key=lambda p: p.stat().st_size),
            len(group),
        )
        for sid, group in sid_to_files.items()
    }


def should_keep_session(session_meta_payload: dict, since_iso: str) -> bool:
    ts = session_meta_payload.get("timestamp", "")
    return bool(ts) and ts >= since_iso


def migrate(db_path: Path, sessions_dir: Path, since_iso: str) -> dict:
    # The corpus may be under concurrent write from another builder; WAL plus a
    # 60s busy timeout lets this writer wait instead of failing immediately.
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")

    # Idempotent source row
    today = now_iso()
    src_id = register_source(
        conn,
        kind="codex",
        base_path=str(sessions_dir),
        byte_size=0,
        captured_at=today,
        notes='~/.codex/sessions/**/rollout-*.jsonl* (OpenAI Codex CLI; zstd-compressed rollouts decompressed on read; largest file per session_id)',
    )
    conn.commit()
    print(f"  source id: {src_id} (kind=codex)")

    existing_sess = {r[0] for r in conn.execute(
        "SELECT external_id FROM migrated_codex_sessions").fetchall()}
    existing_msg = {r[0] for r in conn.execute(
        "SELECT external_id FROM migrated_codex_messages").fetchall()}
    print(f"  existing sessions in DB: {len(existing_sess):,}")
    print(f"  existing messages in DB: {len(existing_msg):,}")

    files = sorted(sessions_dir.rglob("rollout-*.jsonl*"))
    n_zst = sum(1 for f in files if zst_depth(f))
    print(f"  source rollout files: {len(files):,} ({n_zst:,} zstd-compressed)")

    # Group by session_id, pick largest per session
    print(f"  grouping by session_id...")
    sid_to_largest = find_largest_per_session(files)
    print(f"  unique sessions: {len(sid_to_largest):,}")
    print(f"  total snapshots: {sum(c for _, c in sid_to_largest.values()):,}")

    cur = conn.cursor()
    n_sess_inserted = 0
    n_sess_skipped = 0
    n_sess_filtered = 0
    n_msg_inserted = 0
    n_msg_skipped = 0
    n_parse_errors = 0
    n_empty = 0
    total_input = 0
    total_output = 0
    total_cache = 0

    for i, (sid, (largest_file, snapshot_count)) in enumerate(sid_to_largest.items(), 1):
        try:
            with open_rollout(largest_file) as fh:
                lines = []
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        lines.append(json.loads(raw))
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            n_parse_errors += 1
            if n_parse_errors <= 5:
                print(f"  WARN parse error in {largest_file}: {e}")
            continue

        # Find session_meta (first one)
        session_meta = None
        for l in lines:
            if l.get("type") == "session_meta":
                session_meta = l.get("payload", {})
                break
        if not session_meta:
            # Older single-line snapshot stubs carry no session_meta line; keep
            # the session (zero messages) using the id we already resolved.
            ts = ""
            for l in lines:
                ts = l.get("timestamp", "")
                if ts:
                    break
            session_meta = {"session_id": sid, "timestamp": ts}

        if not should_keep_session(session_meta, since_iso):
            n_sess_filtered += 1
            continue

        sess_ext = f"codex_session:{sid}"
        if sess_ext in existing_sess:
            n_sess_skipped += 1
            continue

        # Last turn_context's model (most recent model used)
        model = None
        reasoning_effort = None
        for l in lines:
            if l.get("type") == "turn_context":
                p = l.get("payload", {})
                if p.get("model"):
                    model = p["model"]
                if p.get("effort"):
                    reasoning_effort = p["effort"]

        # Aggregate token usage from token_usage_record lines
        in_t = out_t = cache_t = 0
        for l in lines:
            if l.get("type") == "token_usage_record":
                usage = l.get("payload", {}).get("usage", {})
                in_t += int(usage.get("input_tokens", 0) or 0)
                out_t += int(usage.get("output_tokens", 0) or 0)
                cache_t += int(usage.get("cached_input_tokens", 0) or 0)

        # Last timestamp (most recent event)
        last_ts = session_meta.get("timestamp", "")
        for l in lines:
            ts = l.get("timestamp", "")
            if ts and ts > last_ts:
                last_ts = ts

        # Parse all response_items into messages. Legacy (2025-era) lines carry
        # the event type at the top level; adapt them into the payload shape.
        session_ts = session_meta.get("timestamp") or ""
        messages = []
        for ord_i, l in enumerate(lines):
            lt = l.get("type")
            if lt == "response_item":
                m = parse_response_item(l)
            elif lt in LEGACY_TOP_LEVEL_TYPES:
                adapted = adapt_legacy_line(l, ord_i)
                m = parse_response_item(adapted) if adapted else None
            else:
                m = None
            if m is not None:
                # Legacy event lines carry no timestamp; fall back to the
                # session timestamp so the row is never undated.
                m["timestamp_iso"] = l.get("timestamp") or session_ts
                messages.append(m)

        n_msgs = len(messages)
        if not n_msgs:
            n_empty += 1

        # Insert session row
        # source may be str (e.g. "cli", "vscode", "exec") OR dict with
        # subagent thread_spawn info (most sub-agent threads).
        raw_source = session_meta.get("source")
        source_str: str | None
        source_meta_json: str | None = None
        subagent_parent_id: str | None = None
        subagent_nickname: str | None = None
        subagent_role: str | None = None
        subagent_path: str | None = None
        if isinstance(raw_source, dict):
            source_str = "subagent"
            source_meta_json = json.dumps(raw_source, ensure_ascii=False)
            spawn = raw_source.get("subagent", {}).get("thread_spawn", {})
            subagent_parent_id = spawn.get("parent_thread_id")
            subagent_nickname = spawn.get("agent_nickname")
            subagent_role = spawn.get("agent_role")
            subagent_path = spawn.get("agent_path")
        elif isinstance(raw_source, str):
            source_str = raw_source
        else:
            source_str = None

        cur.execute("""
            INSERT INTO migrated_codex_sessions (
                external_id, session_id, title, parent_id,
                provider_key, provider_session_id, model, reasoning_effort,
                subagent_model, is_canary, is_debug, working_dir, status_json,
                created_at, updated_at, last_active_at, message_count,
                total_input_tokens, total_output_tokens, total_cache_read_tokens,
                cli_version, source, originator, source_meta_json,
                subagent_parent_id, subagent_nickname, subagent_role, subagent_path,
                source_path, snapshot_count, rollup_size_bytes
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            sess_ext, sid, None, None,
            session_meta.get("model_provider"), sid, model, reasoning_effort,
            None, 0, 0, session_meta.get("cwd"), None,
            session_meta.get("timestamp"), last_ts, last_ts, n_msgs,
            in_t, out_t, cache_t,
            session_meta.get("cli_version"), source_str,
            session_meta.get("originator"), source_meta_json,
            subagent_parent_id, subagent_nickname, subagent_role, subagent_path,
            str(largest_file), int(snapshot_count),
            int(largest_file.stat().st_size),
        ))
        n_sess_inserted += 1

        # Insert messages
        for m in messages:
            msg_ext = f"codex_msg:{sid}:{m['msg_id']}"
            if msg_ext in existing_msg:
                n_msg_skipped += 1
                continue

            cur.execute("""
                INSERT INTO migrated_codex_messages (
                    external_id, msg_id, session_external_id, role,
                    timestamp_iso, content_text, content_json,
                    block_count, text_block_count, tool_use_count,
                    tool_result_count, image_block_count, reasoning_block_count,
                    custom_tool_call_count, tool_use_names,
                    input_tokens, output_tokens, cache_read_input_tokens
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                msg_ext, m["msg_id"], sess_ext, str(m["role"]),
                m["timestamp_iso"], m["content_text"] or None, m["content_json"],
                int(m["block_count"]), int(m["text_block_count"]), int(m["tool_use_count"]),
                int(m["tool_result_count"]), int(m["image_block_count"]), int(m["reasoning_block_count"]),
                int(m["custom_tool_call_count"]), m["tool_use_names"] or None,
                0, 0, 0,  # per-message tokens not available in codex format
            ))
            n_msg_inserted += 1

        total_input += in_t
        total_output += out_t
        total_cache += cache_t

        if i % 10 == 0:
            conn.commit()
            print(f"    progress: {i:,}/{len(sid_to_largest):,} sessions, "
                  f"{n_sess_inserted:,} inserted, {n_msg_inserted:,} messages, "
                  f"errs={n_parse_errors}")

    conn.commit()
    conn.close()

    return {
        "files_seen": len(files),
        "unique_sessions": len(sid_to_largest),
        "sessions_inserted": n_sess_inserted,
        "sessions_skipped": n_sess_skipped,
        "sessions_filtered": n_sess_filtered,
        "messages_inserted": n_msg_inserted,
        "messages_skipped": n_msg_skipped,
        "parse_errors": n_parse_errors,
        "empty_sessions": n_empty,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cache_tokens": total_cache,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    add_common_args(p, db_required=True)
    p.add_argument('--sessions-dir', type=Path, default=DEFAULT_SESSIONS_DIR)
    p.add_argument('--since', default=DEFAULT_SINCE,
                   help='ISO 8601 UTC, only sessions at/after this date (default 2026-09-01)')
    args = p.parse_args()

    # Refuse to write the canonical corpus unless --allow-canonical was passed.
    # The guard fires here in main(); the writable connect happens in migrate()
    # below. Position is preserved.
    guard_write_target(str(args.db), allow_canonical=args.allow_canonical)

    print(f"db:             {args.db}")
    print(f"sessions dir:   {args.sessions_dir}")
    print(f"since:          {args.since}")
    print()

    if not args.sessions_dir.is_dir():
        print(f"ERROR: sessions dir not found: {args.sessions_dir}")
        return 1

    r = migrate(args.db, args.sessions_dir, args.since)

    print()
    print("=== migration summary ===")
    print(f"  files seen:              {r['files_seen']:>7,}")
    print(f"  unique sessions:         {r['unique_sessions']:>7,}")
    print(f"  sessions inserted:       {r['sessions_inserted']:>7,}")
    print(f"  sessions skipped:        {r['sessions_skipped']:>7,}  (already in DB)")
    print(f"  sessions filtered:       {r['sessions_filtered']:>7,}  (before --since)")
    print(f"  messages inserted:       {r['messages_inserted']:>7,}")
    print(f"  messages skipped:        {r['messages_skipped']:>7,}  (already in DB)")
    print(f"  parse errors:            {r['parse_errors']:>7,}")
    print(f"  empty sessions:          {r['empty_sessions']:>7,}")
    print(f"  total input tokens:      {r['total_input_tokens']:>13,}")
    print(f"  total output tokens:     {r['total_output_tokens']:>13,}")
    print(f"  total cache tokens:      {r['total_cache_tokens']:>13,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
