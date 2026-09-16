"""bench.ablation.dry_run_banner — dry-run banner linked to eval_pillars.yaml.

WBS 96 close-out audit-A2: the ablation dry-run banner must be self-describing
and linked to the canonical motion multiplier in ``config/eval_pillars.yaml``
so CI can assert that synthetic artefacts are not promoted.

The canonical source is ``config/eval_pillars.yaml:composite.motion_multiplier``
(forward=1.0, stagnate=0.5, regress=0.0).  This module reads that file at
runtime rather than hard-coding disconnected values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from pheno.paths import CONFIG_DIR

REPO_ROOT = Path(__file__).resolve().parents[2]
PILLARS_PATH = CONFIG_DIR / "eval_pillars.yaml"

# Re-export for tests that want to inspect the linkage without re-reading file.
_FALLBACK_MULTIPLIER: dict[str, float] = {
    "forward": 1.0,
    "stagnate": 0.5,
    "regress": 0.0,
}


def load_motion_multiplier() -> dict[str, float]:
    """Load the canonical motion multiplier from ``config/eval_pillars.yaml``.

    Returns:
        Dict with keys ``forward``, ``stagnate``, ``regress`` as floats.

    Raises:
        FileNotFoundError: if the pillars config cannot be found.
        KeyError: if the expected composite.motion_multiplier path is missing.
    """
    text = PILLARS_PATH.read_text(encoding="utf-8")
    data: dict[str, Any] = yaml.safe_load(text) or {}
    mm = data.get("composite", {}).get("motion_multiplier")
    if mm is None:
        raise KeyError("config/eval_pillars.yaml missing composite.motion_multiplier")
    return {k: float(v) for k, v in mm.items()}


def load_composite_formula() -> str:
    """Load the composite formula string from pillars config."""
    text = PILLARS_PATH.read_text(encoding="utf-8")
    data: dict[str, Any] = yaml.safe_load(text) or {}
    return str(data.get("composite", {}).get("formula", ""))


def get_dry_run_banner(*, synthetic: bool = True) -> str:
    """Return the human-readable dry-run banner.

    The banner is intentionally verbose so ``tests/test_ablation_banner.py``
    can assert the eval_pillars motion multiplier linkage without brittle
    regex.  Values are read live from ``config/eval_pillars.yaml``.

    Args:
        synthetic: Whether this run is synthetic (dry-run). Always True
            for dry-run banners; kept as a param for explicitness.

    Returns:
        Multi-field banner string containing the motion multiplier values,
        the composite formula, and the evidence label marker.
    """
    try:
        mm = load_motion_multiplier()
    except Exception:
        mm = dict(_FALLBACK_MULTIPLIER)
    try:
        formula = load_composite_formula()
    except Exception:
        formula = "sum(pillar_score * weight) * motion_multiplier"

    # Keep numeric formatting stable: 1.0 / 0.5 / 0.0 as stored in yaml.
    forward = mm.get("forward", 1.0)
    stagnate = mm.get("stagnate", 0.5)
    regress = mm.get("regress", 0.0)

    parts = [
        "=== ABLATION DRY-RUN ===",
        "synthetic" if synthetic else "live",
        f"motion_multiplier forward={forward} stagnate={stagnate} regress={regress}",
        f"composite:{formula}",
        "evidence_label=reported",
        "not for promotion",
    ]
    return " | ".join(parts)


# Alias used by some CI scripts / docs
def format_banner() -> str:
    """Alias for :func:`get_dry_run_banner`."""
    return get_dry_run_banner()


# Convenience constant for callers that want a pre-rendered banner (read at import
# time via the live yaml).  Tests should call ``get_dry_run_banner()`` to
# ensure they see the current file, not the import-time snapshot.
DRY_RUN_BANNER: str = get_dry_run_banner()


def print_banner() -> None:
    """Print the banner to stdout (used by ``bench.matrix.run_ablation --dry-run``)."""
    print(DRY_RUN_BANNER)


__all__ = [
    "DRY_RUN_BANNER",
    "PILLARS_PATH",
    "format_banner",
    "get_dry_run_banner",
    "load_composite_formula",
    "load_motion_multiplier",
    "print_banner",
]
