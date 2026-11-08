import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from snapshot_adapter import AdapterError, adapt_snapshot, build_draft_manifest


class SnapshotAdapterTests(unittest.TestCase):
    def write(self, root, name, value):
        path = root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_rubric_criteria_rows_preserve_values_and_exact_locators(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(Path(tmp), "rubric.json", {
                "version": "v1", "criteria": [{"id": "A-0001", "source": "s",
                "domain": "d", "status": "satisfied"}]})
            result = adapt_snapshot(path, "rubric")
            self.assertEqual("UNREVIEWED", result["status"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), result["source"]["sha256"])
            self.assertEqual("$.criteria[0]", result["records"][0]["source_locator"])
            self.assertEqual({"id": "A-0001", "source": "s", "domain": "d", "status": "satisfied"}, result["records"][0]["raw"])
            self.assertEqual([], result["blockers"])

    def test_card_criteria_without_reviewed_mapping_is_unreviewed_and_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(Path(tmp), "card.json", {"criteria": [{"id": "A-0001", "status": "satisfied"}]})
            result = adapt_snapshot(path, "card")
            self.assertEqual(["missing_reviewed_mapping"], result["records"][0]["blockers"])
            self.assertEqual({"id": "A-0001", "status": "satisfied"}, result["records"][0]["raw"])
            self.assertNotIn("translated", result["records"][0])

    def test_unsupported_top_level_shape_is_quarantined_without_row_flattening(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(Path(tmp), "bad.json", {"entries": [{"id": "A-1"}]})
            result = adapt_snapshot(path, "card")
            self.assertEqual([], result["records"])
            self.assertEqual(["unsupported_top_level_shape"], result["blockers"])
            self.assertEqual({"entries": [{"id": "A-1"}]}, result["raw_envelope"])

    def test_explicit_bundle_is_an_unreviewed_manifest_without_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "rubric.json", {"criteria": []})
            self.write(root, "card.json", {"criteria": [{"id": "A-0001", "status": "satisfied"}]})
            result = build_draft_manifest(root, [{"path": "rubric.json", "kind": "rubric"},
                                                 {"path": "card.json", "kind": "card"}])
            self.assertEqual("UNREVIEWED", result["status"])
            self.assertEqual(["rubric.json", "card.json"], [x["source"]["path"] for x in result["inputs"]])
            self.assertEqual(["missing_reviewed_mapping"], result["blockers"])
            with self.assertRaises(AdapterError):
                build_draft_manifest(root, [{"path": "../card.json", "kind": "card"}])

    def test_overflow_number_is_rejected_before_a_draft_is_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "overflow.json"
            path.write_text('{"criteria":[{"source":"s","domain":"d","id":"i","weight":1e999}]}')
            with self.assertRaises(AdapterError):
                adapt_snapshot(path, "rubric")


if __name__ == "__main__":
    unittest.main()
