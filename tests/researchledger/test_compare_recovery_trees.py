import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[2] / "scripts/researchledger/compare_recovery_trees.py"
spec = importlib.util.spec_from_file_location("compare_recovery", MODULE)
compare_recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare_recovery)

class ComparisonTests(unittest.TestCase):
    def setup_trees(self, home):
        old = Path(home) / "historical"
        new = Path(home) / "newer"
        old.mkdir()
        new.mkdir()
        return old, new

    def test_missing_newer_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self.setup_trees(tmp)
            new.rmdir()
            (old / "report.md").write_text("old")
            with self.assertRaisesRegex(FileNotFoundError, "SOURCE_TREE_UNAVAILABLE"):
                compare_recovery.compare(old, new)

    def test_identical_is_not_auto_merge_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self.setup_trees(tmp)
            for root in (old, new):
                (root / "file.md").write_text("same")
            r = compare_recovery.compare(old, new)
            self.assertEqual(r["counts"]["BYTE_IDENTICAL"], 1)
            self.assertFalse(r["safe_to_auto_merge"])

    def test_conflict_requires_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self.setup_trees(tmp)
            (old / "file.md").write_text("old")
            (new / "file.md").write_text("changed")
            r = compare_recovery.compare(old, new)
            self.assertEqual(r["counts"]["CONFLICT_NEEDS_THREE_WAY_REVIEW"], 1)
            self.assertTrue(r["review_required"])

    def test_absent_historical_file_cannot_be_silently_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self.setup_trees(tmp)
            (old / "file.md").write_text("old")
            r = compare_recovery.compare(old, new)
            self.assertEqual(r["counts"]["HISTORICAL_ONLY_UNRESOLVED"], 1)
            self.assertTrue(r["review_required"])

    def test_newer_only_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self.setup_trees(tmp)
            (new / "new-file.md").write_text("recent")
            r = compare_recovery.compare(old, new)
            self.assertEqual(r["counts"]["NEWER_ONLY"], 1)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self.setup_trees(tmp)
            (new / "linked").symlink_to(old, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "SYMLINK_IN_SOURCE_TREE"):
                compare_recovery.compare(old, new)

if __name__ == "__main__":
    unittest.main()
