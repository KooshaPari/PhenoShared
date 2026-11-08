"""Tests for the JSONL audit-trail emitter (ADR-032 § "JSONL audit trail").

Run: pytest tests/test_emit_jsonl.py -v
or:  python3 -m unittest tests.test_emit_jsonl
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import pheno_worklog_schema as m
from pheno_worklog_schema import (
    JSONL_FIELDS,
    emit_jsonl,
    worklog_entry_to_json,
)
from pheno_worklog_schema.schema import WorklogEntry


# ---------------------------------------------------------------------------
# Fixtures — small v2.1 WORKLOG.md samples
# ---------------------------------------------------------------------------

V21_SINGLE_ROW = """| task_id | date | repo | category | title | commit_sha | pr_number | status | author | device | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V11-CC-5 | 2026-06-11 | pheno-worklog-schema | Side-CC | commit |  |  | open | koosha | macbook | First entry |
"""

V21_MULTI_ROW = """| task_id | date | repo | category | title | commit_sha | pr_number | status | author | device | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V11-CC-5 | 2026-06-11 | pheno-worklog-schema | Side-CC | commit | abc1234 | 1 | merged | koosha | macbook | First entry |
| V11-CC-6 | 2026-06-12 | pheno-worklog-schema | Side-CC | merge | def5678 | 2 | merged | koosha | heavy-runner | Second entry |
| V11-CC-7 | 2026-06-13 | pheno-worklog-schema | Side-CC | doc |  |  | open | subagent-bot | subagent | Third entry (no commit, no PR) |
| L5-104-1 | 2026-06-14 | phenotype-mcp-router | L5-Migrate | feat | 9f8e7d6 | 100 | in_progress | koosha | subagent | Fourth entry (v2.1 with all 11 columns) |
"""

V20_LEGACY = """| task_id | date | repo | category | title | commit_sha | pr_number | status | author | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V20-1.5 | 2026-06-12 | thegent | V20 | crutch | deadbeef | 50 | merged | koosha | v2.0 legacy row (device missing) |
"""

V1_LEGACY = """| Date | Task ID | Layer | Action | Files | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-06-10 | T15.7 | L0 | doc | AGENTS.md | Tier 0 substrate |
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_tmp(text: str) -> Path:
    """Write `text` to a temp file and return its Path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
    f.write(text)
    f.close()
    return Path(f.name)


def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file and return a list of parsed dicts."""
    text = path.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# worklog_entry_to_json — direct conversion tests
# ---------------------------------------------------------------------------

class TestWorklogEntryToJson(unittest.TestCase):
    def test_canonical_v21_entry(self):
        """A fully-populated v2.1 entry round-trips to the ADR-032 schema.

        Note: the V2 markdown parser sets `entry.layer` from the markdown
        `category` column at parse time, and sets `entry.action` to
        "merge" when status is "merged" (else "commit"). When constructing
        a `WorklogEntry` directly, the caller must set those fields
        explicitly (the dataclass defaults are `"L?"` and `"commit"`).
        """
        entry = WorklogEntry(
            task_id="V11-CC-5",
            date="2026-06-11",
            repo="pheno-worklog-schema",
            category="Side-CC",
            layer="Side-CC",          # mirrors what the V2 parser does at parse time
            title="commit",
            action="merge",           # mirrors V2 parser: status="merged" → action="merge"
            commit_sha="abc1234",
            pr_number=1,
            status="merged",
            author="koosha",
            device="macbook",
            notes="First entry",
        )
        line = worklog_entry_to_json(entry, derived_at="2026-06-18T12:34:56Z",
                                     tool_version="0.2.0")
        record = json.loads(line)
        # ADR-032 schema fields present
        for field in JSONL_FIELDS:
            self.assertIn(field, record, f"missing field: {field}")
        # Field values
        self.assertEqual(record["date"], "2026-06-11")
        self.assertEqual(record["task_id"], "V11-CC-5")
        self.assertEqual(record["layer"], "Side-CC")  # category → layer
        self.assertEqual(record["action"], "merge")   # status=merged → merge
        self.assertEqual(record["files"], "")         # v2.1 markdown has no files
        self.assertEqual(record["notes"], "First entry")
        self.assertEqual(record["status"], "merged")
        self.assertEqual(record["branch"], "")        # not in v2.1
        self.assertEqual(record["commit"], "abc1234")  # commit_sha → commit
        self.assertEqual(record["pr"], 1)              # pr_number → pr
        self.assertEqual(record["device"], "macbook")
        self.assertEqual(record["derived_at"], "2026-06-18T12:34:56Z")
        self.assertEqual(record["tool_version"], "0.2.0")

    def test_pr_none_serializes_as_null(self):
        """An entry with no PR number serializes pr as JSON null."""
        entry = WorklogEntry(
            task_id="V11-CC-7",
            date="2026-06-13",
            title="doc",
            status="open",
            device="subagent",
            notes="no PR",
        )
        line = worklog_entry_to_json(entry, derived_at="t", tool_version="v")
        record = json.loads(line)
        self.assertIsNone(record["pr"])
        self.assertEqual(record["commit"], "")

    def test_date_object_coerced_to_iso(self):
        """A `datetime.date` (what the v2 parser actually populates) is coerced."""
        entry = WorklogEntry(
            task_id="V11-CC-5",
            date=date(2026, 6, 11),
            title="commit",
            status="open",
            device="macbook",
        )
        line = worklog_entry_to_json(entry, derived_at="t", tool_version="v")
        record = json.loads(line)
        self.assertEqual(record["date"], "2026-06-11")

    def test_files_list_joined(self):
        """A WorklogEntry with a populated `files` list joins with commas."""
        entry = WorklogEntry(
            task_id="V11-CC-5",
            date="2026-06-11",
            title="commit",
            status="open",
            device="macbook",
            files=["src/a.py", "src/b.py"],
        )
        line = worklog_entry_to_json(entry, derived_at="t", tool_version="v")
        record = json.loads(line)
        self.assertEqual(record["files"], "src/a.py,src/b.py")

    def test_no_trailing_newline(self):
        """The function returns a line with no trailing newline (caller adds \\n)."""
        entry = WorklogEntry(task_id="V11-CC-5", date="2026-06-11",
                             title="commit", status="open", device="macbook")
        line = worklog_entry_to_json(entry, derived_at="t", tool_version="v")
        self.assertFalse(line.endswith("\n"))

    def test_field_order_is_canonical(self):
        """Field order in the serialized JSON matches ADR-032."""
        entry = WorklogEntry(task_id="V11-CC-5", date="2026-06-11",
                             title="commit", status="open", device="macbook")
        line = worklog_entry_to_json(entry, derived_at="t", tool_version="v")
        record = json.loads(line)
        self.assertEqual(list(record.keys()), list(JSONL_FIELDS))


# ---------------------------------------------------------------------------
# emit_jsonl — file-level round-trip tests
# ---------------------------------------------------------------------------

class TestEmitJsonl(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.worklog = Path(self._tmpdir.name) / "WORKLOG.md"
        self.output = Path(self._tmpdir.name) / "out.jsonl"

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write_worklog(self, text: str) -> None:
        self.worklog.write_text(text, encoding="utf-8")

    # --- basic round-trip ---

    def test_round_trip_v21_single_row(self):
        self._write_worklog(V21_SINGLE_ROW)
        n = emit_jsonl(self.worklog, self.output)
        self.assertEqual(n, 1)
        records = _read_jsonl(self.output)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["task_id"], "V11-CC-5")
        self.assertEqual(records[0]["device"], "macbook")
        self.assertEqual(records[0]["status"], "open")
        # derived_at + tool_version are present (non-empty, since default
        # values were used)
        self.assertTrue(records[0]["derived_at"])
        self.assertTrue(records[0]["tool_version"])

    def test_round_trip_v21_multi_row_all_11_cols(self):
        """Multi-row v2.1 with all 11 columns populated parses + emits correctly."""
        self._write_worklog(V21_MULTI_ROW)
        n = emit_jsonl(self.worklog, self.output)
        self.assertEqual(n, 4)
        records = _read_jsonl(self.output)
        self.assertEqual(len(records), 4)

        # Check task IDs in order
        self.assertEqual([r["task_id"] for r in records],
                         ["V11-CC-5", "V11-CC-6", "V11-CC-7", "L5-104-1"])

        # Spot-check key fields across all rows
        for r in records:
            for field in JSONL_FIELDS:
                self.assertIn(field, r)

        # Row 0: merged status → action="merge"
        self.assertEqual(records[0]["status"], "merged")
        self.assertEqual(records[0]["action"], "merge")
        self.assertEqual(records[0]["commit"], "abc1234")
        self.assertEqual(records[0]["pr"], 1)
        self.assertEqual(records[0]["device"], "macbook")

        # Row 2: open status, no commit, no PR, subagent device
        self.assertEqual(records[2]["status"], "open")
        self.assertEqual(records[2]["action"], "commit")
        self.assertEqual(records[2]["commit"], "")
        self.assertIsNone(records[2]["pr"])
        self.assertEqual(records[2]["device"], "subagent")

        # Row 3: in_progress status
        self.assertEqual(records[3]["status"], "in_progress")
        self.assertEqual(records[3]["action"], "commit")
        self.assertEqual(records[3]["pr"], 100)
        self.assertEqual(records[3]["device"], "subagent")

    # --- custom flags ---

    def test_custom_derived_at(self):
        self._write_worklog(V21_SINGLE_ROW)
        n = emit_jsonl(self.worklog, self.output,
                       derived_at="2026-06-18T09:00:00Z")
        self.assertEqual(n, 1)
        records = _read_jsonl(self.output)
        self.assertEqual(records[0]["derived_at"], "2026-06-18T09:00:00Z")

    def test_custom_tool_version(self):
        self._write_worklog(V21_SINGLE_ROW)
        n = emit_jsonl(self.worklog, self.output,
                       tool_version="0.4.2-test")
        self.assertEqual(n, 1)
        records = _read_jsonl(self.output)
        self.assertEqual(records[0]["tool_version"], "0.4.2-test")

    def test_custom_both_flags(self):
        self._write_worklog(V21_SINGLE_ROW)
        n = emit_jsonl(
            self.worklog, self.output,
            derived_at="2026-06-18T09:00:00Z",
            tool_version="0.4.2-test",
        )
        self.assertEqual(n, 1)
        records = _read_jsonl(self.output)
        self.assertEqual(records[0]["derived_at"], "2026-06-18T09:00:00Z")
        self.assertEqual(records[0]["tool_version"], "0.4.2-test")

    def test_default_derived_at_is_iso8601_z(self):
        """When derived_at is None, the emitter uses a current ISO-8601 Z timestamp."""
        self._write_worklog(V21_SINGLE_ROW)
        n = emit_jsonl(self.worklog, self.output)
        self.assertEqual(n, 1)
        records = _read_jsonl(self.output)
        derived_at = records[0]["derived_at"]
        # Should parse as ISO-8601 with 'Z' suffix
        self.assertTrue(derived_at.endswith("Z"), f"expected Z suffix: {derived_at}")
        # Should be a valid ISO-8601 datetime
        parsed = datetime.strptime(derived_at, "%Y-%m-%dT%H:%M:%SZ")
        # And within 60 seconds of now (UTC)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self.assertLess(abs((now - parsed).total_seconds()), 60)

    def test_default_tool_version_is_package_version(self):
        """When tool_version is None, the emitter uses pheno_worklog_schema.__version__."""
        self._write_worklog(V21_SINGLE_ROW)
        n = emit_jsonl(self.worklog, self.output)
        self.assertEqual(n, 1)
        records = _read_jsonl(self.output)
        self.assertEqual(records[0]["tool_version"], m.__version__)

    # --- edge cases ---

    def test_empty_worklog_emits_empty_file(self):
        """An empty WORKLOG.md yields an output file with zero records."""
        self._write_worklog("# WORKLOG\n\nNo table here.\n")
        n = emit_jsonl(self.worklog, self.output)
        self.assertEqual(n, 0)
        # The file exists and is empty (or contains only a trailing newline)
        self.assertTrue(self.output.exists())
        self.assertEqual(self.output.read_text(encoding="utf-8"), "")

    def test_worklog_with_only_header_no_rows(self):
        """A WORKLOG.md with only the header (no data rows) emits 0 entries."""
        text = ("| task_id | date | repo | category | title | commit_sha | "
                "pr_number | status | author | device | notes |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        self._write_worklog(text)
        n = emit_jsonl(self.worklog, self.output)
        self.assertEqual(n, 0)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "")

    def test_v20_legacy_worklog_parses(self):
        """A v2.0 (10-col) WORKLOG.md parses and emits (device is empty)."""
        self._write_worklog(V20_LEGACY)
        n = emit_jsonl(self.worklog, self.output)
        self.assertEqual(n, 1)
        records = _read_jsonl(self.output)
        self.assertEqual(records[0]["task_id"], "V20-1.5")
        self.assertEqual(records[0]["commit"], "deadbeef")
        self.assertEqual(records[0]["pr"], 50)
        # device is empty (v2.0 has no device column)
        self.assertEqual(records[0]["device"], "")

    def test_v1_legacy_worklog_parses(self):
        """A v1 (6-col) WORKLOG.md parses and emits."""
        self._write_worklog(V1_LEGACY)
        n = emit_jsonl(self.worklog, self.output)
        self.assertEqual(n, 1)
        records = _read_jsonl(self.output)
        self.assertEqual(records[0]["task_id"], "T15.7")
        self.assertEqual(records[0]["date"], "2026-06-10")
        self.assertEqual(records[0]["layer"], "L0")
        self.assertEqual(records[0]["action"], "doc")

    def test_output_ends_with_newline(self):
        """Each JSONL line is terminated with \\n (canonical JSONL wire format)."""
        self._write_worklog(V21_MULTI_ROW)
        n = emit_jsonl(self.worklog, self.output)
        self.assertEqual(n, 4)
        text = self.output.read_text(encoding="utf-8")
        self.assertTrue(text.endswith("\n"))
        # Each line is valid JSON
        for line in text.splitlines():
            if line.strip():
                json.loads(line)  # raises if invalid

    def test_unicode_in_notes(self):
        """Non-ASCII content in `notes` round-trips faithfully."""
        md = """| task_id | date | repo | category | title | commit_sha | pr_number | status | author | device | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V11-CC-5 | 2026-06-11 | r | L1 | commit |  |  | open | koosha | macbook | 🎯 Unicode test — café |
"""
        self._write_worklog(md)
        n = emit_jsonl(self.worklog, self.output)
        self.assertEqual(n, 1)
        records = _read_jsonl(self.output)
        self.assertIn("🎯", records[0]["notes"])
        self.assertIn("café", records[0]["notes"])

    def test_module_level_import(self):
        """emit_jsonl is importable from the top-level package."""
        self.assertTrue(callable(m.emit_jsonl))
        self.assertTrue(callable(m.worklog_entry_to_json))
        # And from the package __all__
        self.assertIn("emit_jsonl", m.__all__)
        self.assertIn("worklog_entry_to_json", m.__all__)
        self.assertIn("JSONL_FIELDS", m.__all__)

    def test_jsonl_fields_canonical_order(self):
        """JSONL_FIELDS has the ADR-032-mandated order and length."""
        self.assertEqual(len(JSONL_FIELDS), 13)
        # First 11 fields are the markdown-derived fields, last 2 are
        # derived_at + tool_version
        self.assertEqual(JSONL_FIELDS[:11], (
            "date", "task_id", "layer", "action", "files",
            "notes", "status", "branch", "commit", "pr", "device",
        ))
        self.assertEqual(JSONL_FIELDS[11:], ("derived_at", "tool_version"))

    def test_re_emit_is_idempotent(self):
        """Calling emit_jsonl twice on the same worklog overwrites cleanly."""
        self._write_worklog(V21_SINGLE_ROW)
        emit_jsonl(self.worklog, self.output,
                   derived_at="2026-06-18T09:00:00Z",
                   tool_version="0.2.0")
        size1 = self.output.stat().st_size

        emit_jsonl(self.worklog, self.output,
                   derived_at="2026-06-18T09:00:00Z",
                   tool_version="0.2.0")
        size2 = self.output.stat().st_size

        self.assertEqual(size1, size2)
        records = _read_jsonl(self.output)
        self.assertEqual(len(records), 1)

    def test_overwrite_existing_output(self):
        """emit_jsonl overwrites the destination file (no append)."""
        self._write_worklog(V21_SINGLE_ROW)
        self.output.write_text("STALE CONTENT\n", encoding="utf-8")
        emit_jsonl(self.worklog, self.output)
        text = self.output.read_text(encoding="utf-8")
        self.assertNotIn("STALE CONTENT", text)


# ---------------------------------------------------------------------------
# CLI entry-point tests
# ---------------------------------------------------------------------------

class TestCli(unittest.TestCase):
    def _run_cli(self, *args: str, input_text: str = V21_SINGLE_ROW
                 ) -> subprocess.CompletedProcess:
        """Invoke `python3 -m pheno_worklog_schema.emit_jsonl` as a subprocess.

        Writes `input_text` to a temp WORKLOG.md and passes the temp
        output path as the second positional arg. Returns the completed
        process.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as wl:
            wl.write(input_text)
            wl_path = Path(wl.name)
        out_path = wl_path.parent / "out.jsonl"
        try:
            cmd = [
                sys.executable, "-m", "pheno_worklog_schema.emit_jsonl",
                str(wl_path), str(out_path),
                *args,
            ]
            return subprocess.run(
                cmd, capture_output=True, text=True, timeout=30,
            ), out_path
        except Exception:
            wl_path.unlink(missing_ok=True)
            raise

    def test_cli_basic_invocation(self):
        result, out_path = self._run_cli()
        wl_path = out_path.parent / list(out_path.parent.glob("*.md"))[0].name
        try:
            self.assertEqual(result.returncode, 0,
                             f"stderr={result.stderr}\nstdout={result.stdout}")
            self.assertTrue(out_path.exists())
            self.assertIn("emitted 1 entries", result.stdout)
            records = _read_jsonl(out_path)
            self.assertEqual(len(records), 1)
        finally:
            wl_path.unlink(missing_ok=True)
            out_path.unlink(missing_ok=True)

    def test_cli_with_derived_at(self):
        result, out_path = self._run_cli("--derived-at", "2026-06-18T09:00:00Z")
        wl_path = out_path.parent / list(out_path.parent.glob("*.md"))[0].name
        try:
            self.assertEqual(result.returncode, 0,
                             f"stderr={result.stderr}\nstdout={result.stdout}")
            records = _read_jsonl(out_path)
            self.assertEqual(records[0]["derived_at"], "2026-06-18T09:00:00Z")
        finally:
            wl_path.unlink(missing_ok=True)
            out_path.unlink(missing_ok=True)

    def test_cli_with_tool_version(self):
        result, out_path = self._run_cli("--tool-version", "0.4.2-test")
        wl_path = out_path.parent / list(out_path.parent.glob("*.md"))[0].name
        try:
            self.assertEqual(result.returncode, 0,
                             f"stderr={result.stderr}\nstdout={result.stdout}")
            records = _read_jsonl(out_path)
            self.assertEqual(records[0]["tool_version"], "0.4.2-test")
        finally:
            wl_path.unlink(missing_ok=True)
            out_path.unlink(missing_ok=True)

    def test_cli_missing_worklog_exits_2(self):
        """Missing WORKLOG.md → exit 2 with an error on stderr."""
        out_path = Path(tempfile.mkdtemp()) / "out.jsonl"
        cmd = [
            sys.executable, "-m", "pheno_worklog_schema.emit_jsonl",
            "/nonexistent/WORKLOG.md", str(out_path),
        ]
        env = {**__import__("os").environ,
               "PYTHONPATH": str(Path(__file__).resolve().parent.parent / "src")}
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                                env=env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())


# ---------------------------------------------------------------------------
# Module-level: __main__ entry-point block
# ---------------------------------------------------------------------------

class TestMainEntryPoint(unittest.TestCase):
    def test_module_main_block_executes_via_runpy(self):
        """`python3 -m pheno_worklog_schema.emit_jsonl --help` exits cleanly
        (argparse `--help` exits with code 0 after printing help).
        """
        env = {**__import__("os").environ,
               "PYTHONPATH": str(Path(__file__).resolve().parent.parent / "src")}
        result = subprocess.run(
            [sys.executable, "-m", "pheno_worklog_schema.emit_jsonl", "--help"],
            capture_output=True, text=True, timeout=60,
            env=env,
        )
        self.assertEqual(result.returncode, 0,
                         f"stderr={result.stderr}\nstdout={result.stdout}")
        self.assertIn("JSONL audit trail", result.stdout)


if __name__ == "__main__":
    unittest.main()