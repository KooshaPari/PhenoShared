"""imessage_build_canonical characterization.

Pins down the imessage canonical items + attachments builder. Reads
migrated_imessage_{chats,messages,attachments} and produces three
artifacts: items.item_kind='imessage_chat' (one per chat),
items.item_kind='imessage_message' (one per message), and
attachments.kind='imessage_attachment' (one per attachment).

We seed a synthetic chat + 2 messages + 1 attachment, then assert
the output contract and FK integrity.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ANALYSIS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ANALYSIS))


@pytest.fixture
def imessage_builder(tmp_path, monkeypatch):
    mod = importlib.import_module("imessage_build_canonical")
    return mod


def _seed_imessage_db(p: Path) -> None:
    from research_ledger_init.sources_chat import imessage_migrated_schema
    from research_ledger_init import init as init_research_ledger

    init_research_ledger(p)
    conn = sqlite3.connect(p)
    try:
        for stmt in imessage_migrated_schema():
            conn.execute(stmt)
        conn.execute("""
            INSERT INTO sources (id, kind, base_path, captured_at)
            VALUES (1, 'imessage', '/fake/imessage', '2026-09-01T00:00:00Z')
        """)
        # 1 chat
        conn.execute("""
            INSERT INTO migrated_imessage_chats (
                id, external_id, chat_guid, service_name, style,
                display_name, chat_identifier, is_archived,
                last_read_message_iso, message_count
            ) VALUES (
                1, 'chat:10', 'guid-1', 'iMessage', 43,
                NULL, '+15555550100', 0,
                '2026-09-01T12:00:00.000000+00:00', 2
            )
        """)
        # 1 handle
        conn.execute("""
            INSERT INTO migrated_imessage_handles (
                id, external_id, handle_rowid, service,
                uncanonicalized_id, country, is_me_handle
            ) VALUES (
                1, 'handle:1', 1, 'iMessage',
                '+15555550100', 'US', 0
            )
        """)
        # 2 messages: one from-me (text), one from-them (text with URL)
        conn.execute("""
            INSERT INTO migrated_imessage_messages (
                id, external_id, msg_guid, chat_external_id,
                handle_external_id, is_from_me, text, date_iso,
                date_raw_ns, date_read_iso, date_delivered_iso,
                is_empty, is_read, is_delivered, is_audio_message,
                is_archive, has_attachments, service, item_type,
                associated_message_type
            ) VALUES (
                100, 'msg:100', 'msg-guid-100', 'chat:10',
                'handle:1', 1, 'Hello from koosha',
                '2026-09-01T12:00:00.000000+00:00',
                0, '2026-09-01T12:00:05+00:00', '2026-09-01T12:00:01+00:00',
                0, 1, 1, 0, 0, 0, 'iMessage', 0, 0
            )
        """)
        conn.execute("""
            INSERT INTO migrated_imessage_messages (
                id, external_id, msg_guid, chat_external_id,
                handle_external_id, is_from_me, text, date_iso,
                date_raw_ns, date_read_iso, date_delivered_iso,
                is_empty, is_read, is_delivered, is_audio_message,
                is_archive, has_attachments, service, item_type,
                associated_message_type
            ) VALUES (
                101, 'msg:101', 'msg-guid-101', 'chat:10',
                'handle:1', 0, 'Check this out: https://example.com/cool',
                '2026-09-01T12:01:00.000000+00:00',
                0, '2026-09-01T12:01:30+00:00', NULL,
                0, 1, 1, 0, 0, 0, 'iMessage', 0, 0
            )
        """)
        # 1 attachment (orphan test fixture: an attachment whose message
        # does NOT exist must be skipped, not error.)
        conn.execute("""
            INSERT INTO migrated_imessage_attachments (
                id, external_id, msg_external_id, attach_guid,
                filename, mime_type, byte_size, uti, is_sticker,
                is_outgoing, local_path
            ) VALUES (
                1000, 'attach:1000', 'msg:100', 'att-1000',
                '/Users/x/foo.png', 'image/png', 5000, 'public.png',
                0, 1, '/Users/x/foo.png'
            )
        """)
        conn.execute("""
            INSERT INTO migrated_imessage_attachments (
                id, external_id, msg_external_id, attach_guid,
                filename, mime_type, byte_size, uti, is_sticker,
                is_outgoing, local_path
            ) VALUES (
                1001, 'attach:1001', 'msg:999', 'att-1001',
                '/Users/x/orphan.png', 'image/png', 1000, 'public.png',
                0, 0, '/Users/x/orphan.png'
            )
        """)
        conn.commit()
    finally:
        conn.close()


def test_imessage_builds_chats_messages_attachments(
    research_db, monkeypatch, imessage_builder
):
    _seed_imessage_db(research_db)
    monkeypatch.setattr(sys, "argv", [
        "imessage_build_canonical.py", "--db", str(research_db),
    ])
    rc = imessage_builder.main()
    assert rc == 0

    conn = sqlite3.connect(research_db)
    try:
        # 1 chat item.
        n_chat = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE source_id = 1 AND item_kind = 'imessage_chat'
        """).fetchone()[0]
        assert n_chat == 1
        # 2 message items.
        n_msg = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE source_id = 1 AND item_kind = 'imessage_message'
        """).fetchone()[0]
        assert n_msg == 2
        # 1 attachment (orphan skipped).
        n_att = conn.execute("""
            SELECT COUNT(*) FROM attachments
            WHERE source_id = 1 AND kind = 'imessage_attachment'
        """).fetchone()[0]
        assert n_att == 1

        # Chat item: title prefers chat_identifier, body is a short summary
        # including the message_count.
        chat = conn.execute("""
            SELECT title, body, attrs_json
            FROM items
            WHERE source_id = 1 AND item_kind = 'imessage_chat'
        """).fetchone()
        title, body, attrs_json = chat
        assert title == "+15555550100"
        assert "messages: 2" in body
        assert "type: 1:1" in body
        parsed = json.loads(attrs_json)
        assert parsed["service"] == "iMessage"
        assert parsed["style"] == 43
        assert parsed["is_group"] is False
        assert parsed["message_count"] == 2
        assert parsed["platform"] == "imessage"

        # From-me message: author='koosha', title is first line.
        m1 = conn.execute("""
            SELECT author, title, body, url, attrs_json
            FROM items
            WHERE source_id = 1 AND external_id = 'msg:100'
        """).fetchone()
        author, mtitle, mbody, murl, mattrs = m1
        assert author == "koosha"
        assert mtitle == "Hello from koosha"
        assert murl is None
        # The body starts with a date: header line + 'from: me (koosha)'.
        assert mbody.startswith("date: 2026-09-01T12:00:00+00:00")
        assert "from: me (koosha)" in mbody
        assert "Hello from koosha" in mbody
        m1_parsed = json.loads(mattrs)
        assert m1_parsed["is_from_me"] is True
        assert m1_parsed["chat_external_id"] == "chat:10"
        assert m1_parsed["handle_external_id"] == "handle:1"
        assert m1_parsed["platform"] == "imessage"

        # From-them message: author=handle_external_id, body has 'from:' header
        # and url is captured.
        m2 = conn.execute("""
            SELECT author, url, body
            FROM items
            WHERE source_id = 1 AND external_id = 'msg:101'
        """).fetchone()
        m2_author, m2_url, m2_body = m2
        assert m2_author == "handle:1"
        assert m2_url == "https://example.com/cool"
        assert "from: handle:1" in m2_body
        assert "https://example.com/cool" in m2_body

        # Attachment: bound to msg:100 by item_id, mime and local_path match.
        att = conn.execute("""
            SELECT a.external_id, a.item_id, a.kind, a.mime_type,
                   a.byte_size, a.local_path
            FROM attachments a
            WHERE a.source_id = 1 AND a.external_id = 'attach:1000'
        """).fetchone()
        assert att[0] == "attach:1000"
        assert att[1] is not None
        assert att[2] == "imessage_attachment"
        assert att[3] == "image/png"
        assert att[4] == 5000
        assert att[5] == "/Users/x/foo.png"

        # Orphan attachment (msg:999 doesn't exist) must be skipped.
        n_orphan = conn.execute("""
            SELECT COUNT(*) FROM attachments
            WHERE source_id = 1 AND external_id = 'attach:1001'
        """).fetchone()[0]
        assert n_orphan == 0

        # FK integrity: no orphan attachments.
        n_fk_orphan = conn.execute("""
            SELECT COUNT(*) FROM attachments a
            WHERE a.source_id = 1 AND a.item_id IS NOT NULL
              AND a.item_id NOT IN (SELECT id FROM items WHERE source_id = 1)
        """).fetchone()[0]
        assert n_fk_orphan == 0

        # FTS5 sanity: 'koosha' should match the from-me message body.
        n_fts = conn.execute("""
            SELECT COUNT(*) FROM items_fts f
            JOIN items i ON i.id = f.rowid
            WHERE items_fts MATCH 'koosha' AND i.source_id = 1
        """).fetchone()[0]
        assert n_fts >= 1
    finally:
        conn.close()