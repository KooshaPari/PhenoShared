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
    return json.dumps(["criterion-v2", source, domain, legacy_id], ensure_ascii=False,
                      separators=(",", ":"))


def write_json(root, name, value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    (root / name).write_bytes(raw)
    return {"path": name, "kind": "rubric" if name == "rubric.json" else "audit"}


def fixture(root, rubric=None, audit=None, **changes):
    rubric = rubric if rubric is not None else [
        {"source": "alpha", "domain": "architecture", "legacy_id": "A-0001"},
        {"source": "beta", "domain": "security", "legacy_id": "A-0001"},
    ]
    audit = audit if audit is not None else [
        {"source": "alpha", "domain": "architecture", "legacy_id": "A-0001",
         "status": "satisfied", "subject": "service-a"},
    ]
    inputs = [write_json(root, "rubric.json", rubric), write_json(root, "audit.json", audit)]
    rubric_bytes = (root / "rubric.json").read_bytes()
    manifest = {
        "implementation_version": "synthetic-v1",
        "capture_timestamp": "2026-09-07T00:00:00Z",
        "inputs": inputs,
        "expected_baseline": {"rubric": {"count": len(rubric),
                                           "sha256": hashlib.sha256(rubric_bytes).hexdigest()}},
        "lineage": {
            "assessed_subject": "service-a", "source_path": "capture.json",
            "source_hash": "a" * 64, "declared_subject": "service-a",
            "declared_date": "2026-09-07", "conversion_identity": "none",
            "conversion_version": "1", "rubric_hash": "b" * 64,
            "rubric_version": "v1", "scorer_hash": "c" * 64,
            "scorer_version": "v1", "capture_timestamp": "2026-09-07T00:00:00Z",
        },
        "applicability": [key("alpha", "architecture", "A-0001"),
                            key("beta", "security", "A-0001")],
        "weights": {key("alpha", "architecture", "A-0001"): 1,
                    key("beta", "security", "A-0001"): 1},
    }
    manifest.update(changes)
    return manifest


class DryRunContractTests(unittest.TestCase):
    def run_fixture(self, **changes):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "input"
        out = Path(tmp.name) / "output"
        root.mkdir()
        return root, out, run_dry_run(root, out, fixture(root, **changes))

    def valid_frozen_manifest(self, root):
        manifest = fixture(root)
        (root / "capture.json").write_text('{"subject":"service-a","date":"2026-09-07"}')
        (root / "scorer.py").write_text("VERSION = 'v1'\n")
        (root / "conversion.json").write_text('{"identity":"none","version":"1"}')
        source = (root / "capture.json").read_bytes()
        rubric = (root / "rubric.json").read_bytes()
        scorer = (root / "scorer.py").read_bytes()
        conversion = (root / "conversion.json").read_bytes()
        manifest["inputs"] += [{"path": "capture.json", "kind": "source"},
                               {"path": "scorer.py", "kind": "scorer"},
                               {"path": "conversion.json", "kind": "conversion"}]
        manifest["lineage"].update({"source_hash": hashlib.sha256(source).hexdigest(),
                                    "rubric_hash": hashlib.sha256(rubric).hexdigest(),
                                    "scorer_hash": hashlib.sha256(scorer).hexdigest()})
        manifest["reviewed_metadata"] = {"capture_timestamp": "2026-09-07T00:00:00Z",
                                         "rubric": {"version": "v1", "sha256": hashlib.sha256(rubric).hexdigest()},
                                         "scorer": {"version": "v1", "sha256": hashlib.sha256(scorer).hexdigest()},
                                         "conversion": {"identity": "none", "version": "1", "sha256": hashlib.sha256(conversion).hexdigest()}}
        manifest["applicability"] = [key("alpha", "architecture", "A-0001")]
        manifest["weights"] = {manifest["applicability"][0]: 1}
        return manifest

    def test_reviewed_artifact_hashes_and_all_capture_timestamps_must_bind(self):
        for mutate, blocker in (("scorer_hash", "reviewed_scorer_hash"),
                                ("conversion_hash", "reviewed_conversion_hash"),
                                ("top_capture", "lineage_capture_timestamp")):
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "input"
                root.mkdir()
                manifest = self.valid_frozen_manifest(root)
                if mutate == "top_capture":
                    manifest["capture_timestamp"] = "1999-01-01T00:00:00Z"
                else:
                    target = "scorer" if mutate == "scorer_hash" else "conversion"
                    manifest["reviewed_metadata"][target]["sha256"] = "0" * 64
                result = run_dry_run(root, Path(tmp) / "out", manifest)
                self.assertIn(blocker, result["validation.json"]["blockers"])

    def test_nonfinite_input_leaves_no_partial_candidate_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output = Path(tmp) / "out"
            root.mkdir()
            manifest = fixture(root)
            (root / "audit.json").write_text('[{"source":"alpha","domain":"architecture",'
                                              '"legacy_id":"A-0001","status":"satisfied",'
                                              '"subject":"service-a","extra":1e400}]')
            with self.assertRaises(ContractError):
                run_dry_run(root, output, manifest)
            self.assertFalse(output.exists())
            (root / "audit.json").write_text("[]")
            self.assertIsNotNone(run_dry_run(root, output, manifest)["output_dir"])

    def test_malformed_nested_values_fail_closed_without_runtime_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            result = run_dry_run(root, Path(tmp) / "out", fixture(root, audit=[
                {"source": "alpha", "domain": "architecture", "legacy_id": "A-0001",
                 "status": [], "subject": "service-a"}]))
            self.assertEqual("quarantined", result["identity-crosswalk.json"]["rows"][-1]["disposition"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = fixture(root, lineage=None)
            with self.assertRaises(ContractError):
                run_dry_run(root, Path(tmp) / "out", manifest)

    def test_candidate_identity_includes_frozen_semantic_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = self.valid_frozen_manifest(root)
            first = run_dry_run(root, Path(tmp) / "one", manifest)
            manifest["applicability"] = [key("beta", "security", "A-0001")]
            manifest["weights"] = {manifest["applicability"][0]: 1}
            second = run_dry_run(root, Path(tmp) / "two", manifest)
            self.assertNotEqual(first["output_dir"].name, second["output_dir"].name)

    def test_resolved_path_alias_cannot_duplicate_an_explicit_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = fixture(root)
            manifest["inputs"].append({"path": "./audit.json", "kind": "audit"})
            with self.assertRaises(ContractError):
                run_dry_run(root, Path(tmp) / "out", manifest)

    def test_missing_baseline_and_invalid_frozen_lineage_fail_closed(self):
        for mutate in ("baseline", "path", "hash"):
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "input"
                root.mkdir()
                manifest = self.valid_frozen_manifest(root)
                if mutate == "baseline":
                    manifest.pop("expected_baseline")
                elif mutate == "path":
                    manifest["lineage"]["source_path"] = "missing.json"
                else:
                    manifest["lineage"]["scorer_hash"] = "not-a-hash"
                result = run_dry_run(root, Path(tmp) / "out", manifest)
                self.assertFalse(result["validation.json"]["publication_allowed"])
                expected = {"baseline": "missing_expected_baseline", "path": "lineage_source_path",
                            "hash": "lineage_scorer_hash"}[mutate]
                self.assertIn(expected, result["validation.json"]["blockers"])

    def test_reviewed_unstructured_metadata_must_match_lineage(self):
        for field, value, blocker in (("scorer_version", "v999", "lineage_scorer_version"),
                                      ("capture_timestamp", "1999-01-01T00:00:00Z", "lineage_capture_timestamp")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "input"
                root.mkdir()
                manifest = self.valid_frozen_manifest(root)
                manifest["lineage"][field] = value
                result = run_dry_run(root, Path(tmp) / "out", manifest)
                self.assertIn(blocker, result["validation.json"]["blockers"])

    def test_ancillary_raw_input_and_actual_fingerprints_change_candidate_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = self.valid_frozen_manifest(root)
            (root / "schema.json").write_bytes(b"not parsed as rows\x00")
            manifest["inputs"].append({"path": "schema.json", "kind": "schema"})
            first = run_dry_run(root, Path(tmp) / "one", manifest)
            (root / "audit.json").write_bytes(b"[]")
            second = run_dry_run(root, Path(tmp) / "two", manifest)
            self.assertNotEqual(first["output_dir"].name, second["output_dir"].name)
            self.assertIn("schema.json", {x["path"] for x in first["inputs.json"]["inputs"]})

    def test_duplicate_input_locator_and_ambiguous_rubric_propagate_to_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = fixture(root, rubric=[
                {"source": "alpha", "domain": "architecture", "legacy_id": "A-0001"},
                {"source": "alpha", "domain": "architecture", "legacy_id": "A-0001"},
            ])
            manifest["inputs"].append({"path": "audit.json", "kind": "audit"})
            with self.assertRaises(ContractError):
                run_dry_run(root, Path(tmp) / "out", manifest)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = fixture(root, rubric=[
                {"source": "alpha", "domain": "architecture", "legacy_id": "A-0001"},
                {"source": "alpha", "domain": "architecture", "legacy_id": "A-0001"},
            ])
            result = run_dry_run(root, Path(tmp) / "out", manifest)
            self.assertEqual("quarantined", result["identity-crosswalk.json"]["rows"][2]["disposition"])

    def test_unknown_applicability_preserves_denominator_and_invalid_target_blocks(self):
        for mutation in ("unknown_applicable", "invalid_target"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "input"
                root.mkdir()
                manifest = fixture(root)
                if mutation == "unknown_applicable":
                    manifest["applicability"].append(key("missing", "x", "X-1"))
                else:
                    manifest["applicability"] = [key("alpha", "architecture", "A-0001")]
                    manifest["weights"] = {manifest["applicability"][0]: 1}
                    manifest["inputs"] = fixture(root, audit=[{"source": "alpha", "domain": "architecture",
                        "legacy_id": "A-0001", "status": "satisfied", "subject": "service-a",
                        "target_keys": ["garbage"]}])["inputs"]
                result = run_dry_run(root, Path(tmp) / "out", manifest)
                counts = result["applicability.json"]["counts"]
                self.assertEqual(counts["applicable"], counts["assessed"] + counts["unassessed"])
                self.assertFalse(result["validation.json"]["publication_allowed"])
                if mutation == "invalid_target":
                    self.assertIn("invalid_reviewed_mapping", result["validation.json"]["blockers"])

    def test_preserves_source_bytes_and_accounts_for_every_row(self):
        root, _, result = self.run_fixture()
        before = {p.name: (len(p.read_bytes()), hashlib.sha256(p.read_bytes()).hexdigest())
                  for p in root.iterdir()}
        crosswalk = result["identity-crosswalk.json"]["rows"]
        self.assertEqual(3, len(crosswalk))
        self.assertEqual({("rubric.json", 0), ("rubric.json", 1), ("audit.json", 0)},
                         {(x["locator"]["path"], x["locator"]["row_index"]) for x in crosswalk})
        self.assertEqual(before, {p.name: (len(p.read_bytes()), hashlib.sha256(p.read_bytes()).hexdigest())
                                  for p in root.iterdir()})
        self.assertEqual({"source": "alpha", "domain": "architecture", "legacy_id": "A-0001"},
                         crosswalk[0]["row"])

    def test_same_bare_id_in_distinct_qualified_keys_stays_distinct(self):
        _, _, result = self.run_fixture()
        keys = [x["qualified_key"] for x in result["identity-crosswalk.json"]["rows"][:2]]
        self.assertEqual(2, len(set(keys)))
        self.assertEqual([], result["quarantine.json"]["groups"])

    def test_repeated_full_tuple_quarantines_all_members(self):
        duplicate = [{"source": "alpha", "domain": "architecture", "legacy_id": "A-0001"}] * 2
        _, _, result = self.run_fixture(rubric=duplicate, audit=[])
        rows = result["identity-crosswalk.json"]["rows"]
        self.assertTrue(all(r["disposition"] == "quarantined" for r in rows))
        self.assertEqual("repeated_qualified_tuple", result["quarantine.json"]["groups"][0]["reasons"][0])

    def test_one_to_many_reviewed_mapping_quarantines_the_affected_group(self):
        audit = [{"source": "alpha", "domain": "architecture", "legacy_id": "A-0001",
                  "status": "satisfied", "subject": "service-a",
                  "target_keys": [key("alpha", "architecture", "A-0001"),
                                  key("beta", "security", "A-0001")]}]
        _, _, result = self.run_fixture(audit=audit)
        self.assertEqual("quarantined", result["identity-crosswalk.json"]["rows"][-1]["disposition"])
        self.assertIn("one_to_many_mapping", result["validation.json"]["blockers"])

    def test_opposing_statuses_quarantine_both_independent_of_order(self):
        audit = [
            {"source": "alpha", "domain": "architecture", "legacy_id": "A-0001", "status": "satisfied", "subject": "service-a"},
            {"source": "alpha", "domain": "architecture", "legacy_id": "A-0001", "status": "unsatisfied", "subject": "service-a"},
        ]
        root, out, first = self.run_fixture(audit=audit)
        second = run_dry_run(root, out / "next", fixture(root, audit=list(reversed(audit))))
        self.assertEqual(first["quarantine.json"]["groups"][0]["reasons"],
                         second["quarantine.json"]["groups"][0]["reasons"])
        self.assertFalse(first["validation.json"]["publication_allowed"])
        self.assertIsNone(first["validation.json"]["readiness_grade"])

    def test_lineage_subject_path_and_source_fail_independently(self):
        for field, value in (("assessed_subject", "other"), ("source_path", ""), ("source_hash", "")):
            with self.subTest(field=field):
                lineage = fixture(Path(tempfile.mkdtemp()))["lineage"]
                lineage[field] = value
                _, _, result = self.run_fixture(lineage=lineage)
                self.assertFalse(result["validation.json"]["publication_allowed"])
                self.assertIn("lineage_" + field, result["validation.json"]["blockers"])

    def test_applicability_reports_two_one_one_and_withholds_grade(self):
        _, _, result = self.run_fixture()
        app = result["applicability.json"]
        self.assertEqual({"applicable": 2, "assessed": 1, "unassessed": 1}, app["counts"])
        self.assertIsNone(result["validation.json"]["readiness_grade"])

    def test_reproducible_bytes_in_fresh_roots_and_nonoverwrite_safe_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roots = [base / "one", base / "two"]
            outputs = []
            for root in roots:
                root.mkdir()
                result = run_dry_run(root, base / (root.name + "-out"), fixture(root))
                outputs.append({n: (result["output_dir"] / n).read_bytes() for n in result if n.endswith(".json")})
            self.assertEqual(outputs[0], outputs[1])
            with self.assertRaises(ContractError):
                run_dry_run(roots[0], base / "one-out", fixture(roots[0]))
            with self.assertRaises(ContractError):
                run_dry_run(roots[0], roots[0] / "output", fixture(roots[0]))

    def test_invalid_status_weights_and_unresolved_applicable_fail_closed(self):
        for changes in (
            {"audit": [{"source": "alpha", "domain": "architecture", "legacy_id": "A-0001", "status": "maybe", "subject": "service-a"}]},
            {"weights": {key("alpha", "architecture", "A-0001"): float("nan")}},
            {"applicability": [key("alpha", "architecture", "A-0001"), key("missing", "x", "X-1")]},
        ):
            with self.subTest(changes=changes):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp) / "input"
                    root.mkdir()
                    manifest = fixture(root, **{k: v for k, v in changes.items() if k != "audit"})
                    if "audit" in changes:
                        manifest = fixture(root, audit=changes["audit"])
                    result = run_dry_run(root, Path(tmp) / "out", manifest)
                    self.assertFalse(result["validation.json"]["publication_allowed"])
                    self.assertEqual(0, result["applicability.json"]["counts"]["assessed"])

    def test_rejects_duplicate_json_keys_and_nonfinite_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = fixture(root, rubric=[], audit=[])
            (root / "rubric.json").write_text('[{"source":"a","source":"b","domain":"d","legacy_id":"x"}]')
            with self.assertRaises(ContractError):
                run_dry_run(root, Path(tmp) / "out", manifest)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            manifest = fixture(root)
            (root / "rubric.json").write_text("[NaN]")
            with self.assertRaises(ContractError):
                run_dry_run(root, Path(tmp) / "out", manifest)


if __name__ == "__main__":
    unittest.main()
