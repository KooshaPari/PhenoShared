"""imessage_migrate_to_research characterization.

Pins down the imessage migrator's output contract. The migrator reads
~/Library/Messages/chat.db (read-only URI mode) and writes 4 migrated_imessage_*
tables plus registers the `imessage` source row. We monkey-patch CHAT_DB so
the script reads our synthetic chat.db under tmp_path.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path

import pytest

ANALYSIS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ANALYSIS))


@pytest.fixture
def imessage_migrator(tmp_path, monkeypatch):
    mod = importlib.import_module("imessage_migrate_to_research")
    chat_db = tmp_path / "chat.db"
    monkeypatch.setattr(mod, "CHAT_DB", chat_db)
    return mod, chat_db


def _seed_chat_db(p: Path) -> None:
    """Synthetic macOS chat.db with 1 handle, 1 chat, 1 message, 1 attachment.

    Date is 2026-09-01 (post Apr 2025+ filter). NS since 2001-01-01:
    (1788259200 - 978307200) * 1e9 = 809_952_000_000_000_000.
    """
    ns = 809_952_000_000_000_000
    conn = sqlite3.connect(p)
    conn.executescript("""
        CREATE TABLE handle (
            ROWID INTEGER PRIMARY KEY, id TEXT, service TEXT,
            uncanonicalized_id TEXT, country TEXT
        );
        CREATE TABLE chat (
            ROWID INTEGER PRIMARY KEY, guid TEXT, service_name TEXT,
            style INTEGER, display_name TEXT, chat_identifier TEXT,
            is_archived INTEGER, last_read_message_timestamp INTEGER
        );
        CREATE TABLE message (
            ROWID INTEGER PRIMARY KEY, guid TEXT, text TEXT,
            handle_id INTEGER, is_from_me INTEGER, date INTEGER,
            date_read INTEGER, date_delivered INTEGER,
            is_empty INTEGER, is_read INTEGER, is_delivered INTEGER,
            is_audio_message INTEGER, is_archive INTEGER,
            cache_has_attachments INTEGER, service TEXT, item_type INTEGER,
            associated_message_type INTEGER, is_spam INTEGER,
            is_system_message INTEGER
        );
        CREATE TABLE chat_message_join (chat_id INTEGER, message_id INTEGER);
        CREATE TABLE attachment (
            ROWID INTEGER PRIMARY KEY, guid TEXT, filename TEXT,
            mime_type TEXT, total_bytes INTEGER, uti TEXT,
            is_sticker INTEGER, is_outgoing INTEGER, transfer_name TEXT
        );
        CREATE TABLE message_attachment_join (
            attachment_id INTEGER, message_id INTEGER
        );
    """)
    conn.execute("INSERT INTO handle VALUES (1,'h1','iMessage','+15555550100','US')")
    conn.execute(
        "INSERT INTO chat VALUES (10,'guid-1','iMessage',43,NULL,"
        "'chat-1',0,?)",
        (ns,),
    )
    conn.execute(
        "INSERT INTO message VALUES (100,'msg-1','hello world',"
        "1,1,?,?,?,0,1,1,0,0,0,'iMessage',0,0,0,0)",
        (ns, ns, ns),
    )
    conn.execute("INSERT INTO chat_message_join VALUES (10,100)")
    conn.execute(
        "INSERT INTO attachment VALUES (1000,'att-1','/tmp/img.png',"
        "'image/png',1234,'public.png',0,1,'img.png')"
    )
    conn.execute("INSERT INTO message_attachment_join VALUES (1000,100)")
    conn.commit()
    conn.close()


def test_migrator_writes_all_four_tables(
    tmp_path, research_db, imessage_migrator, monkeypatch
):
    mod, chat_db = imessage_migrator
    _seed_chat_db(chat_db)
    monkeypatch.setattr(sys, "argv", [
        "imessage_migrate_to_research.py",
        "--db", str(research_db),
        "--since", "2025-04-01",
    ])
    rc = mod.main()
    assert rc == 0
    conn = sqlite3.connect(research_db)
    try:
        for tbl in [
            "migrated_imessage_handles",
            "migrated_imessage_chats",
            "migrated_imessage_messages",
            "migrated_imessage_attachments",
        ]:
            n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            assert n == 1, f"{tbl} expected 1 row, got {n}"
        # Source registered with kind=imessage.
        kind = conn.execute(
            "SELECT kind FROM sources WHERE kind='imessage'"
        ).fetchone()
        assert kind is not None and kind[0] == "imessage"
        # The chat.external_id contract.
        ext = conn.execute(
            "SELECT external_id FROM migrated_imessage_chats"
        ).fetchone()[0]
        assert ext == "chat:10"
        # The message external_id must be 'msg:<ROWID>' and chat_external_id
        # must reference the chat we just inserted (FK by external_id).
        msg = conn.execute("""
            SELECT external_id, chat_external_id, is_from_me
            FROM migrated_imessage_messages
        """).fetchone()
        assert msg == ("msg:100", "chat:10", 1)
        # Attachment external_id must be 'attach:<ROWID>'.
        att = conn.execute(
            "SELECT external_id, msg_external_id FROM migrated_imessage_attachments"
        ).fetchone()
        assert att == ("attach:1000", "msg:100")
        # date_iso must be a valid ISO 8601 UTC string (parses).
        date_iso = conn.execute(
            "SELECT date_iso FROM migrated_imessage_messages"
        ).fetchone()[0]
        assert date_iso.startswith("2026-09-01")
    finally:
        conn.close()


def test_migrator_drops_spam_system_and_old(
    tmp_path, research_db, imessage_migrator, monkeypatch
):
    """The Apr 2025+ filter + spam/system filter actually filter.

    A 2024 message + a spam message must NOT appear in migrated_imessage_messages.
    """
    mod, chat_db = imessage_migrator
    conn = sqlite3.connect(chat_db)
    conn.executescript("""
        CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT, service TEXT,
            uncanonicalized_id TEXT, country TEXT);
        CREATE TABLE chat (ROWID INTEGER PRIMARY KEY, guid TEXT, service_name TEXT,
            style INTEGER, display_name TEXT, chat_identifier TEXT,
            is_archived INTEGER, last_read_message_timestamp INTEGER);
        CREATE TABLE message (ROWID INTEGER PRIMARY KEY, guid TEXT, text TEXT,
            handle_id INTEGER, is_from_me INTEGER, date INTEGER,
            date_read INTEGER, date_delivered INTEGER,
            is_empty INTEGER, is_read INTEGER, is_delivered INTEGER,
            is_audio_message INTEGER, is_archive INTEGER,
            cache_has_attachments INTEGER, service TEXT, item_type INTEGER,
            associated_message_type INTEGER, is_spam INTEGER,
            is_system_message INTEGER);
        CREATE TABLE chat_message_join (chat_id INTEGER, message_id INTEGER);
        CREATE TABLE attachment (
            ROWID INTEGER PRIMARY KEY, guid TEXT, filename TEXT,
            mime_type TEXT, total_bytes INTEGER, uti TEXT,
            is_sticker INTEGER, is_outgoing INTEGER, transfer_name TEXT
        );
        CREATE TABLE message_attachment_join (
            attachment_id INTEGER, message_id INTEGER
        );
    """)
    # 2024 message (PRE filter) — should be dropped.
    old_ns = (1704067200 - 978307200) * 1_000_000_000  # 2024-01-01
    # 2026 message that IS spam — should be dropped.
    spam_ns = 809_952_000_000_000_000
    conn.execute("INSERT INTO handle VALUES (1,'h','iMessage','+1','x')")
    conn.execute("INSERT INTO chat VALUES (1,'g','iMessage',43,NULL,'c',0,?)",
                 (spam_ns,))
    conn.execute(
        "INSERT INTO message VALUES (10,'old','old',1,1,?,NULL,NULL,0,1,1,0,0,0,"
        "'iMessage',0,0,0,0)", (old_ns,)
    )
    conn.execute(
        "INSERT INTO message VALUES (11,'spam','spam',1,1,?,NULL,NULL,0,1,1,0,0,0,"
        "'iMessage',0,0,1,0)", (spam_ns,)
    )
    conn.execute("INSERT INTO chat_message_join VALUES (1,10)")
    conn.execute("INSERT INTO chat_message_join VALUES (1,11)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(sys, "argv", [
        "imessage_migrate_to_research.py",
        "--db", str(research_db),
        "--since", "2025-04-01",
    ])
    rc = mod.main()
    assert rc == 0
    conn = sqlite3.connect(research_db)
    try:
        # Chat is inactive because both its messages are filtered out.
        n_chat = conn.execute(
            "SELECT COUNT(*) FROM migrated_imessage_chats"
        ).fetchone()[0]
        assert n_chat == 0, "inactive chat should not be migrated"
        n_msg = conn.execute(
            "SELECT COUNT(*) FROM migrated_imessage_messages"
        ).fetchone()[0]
        assert n_msg == 0
    finally:
        conn.close()