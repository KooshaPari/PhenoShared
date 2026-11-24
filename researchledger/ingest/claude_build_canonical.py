"""
claude_build_canonical.py — Pump migrated_anthropic_claude_* into canonical
research_ledger tables (items, attachments).

Applies §4.3 provenance to every row:
  source_id=2, evidence_type=direct, confidence=high, redaction_state=partial
  (messages and project docs may contain personal data, so partial is honest)

Item kinds produced:
  - claude_conversation         1 per migrated_anthropic_claude_conversations
  - claude_message              1 per migrated_anthropic_claude_messages, parent=conversation
  - claude_memory               1 per migrated_anthropic_claude_memories
  - claude_project              1 per migrated_anthropic_claude_projects
  - claude_project_doc          1 per migrated_anthropic_claude_project_docs, parent=project
  - claude_design_chat          1 per migrated_anthropic_claude_design_chats
  - claude_design_chat_message  1 per migrated_anthropic_claude_design_chat_messages, parent=design_chat

Attachment kinds produced:
  - file (extracted_content)    1 per migrated_anthropic_claude_attachments, attached to message

Message body extraction (claude-specific):
  migrated_anthropic_claude_messages.content_json is a JSON list of parts;
  types: text (15,636), tool_use (8,864), tool_result (8,572), thinking (2,893),
         token_budget (41). We concatenate all 'text' parts into items.body
  so FTS5 searches the prose. tool_use/tool_result/thinking are skipped for
  now (could be extracted as separate items in a future iteration).

Project docs (40 across 12 projects) have substantial content (e.g. P4 has
38 KB across 18 docs, Reverse Engineering has 79 KB across 5 docs) so we
FTS-index them as items.

Idempotent: every insert uses (source_id, external_id) uniqueness.

Usage:
    python3 claude_build_canonical.py
    python3 claude_build_canonical.py --dry-run
    python3 claude_build_canonical.py --research PATH
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from researchledger import corpus_guard  # noqa: E402
from researchledger.corpus_guard import guard_write_target  # noqa: E402

# The canonical corpus path is captured here ONLY so the guard can recognise it
# when the operator passes it explicitly with --allow-canonical. Do NOT pass this
# directly to sqlite3.connect() — always go through guard_write_target() first.
DEFAULT_RESEARCH = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"

# Re-export from claude_canonical_builders so callers can still write
# `from claude_build_canonical import build_messages, PHASE_FNS`.
from claude_canonical_builders import (
    CLAUDE_SOURCE_ID,
    DEFAULT_REDACTION_STATE,
    PHASE_FNS,
    build_conversations,
    build_design_chat_messages,
    build_design_chats,
    build_files_attachments,
    build_memories,
    build_messages,
    build_project_docs,
    build_projects,
    extract_text_from_content_json,
    now_iso,
    sha256_hex,
)


def validate(dst: sqlite3.Connection) -> dict:
    out = {}
    for kind in ("claude_conversation", "claude_message", "claude_memory",
                 "claude_project", "claude_project_doc",
                 "claude_design_chat", "claude_design_chat_message"):
        n = dst.execute(
            "SELECT COUNT(*) FROM items WHERE source_id=? AND item_kind=?",
            (CLAUDE_SOURCE_ID, kind)).fetchone()[0]
        out[f"items:{kind}"] = n
    n = dst.execute(
        "SELECT COUNT(*) FROM attachments WHERE source_id=?",
        (CLAUDE_SOURCE_ID,)).fetchone()[0]
    out["attachments:file"] = n

    # FTS5 sanity: search for distinctive terms that should appear in claude data
    fts_match = dst.execute(
        "SELECT COUNT(*) FROM items_fts WHERE items_fts MATCH 'claude OR agent'"
    ).fetchone()[0]
    out["items_fts:claude_or_agent"] = fts_match

    n_missing_provenance = dst.execute(f"""
        SELECT COUNT(*) FROM items
        WHERE source_id={CLAUDE_SOURCE_ID}
          AND (evidence_type IS NULL OR confidence IS NULL OR captured_at IS NULL)
    """).fetchone()[0]
    out["items:missing_provenance"] = n_missing_provenance

    n_orphans = dst.execute(f"""
        SELECT COUNT(*) FROM items m
        WHERE m.source_id={CLAUDE_SOURCE_ID} AND m.item_kind='claude_message'
          AND (m.parent_id IS NULL
               OR NOT EXISTS (SELECT 1 FROM items p WHERE p.id = m.parent_id
                              AND p.item_kind='claude_conversation'))
    """).fetchone()[0]
    out["items:orphan_messages"] = n_orphans

    n_orphan_doc = dst.execute(f"""
        SELECT COUNT(*) FROM items d
        WHERE d.source_id={CLAUDE_SOURCE_ID} AND d.item_kind='claude_project_doc'
          AND (d.parent_id IS NULL
               OR NOT EXISTS (SELECT 1 FROM items p WHERE p.id = d.parent_id
                              AND p.item_kind='claude_project'))
    """).fetchone()[0]
    out["items:orphan_project_docs"] = n_orphan_doc

    n_orphan_dcm = dst.execute(f"""
        SELECT COUNT(*) FROM items d
        WHERE d.source_id={CLAUDE_SOURCE_ID} AND d.item_kind='claude_design_chat_message'
          AND (d.parent_id IS NULL
               OR NOT EXISTS (SELECT 1 FROM items p WHERE p.id = d.parent_id
                              AND p.item_kind='claude_design_chat'))
    """).fetchone()[0]
    out["items:orphan_design_chat_messages"] = n_orphan_dcm

    n_orphan_att = dst.execute(f"""
        SELECT COUNT(*) FROM attachments a
        WHERE a.source_id={CLAUDE_SOURCE_ID}
          AND (a.item_id IS NULL
               OR NOT EXISTS (SELECT 1 FROM items p WHERE p.id = a.item_id
                              AND p.item_kind='claude_message'))
    """).fetchone()[0]
    out["attachments:orphan_attachments"] = n_orphan_att

    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--research", type=Path, required=True,
                   help="Path to research_ledger DB to write. REQUIRED — the "
                        "canonical corpus is rejected unless --allow-canonical "
                        "is also passed. Flag name kept for backward compat "
                        "with existing test harnesses.")
    p.add_argument("--allow-canonical", action="store_true",
                   help="Permit writing the canonical corpus (dangerous).")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    research_path = args.research
    if not research_path.exists():
        print(f"ERROR: research_ledger not found: {research_path}", file=sys.stderr)
        return 1

    # Hard guard: refuse canonical / sealed backup / symlink trickery.
    # Pass the *target* (--research) path, not any migrated source path.
    guard_write_target(str(research_path), allow_canonical=args.allow_canonical)

    print(f"research: {research_path}")
    print(f"dry-run:  {args.dry_run}")
    print()

    dst = sqlite3.connect(str(research_path))
    dst.execute("PRAGMA journal_mode = WAL")
    dst.execute("PRAGMA synchronous = NORMAL")
    dst.execute("PRAGMA foreign_keys = ON")
    try:
        n_src = dst.execute(
            "SELECT COUNT(*) FROM sources WHERE id=? AND kind='claude'",
            (CLAUDE_SOURCE_ID,)).fetchone()[0]
        if n_src != 1:
            print(f"ERROR: source id={CLAUDE_SOURCE_ID} (claude) not registered. Run claude_migrate_to_research.py first.", file=sys.stderr)
            return 1

        print("Migrated row counts:")
        for t in ['migrated_anthropic_claude_conversations', 'migrated_anthropic_claude_messages',
                  'migrated_anthropic_claude_attachments', 'migrated_anthropic_claude_files',
                  'migrated_anthropic_claude_memories', 'migrated_anthropic_claude_projects',
                  'migrated_anthropic_claude_project_docs',
                  'migrated_anthropic_claude_design_chats',
                  'migrated_anthropic_claude_design_chat_messages']:
            n = dst.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {n:,}")
        print()

        if args.dry_run:
            for phase, fn in PHASE_FNS.items():
                print(f"  {phase:20s}  (would insert, dry-run)")
            return 0

        # Order matters: parents before children
        phase_order = [
            "conversations", "memories", "projects", "design_chats",
            "messages", "project_docs", "design_chat_messages",
            "files_attachments",
        ]
        results = {}
        for phase in phase_order:
            t0 = time.time()
            n = PHASE_FNS[phase](dst)
            dst.commit()
            results[phase] = (n, time.time() - t0)
            print(f"  {phase:25s}  inserted={n:>7,}  {results[phase][1]:6.2f}s")

        print("\nValidation:")
        v = validate(dst)
        for k, val in v.items():
            ok = True
            if k.startswith("items:missing_") and val != 0:
                ok = False
            if k.endswith("_orphans") or "orphan_" in k:
                if val != 0:
                    ok = False
            print(f"  {k:55s}  {val:>7,}  {'OK' if ok else 'FAIL'}")

        return 0
    finally:
        dst.close()


if __name__ == "__main__":
    sys.exit(main())
