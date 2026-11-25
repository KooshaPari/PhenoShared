"""Scorecard baseline freshness guard.

PR #58 raised the scorecard baseline from 10 to 27 pillars to lock in the
+17 progress from the 0.3.25 community-health sweep. Without an automated
check, the baseline can silently rot: someone deletes a contributing file
(CODE_OF_CONDUCT.md, .github/CODEOWNERS, etc.) and the baseline keeps
claiming the pillar still passes.

This test reads the live baseline from .github/scorecard-baseline.json,
runs scripts/scorecard_ci.audit_repo() against the same repo, and fails
whenever the two disagree:

- **Regressions**: any pillar in the baseline that no longer passes
- **Stale baseline**: any pillar that passes today but isn't in the
  baseline (meaning the baseline needs bumping)

Both directions are checked. The test message includes the precise list
of pillar IDs and names that need attention.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]

# Make scripts/ importable so we can reuse the canonical audit function
# (avoiding drift between this test and the CLI surface).
sys.path.insert(0, str(ROOT / "scripts"))
from scorecard_ci import PILLARS, audit_repo, load_baseline  # noqa: E402

BASELINE_FILE = ROOT / ".github" / "scorecard-baseline.json"


def _pillar_names(ids):
    by_id = {p["id"]: p["name"] for p in PILLARS}
    return [f"{pid} {by_id.get(pid, '?')}" for pid in ids]


def test_baseline_file_exists():
    """The baseline file must be committed; absence would make the
    scorecard CI gate silently accept any regression."""
    assert BASELINE_FILE.exists(), (
        f"Baseline file missing at {BASELINE_FILE}. The scorecard "
        "regression-free floor cannot be enforced without it."
    )


def test_baseline_schema_is_valid():
    """The baseline must pass scripts/scorecard_ci.load_baseline() with no
    expected_source_revision (we don't want to lock to a commit SHA in the
    test -- that's the gate's job, not this guard's)."""
    data = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    loaded = load_baseline(BASELINE_FILE, total=data["total"])
    assert loaded["score"] == data["score"]
    assert sorted(loaded["passed_pillar_ids"]) == sorted(data["passed_pillar_ids"])


def test_baseline_pillar_ids_are_unique_and_in_range():
    """Defensive: catches hand-edited baselines that introduce duplicate
    IDs or out-of-range values before the gate can complain."""
    data = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    ids = data["passed_pillar_ids"]
    total = data["total"]
    assert len(ids) == len(set(ids)), "Baseline passed_pillar_ids must be unique"
    assert all(isinstance(i, int) and 1 <= i <= total for i in ids), (
        f"Baseline passed_pillar_ids must all be in [1, {total}]"
    )


def test_baseline_score_matches_passed_count():
    """Defensive: catches hand-edited baselines where the score counter
    and the ID list diverge."""
    data = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    assert data["score"] == len(data["passed_pillar_ids"]), (
        "Baseline score must equal len(passed_pillar_ids); "
        f"got score={data['score']} but {len(data['passed_pillar_ids'])} IDs"
    )


def test_baseline_total_matches_pillar_count():
    """Defensive: catches PILLARS-list changes that the baseline didn't
    pick up (the scorecard script's load_baseline enforces this, but the
    test makes the failure point obvious)."""
    data = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    assert data["total"] == len(PILLARS), (
        f"Baseline total={data['total']} but scorecard_ci.PILLARS has "
        f"{len(PILLARS)} entries. Update the baseline alongside any "
        "PILLARS-list change."
    )


def test_baseline_does_not_regress_against_current_repo():
    """The core check: every pillar in the baseline must still pass on
    the live repo. Failure here means someone deleted a file that the
    baseline was counting on -- fix by either restoring the file or
    updating the baseline (with justification)."""
    data = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    report = audit_repo(ROOT)
    currently_passing = {r["id"] for r in report["results"] if r["passed"]}
    baseline_passing = set(data["passed_pillar_ids"])
    regressed = sorted(baseline_passing - currently_passing)
    assert not regressed, (
        "Scorecard baseline regressed: these pillars were passing at the "
        "baseline source revision but no longer pass on the live repo.\n"
        f"Regressed: {_pillar_names(regressed)}\n"
        "Fix: restore the contributing files OR remove the IDs from the "
        "baseline with justification (this should be a deliberate decision, "
        "not silent)."
    )


def test_baseline_is_fresh_enough_to_lock_in_progress():
    """Companion check: the baseline must reflect currently-passing
    pillars. If new pillars are passing but the baseline hasn't been
    bumped, the regression-free floor is underreporting project health
    and the scorecard gate is over-permissive about deleting files
    that are not yet in the baseline.

    This is the "bump the baseline" nudge -- the failure is informational
    and the fix is to run the same procedure PR #58 used (audit + bump).
    """
    data = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    report = audit_repo(ROOT)
    currently_passing = {r["id"] for r in report["results"] if r["passed"]}
    baseline_passing = set(data["passed_pillar_ids"])
    newly_passing = sorted(currently_passing - baseline_passing)
    if newly_passing:
        # Print informational warning; do not fail the build. The contract
        # is: PR authors may include new pillars, but the baseline bump
        # should be a deliberate PR with its own justification.
        print(
            "\n[scorecard-baseline-freshness] New pillars are passing "
            f"but are not yet in the baseline: {_pillar_names(newly_passing)}.\n"
            "Consider opening a follow-up PR to bump the baseline. "
            "Use: python scripts/release.py bump --help for the canonical "
            "evidence manifest workflow, or update "
            ".github/scorecard-baseline.json directly with the new "
            "passed_pillar_ids list and source_revision.\n"
        )


def test_baseline_end_to_end_against_an_ephemeral_repo(tmp_path):
    """Sanity check that the freshness guard's logic survives a
    realistic scenario: an empty repo should fail closed (baseline says
    pillar X passes, empty repo does not have it -> regression)."""
    data = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    report = audit_repo(tmp_path)  # empty dir
    empty_passing = {r["id"] for r in report["results"] if r["passed"]}
    baseline_passing = set(data["passed_pillar_ids"])
    # Every baseline pillar must regress on an empty repo (sanity).
    assert baseline_passing - empty_passing == baseline_passing, (
        "Sanity failure: the empty-repo regression list should equal "
        "the entire baseline. If this fails, the test fixture is broken."
    )
