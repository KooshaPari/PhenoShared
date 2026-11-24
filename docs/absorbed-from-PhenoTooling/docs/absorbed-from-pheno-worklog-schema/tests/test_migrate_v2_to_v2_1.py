"""Tests for the v2.0 → v2.1 migration script (ADR-015 device: column).

Run: pytest tests/test_migrate_v2_to_v2_1.py -v
or:  python -m unittest tests.test_migrate_v2_to_v2_1
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from migrate_v2_to_v2_1 import (
    V1_HEADER,
    V1P_HEADER,
    V20_HEADER,
    V21_HEADER,
    detect_format,
    is_v1,
    is_v1p,
    is_v20,
    is_v21,
    migrate_file,
    migrate_repo,
    migrate_text,
)


# Minimal v2.0 sample (10-col) used for migration tests
V20_SAMPLE = """| task_id | date | repo | category | title | commit_sha | pr_number | status | author | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1-001 | 2026-06-15 | pheno | docs | refactor | abc1234 | #1 | done | koosha | sample |
| L1-002 | 2026-06-16 | pheno | feat | scaffold | def5678 |  | wip | koosha |  |
"""

V21_EXPECTED = """| task_id | date | repo | category | title | commit_sha | pr_number | status | author | device | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1-001 | 2026-06-15 | pheno | docs | refactor | abc1234 | #1 | done | koosha |  | sample |
| L1-002 | 2026-06-16 | pheno | feat | scaffold | def5678 |  | wip | koosha |  |  |
"""


# v1 (6-col, capital) sample — pre-v2.0 legacy format. Source:
# pheno-go-ctxkit/WORKLOG.md and the local pheno-worklog-schema/WORKLOG.md.
V1_SAMPLE = """| Date | Task ID | Layer | Action | Files | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-06-18 | T15.7 | T0 | Author meta-bundle | README.md, AGENTS.md | Tier 0 substrate (ADR-023) |
| 2026-06-18 | T15.7 | T0 | Author CI | .github/workflows/ci.yml | test + lint + coverage |
"""

V21_EXPECTED_FROM_V1 = """| task_id | date | repo | category | title | commit_sha | pr_number | status | author | device | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T15.7 | 2026-06-18 |  | T0 | Author meta-bundle |  |  |  |  |  | files: README.md, AGENTS.md + Tier 0 substrate (ADR-023) |
| T15.7 | 2026-06-18 |  | T0 | Author CI |  |  |  |  |  | files: .github/workflows/ci.yml + test + lint + coverage |
"""


# v1+device (7-col, capital + device) sample — pre-v2.1 hybrid. Source:
# pheno-config/WORKLOG.md, pheno-context/WORKLOG.md, pheno-otel/WORKLOG.md,
# pheno-port-adapter/WORKLOG.md.
V1P_SAMPLE = """| Date | Task ID | Layer | Action | Files | Notes | device |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-06-18 | T1.3 | L0 | docs | meta-bundle | chore(meta): add files | macbook |
| 2026-06-15 | PR-6 | L3 | feat | src/lib.rs | v0.2.0 — TOML | heavy-runner |
"""

V21_EXPECTED_FROM_V1P = """| task_id | date | repo | category | title | commit_sha | pr_number | status | author | device | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1.3 | 2026-06-18 |  | L0 | docs |  |  |  |  | macbook | files: meta-bundle + chore(meta): add files |
| PR-6 | 2026-06-15 |  | L3 | feat |  |  |  |  | heavy-runner | files: src/lib.rs + v0.2.0 — TOML |
"""


class TestMigrateText(unittest.TestCase):
    def test_migrate_v20_to_v21(self):
        new_text, n = migrate_text(V20_SAMPLE)
        self.assertEqual(n, 2)
        # Strip trailing newline difference
        self.assertEqual(new_text.rstrip("\n"), V21_EXPECTED.rstrip("\n"))

    def test_idempotent_v21(self):
        new_text, n = migrate_text(V21_EXPECTED)
        self.assertEqual(n, 0)
        self.assertEqual(new_text, V21_EXPECTED)

    def test_unknown_format_passthrough(self):
        garbage = "# Just a title\n\nSome prose.\n"
        new_text, n = migrate_text(garbage)
        self.assertEqual(n, 0)
        self.assertEqual(new_text, garbage)

    def test_is_v20_v21_detection(self):
        self.assertTrue(is_v20(V20_SAMPLE))
        self.assertFalse(is_v21(V20_SAMPLE))
        self.assertFalse(is_v20(V21_EXPECTED))
        self.assertTrue(is_v21(V21_EXPECTED))

    def test_separator_replaced_with_11_dashes(self):
        new_text, _ = migrate_text(V20_SAMPLE)
        sep_line = [l for l in new_text.splitlines() if "---" in l][0]
        self.assertEqual(sep_line.count("---"), 11)

    def test_header_position_correct(self):
        new_text, _ = migrate_text(V20_SAMPLE)
        header_line = new_text.splitlines()[0]
        # device is at position 9 (0-indexed)
        cells = [c.strip() for c in header_line.strip("|").split("|")]
        self.assertEqual(cells[9], "device")
        # notes pushed to position 10
        self.assertEqual(cells[10], "notes")

    def test_preserves_trailing_newline(self):
        s = V20_SAMPLE + "\n"
        new_text, _ = migrate_text(s)
        self.assertTrue(new_text.endswith("\n"))

    # --- v1 (6-col, capital) migration tests (added 2026-06-18) ---

    def test_migrate_v1_to_v21(self):
        new_text, n = migrate_text(V1_SAMPLE)
        self.assertEqual(n, 2)
        self.assertTrue(is_v21(new_text))
        # Device column is empty for v1 sources (they have no device info).
        self.assertEqual(new_text.rstrip("\n"), V21_EXPECTED_FROM_V1.rstrip("\n"))

    def test_is_v1_detection(self):
        self.assertTrue(is_v1(V1_SAMPLE))
        self.assertFalse(is_v1(V1P_SAMPLE))
        self.assertFalse(is_v1(V20_SAMPLE))
        self.assertFalse(is_v1(V21_EXPECTED))

    def test_v1_idempotent_via_v21(self):
        # After v1 → v2.1 migration, the text is now v2.1; re-migrating is a no-op.
        new_text, n = migrate_text(V1_SAMPLE)
        self.assertEqual(n, 2)
        new_text2, n2 = migrate_text(new_text)
        self.assertEqual(n2, 0)
        self.assertEqual(new_text, new_text2)

    # --- v1+device (7-col, capital + device) migration tests ---

    def test_migrate_v1p_to_v21(self):
        new_text, n = migrate_text(V1P_SAMPLE)
        self.assertEqual(n, 2)
        self.assertTrue(is_v21(new_text))
        # Device values are preserved (macbook, heavy-runner).
        self.assertEqual(new_text.rstrip("\n"), V21_EXPECTED_FROM_V1P.rstrip("\n"))

    def test_is_v1p_detection(self):
        self.assertTrue(is_v1p(V1P_SAMPLE))
        self.assertFalse(is_v1p(V1_SAMPLE))
        self.assertFalse(is_v1p(V20_SAMPLE))
        self.assertFalse(is_v1p(V21_EXPECTED))

    def test_v1p_preserves_device(self):
        # The trailing device cell survives the v1+device → v2.1 migration
        # at v2.1 column 9 (the canonical `device` position).
        new_text, _ = migrate_text(V1P_SAMPLE)
        lines = [l for l in new_text.splitlines() if l.strip().startswith("|")
                 and "---" not in l]
        # lines[0] is the header; skip it.
        for row in lines[1:]:
            cells = [c.strip() for c in row.strip("|").split("|")]
            self.assertEqual(len(cells), 11)
            self.assertIn(cells[9], ("", "macbook", "heavy-runner", "subagent", "ci"))

    # --- detect_format() tests ---

    def test_detect_format(self):
        self.assertEqual(detect_format(V21_EXPECTED), "v21")
        self.assertEqual(detect_format(V20_SAMPLE), "v20")
        self.assertEqual(detect_format(V1P_SAMPLE), "v1p")
        self.assertEqual(detect_format(V1_SAMPLE), "v1")
        self.assertEqual(detect_format("# Just prose\n\nNothing here.\n"), "none")


class TestMigrateFile(unittest.TestCase):
    def test_dry_run_no_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "WORKLOG.md"
            p.write_text(V20_SAMPLE)
            n = migrate_file(p, dry_run=True)
            self.assertEqual(n, 2)
            # File should still be v2.0
            self.assertTrue(is_v20(p.read_text()))

    def test_actual_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "WORKLOG.md"
            p.write_text(V20_SAMPLE)
            n = migrate_file(p)
            self.assertEqual(n, 2)
            self.assertTrue(is_v21(p.read_text()))

    def test_idempotent_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "WORKLOG.md"
            p.write_text(V20_SAMPLE)
            migrate_file(p)
            # Second call should be a no-op
            n2 = migrate_file(p)
            self.assertEqual(n2, 0)

    def test_force_re_migrates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "WORKLOG.md"
            p.write_text(V20_SAMPLE)
            migrate_file(p)
            # Without --force: 0 rows
            self.assertEqual(migrate_file(p), 0)
            # With --force: 2 rows
            self.assertEqual(migrate_file(p, force=True), 2)


class TestMigrateRepo(unittest.TestCase):
    def test_walks_repo_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Two WORKLOG files
            (root / "WORKLOG.md").write_text(V20_SAMPLE)
            sub = root / "subdir"
            sub.mkdir()
            (sub / "WORKLOG.md").write_text(V20_SAMPLE)
            # One non-WORKLOG file
            (root / "README.md").write_text("hello")
            n_files, n_rows = migrate_repo(root)
            self.assertEqual(n_files, 2)
            self.assertEqual(n_rows, 4)

    def test_no_worklog_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("hello")
            n_files, n_rows = migrate_repo(root)
            self.assertEqual(n_files, 0)
            self.assertEqual(n_rows, 0)


if __name__ == "__main__":
    unittest.main()
