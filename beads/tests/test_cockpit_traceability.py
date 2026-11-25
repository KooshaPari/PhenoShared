"""Regression contract for the generated cockpit traceability view."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "bead-cockpit.py"


def load_cockpit_module():
    spec = importlib.util.spec_from_file_location("bead_cockpit", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rendered_cockpit_exposes_traceability_matrix_contract() -> None:
    cockpit = load_cockpit_module()
    html = cockpit.render_html([], "2026-08-11T09:00:00Z", "trace-test")

    assert 'id="traceability"' in html
    assert "Traceability matrix" in html
    assert "window.TRACEABILITY_SCHEMA_V1=true" in html
    for state in (
        "intake",
        "triage",
        "discovery",
        "planned",
        "ready",
        "active",
        "blocked",
        "review",
        "verification",
        "evidence",
        "accepted",
        "released",
        "closed",
        "unknown",
    ):
        assert f"'{state}'" in html


def test_kanban_keeps_missing_lifecycle_state_unknown() -> None:
    """Kind labels must not fabricate a lifecycle placement."""
    cockpit = load_cockpit_module()

    html = cockpit.render_kanban(
        [
            {"id": "claim-without-state", "kind": "claim", "text": "work started"},
        ]
    )

    assert 'data-col="active"><div class="kanban-col-head">🔥 Active (0)' in html
    assert 'data-col="unknown"><div class="kanban-col-head">❔ Unknown (1)' in html


def test_full_lifecycle_vocabulary_has_structural_empty_lanes() -> None:
    """Lifecycle vocabulary is visible without assigning states from kind."""
    cockpit = load_cockpit_module()

    html = cockpit.render_html([], "2026-08-11T09:00:00Z", "trace-test")

    for state in ("preserved", "promoted", "verified", "parked"):
        assert state in cockpit.LIFECYCLE_STATES
        assert f'data-col="{state}"' in html
        assert f"'{state}'" in html
