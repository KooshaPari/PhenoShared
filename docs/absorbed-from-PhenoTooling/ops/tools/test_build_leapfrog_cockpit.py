"""Regression tests for the one approved temporary cockpit renderer."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("build_leapfrog_cockpit", ROOT / "build_leapfrog_cockpit.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CockpitSourceTests(unittest.TestCase):
    # FR-COCKPIT-CUSTODY-PROVENANCE: a supplied preserved ledger must be
    # visibly attributed without representing the resulting view as recovery
    # of the overwritten historical artifact.
    def test_explicit_custody_ledger_renders_checksum_count_and_non_recovery_label(self) -> None:
        records = [
            {"id": "one", "kind": "prompt", "ts": "2026-08-01T00:00:00Z"},
            {"id": "two", "kind": "goal", "ts": "2026-08-02T00:00:00Z"},
        ]
        ledger_text = "".join(json.dumps(record) + "\n" for record in records)
        expected_checksum = hashlib.sha256(ledger_text.encode("utf-8")).hexdigest()
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            ledger_path = temporary_path / "custody-ledger.jsonl"
            output_path = temporary_path / MODULE.OUTPUT_PATH.name
            ledger_path.write_text(ledger_text, encoding="utf-8")
            output_path.touch()
            with patch.object(MODULE, "OUTPUT_PATH", output_path):
                self.assertEqual(MODULE.main(["--ledger", str(ledger_path)]), 0)

            rendered = output_path.read_text(encoding="utf-8")

        self.assertIn("custody-ledger.jsonl", rendered)
        self.assertIn(expected_checksum, rendered)
        self.assertIn("2 records", rendered)
        self.assertIn("historical custody ledger", rendered)
        self.assertIn("not historical artifact recovery", rendered)
        self.assertNotIn("beads.jsonl", rendered)

    # FR-COCKPIT-CUSTODY-PROVENANCE: the rendered cards and integrity facts
    # must come from one immutable read, even if an append-only writer changes
    # the path after the builder captures its snapshot.
    def test_render_uses_one_snapshot_when_ledger_changes_during_render(self) -> None:
        initial_text = json.dumps(
            {"id": "initial", "kind": "prompt", "ts": "2026-08-01T00:00:00Z"}
        ) + "\n"
        mutated_text = initial_text + json.dumps(
            {"id": "later", "kind": "goal", "ts": "2026-08-02T00:00:00Z"}
        ) + "\n"
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            ledger_path = temporary_path / "custody-ledger.jsonl"
            output_path = temporary_path / MODULE.OUTPUT_PATH.name
            ledger_path.write_text(initial_text, encoding="utf-8")
            output_path.touch()
            real_input_provenance = MODULE.input_provenance

            def mutate_after_provenance(*args: object, **kwargs: object) -> object:
                result = real_input_provenance(*args, **kwargs)
                ledger_path.write_text(mutated_text, encoding="utf-8")
                return result

            with patch.object(MODULE, "OUTPUT_PATH", output_path), patch.object(
                MODULE, "input_provenance", side_effect=mutate_after_provenance
            ):
                self.assertEqual(MODULE.main(["--ledger", str(ledger_path)]), 0)

            rendered = output_path.read_text(encoding="utf-8")

        self.assertIn(hashlib.sha256(initial_text.encode("utf-8")).hexdigest(), rendered)
        self.assertNotIn('data-kind="goal"', rendered)

    # FR-COCKPIT-CUSTODY-PROVENANCE: default live-root input must not silently
    # claim complete historical continuity.
    def test_default_root_ledger_renders_incomplete_continuity_warning(self) -> None:
        ledger_text = json.dumps(
            {"id": "live", "kind": "prompt", "ts": "2026-08-03T00:00:00Z"}
        ) + "\n"
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            ledger_path = temporary_path / "beads.jsonl"
            output_path = temporary_path / MODULE.OUTPUT_PATH.name
            ledger_path.write_text(ledger_text, encoding="utf-8")
            output_path.touch()
            with patch.object(MODULE, "BEADS_PATH", ledger_path), patch.object(
                MODULE, "BEAD_SOURCES", (ledger_path,)
            ), patch.object(MODULE, "OUTPUT_PATH", output_path):
                self.assertEqual(MODULE.main([]), 0)

            rendered = output_path.read_text(encoding="utf-8")

        self.assertIn("live root ledger", rendered.lower())
        self.assertIn("historical continuity is incomplete", rendered.lower())

    # FR-COCKPIT-CUSTODY-PROVENANCE: an explicit spelling of the canonical
    # root path is still the live ledger, never a historical custody input.
    def test_explicit_resolved_root_ledger_keeps_live_root_label(self) -> None:
        ledger_text = json.dumps(
            {"id": "live", "kind": "prompt", "ts": "2026-08-03T00:00:00Z"}
        ) + "\n"
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            ledger_path = temporary_path / "beads.jsonl"
            output_path = temporary_path / MODULE.OUTPUT_PATH.name
            ledger_path.write_text(ledger_text, encoding="utf-8")
            output_path.touch()
            with patch.object(MODULE, "BEADS_PATH", ledger_path), patch.object(
                MODULE, "OUTPUT_PATH", output_path
            ):
                self.assertEqual(MODULE.main(["--ledger", str(ledger_path.resolve())]), 0)

            rendered = output_path.read_text(encoding="utf-8")

        self.assertIn("live root ledger", rendered.lower())
        self.assertNotIn("historical custody ledger", rendered.lower())
    def test_renderer_uses_only_the_append_only_bead_ledger(self) -> None:
        self.assertEqual(MODULE.BEAD_SOURCES, (MODULE.BEADS_PATH,))
        self.assertEqual(
            MODULE.OUTPUT_PATH.name,
            "bead-cockpit-20260809-191131-f5ca38f7.html",
        )

    def test_rendered_output_names_only_the_bead_ledger_as_its_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            ledger_path = temporary_path / "beads.jsonl"
            output_path = temporary_path / MODULE.OUTPUT_PATH.name
            ledger_path.write_text(
                json.dumps({"id": "live", "kind": "prompt", "ts": "2026-08-03T00:00:00Z"}) + "\n",
                encoding="utf-8",
            )
            output_path.touch()
            with patch.object(MODULE, "BEADS_PATH", ledger_path), patch.object(
                MODULE, "BEAD_SOURCES", (ledger_path,)
            ), patch.object(MODULE, "OUTPUT_PATH", output_path):
                self.assertEqual(MODULE.main(), 0)

            rendered = output_path.read_text(encoding="utf-8").lower()

        self.assertIn("beads.jsonl (repository root) is authoritative", rendered)
        self.assertNotIn("~/.agileplus/audit.jsonl", rendered)
        self.assertNotIn("audit mirror", rendered)

    def test_render_preserves_existing_appendix_entries_with_truthful_sources(self) -> None:
        appendix = (
            "<section data-agent=\"agent-preserved\">"
            "canonical inputs: phenotype-dag/beads.jsonl and ~/.agileplus/audit.jsonl"
            "</section>"
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            ledger_path = temporary_path / "beads.jsonl"
            output_path = temporary_path / MODULE.OUTPUT_PATH.name
            ledger_path.write_text(
                json.dumps({"id": "live", "kind": "prompt", "ts": "2026-08-03T00:00:00Z"}) + "\n",
                encoding="utf-8",
            )
            output_path.write_text(f"<!doctype html><html></html>{appendix}", encoding="utf-8")
            with patch.object(MODULE, "BEADS_PATH", ledger_path), patch.object(
                MODULE, "BEAD_SOURCES", (ledger_path,)
            ), patch.object(MODULE, "OUTPUT_PATH", output_path):
                self.assertEqual(MODULE.main(), 0)

            rendered = output_path.read_text(encoding="utf-8").lower()

        self.assertIn('data-agent="agent-preserved"', rendered)
        self.assertIn("canonical inputs: beads.jsonl and beads.jsonl", rendered)
        self.assertNotIn("~/.agileplus/audit.jsonl", rendered)


if __name__ == "__main__":
    unittest.main()
