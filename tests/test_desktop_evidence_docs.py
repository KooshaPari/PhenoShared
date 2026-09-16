"""Regression checks for truthful desktop-promotion session records."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "docs" / "sessions" / "20260802-desktop-nvidia-mvp"


def test_desktop_session_docs_separate_historical_diagnostics_from_promotion_proof() -> (
    None
):
    """Historical helper runs must not be presented as current promotion evidence."""
    overview = (SESSION / "00_SESSION_OVERVIEW.md").read_text(encoding="utf-8")
    dag = (SESSION / "03_DAG_WBS.md").read_text(encoding="utf-8")
    session_four = (SESSION / "04_dag_wbs.md").read_text(encoding="utf-8")
    phase_two_gate = (SESSION / "05_phase_gate.md").read_text(encoding="utf-8")
    phase_six_gate = (SESSION / "06_phase_gate.md").read_text(encoding="utf-8")
    issues = (SESSION / "05_KNOWN_ISSUES.md").read_text(encoding="utf-8")
    overview_words = " ".join(overview.lower().split())
    dag_words = " ".join(dag.lower().split())
    session_four_words = " ".join(session_four.lower().split())
    phase_two_gate_words = " ".join(phase_two_gate.lower().split())
    phase_six_gate_words = " ".join(phase_six_gate.lower().split())
    issue_words = " ".join(issues.lower().split())

    assert "historical helper diagnostic" in overview_words
    assert "not current repeatability or promotion evidence" in overview_words
    assert "historical helper diagnostics are non-promotable" in dag_words
    assert "owner-issued execution authority" in dag_words
    assert "owner-issued execution authority" in session_four_words
    assert "owner-issued execution authority" in phase_two_gate_words
    assert "owner-issued execution authority" in phase_six_gate_words
    assert "port 19000" not in session_four_words
    assert "port 19000" not in phase_two_gate_words
    assert "historical observations" in issue_words
    assert "planning_only" in issues
    assert "reserved and authority-blocked" in issue_words
    assert "before it can write a sidecar" in issue_words
