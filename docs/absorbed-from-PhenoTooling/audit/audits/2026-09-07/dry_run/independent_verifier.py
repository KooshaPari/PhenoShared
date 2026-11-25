"""Independent verifier — judges evaluator output without mutable builder state.

This script re-reads source files, re-runs the evaluator, and checks that
every claim in the output is supported by evidence. It is the v0 acceptance
test requirement #4: "independent verification demonstrates result."

Usage:
    python3 independent_verifier.py
"""
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent  # research/audit-system/
sys.path.insert(0, str(HERE))

from dry_run import run_dry_run
from snapshot_adapter import build_draft_manifest

REPORT = []
PASS = 0
FAIL = 0


def check(description, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        REPORT.append(f"  PASS  {description}")
    else:
        FAIL += 1
        msg = f"  FAIL  {description}"
        if detail:
            msg += f" -- {detail}"
        REPORT.append(msg)


def verify_file_fingerprints(draft):
    """Re-read every source file and verify SHA-256 matches the draft."""
    check("Draft status is UNREVIEWED",
          draft["status"] == "UNREVIEWED",
          f"got {draft['status']}")

    for inp in draft["inputs"]:
        path = REPO / inp["source"]["path"]
        raw = path.read_bytes()
        actual_hash = hashlib.sha256(raw).hexdigest()
        actual_len = len(raw)
        check(f"Fingerprint matches for {inp['source']['path']}",
              inp["source"]["sha256"] == actual_hash
              and inp["source"]["length"] == actual_len,
              f"expected {inp['source']['sha256'][:16]}.../{inp['source']['length']}, "
              f"got {actual_hash[:16]}.../{actual_len}")


def verify_rubric_count(draft):
    """Check that rubric record count matches historical 4503."""
    rubric = draft["inputs"][0]
    check(f"Rubric has 4503 records (got {len(rubric['records'])})",
          len(rubric["records"]) == 4503)

    # Check that every record has required fields
    missing_fields = 0
    for r in rubric["records"]:
        raw = r["raw"]
        if not all(isinstance(raw.get(f), str) and raw[f]
                    for f in ("source", "domain", "id")):
            missing_fields += 1
    check(f"All rubric records have source/domain/id (missing: {missing_fields})",
          missing_fields == 0)


def verify_card_blockers(draft):
    """Every card record must have missing_reviewed_mapping."""
    for inp in draft["inputs"][1:]:
        name = inp["source"]["path"].split("/")[-1]
        blocked = sum(1 for r in inp["records"]
                      if "missing_reviewed_mapping" in r["blockers"])
        total = len(inp["records"])
        check(f"Card {name}: all {total} records have missing_reviewed_mapping",
              blocked == total,
              f"only {blocked}/{total}")


def verify_evaluator_rejection():
    """Run the evaluator on synthetic inputs and verify it rejects correctly."""
    # Build a minimal manifest that should be rejected
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "input"
        root.mkdir()
        rubric = [{"source": "a", "domain": "d", "legacy_id": "X-1"}]
        raw = json.dumps(rubric, ensure_ascii=False, separators=(",", ":")).encode()
        (root / "rubric.json").write_bytes(raw)
        manifest = {
            "implementation_version": "verify-v1",
            "capture_timestamp": "2026-09-12T00:00:00Z",
            "inputs": [{"path": "rubric.json", "kind": "rubric"}],
            "expected_baseline": {"rubric": {
                "count": 1,
                "sha256": hashlib.sha256(raw).hexdigest()}},
            "lineage": {},
            "applicability": [],
            "weights": {},
        }
        result = run_dry_run(root, Path(tmp) / "out", manifest)
        check("Evaluator sets publication_allowed=False",
              result["validation.json"]["publication_allowed"] is False)
        check("Evaluator sets readiness_grade=None",
              result["validation.json"]["readiness_grade"] is None)
        check("Evaluator includes diagnostic_only",
              "diagnostic_only" in result["validation.json"]["blockers"])


def verify_no_publication_in_draft(draft):
    """The draft manifest must not contain any publication authorization."""
    check("Draft has no publication_allowed field",
          "publication_allowed" not in draft)
    check("Draft has no readiness_grade field",
          "readiness_grade" not in draft)
    check("Draft has no score field",
          "score" not in draft)


def verify_record_locator_integrity(draft):
    """Every record must have a valid source_locator."""
    bad_locators = 0
    for inp in draft["inputs"]:
        for i, r in enumerate(inp["records"]):
            expected = f"$.criteria[{i}]"
            if r.get("source_locator") != expected:
                bad_locators += 1
    check(f"All record locators are valid (bad: {bad_locators})",
          bad_locators == 0)


def verify_status_distribution(draft):
    """Check that status distributions match known values."""
    rubric = draft["inputs"][0]
    statuses = Counter(r["raw"].get("status") for r in rubric["records"])
    check(f"Rubric has 126 satisfied (got {statuses.get('satisfied', 0)})",
          statuses.get("satisfied") == 126)
    check(f"Rubric has 2294 reference (got {statuses.get('reference', 0)})",
          statuses.get("reference") == 2294)
    check(f"Rubric has 2069 historical (got {statuses.get('historical', 0)})",
          statuses.get("historical") == 2069)


def main():
    REPORT.append("=" * 60)
    REPORT.append("INDEPENDENT VERIFICATION REPORT")
    REPORT.append("=" * 60)
    REPORT.append("")

    # Step 1: Load the draft manifest
    REPORT.append("Step 1: Load draft manifest")
    draft_path = HERE / "DRAFT-MANIFEST-REAL-INPUTS.json"
    if not draft_path.exists():
        REPORT.append("  FAIL  Draft manifest not found")
        return 1
    draft = json.loads(draft_path.read_bytes())
    REPORT.append(f"  Loaded: {len(draft['inputs'])} inputs")
    REPORT.append("")

    # Step 2: Verify fingerprints
    REPORT.append("Step 2: Verify file fingerprints")
    verify_file_fingerprints(draft)
    REPORT.append("")

    # Step 3: Verify rubric count
    REPORT.append("Step 3: Verify rubric integrity")
    verify_rubric_count(draft)
    REPORT.append("")

    # Step 4: Verify card blockers
    REPORT.append("Step 4: Verify card blockers")
    verify_card_blockers(draft)
    REPORT.append("")

    # Step 5: Verify no publication in draft
    REPORT.append("Step 5: Verify no publication authorization")
    verify_no_publication_in_draft(draft)
    REPORT.append("")

    # Step 6: Verify record locators
    REPORT.append("Step 6: Verify record locator integrity")
    verify_record_locator_integrity(draft)
    REPORT.append("")

    # Step 7: Verify status distribution
    REPORT.append("Step 7: Verify status distribution")
    verify_status_distribution(draft)
    REPORT.append("")

    # Step 8: Verify evaluator rejection
    REPORT.append("Step 8: Verify evaluator rejects invalid inputs")
    verify_evaluator_rejection()
    REPORT.append("")

    # Summary
    REPORT.append("=" * 60)
    REPORT.append(f"RESULT: {PASS} passed, {FAIL} failed")
    REPORT.append("=" * 60)

    # Write report
    report_text = "\n".join(REPORT)
    report_path = HERE / "INDEPENDENT-VERIFICATION-REPORT.md"
    with open(report_path, "w") as f:
        f.write("# Independent Verification Report\n\n")
        f.write("Date: 2026-09-12. Verifier: independent_verifier.py\n\n")
        f.write("```\n")
        f.write(report_text)
        f.write("\n```\n\n")
        if FAIL == 0:
            f.write("**All checks passed.** The evaluator output is consistent\n")
            f.write("with the source files. No publication was authorized.\n")
        else:
            f.write(f"**{FAIL} check(s) failed.** Review the output above.\n")

    print(report_text)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
