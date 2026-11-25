"""
kcode_migrate_to_research.py — pump ~/.kcode/sessions/session_*.json → migrated_kcode_*

Source: ~/.kcode/sessions/session_<short>_<ts>_<hash>.json (or
        session_<short>.json for static-named sessions like 'session_alpha').

kcode is the KooshaPari fork of jcode. Session format is 99% identical:
same id/parent_id/title/messages[]/provider_key/model/working_dir/status.
Differences:
  - kcode has `fork_depth`, `fork_max_depth` (no `short_name`)
  - kcode has many mock/panic-on-fork/test sessions (~75% of corpus)
  - kcode is much smaller: ~385 sessions, ~1K messages vs jcode's 4,349/435K
  - kcode dates from 2026-10-08 (4-day window vs jcode's 2+ months)

Default --since 2026-10-01 (captures all kcode activity).

Idempotent: 2nd run inserts 0 rows. Source row check-then-insert (avoids
the auto-increment INSERT OR IGNORE bug discovered in jcode W9).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from migrator_base import add_common_args, register_source
import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from researchledger import corpus_guard  # noqa: E402
from researchledger.corpus_guard import guard_write_target  # noqa: E402

DEFAULT_DB = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"
DEFAULT_SESSIONS_DIR = Path.home() / ".kcode" / "sessions"
DEFAULT_SINCE = "2026-10-01T00:00:00Z"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_status(s) -> str:
    """Status is sometimes a string ('Active'), sometimes a dict ({'Crashed': ...})."""
    return json.dumps(s, ensure_ascii=False) if isinstance(s, (dict, list)) else str(s)


def classify_blocks(content) -> tuple[str, int, int, int, int, int, str]:
    """
    Return (concatenated_text, n_text, n_tool_use, n_tool_result, n_image, n_reasoning, tool_names_csv).
    Identical to jcode version — content blocks are the same jcode format.
    """
    if content is None:
        return "", 0, 0, 0, 0, 0, ""
    if isinstance(content, str):
        return content, 1, 0, 0, 0, 0, ""

    texts: list[str] = []
    n_text = n_tool_use = n_tool_result = n_image = n_reasoning = 0
    tool_names: list[str] = []

    for blk in content:
        if not isinstance(blk, dict):
            continue
        btype = blk.get("type", "unknown")
        if btype == "text":
            n_text += 1
            t = blk.get("text", "")
            if t:
                texts.append(t)
        elif btype == "reasoning":
            n_reasoning += 1
            t = blk.get("text", "")
            if t:
                texts.append(f"<<reasoning>>\n{t}\n<<end reasoning>>")
        elif btype == "tool_use":
            n_tool_use += 1
            name = blk.get("name", "")
            if name:
                tool_names.append(name)
            tool_input = blk.get("input", {})
            if isinstance(tool_input, dict):
                if "intent" in tool_input:
                    texts.append(f"<<tool_use {name}: {tool_input['intent']}>>")
                elif "command" in tool_input:
                    cmd = tool_input["command"]
                    if len(cmd) > 200:
                        cmd = cmd[:200] + "..."
                    texts.append(f"<<tool_use {name}: $ {cmd}>>")
                elif "file_path" in tool_input:
                    texts.append(f"<<tool_use {name}: {tool_input['file_path']}>>")
                else:
                    texts.append(f"<<tool_use {name}>>")
            else:
                texts.append(f"<<tool_use {name}>>")
        elif btype == "tool_result":
            n_tool_result += 1
            tr_content = blk.get("content", "")
            if isinstance(tr_content, str) and tr_content:
                if len(tr_content) > 4096:
                    tr_content = tr_content[:4096] + "\n... [truncated]"
                texts.append(f"<<tool_result>>\n{tr_content}\n<<end tool_result>>")
            else:
                texts.append("<<tool_result (no text content)>>")
        elif btype == "image":
            n_image += 1
            src = blk.get("source", {})
            if isinstance(src, dict):
                kind = src.get("type", "?")
                if kind == "base64":
                    texts.append(f"<<image base64: {len(src.get('data',''))} chars, media_type={src.get('media_type','?')}>>")
                else:
                    texts.append(f"<<image {kind}>>")
            else:
                texts.append("<<image>>")
        else:
            texts.append(f"<<{btype}>>")

    return ("\n".join(texts).strip(), n_text, n_tool_use, n_tool_result, n_image, n_reasoning,
            ",".join(tool_names))


def aggregate_tokens(usage) -> tuple[int, int, int]:
    if not isinstance(usage, dict):
        return 0, 0, 0
    return (int(usage.get("input_tokens", 0) or 0),
            int(usage.get("output_tokens", 0) or 0),
            int(usage.get("cache_read_input_tokens", 0) or 0))


def should_keep(d: dict, since_iso: str) -> tuple[bool, str]:
    created = d.get("created_at", "")
    if not created:
        return False, ""
    if created < since_iso:
        return False, created
    return True, created


def migrate(db_path: Path, sessions_dir: Path, since_iso: str) -> dict:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")

    # Idempotent source row (check first, then insert — avoids auto-increment dup bug)
    today = now_iso()
    src_id = register_source(
        conn,
        kind="kcode",
        base_path=str(sessions_dir),
        byte_size=0,
        captured_at=today,
        notes='~/.kcode/sessions/session_*.json (KooshaPari fork of jcode)',
    )
    print(f"  source id: {src_id} (kind=kcode)")

    existing_sess = {r[0] for r in conn.execute(
        "SELECT external_id FROM migrated_kcode_sessions").fetchall()}
    existing_msg = {r[0] for r in conn.execute(
        "SELECT external_id FROM migrated_kcode_messages").fetchall()}
    print(f"  existing sessions in DB: {len(existing_sess):,}")
    print(f"  existing messages in DB: {len(existing_msg):,}")

    files = sorted(sessions_dir.glob("session_*.json"))
    files = [f for f in files if ".journal." not in f.name]
    print(f"  source .json files: {len(files):,}")

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

    for i, fp in enumerate(files, 1):
        try:
            with open(fp) as fh:
                d = json.load(fh)
        except json.JSONDecodeError as e:
            n_parse_errors += 1
            if n_parse_errors <= 5:
                print(f"  WARN parse error in {fp.name}: {e}")
            continue
        except OSError as e:
            n_parse_errors += 1
            if n_parse_errors <= 5:
                print(f"  WARN read error in {fp.name}: {e}")
            continue

        keep, created = should_keep(d, since_iso)
        if not keep:
            n_sess_filtered += 1
            continue

        session_id = d.get("id") or fp.stem
        sess_ext = f"kcode_session:{session_id}"

        if sess_ext in existing_sess:
            n_sess_skipped += 1
            continue

        msgs = d.get("messages") or []
        if not msgs:
            n_empty += 1

        in_t = out_t = cache_t = 0

        cur.execute("""
            INSERT INTO migrated_kcode_sessions (
                external_id, session_id, title, parent_id,
                provider_key, provider_session_id, model, reasoning_effort,
                subagent_model, is_canary, is_debug, working_dir, status_json,
                created_at, updated_at, last_active_at, message_count,
                total_input_tokens, total_output_tokens, total_cache_read_tokens,
                saved, save_label, fork_depth, fork_max_depth, raw_json_path
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            sess_ext, session_id, d.get("title"), d.get("parent_id"),
            d.get("provider_key"), d.get("provider_session_id"), d.get("model"),
            d.get("reasoning_effort"), d.get("subagent_model"),
            int(bool(d.get("is_canary"))), int(bool(d.get("is_debug"))),
            d.get("working_dir"), parse_status(d.get("status")),
            d.get("created_at"), d.get("updated_at"),
            d.get("last_active_at"), len(msgs),
            0, 0, 0,
            int(bool(d.get("saved"))), d.get("save_label"),
            d.get("fork_depth"), d.get("fork_max_depth"),
            str(fp),
        ))
        n_sess_inserted += 1

        for m in msgs:
            mid = m.get("id") or ""
            if not mid:
                continue
            # Same collision pattern as jcode — use composite external_id
            msg_ext = f"kcode_msg:{session_id}:{mid}"
            if msg_ext in existing_msg:
                n_msg_skipped += 1
                continue

            role = m.get("role", "")
            content = m.get("content")
            content_json_str = (json.dumps(content, ensure_ascii=False)
                                if content is not None else None)
            text, n_text, n_tool_use, n_tool_result, n_image, n_reasoning, tool_names = \
                classify_blocks(content)
            usage = m.get("token_usage") or {}
            mi, mo, mc = aggregate_tokens(usage)
            in_t += mi
            out_t += mo
            cache_t += mc

            cur.execute("""
                INSERT INTO migrated_kcode_messages (
                    external_id, msg_id, session_external_id, role,
                    timestamp_iso, content_text, content_json,
                    block_count, text_block_count, tool_use_count,
                    tool_result_count, image_block_count, reasoning_block_count,
                    tool_use_names, input_tokens, output_tokens, cache_read_input_tokens
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                msg_ext, mid, sess_ext, role,
                m.get("timestamp"), text or None, content_json_str,
                (len(content) if isinstance(content, list) else 1 if isinstance(content, str) else 0),
                n_text, n_tool_use, n_tool_result, n_image, n_reasoning,
                tool_names or None,
                mi, mo, mc,
            ))
            n_msg_inserted += 1

        cur.execute("""
            UPDATE migrated_kcode_sessions
            SET total_input_tokens = ?, total_output_tokens = ?, total_cache_read_tokens = ?
            WHERE external_id = ?
        """, (in_t, out_t, cache_t, sess_ext))
        total_input += in_t
        total_output += out_t

        if n_sess_inserted % 200 == 0:
            conn.commit()
            print(f"    progress: {i:,}/{len(files):,} files, "
                  f"{n_sess_inserted:,} sessions, {n_msg_inserted:,} messages, "
                  f"errs={n_parse_errors}")

    conn.commit()
    conn.close()

    return {
        "files_seen": len(files),
        "sessions_inserted": n_sess_inserted,
        "sessions_skipped": n_sess_skipped,
        "sessions_filtered": n_sess_filtered,
        "messages_inserted": n_msg_inserted,
        "messages_skipped": n_msg_skipped,
        "parse_errors": n_parse_errors,
        "empty_sessions": n_empty,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    add_common_args(p, db_required=True)
    p.add_argument('--sessions-dir', type=Path, default=DEFAULT_SESSIONS_DIR)
    p.add_argument('--since', default=DEFAULT_SINCE,
                   help='ISO 8601 UTC, only sessions created at/after this date (default 2026-10-01)')
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
    print(f"  files seen:         {r['files_seen']:>7,}")
    print(f"  sessions inserted:  {r['sessions_inserted']:>7,}")
    print(f"  sessions skipped:   {r['sessions_skipped']:>7,}  (already in DB)")
    print(f"  sessions filtered:  {r['sessions_filtered']:>7,}  (before --since)")
    print(f"  messages inserted:  {r['messages_inserted']:>7,}")
    print(f"  messages skipped:   {r['messages_skipped']:>7,}  (already in DB)")
    print(f"  parse errors:       {r['parse_errors']:>7,}")
    print(f"  empty sessions:     {r['empty_sessions']:>7,}")
    print(f"  total input tokens: {r['total_input_tokens']:>13,}")
    print(f"  total output tokens:{r['total_output_tokens']:>13,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
