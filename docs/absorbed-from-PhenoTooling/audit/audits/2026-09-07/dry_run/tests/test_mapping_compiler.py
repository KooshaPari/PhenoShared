import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
AUDIT_ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

from mapping_compiler import MappingError, compile_mapping


class MappingCompilerTests(unittest.TestCase):
    def test_maps_title_sorted_rows_with_qualified_keys(self):
        legacy = [
            {"id": "CQ-02", "domain": "code_quality", "title": "Beta"},
            {"id": "CQ-01", "domain": "code_quality", "title": "Alpha"},
        ]
        normalized = [
            {"id": "CQ-0002", "domain": "code_quality", "title": "Beta"},
            {"id": "CQ-0001", "domain": "code_quality", "title": "Alpha"},
        ]
        result = compile_mapping("substrate-v3", legacy, normalized)
        self.assertEqual(2, len(result))
        self.assertEqual(
            ["criterion-v2", "substrate-v3", "code_quality", "CQ-01"],
            result[0]["legacy_key"],
        )
        self.assertEqual(
            ["criterion-v2", "substrate-v3", "code_quality", "CQ-0001"],
            result[0]["normalized_key"],
        )

    def test_same_bare_normalized_id_stays_distinct_across_domains(self):
        legacy = [
            {"id": "DOC-01", "domain": "documentation", "title": "Guide"},
            {"id": "DX-01", "domain": "dx", "title": "Guide"},
        ]
        normalized = [
            {"id": "D-0001", "domain": "documentation", "title": "Guide"},
            {"id": "D-0001", "domain": "dx", "title": "Guide"},
        ]
        result = compile_mapping("substrate-v3", legacy, normalized)
        self.assertEqual(2, len(result))
        self.assertNotEqual(result[0]["normalized_key"], result[1]["normalized_key"])

    def test_rejects_unequal_domain_cardinality(self):
        with self.assertRaises(MappingError):
            compile_mapping("s", [{"id": "L-1", "domain": "d", "title": "One"}], [])

    def test_rejects_title_pairing_mismatch(self):
        with self.assertRaises(MappingError):
            compile_mapping(
                "s",
                [{"id": "L-1", "domain": "d", "title": "One"}],
                [{"id": "N-1", "domain": "d", "title": "Different"}],
            )

    def test_reproduces_preserved_native_to_example_crosswalk(self):
        consolidated = json.loads((AUDIT_ROOT / "CONSOLIDATED_RUBRIC.json").read_text())
        rubric = json.loads((AUDIT_ROOT / "rubric" / "rubric-v1.json").read_text())
        expected = json.loads((AUDIT_ROOT / "rubric" / "id-crosswalk.json").read_text())["mappings"]
        legacy = [row for row in consolidated["criteria"] if row.get("source") == "substrate-v3"]
        normalized = [row for row in rubric["criteria"] if row.get("source") == "substrate-v3"]
        result = compile_mapping("substrate-v3", legacy, normalized)
        actual = sorted(
            ({key: row[key] for key in ("legacy_id", "unified_id", "domain", "title")} for row in result),
            key=lambda row: (row["domain"], row["legacy_id"]),
        )
        self.assertEqual(
            sorted(expected, key=lambda row: (row["domain"], row["legacy_id"])),
            actual,
        )


if __name__ == "__main__":
    unittest.main()
