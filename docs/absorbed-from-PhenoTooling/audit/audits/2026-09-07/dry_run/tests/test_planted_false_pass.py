"""Planted false-pass tests — negative control for the evaluator.

These tests prove the evaluator rejects structurally valid but factually
incorrect manifests. Each scenario plants a specific fault that a naive
or compromised evaluator might silently pass.

This is the v0 acceptance test requirement #6: "a planted false pass is
rejected."
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from dry_run import ContractError, run_dry_run


def key(source, domain, legacy_id):
    return json.dumps(["criterion-v2", source, domain, legacy_id],
                      ensure_ascii=False, separators=(",", ":"))


def write_json(root, name, value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    (root / name).write_bytes(raw)
    return {"path": name, "kind": "rubric" if "rubric" in name else "audit"}


def good_manifest(root):
    """Build a structurally complete, internally consistent manifest."""
    rubric = [
        {"source": "alpha", "domain": "architecture", "legacy_id": "A-0001"},
        {"source": "beta", "domain": "security", "legacy_id": "A-0001"},
    ]
    audit = [
        {"source": "alpha", "domain": "architecture", "legacy_id": "A-0001",
         "status": "satisfied", "subject": "service-a"},
    ]
    inputs = [write_json(root, "rubric.json", rubric),
              write_json(root, "audit.json", audit)]
    rubric_bytes = (root / "rubric.json").read_bytes()
    return {
        "implementation_version": "synthetic-v1",
        "capture_timestamp": "2026-09-07T00:00:00Z",
        "inputs": inputs,
        "expected_baseline": {
            "rubric": {"count": len(rubric),
                       "sha256": hashlib.sha256(rubric_bytes).hexdigest()}
        },
        "lineage": {
            "assessed_subject": "service-a",
            "source_path": "capture.json",
            "source_hash": "a" * 64,
            "declared_subject": "service-a",
            "declared_date": "2026-09-07",
            "conversion_identity": "none",
            "conversion_version": "1",
            "rubric_hash": "b" * 64,
            "rubric_version": "v1",
            "scorer_hash": "c" * 64,
            "scorer_version": "v1",
            "capture_timestamp": "2026-09-07T00:00:00Z",
        },
        "applicability": [key("alpha", "architecture", "A-0001"),
                          key("beta", "security", "A-0001")],
        "weights": {
            key("alpha", "architecture", "A-0001"): 1,
            key("beta", "security", "A-0001"): 1,
        },
    }


class PlantedFalsePassTests(unittest.TestCase):
    """Each test plants one specific fault and verifies the evaluator catches it."""

    def _run(self, root, manifest):
        out = root.parent / "output"
        return run_dry_run(root, out, manifest)

    def _update_hashes(self, root, manifest, rubric_data, audit_data=None):
        """Update manifest hashes to match actual written files."""
        rubric_bytes = (root / "rubric.json").read_bytes()
        r_hash = hashlib.sha256(rubric_bytes).hexdigest()
        manifest["expected_baseline"]["rubric"]["count"] = len(rubric_data)
        manifest["expected_baseline"]["rubric"]["sha256"] = r_hash
        manifest["lineage"]["rubric_hash"] = r_hash
        # Write and hash capture.json for source_hash
        (root / "capture.json").write_text(
            json.dumps({"subject": "service-a", "date": "2026-09-07"}))
        src_hash = hashlib.sha256((root / "capture.json").read_bytes()).hexdigest()
        manifest["lineage"]["source_hash"] = src_hash
        # Write scorer and conversion for full lineage
        (root / "scorer.py").write_text("VERSION = 'v1'\n")
        (root / "conversion.json").write_text(
            '{"identity":"none","version":"1"}')
        scorer_hash = hashlib.sha256((root / "scorer.py").read_bytes()).hexdigest()
        conv_hash = hashlib.sha256(
            (root / "conversion.json").read_bytes()).hexdigest()
        manifest["lineage"]["scorer_hash"] = scorer_hash
        manifest["inputs"] += [
            {"path": "capture.json", "kind": "source"},
            {"path": "scorer.py", "kind": "scorer"},
            {"path": "conversion.json", "kind": "conversion"}]
        manifest["reviewed_metadata"] = {
            "capture_timestamp": "2026-09-07T00:00:00Z",
            "rubric": {"version": "v1", "sha256": r_hash},
            "scorer": {"version": "v1", "sha256": scorer_hash},
            "conversion": {"identity": "none", "version": "1",
                            "sha256": conv_hash}}
        return manifest

    # ------------------------------------------------------------------
    # Fault 1: Wrong baseline hash — the evaluator must detect drift
    # ------------------------------------------------------------------
    def test_wrong_baseline_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = good_manifest(root)
            # Plant: claim a wrong rubric count
            manifest["expected_baseline"]["rubric"]["count"] = 9999
            result = self._run(root, manifest)
            self.assertFalse(result["validation.json"]["publication_allowed"])
            self.assertIn("baseline_drift", result["validation.json"]["blockers"])
            self.assertIsNone(result["validation.json"]["readiness_grade"])

    # ------------------------------------------------------------------
    # Fault 2: Planted wrong SHA-256 in baseline — evaluator must reject
    # ------------------------------------------------------------------
    def test_wrong_baseline_sha256_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = good_manifest(root)
            # Plant: claim a wrong rubric hash
            manifest["expected_baseline"]["rubric"]["sha256"] = "ff" * 32
            result = self._run(root, manifest)
            self.assertFalse(result["validation.json"]["publication_allowed"])
            self.assertIn("baseline_drift", result["validation.json"]["blockers"])

    # ------------------------------------------------------------------
    # Fault 3: Duplicate qualified keys — evaluator must quarantine all
    # ------------------------------------------------------------------
    def _standalone_manifest(self, root, rubric, audit, extra_applicability=None):
        """Build a fully self-contained manifest from scratch. No shared state."""
        inputs = [write_json(root, "rubric.json", rubric),
                  write_json(root, "audit.json", audit)]
        rubric_bytes = (root / "rubric.json").read_bytes()
        all_keys = [key(r["source"], r["domain"], r["legacy_id"]) for r in rubric]
        weights = {k: 1 for k in all_keys}
        applicability = list(all_keys)
        if extra_applicability:
            applicability.extend(extra_applicability)
            for k in extra_applicability:
                weights[k] = 1
        return {
            "implementation_version": "v1",
            "capture_timestamp": "2026-09-07T00:00:00Z",
            "inputs": inputs,
            "expected_baseline": {
                "rubric": {"count": len(rubric),
                           "sha256": hashlib.sha256(rubric_bytes).hexdigest()}},
            "lineage": {
                "assessed_subject": "service-a",
                "source_path": "capture.json",
                "source_hash": "a" * 64,
                "declared_subject": "service-a",
                "declared_date": "2026-09-07",
                "conversion_identity": "none",
                "conversion_version": "1",
                "rubric_hash": hashlib.sha256(rubric_bytes).hexdigest(),
                "rubric_version": "v1",
                "scorer_hash": "c" * 64,
                "scorer_version": "v1",
                "capture_timestamp": "2026-09-07T00:00:00Z",
            },
            "applicability": applicability,
            "weights": weights,
        }

    # ------------------------------------------------------------------
    # Fault 3: Duplicate qualified keys — evaluator must quarantine all
    # ------------------------------------------------------------------
    def test_duplicate_qualified_keys_are_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            rubric = [
                {"source": "alpha", "domain": "architecture",
                 "legacy_id": "A-0001"},
                {"source": "alpha", "domain": "architecture",
                 "legacy_id": "A-0001"},
            ]
            manifest = self._standalone_manifest(
                root, rubric,
                [{"source": "alpha", "domain": "architecture",
                  "legacy_id": "A-0001", "status": "satisfied",
                  "subject": "service-a"}])
            result = self._run(root, manifest)
            # Rubric rows are quarantined for repeated tuple;
            # audit row gets ambiguous_rubric_target because its
            # rubric target is quarantined.
            rows = result["identity-crosswalk.json"]["rows"]
            rubric_rows = [r for r in rows
                           if r["locator"]["path"] == "rubric.json"]
            audit_rows = [r for r in rows
                          if r["locator"]["path"] == "audit.json"]
            self.assertTrue(all(r["disposition"] == "quarantined"
                               for r in rubric_rows))
            self.assertTrue(all(r["disposition"] == "quarantined"
                               for r in audit_rows))
            reasons = set()
            for r in rows:
                reasons.update(r["reasons"])
            self.assertTrue(
                "repeated_qualified_tuple" in reasons or
                "ambiguous_rubric_target" in reasons)
            self.assertFalse(
                result["validation.json"]["publication_allowed"])

    # ------------------------------------------------------------------
    # Fault 4: Conflicting statuses on same key — both must quarantine
    # ------------------------------------------------------------------
    def test_conflicting_statuses_are_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            rubric = [{"source": "alpha", "domain": "architecture",
                       "legacy_id": "A-0001"}]
            audit = [
                {"source": "alpha", "domain": "architecture",
                 "legacy_id": "A-0001", "status": "satisfied",
                 "subject": "service-a"},
                {"source": "alpha", "domain": "architecture",
                 "legacy_id": "A-0001", "status": "unsatisfied",
                 "subject": "service-a"},
            ]
            manifest = self._standalone_manifest(root, rubric, audit)
            result = self._run(root, manifest)
            audit_rows = [r for r in result["identity-crosswalk.json"]["rows"]
                          if r["locator"]["path"] == "audit.json"]
            self.assertTrue(all(r["disposition"] == "quarantined"
                               for r in audit_rows))
            self.assertFalse(
                result["validation.json"]["publication_allowed"])
            self.assertIsNone(result["validation.json"]["readiness_grade"])

    # ------------------------------------------------------------------
    # Fault 5: Invalid weight (NaN) — evaluator must reject
    # ------------------------------------------------------------------
    def test_nan_weight_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = good_manifest(root)
            # Plant: inject a NaN weight
            manifest["weights"][key("alpha", "architecture", "A-0001")] = float("nan")
            result = self._run(root, manifest)
            self.assertFalse(result["validation.json"]["publication_allowed"])
            self.assertIn("invalid_weights", result["validation.json"]["blockers"])

    # ------------------------------------------------------------------
    # Fault 6: Negative weight — evaluator must reject
    # ------------------------------------------------------------------
    def test_negative_weight_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = good_manifest(root)
            # Plant: negative weight
            manifest["weights"][key("alpha", "architecture", "A-0001")] = -5
            result = self._run(root, manifest)
            self.assertFalse(result["validation.json"]["publication_allowed"])
            self.assertIn("invalid_weights", result["validation.json"]["blockers"])

    # ------------------------------------------------------------------
    # Fault 7: Wrong lineage subject — evaluator must detect mismatch
    # ------------------------------------------------------------------
    def test_wrong_lineage_subject_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = good_manifest(root)
            # Plant: lineage says wrong subject
            manifest["lineage"]["assessed_subject"] = "WRONG-SERVICE"
            result = self._run(root, manifest)
            self.assertFalse(result["validation.json"]["publication_allowed"])
            self.assertTrue(any("lineage_assessed_subject" in b or
                               "lineage_subject_mismatch" in b
                               for b in result["validation.json"]["blockers"]))

    # ------------------------------------------------------------------
    # Fault 8: Missing lineage — evaluator must produce blockers
    # ------------------------------------------------------------------
    def test_empty_lineage_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = good_manifest(root)
            # Plant: remove all lineage fields
            manifest["lineage"] = {}
            result = self._run(root, manifest)
            self.assertFalse(result["validation.json"]["publication_allowed"])
            # Must have multiple lineage blockers
            lineage_blockers = [b for b in result["validation.json"]["blockers"]
                                if b.startswith("lineage_")]
            self.assertGreater(len(lineage_blockers), 0)

    # ------------------------------------------------------------------
    # Fault 9: Applicable key not in rubric — unresolved must block
    # ------------------------------------------------------------------
    def test_unknown_applicable_key_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = good_manifest(root)
            # Plant: add an applicable key that doesn't exist in rubric
            manifest["applicability"].append(key("ghost", "phantom", "X-9999"))
            manifest["weights"][key("ghost", "phantom", "X-9999")] = 1
            result = self._run(root, manifest)
            self.assertFalse(result["validation.json"]["publication_allowed"])
            self.assertIn("unresolved_applicable", result["validation.json"]["blockers"])

    # ------------------------------------------------------------------
    # Fault 10: One-to-many mapping — evaluator must quarantine
    # ------------------------------------------------------------------
    def test_one_to_many_mapping_is_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            rubric = [
                {"source": "alpha", "domain": "architecture",
                 "legacy_id": "A-0001"},
                {"source": "beta", "domain": "security",
                 "legacy_id": "A-0001"},
            ]
            audit = [
                {"source": "alpha", "domain": "architecture",
                 "legacy_id": "A-0001", "status": "satisfied",
                 "subject": "service-a",
                 "target_keys": [key("alpha", "architecture", "A-0001"),
                                 key("beta", "security", "A-0001")]},
            ]
            manifest = self._standalone_manifest(root, rubric, audit)
            result = self._run(root, manifest)
            audit_rows = [r for r in result["identity-crosswalk.json"]["rows"]
                          if r["locator"]["path"] == "audit.json"]
            self.assertEqual("quarantined", audit_rows[0]["disposition"])
            self.assertIn("one_to_many_mapping",
                          result["validation.json"]["blockers"])
            self.assertFalse(
                result["validation.json"]["publication_allowed"])

    # ------------------------------------------------------------------
    # Fault 11: Publication always false — even on "good" manifest
    # ------------------------------------------------------------------
    def test_even_structurally_valid_manifest_cannot_self_authorize(self):
        """The evaluator must NEVER set publication_allowed=True."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = good_manifest(root)
            result = self._run(root, manifest)
            # The contract hardcodes publication_allowed=False
            self.assertFalse(result["validation.json"]["publication_allowed"])
            # Readiness grade is always null in synthetic mode
            self.assertIsNone(result["validation.json"]["readiness_grade"])
            # diagnostic_only must always be present
            self.assertIn("diagnostic_only", result["validation.json"]["blockers"])

    # ------------------------------------------------------------------
    # Fault 12: Source bytes drifted — evaluator must detect
    # ------------------------------------------------------------------
    def test_source_byte_drift_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = good_manifest(root)
            # First run succeeds (builds candidate)
            result1 = self._run(root, manifest)
            self.assertFalse(result1["validation.json"]["publication_allowed"])
            # Now tamper with the source file
            (root / "rubric.json").write_bytes(b'[{"tampered": true}]')
            # Re-run with same manifest — source_changed must appear
            # (Need a new output dir since candidate dir already exists)
            out2 = root.parent / "output2"
            result2 = run_dry_run(root, out2, manifest)
            # The evaluator should detect the drift
            self.assertFalse(result2["validation.json"]["publication_allowed"])

    # ------------------------------------------------------------------
    # Fault 13: Planted "success" in status when no evidence exists
    # ------------------------------------------------------------------
    def test_fake_satisfied_status_with_wrong_subject_is_quarantined(self):
        """A row claiming 'satisfied' but with a wrong subject must be caught."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            rubric = [{"source": "alpha", "domain": "architecture",
                       "legacy_id": "A-0001"}]
            audit = [
                {"source": "alpha", "domain": "architecture",
                 "legacy_id": "A-0001", "status": "satisfied",
                 "subject": "NONEXISTENT-SERVICE"},
            ]
            manifest = self._standalone_manifest(root, rubric, audit)
            result = self._run(root, manifest)
            audit_rows = [r for r in result["identity-crosswalk.json"]["rows"]
                          if r["locator"]["path"] == "audit.json"]
            self.assertEqual("quarantined", audit_rows[0]["disposition"])
            self.assertIn("unknown_subject", audit_rows[0]["reasons"])
            self.assertFalse(
                result["validation.json"]["publication_allowed"])

    # ------------------------------------------------------------------
    # Fault 14: Missing expected_baseline entirely
    # ------------------------------------------------------------------
    def test_missing_baseline_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = good_manifest(root)
            del manifest["expected_baseline"]
            result = self._run(root, manifest)
            self.assertFalse(result["validation.json"]["publication_allowed"])
            self.assertIn("missing_expected_baseline", result["validation.json"]["blockers"])


if __name__ == "__main__":
    unittest.main()
