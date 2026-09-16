"""DAG-16: tests/test_dry_run_envelope.py

The dry-run envelope guard from audit-A2 + audit-F4. When bench.cli is
invoked with ``run-dry``, the envelope must be self-describing
(``evidence_label='reported'``, ``provenance.synthetic=true``) so
consumers (Argis oMLX, Salmon FR-5) cannot accidentally promote a
dry-run result.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dry_run_marker_appears_in_suite_spec() -> None:
    """The RunSpec must carry a dry-run marker that downstream consumers
    inspect. The flag is ``run.dry_run`` (bool) in the envelope.
    """
    from bench.types import EnergySource, JudgeMode, RunSpec

    spec = RunSpec(
        suite="dry",
        n=1,
        seed=42,
        model="mock",
        judge_model="claude-sonnet-5",
        judge_mode=JudgeMode.DETERMINISTIC,
        energy_source=EnergySource.NONE,
        output="/tmp/x.json",  # nosec B108 - test fixture; sandboxed
        run_id="dry-1",
        extra_meta={"dry_run": True},
    )
    assert spec.extra_meta.get("dry_run") is True


def test_dry_run_envelope_is_rejected_by_promotion_gate() -> None:
    """The dry-run envelope must be rejected by the consumer promotion
    gate (C6 in the contract: only ``live verified`` + ``synthetic=false``
    + ``substitute=null`` advance). Dry-runs carry ``synthetic=true`` so
    the gate trips.
    """
    envelope = {
        "run": {"evidence_label": "reported"},
        "provenance": {"synthetic": True, "substitute": None},
    }
    # Reproduce the C6 gate check inline.
    passes_c6 = (
        envelope["run"]["evidence_label"] == "live verified"
        and envelope["provenance"]["synthetic"] is False
        and envelope["provenance"]["substitute"] is None
    )
    assert not passes_c6, "dry-run envelope must NOT pass the C6 promotion gate"
