"""codex pipeline characterization.

Codex is the OpenAI Codex CLI. Source is .jsonl rollouts with session_meta /
turn_context / response_item / token_usage_record event lines. tool_use_names is
CSV TEXT; content_json is JSON. The migrator picks the LARGEST .jsonl per
session_id (smaller snapshots are intermediate states).
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
def codex_migrator():
    return importlib.import_module("codex_migrate_to_research")


@pytest.fixture
def codex_sessions_dir(tmp_path: Path) -> Path:
    """Synthetic ~/.codex/sessions/<date>/rollout-<sid>.jsonl."""
    sdir = tmp_path / "2026" / "10" / "10"
    sdir.mkdir(parents=True)
    fp = sdir / "rollout-codex-sid-1.jsonl"
    lines = [
        json.dumps({
            "type": "session_meta",
            "payload": {
                "session_id": "codex-sid-1",
                "timestamp": "2026-10-10T12:00:00Z",
                "cwd": "/tmp",
                "model_provider": "openai",
                "cli_version": "0.1.0",
                "source": "cli",
                "originator": "codex-cli",
            },
        }),
        json.dumps({
            "type": "turn_context",
            "payload": {"model": "gpt-6-astra", "effort": "low"},
        }),
        json.dumps({
            "type": "response_item",
            "timestamp": "2026-10-10T12:00:30Z",
            "payload": {
                "type": "message", "role": "user", "id": "resp-1",
                "content": [{"type": "input_text", "text": "hello"}],
            },
        }),
        json.dumps({
            "type": "response_item",
            "timestamp": "2026-10-10T12:00:35Z",
            "payload": {
                "type": "function_call", "id": "fc-1",
                "name": "bash", "arguments": '{"command": "ls"}',
                "call_id": "call-1",
            },
        }),
        json.dumps({
            "type": "response_item",
            "timestamp": "2026-10-10T12:00:40Z",
            "payload": {
                "type": "function_call_output", "id": "fco-1",
                "call_id": "call-1", "output": "file1\nfile2",
            },
        }),
        json.dumps({
            "type": "token_usage_record",
            "payload": {
                "usage": {"input_tokens": 100, "output_tokens": 50,
                          "cached_input_tokens": 25},
            },
        }),
    ]
    fp.write_text("\n".join(lines) + "\n")
    return sdir


def test_migrator_writes_codex_sessions_and_messages(
    tmp_path, codex_sessions_dir, research_db,
    codex_migrator, monkeypatch,
):
    """Phase A: 1 session + 3 response_items written (user, fc, fc_output).

    codex main() takes no argv; reads sys.argv directly.
    """
    monkeypatch.setattr(sys, "argv", [
        "codex_migrate_to_research.py",
        "--db", str(research_db),
        "--sessions-dir", str(codex_sessions_dir),
        "--since", "2026-09-01T00:00:00Z",
    ])
    rc = codex_migrator.main()
    assert rc == 0
    conn = sqlite3.connect(research_db)
    try:
        n_sess = conn.execute(
            "SELECT COUNT(*) FROM migrated_codex_sessions"
        ).fetchone()[0]
        n_msg = conn.execute(
            "SELECT COUNT(*) FROM migrated_codex_messages"
        ).fetchone()[0]
        assert n_sess == 1
        assert n_msg >= 3, f"expected >=3 messages, got {n_msg}"

        # tool_use_names is a CSV string (function_call name)
        csv = conn.execute(
            "SELECT tool_use_names FROM migrated_codex_messages "
            "WHERE role='assistant' AND tool_use_names IS NOT NULL"
        ).fetchone()
        assert csv is not None and csv[0] == "bash"

        # content_json MUST be valid JSON for every non-null row.
        # This is the regression class that caused 195,878-row corruption.
        bad = conn.execute(
            "SELECT COUNT(*) FROM migrated_codex_messages "
            "WHERE content_json IS NOT NULL "
            "AND json_valid(content_json) = 0"
        ).fetchone()[0]
        assert bad == 0, "content_json must be valid JSON"

        # The function_call payload is a JSON OBJECT (not an array).
        parsed = conn.execute(
            "SELECT content_json FROM migrated_codex_messages "
            "WHERE role='assistant' AND tool_use_names='bash'"
        ).fetchone()[0]
        obj = json.loads(parsed)
        assert isinstance(obj, dict) and obj.get("type") == "function_call"
        assert obj.get("name") == "bash"

        # source_meta_json: source is the string "cli" so the migrator
        # stores source="cli" and source_meta_json=NULL (NULL = scalar case).
        src = conn.execute(
            "SELECT source, source_meta_json FROM migrated_codex_sessions"
        ).fetchone()
        assert src[0] == "cli"
        assert src[1] is None

        # Token totals come from token_usage_record lines.
        tot = conn.execute(
            "SELECT total_input_tokens, total_output_tokens, "
            "total_cache_read_tokens FROM migrated_codex_sessions"
        ).fetchone()
        assert tot == (100, 50, 25)

        # Sources row registered.
        kind = conn.execute(
            "SELECT kind FROM sources WHERE kind='codex'"
        ).fetchone()
        assert kind is not None and kind[0] == "codex"

        # model + cli_version come from session_meta / turn_context
        meta = conn.execute(
            "SELECT model, cli_version, working_dir FROM migrated_codex_sessions"
        ).fetchone()
        assert meta == ("gpt-6-astra", "0.1.0", "/tmp")
    finally:
        conn.close()