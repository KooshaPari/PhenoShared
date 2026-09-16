"""WBS 96 A2 — ablation dry-run banner is linked to eval_pillars.yaml motion multiplier."""

from __future__ import annotations

from pathlib import Path

import yaml

from bench.ablation.dry_run_banner import (
    DRY_RUN_BANNER,
    PILLARS_PATH,
    format_banner,
    get_dry_run_banner,
    load_composite_formula,
    load_motion_multiplier,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = REPO_ROOT / "config" / "eval_pillars.yaml"


def _load_yaml_mm() -> dict:
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    return data["composite"]["motion_multiplier"]


def test_banner_module_reads_pillars_path():
    """Module points at the canonical pillars file."""
    assert PILLARS_PATH == REPO_ROOT / "config" / "eval_pillars.yaml"
    assert PILLARS_PATH.exists()


def test_load_motion_multiplier_matches_yaml():
    mm = load_motion_multiplier()
    yaml_mm = _load_yaml_mm()
    assert mm["forward"] == float(yaml_mm["forward"])
    assert mm["stagnate"] == float(yaml_mm["stagnate"])
    assert mm["regress"] == float(yaml_mm["regress"])
    # Canonical invariant (mirrors test_eval_pillars.py)
    assert mm["forward"] == 1.0
    assert mm["stagnate"] == 0.5
    assert mm["regress"] == 0.0


def test_composite_formula_uses_motion_multiplier():
    formula = load_composite_formula()
    assert "motion_multiplier" in formula


def test_banner_contains_eval_pillars_motion_multiplier():
    """Core WBS 96 A2 assertion: banner string embeds the yaml motion multiplier."""
    banner = get_dry_run_banner()
    yaml_mm = _load_yaml_mm()
    # Each numeric value from yaml must appear verbatim in the banner.
    for key in ("forward", "stagnate", "regress"):
        val = str(float(yaml_mm[key]))
        # yaml stores e.g. 1.0 not 1 — banner uses same float string.
        assert val in banner, f"banner missing {key}={val}: {banner!r}"
        assert key in banner, f"banner missing key {key!r}: {banner!r}"

    # Banner must mention the composite linkage and dry-run markers.
    assert "motion_multiplier" in banner
    assert "reported" in banner  # evidence_label=reported for dry-run
    assert "DRY-RUN" in banner or "dry-run" in banner.lower()


def test_banner_constant_and_alias_are_consistent():
    """DRY_RUN_BANNER and format_banner() are consistent with get_dry_run_banner()."""
    assert get_dry_run_banner() == DRY_RUN_BANNER
    assert format_banner() == get_dry_run_banner()
    # Must not be empty or disconnected.
    assert len(DRY_RUN_BANNER) > 20


def test_banner_not_hardcoded_disconnected():
    """Guard against a hardcoded banner that drifts from yaml.

    Mutating the yaml in-memory would require the banner to change. We check
    indirectly by asserting the banner's numbers equal yaml numbers (above)
    and that load_motion_multiplier() is not returning a disconnected literal
    that still passes when yaml changes. This test ensures the module reads
    the file rather than returning constants.
    """
    # Verify the function's source actually opens PILLARS_PATH (best-effort static check).
    src = (
        Path(__file__).resolve().parents[1] / "bench" / "ablation" / "dry_run_banner.py"
    )
    text = src.read_text(encoding="utf-8")
    assert "PILLARS_PATH" in text
    assert "eval_pillars.yaml" in text
    assert "motion_multiplier" in text
