"""core schema definitions for research_ledger.sqlite.

Holds the canonical §4.1–§4.4 DDL (sources, items, entities, attachments,
metrics, FTS5, triggers, views) plus the shared `PROVENANCE_COLS` and
`DEFAULT_DB` constants consumed by every per-source migrated_* module.
"""

from __future__ import annotations

from pathlib import Path

DEFAULT_DB = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"

# Provenance fields required on every item per spec §4.3
PROVENANCE_COLS = (
    "source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,"
    "external_id TEXT NOT NULL,"
    "captured_at TEXT NOT NULL,"         # when this row was extracted
    "source_captured_at TEXT,"           # when the source created the item
    "evidence_type TEXT NOT NULL CHECK(evidence_type IN ('direct','inferred','analogical','unknown')),"
    "confidence TEXT NOT NULL CHECK(confidence IN ('high','medium','low')),"
    "note TEXT,"
    "redaction_state TEXT NOT NULL DEFAULT 'none' CHECK(redaction_state IN ('none','partial','full')),"
)


def core_schema() -> list[str]:
    """Return the core DDL statements from spec §4.1-4.4."""
    return [
        # ------------------------------------------------------------------
        # 4.1.1 sources — one row per data origin
        # ------------------------------------------------------------------
        """
        CREATE TABLE IF NOT EXISTS sources (
            id              INTEGER PRIMARY KEY,
            kind            TEXT NOT NULL CHECK(kind IN (
                'harness','chatgpt','claude','gemini','imessage',
                'jcode','kcode','helioslite','forge','codex',
                'claude_desktop','cursor',
                'reddit','linkedin','github','youtube','web_export',
                'pmp','session_ledger_migrated'
            )),
            base_path       TEXT,
            captured_at     TEXT NOT NULL,
            byte_size       INTEGER,
            schema_version  TEXT,
            notes           TEXT
        )
        """,
        # ------------------------------------------------------------------
        # 4.1.2 items — one row per content unit (msg, post, comment, file, etc.)
        # ------------------------------------------------------------------
        f"""
        CREATE TABLE IF NOT EXISTS items (
            id              INTEGER PRIMARY KEY,
            {PROVENANCE_COLS}
            item_kind       TEXT NOT NULL,
            author          TEXT,
            title           TEXT,
            body            TEXT,
            url             TEXT,
            raw_json_path   TEXT,
            parent_id       INTEGER REFERENCES items(id) ON DELETE SET NULL,
            dedupe_hash     TEXT,
            attrs_json      TEXT
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_items_source_ext ON items(source_id, external_id)",
        "CREATE INDEX IF NOT EXISTS ix_items_kind ON items(item_kind)",
        "CREATE INDEX IF NOT EXISTS ix_items_author ON items(author)",
        "CREATE INDEX IF NOT EXISTS ix_items_parent ON items(parent_id)",
        "CREATE INDEX IF NOT EXISTS ix_items_dedupe ON items(dedupe_hash)",
        "CREATE INDEX IF NOT EXISTS ix_items_source_captured ON items(source_captured_at)",
        # ------------------------------------------------------------------
        # items_fts — FTS5 over the most-searched text fields
        # ------------------------------------------------------------------
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
            title, body, author,
            content='items', content_rowid='id', tokenize='porter unicode61'
        )
        """,
        """
        CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
            INSERT INTO items_fts(rowid, title, body, author)
            VALUES (new.id, COALESCE(new.title,''), COALESCE(new.body,''), COALESCE(new.author,''));
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
            INSERT INTO items_fts(items_fts, rowid, title, body, author)
            VALUES ('delete', old.id, COALESCE(old.title,''), COALESCE(old.body,''), COALESCE(old.author,''));
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
            INSERT INTO items_fts(items_fts, rowid, title, body, author)
            VALUES ('delete', old.id, COALESCE(old.title,''), COALESCE(old.body,''), COALESCE(old.author,''));
            INSERT INTO items_fts(rowid, title, body, author)
            VALUES (new.id, COALESCE(new.title,''), COALESCE(new.body,''), COALESCE(new.author,''));
        END
        """,
        # ------------------------------------------------------------------
        # 4.1.3 entities — people, companies, projects, products, repos
        # ------------------------------------------------------------------
        """
        CREATE TABLE IF NOT EXISTS entities (
            id              INTEGER PRIMARY KEY,
            kind            TEXT NOT NULL CHECK(kind IN ('person','company','project','product','repo','topic')),
            name            TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            attributes_json TEXT
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_entities_norm ON entities(kind, normalized_name)",
        "CREATE INDEX IF NOT EXISTS ix_entities_kind ON entities(kind)",
        # ------------------------------------------------------------------
        # 4.1.4 item_entities — many-to-many with confidence + evidence
        # ------------------------------------------------------------------
        f"""
        CREATE TABLE IF NOT EXISTS item_entities (
            item_id         INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
            entity_id       INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            role            TEXT,
            confidence      TEXT NOT NULL CHECK(confidence IN ('high','medium','low')),
            evidence        TEXT,
            PRIMARY KEY (item_id, entity_id, role)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_item_entities_entity ON item_entities(entity_id)",
        # ------------------------------------------------------------------
        # 4.1.5 attachments
        # ------------------------------------------------------------------
        f"""
        CREATE TABLE IF NOT EXISTS attachments (
            id              INTEGER PRIMARY KEY,
            {PROVENANCE_COLS}
            item_id         INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
            kind            TEXT NOT NULL,
            local_path      TEXT,
            byte_size       INTEGER,
            sha256          TEXT,
            mime_type       TEXT,
            source_url      TEXT,
            extracted_text  TEXT
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_attachments_item ON attachments(item_id)",
        "CREATE INDEX IF NOT EXISTS ix_attachments_sha ON attachments(sha256)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_attachments_source_ext ON attachments(source_id, external_id)",
        # ------------------------------------------------------------------
        # attachments_fts
        # ------------------------------------------------------------------
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS attachments_fts USING fts5(
            extracted_text,
            content='attachments', content_rowid='id', tokenize='porter unicode61'
        )
        """,
        """
        CREATE TRIGGER IF NOT EXISTS att_ai AFTER INSERT ON attachments BEGIN
            INSERT INTO attachments_fts(rowid, extracted_text)
            VALUES (new.id, COALESCE(new.extracted_text,''));
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS att_ad AFTER DELETE ON attachments BEGIN
            INSERT INTO attachments_fts(attachments_fts, rowid, extracted_text)
            VALUES ('delete', old.id, COALESCE(old.extracted_text,''));
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS att_au AFTER UPDATE ON attachments BEGIN
            INSERT INTO attachments_fts(attachments_fts, rowid, extracted_text)
            VALUES ('delete', old.id, COALESCE(old.extracted_text,''));
            INSERT INTO attachments_fts(rowid, extracted_text)
            VALUES (new.id, COALESCE(new.extracted_text,''));
        END
        """,
        # ------------------------------------------------------------------
        # 4.1.6 metrics — every claim with source + confidence (feeds pmp brand/recruiting)
        # ------------------------------------------------------------------
        """
        CREATE TABLE IF NOT EXISTS metrics (
            id              INTEGER PRIMARY KEY,
            {PROVENANCE_COLS}
            metric_key      TEXT NOT NULL,
            value_num       REAL,
            value_text      TEXT,
            qualifier       TEXT,
            source_url      TEXT,
            entity_id       INTEGER REFERENCES entities(id) ON DELETE SET NULL,
            project_id      INTEGER REFERENCES entities(id) ON DELETE SET NULL,
            CHECK ((value_num IS NULL) <> (value_text IS NULL))
        )
        """.format(PROVENANCE_COLS=PROVENANCE_COLS),
        "CREATE INDEX IF NOT EXISTS ix_metrics_key ON metrics(metric_key)",
        "CREATE INDEX IF NOT EXISTS ix_metrics_entity ON metrics(entity_id)",
        "CREATE INDEX IF NOT EXISTS ix_metrics_source ON metrics(source_id)",
        # ------------------------------------------------------------------
        # OmniRoute attribution guard (spec §2.4 / §4.4)
        #   Trigger warns if a project is mentioned with too-strong language
        # ------------------------------------------------------------------
        """
        CREATE TRIGGER IF NOT EXISTS metrics_omniroute_guard
        BEFORE INSERT ON metrics
        FOR EACH ROW
        WHEN NEW.metric_key LIKE '%omniroute%'
             AND (NEW.value_text LIKE '%built%omniroute%'
                  OR NEW.value_text LIKE '%creator%omniroute%'
                  OR NEW.value_text LIKE '%maintainer%omniroute%'
                  OR NEW.value_text LIKE '%my 59.9k%'
                  OR NEW.value_text LIKE '%101 features%')
        BEGIN
            SELECT RAISE(ABORT, 'metrics_omniroute_guard: forbidden phrasing for OmniRoute metric');
        END
        """,
        # ------------------------------------------------------------------
        # spec_views — convenience views for the pmp consumers
        # ------------------------------------------------------------------
        """
        CREATE VIEW IF NOT EXISTS v_items_with_source AS
        SELECT i.*, s.kind AS source_kind, s.base_path AS source_base_path
        FROM items i JOIN sources s ON s.id = i.source_id
        """,
        """
        CREATE VIEW IF NOT EXISTS v_metrics_with_provenance AS
        SELECT m.*, s.kind AS source_kind
        FROM metrics m JOIN sources s ON s.id = m.source_id
        """,
        """
        CREATE VIEW IF NOT EXISTS v_attachments_text AS
        SELECT id, item_id, source_id, extracted_text
        FROM attachments WHERE extracted_text IS NOT NULL AND length(extracted_text) > 0
        """,
    ]
