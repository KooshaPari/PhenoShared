"""DAG-24: tests/test_canonicalization.py (revised 2026-08-07)

The bench.contracts.canonicalize module (DAG-66) is the production
canonicalizer for v0.5 EvalResult envelopes. It exposes:

  * ``canonicalize(obj)`` — dict/list/scalar → canonical UTF-8 bytes
  * ``sha256_hex(obj)`` — SHA-256 over ``canonicalize(obj)``
  * ``prepare_artifact(artifact)`` — apply producer-side acceptance
    cases P5 (sort task_results by task_id) + P7 (round pass_at_1 to
    4 dp) before canonicalizing
  * ``top_level_sha256(artifact)`` — SHA-256 over the artifact body
    minus the ``hash_chain`` field
  * ``task_ids_sorted_sha256(artifact)`` — task-id-list hash for
    cross-artifact identity checks

This test pins the canonicalization contract so consumer rejections
stay deterministic. The original DAG-24 test referenced an aspirational
``canonicalize_suite_result`` / ``validate_evidence_label`` / envelope
wrapper API that never landed; the actual DAG-66 surface above is the
canonical one.
"""

from __future__ import annotations


def _artifact() -> dict:
    """Build a minimal v0.5 envelope for the fixtures."""
    return {
        "contract_version": "v0.5",
        "artifact_kind": "EvaluationReport",
        "run": {"model": "mlx-stub", "engine": "stub", "seed": 0},
        "matrix": {},
        "suites": [
            {
                "suite": "canon-test",
                "pass_at_1": 1.0,
                "task_results": [
                    {
                        "task_id": "t1",
                        "raw_score": 1.0,
                        "gen_ok": 1.0,
                    },
                    {
                        "task_id": "t0",
                        "raw_score": 0.5,
                        "gen_ok": 0.5,
                    },
                ],
            }
        ],
        "totals": {"pass_at_1": 1.0},
    }


def test_canonicalize_module_exposes_dag66_surface() -> None:
    """The canonicalize module must expose the DAG-66 surface."""
    from bench.contracts import canonicalize  # type: ignore

    for name in (
        "canonicalize",
        "sha256_hex",
        "prepare_artifact",
        "top_level_sha256",
        "task_ids_sorted_sha256",
    ):
        assert hasattr(canonicalize, name), (
            f"bench.contracts.canonicalize missing {name!r}"
        )


def test_canonicalize_emits_canonical_bytes() -> None:
    """``canonicalize(obj)`` returns deterministic UTF-8 bytes."""
    from bench.contracts.canonicalize import canonicalize  # type: ignore

    a = canonicalize({"b": 1, "a": 2})
    b = canonicalize({"a": 2, "b": 1})
    assert a == b, "canonical bytes depend on dict key order"
    assert isinstance(a, bytes)
    # No whitespace (separators=(",", ":")).
    assert b" " not in a


def test_prepare_artifact_sorts_task_results_by_task_id_p5() -> None:
    """Acceptance case P5: ``task_results`` sorted by ``task_id`` lex."""
    from bench.contracts.canonicalize import prepare_artifact  # type: ignore

    env = _artifact()
    prepared = prepare_artifact(env)
    suite = prepared["suites"][0]
    ids = [t["task_id"] for t in suite["task_results"]]
    assert ids == sorted(ids), f"task_results not sorted by task_id: {ids}"


def test_prepare_artifact_rounds_pass_at_1_to_4dp_p7() -> None:
    """Acceptance case P7: ``pass_at_1`` rounded to 4 decimal places."""
    from bench.contracts.canonicalize import prepare_artifact  # type: ignore

    env = _artifact()
    env["totals"]["pass_at_1"] = 0.123456789
    env["suites"][0]["pass_at_1"] = 0.987654321
    prepared = prepare_artifact(env)
    assert prepared["totals"]["pass_at_1"] == 0.1235
    assert prepared["suites"][0]["pass_at_1"] == 0.9877


def test_top_level_sha256_is_stable_across_key_order() -> None:
    """Same envelope, different dict-key order → same top_level_sha256."""
    from bench.contracts.canonicalize import top_level_sha256  # type: ignore

    a = _artifact()
    # Shuffle dict keys by rebuilding from a different insertion order.
    b = {
        "totals": a["totals"],
        "suites": a["suites"],
        "matrix": a["matrix"],
        "run": a["run"],
        "artifact_kind": a["artifact_kind"],
        "contract_version": a["contract_version"],
    }
    assert top_level_sha256(a) == top_level_sha256(b)


def test_top_level_sha256_strips_hash_chain_field() -> None:
    """``top_level_sha256`` ignores the ``hash_chain`` field by contract."""
    from bench.contracts.canonicalize import top_level_sha256  # type: ignore

    base = _artifact()
    base_sha = top_level_sha256(base)
    with_chain = dict(base)
    with_chain["hash_chain"] = {
        "top_level_sha256": "0" * 64,
        "task_ids_sorted_sha256": "1" * 64,
    }
    assert top_level_sha256(with_chain) == base_sha


def test_task_ids_sorted_sha256_orders_lex() -> None:
    """``task_ids_sorted_sha256`` sorts task_ids lex before hashing."""
    from bench.contracts.canonicalize import (  # type: ignore
        task_ids_sorted_sha256,
    )

    a = _artifact()
    b = _artifact()
    b["suites"][0]["task_results"] = list(reversed(b["suites"][0]["task_results"]))
    assert task_ids_sorted_sha256(a) == task_ids_sorted_sha256(b)
