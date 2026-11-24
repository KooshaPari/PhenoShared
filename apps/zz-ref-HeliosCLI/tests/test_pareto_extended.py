import sys

import pandas as pd

sys.path.insert(0, "src")
from helios_router_ui.pareto.engine import compute_combos, compute_pareto, pareto_front_mask


def test_compute_pareto_marks_frontier():
    df = pd.DataFrame(
        {
            "offer_id": ["a", "b", "c"],
            "cost_usd": [1.0, 2.0, 1.5],
            "speed_score": [10.0, 8.0, 9.0],
            "quality": [0.9, 0.95, 0.85],
        }
    )
    result = compute_pareto(df)
    assert "on_pareto" in result.columns
    assert result["on_pareto"].any()


def test_compute_combos_builds_pair_rows():
    df = pd.DataFrame(
        {
            "offer_id": ["a", "b", "c"],
            "provider": ["p1", "p1", "p2"],
            "model_id": ["m1", "m2", "m3"],
            "cost_usd": [1.0, 2.0, 3.0],
            "speed_score": [10.0, 9.0, 8.0],
            "quality": [0.8, 0.9, 0.7],
        }
    )
    combos = compute_combos(df, size=2)
    assert len(combos) == 3
    assert set(combos.columns) >= {"combo", "quality", "cost_usd", "speed_score"}


def test_pareto_front_mask_minimize_only():
    df = pd.DataFrame({"cost": [3, 1, 2]})
    mask = pareto_front_mask(df, minimize=["cost"], maximize=[])
    assert mask.tolist() == [False, True, False]
