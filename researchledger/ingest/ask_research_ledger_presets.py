"""Preset definitions for ask_research_ledger.py — pure data, no logic.

Each dict maps a preset name to a tuple consumed by ask_research_ledger.main():

  PRESETS         -> {name: (description, sql)}       run via conn.execute(sql)
  PYTHON_PRESETS  -> {name: description}               dispatched in main()
  INSPECT_QUERIES -> {name: (description, sql)}        schema introspection

Read-only is enforced at the connection level (mode=ro URI), so any preset
or custom query that tries to write will be rejected by sqlite itself.
"""

# --preset definitions. Each is a (description, sql) pair.
PRESETS = {
    "counts": (
        "Per-source item/attachment counts (the headline number)",
        "SELECT s.id, s.kind, "
        "  (SELECT COUNT(*) FROM items WHERE source_id = s.id) AS items, "
        "  (SELECT COUNT(*) FROM attachments WHERE source_id = s.id) AS attachments "
        "FROM sources s ORDER BY s.id",
    ),
    "by-source": (
        "Per-source totals only (compact, no attachment count)",
        "SELECT s.kind, COUNT(i.id) AS n "
        "FROM sources s LEFT JOIN items i ON i.source_id = s.id "
        "GROUP BY s.kind ORDER BY n DESC",
    ),
    "by-day": (
        "Per-day item counts, last 30 days (across all sources)",
        "SELECT DATE(captured_at) AS day, COUNT(*) AS n "
        "FROM items "
        "WHERE captured_at >= DATE('now', '-30 days') "
        "GROUP BY DATE(captured_at) ORDER BY day DESC",
    ),
    "by-source-by-day": (
        "Per-source per-day counts, last 30 days (small grid)",
        "SELECT s.kind, DATE(i.captured_at) AS day, COUNT(*) AS n "
        "FROM items i JOIN sources s ON s.id = i.source_id "
        "WHERE i.captured_at >= DATE('now', '-30 days') "
        "GROUP BY s.kind, DATE(i.captured_at) "
        "ORDER BY day DESC, n DESC",
    ),
    "by-item-kind": (
        "All distinct item_kind values with counts (top 30)",
        "SELECT item_kind, COUNT(*) AS n "
        "FROM items GROUP BY item_kind ORDER BY n DESC LIMIT 30",
    ),
    "by-author": (
        "Top 20 author values across all sources",
        "SELECT COALESCE(author, '<null>') AS author, COUNT(*) AS n "
        "FROM items GROUP BY author ORDER BY n DESC LIMIT 20",
    ),
    "by-model": (
        "Top 20 model values (harness data only; reads from attrs_json)",
        "SELECT json_extract(attrs_json, '$.model') AS model, COUNT(*) AS n "
        "FROM items "
        "WHERE json_extract(attrs_json, '$.model') IS NOT NULL "
        "GROUP BY model ORDER BY n DESC LIMIT 20",
    ),
    "by-redaction": (
        "Per-source redaction state distribution",
        "SELECT s.kind, i.redaction_state, COUNT(*) AS n "
        "FROM items i JOIN sources s ON s.id = i.source_id "
        "GROUP BY s.kind, i.redaction_state "
        "ORDER BY s.id, i.redaction_state",
    ),
    "by-confidence": (
        "Per-source evidence-confidence distribution",
        "SELECT s.kind, i.confidence, i.evidence_type, COUNT(*) AS n "
        "FROM items i JOIN sources s ON s.id = i.source_id "
        "GROUP BY s.kind, i.confidence, i.evidence_type "
        "ORDER BY s.id, i.confidence",
    ),
    "recent": (
        "Most recent 20 items across all sources",
        "SELECT s.kind, i.item_kind, i.captured_at, "
        "  COALESCE(SUBSTR(i.title, 1, 60), SUBSTR(i.body, 1, 60)) AS snippet, "
        "  COALESCE(i.author, '<null>') AS author "
        "FROM items i JOIN sources s ON s.id = i.source_id "
        "ORDER BY i.captured_at DESC LIMIT 20",
    ),
    "tokens-by-source": (
        "Token usage by source (only for sources that record token counts)",
        "SELECT s.kind, "
        "  ROUND(SUM(COALESCE(json_extract(attrs_json, '$.input_tokens'), 0)) / 1e6, 1) AS input_m, "
        "  ROUND(SUM(COALESCE(json_extract(attrs_json, '$.output_tokens'), 0)) / 1e6, 1) AS output_m, "
        "  ROUND(SUM(COALESCE(json_extract(attrs_json, '$.cache_read_tokens'), 0)) / 1e6, 1) AS cache_read_m, "
        "  ROUND(SUM(COALESCE(json_extract(attrs_json, '$.cache_write_tokens'), 0)) / 1e6, 1) AS cache_write_m, "
        "  COUNT(*) AS n "
        "FROM items i JOIN sources s ON s.id = i.source_id "
        "GROUP BY s.kind ORDER BY input_m DESC NULLS LAST",
    ),
    "tokens-by-model": (
        "Top 20 models by total input tokens (from harness data)",
        "SELECT json_extract(attrs_json, '$.model') AS model, "
        "  ROUND(SUM(COALESCE(json_extract(attrs_json, '$.input_tokens'), 0)) / 1e9, 2) AS input_b, "
        "  ROUND(SUM(COALESCE(json_extract(attrs_json, '$.output_tokens'), 0)) / 1e6, 1) AS output_m, "
        "  COUNT(*) AS n "
        "FROM items "
        "WHERE json_extract(attrs_json, '$.model') IS NOT NULL "
        "  AND json_extract(attrs_json, '$.input_tokens') IS NOT NULL "
        "GROUP BY model ORDER BY input_b DESC LIMIT 20",
    ),
    "search": (
        "FTS5 search across items.title/body/author (use --query)",
        # Filled in by main() based on --query, this is just the template.
        "SELECT s.kind, i.item_kind, i.captured_at, "
        "  COALESCE(SUBSTR(i.title, 1, 80), SUBSTR(i.body, 1, 80)) AS snippet "
        "FROM items_fts f "
        "JOIN items i ON i.id = f.rowid "
        "JOIN sources s ON s.id = i.source_id "
        "WHERE items_fts MATCH ? "
        "ORDER BY rank LIMIT 20",
    ),
    "attachments-by-source": (
        "Per-source attachment counts and total bytes",
        "SELECT s.kind, COUNT(a.id) AS n, "
        "  ROUND(SUM(COALESCE(a.byte_size, 0)) / 1024.0 / 1024.0, 1) AS mb "
        "FROM sources s LEFT JOIN attachments a ON a.source_id = s.id "
        "GROUP BY s.kind ORDER BY n DESC",
    ),
    "attachments-by-kind": (
        "Per-source per-kind attachment counts (top 30)",
        "SELECT s.kind, a.kind, COUNT(*) AS n "
        "FROM attachments a JOIN sources s ON s.id = a.source_id "
        "GROUP BY s.kind, a.kind ORDER BY n DESC LIMIT 30",
    ),
    "orphan-check": (
        "Sanity: any items with no source, or no source_captured_at",
        "SELECT 'no_source' AS k, COUNT(*) AS n FROM items "
        "WHERE source_id NOT IN (SELECT id FROM sources) "
        "UNION ALL "
        "SELECT 'no_capture', COUNT(*) FROM items WHERE captured_at IS NULL "
        "UNION ALL "
        "SELECT 'no_source_capture', COUNT(*) FROM items WHERE source_captured_at IS NULL "
        "UNION ALL "
        "SELECT 'orphans_in_attachments', COUNT(*) FROM attachments a "
        "  WHERE a.item_id NOT IN (SELECT id FROM items)",
    ),
    "dedupe-stats": (
        "Per-source dedupe_hash distribution (how much is unique vs repeated)",
        "SELECT s.kind, "
        "  COUNT(*) AS n_items, "
        "  COUNT(DISTINCT i.dedupe_hash) AS n_unique_hashes, "
        "  ROUND(100.0 * COUNT(DISTINCT i.dedupe_hash) / NULLIF(COUNT(*), 0), 1) AS pct_unique "
        "FROM items i JOIN sources s ON s.id = i.source_id "
        "GROUP BY s.kind ORDER BY n_items DESC",
    ),
    "schema-version": (
        "Per-source schema_version + captured_at (was the migrate run clean?)",
        "SELECT id, kind, schema_version, captured_at, byte_size "
        "FROM sources ORDER BY id",
    ),
    "fts-coverage": (
        "FTS5 sanity: do all items have an FTS entry?",
        "SELECT "
        "  (SELECT COUNT(*) FROM items) AS items, "
        "  (SELECT COUNT(*) FROM items_fts) AS fts_rows, "
        "  (SELECT COUNT(*) FROM items) - (SELECT COUNT(*) FROM items_fts) AS missing",
    ),
    "tool-names-malformed": (
        "Sanity: any items with tool_use_names/tool_call_names that are not valid JSON arrays "
        "(regression check; W9-11 fixup removed 195,878 of these; clean DB shows 0 rows)",
        "SELECT source_id, "
        "  COUNT(*) FILTER (WHERE json_extract(attrs_json, '$.tool_use_names') IS NOT NULL "
        "                    AND json_valid(json_extract(attrs_json, '$.tool_use_names')) = 0) "
        "    AS tool_use_names_malformed, "
        "  COUNT(*) FILTER (WHERE json_extract(attrs_json, '$.tool_call_names') IS NOT NULL "
        "                    AND json_valid(json_extract(attrs_json, '$.tool_call_names')) = 0) "
        "    AS tool_call_names_malformed, "
        "  (COUNT(*) FILTER (WHERE json_extract(attrs_json, '$.tool_use_names') IS NOT NULL "
        "                    AND json_valid(json_extract(attrs_json, '$.tool_use_names')) = 0)) "
        "    + "
        "  (COUNT(*) FILTER (WHERE json_extract(attrs_json, '$.tool_call_names') IS NOT NULL "
        "                    AND json_valid(json_extract(attrs_json, '$.tool_call_names')) = 0)) "
        "    AS total_malformed "
        "FROM items "
        "GROUP BY source_id "
        "HAVING total_malformed > 0 "
        "ORDER BY total_malformed DESC",
    ),
}

# Presets that need Python post-processing rather than raw SQL.
PYTHON_PRESETS = {
    "tokens-by-day": "Per-day total input tokens across all sources (Python aggregation; can be slow)",
    "model-routing": "Cross-source model usage (any source with attrs_json.model)",
}

# Schema introspection queries (run via --inspect).
INSPECT_QUERIES = {
    "schema": (
        "All tables, views, and indexes",
        "SELECT type, name FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' "
        "ORDER BY type, name",
    ),
    "sources": (
        "sources table contents",
        "SELECT * FROM sources ORDER BY id",
    ),
    "items-schema": (
        "items table schema",
        "SELECT sql FROM sqlite_master WHERE name = 'items'",
    ),
    "items-sample": (
        "10 sample items (most recent)",
        "SELECT id, source_id, item_kind, author, captured_at, "
        "  SUBSTR(body, 1, 100) AS body_preview "
        "FROM items ORDER BY id DESC LIMIT 10",
    ),
    "counts-summary": (
        "Headline numbers (item count, attachment count, FTS rows)",
        "SELECT "
        "  (SELECT COUNT(*) FROM items) AS items, "
        "  (SELECT COUNT(*) FROM attachments) AS attachments, "
        "  (SELECT COUNT(*) FROM sources) AS sources, "
        "  (SELECT COUNT(*) FROM items_fts) AS fts_rows, "
        "  (SELECT COUNT(*) FROM entities) AS entities, "
        "  (SELECT COUNT(*) FROM item_entities) AS item_entities, "
        "  (SELECT COUNT(*) FROM metrics) AS metrics",
    ),
}
