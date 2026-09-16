"""DAG-66: drift-guard tests for bench/contracts/canonicalize.py.

The contract is normative (see EVAL_RESULT_CANONICALIZATION.md); these
tests pin:

  * canonical bytes are deterministic across dict insertion order
  * dict keys sort lex; lists preserve order
  * whitespace and key-separator choices match the contract
  * prepare_artifact sorts task_results by task_id (P5)
  * prepare_artifact rounds pass_at_1 / raw_score to 4 dp (P7)
  * top_level_sha256 strips the hash_chain field
  * task_ids_sorted_sha256 is independent of suite/task order
"""

from __future__ import annotations

from typing import Any

from bench.contracts.canonicalize import (
    canonicalize,
    prepare_artifact,
    sha256_hex,
    task_ids_sorted_sha256,
    top_level_sha256,
)

# ---------------------------------------------------------------------------
# canonicalize() — byte-level determinism
# ---------------------------------------------------------------------------


def test_canonical_bytes_are_deterministic_across_dict_order() -> None:
    a = canonicalize({"b": 1, "a": 2})
    b = canonicalize({"a": 2, "b": 1})
    assert a == b
    assert a == b'{"a":2,"b":1}'


def test_canonical_bytes_use_compact_separators() -> None:
    """No spaces, no newlines, only ',' between items and ':' between k:v."""
    out = canonicalize({"a": 1, "b": [1, 2, 3]})
    assert out == b'{"a":1,"b":[1,2,3]}'


def test_lists_preserve_input_order() -> None:
    out = canonicalize([3, 1, 2])
    assert out == b"[3,1,2]"


def test_unicode_passes_through_with_ensure_ascii_false() -> None:
    out = canonicalize({"name": "qwen35"})
    assert out == b'{"name":"qwen35"}'
    # Non-ASCII must survive verbatim:
    out_unicode = canonicalize({"name": "qwen模型"})
    assert out_unicode == '{"name":"qwen模型"}'.encode()


def test_nested_dicts_sort_recursively() -> None:
    out = canonicalize({"outer": {"z": 1, "a": 2}, "first": 0})
    assert out == b'{"first":0,"outer":{"a":2,"z":1}}'


# ---------------------------------------------------------------------------
# sha256_hex() — same input -> same output
# ---------------------------------------------------------------------------


def test_sha256_hex_is_64_lowercase_hex() -> None:
    h = sha256_hex({"a": 1})
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_sha256_hex_stable_under_dict_ordering() -> None:
    assert sha256_hex({"a": 1, "b": 2}) == sha256_hex({"b": 2, "a": 1})


# ---------------------------------------------------------------------------
# prepare_artifact() — producer acceptance cases P5 + P7
# ---------------------------------------------------------------------------


def _suite(
    suite_id: str, task_ids: list[str], pass_at_1: float = 0.0
) -> dict[str, Any]:
    return {
        "suite": suite_id,
        "n": len(task_ids),
        "pass_at_1": pass_at_1,
        "task_results": [
            {"task_id": tid, "raw_score": 0.123456789} for tid in task_ids
        ],
    }


def test_prepare_artifact_sorts_suites_by_suite_name() -> None:
    artifact = {
        "suites": [_suite("zebra", []), _suite("apple", []), _suite("mango", [])]
    }
    prepared = prepare_artifact(artifact)
    names = [s["suite"] for s in prepared["suites"]]
    assert names == ["apple", "mango", "zebra"]


def test_prepare_artifact_sorts_task_results_by_task_id_p5() -> None:
    suite = _suite("ifeval", ["t-3", "t-1", "t-2"])
    artifact = {"suites": [suite]}
    prepared = prepare_artifact(artifact)
    ids = [t["task_id"] for t in prepared["suites"][0]["task_results"]]
    assert ids == ["t-1", "t-2", "t-3"]


def test_prepare_artifact_rounds_pass_at_1_to_4dp_p7() -> None:
    suite = _suite("ifeval", [], pass_at_1=0.123456789)
    artifact = {"suites": [suite]}
    prepared = prepare_artifact(artifact)
    assert prepared["suites"][0]["pass_at_1"] == 0.1235


def test_prepare_artifact_rounds_totals_pass_at_1_to_4dp() -> None:
    artifact = {"totals": {"pass_at_1": 0.987654321}, "suites": []}
    prepared = prepare_artifact(artifact)
    assert prepared["totals"]["pass_at_1"] == 0.9877


def test_prepare_artifact_rounds_raw_score_to_4dp() -> None:
    suite = _suite("ifeval", ["t1"])
    suite["task_results"][0]["raw_score"] = 0.55555555
    prepared = prepare_artifact({"suites": [suite]})
    assert prepared["suites"][0]["task_results"][0]["raw_score"] == 0.5556


def test_prepare_artifact_does_not_mutate_input() -> None:
    suite = _suite("zebra", ["t-2", "t-1"], pass_at_1=0.123456789)
    artifact = {"suites": [suite]}
    snapshot = {
        "suites": [
            {"suite": s["suite"], "task_ids": [t["task_id"] for t in s["task_results"]]}
            for s in artifact["suites"]
        ],
        "pass_at_1": suite["pass_at_1"],
    }
    prepare_artifact(artifact)
    # Original still out of order and unrounded.
    assert artifact["suites"][0]["suite"] == "zebra"
    assert [t["task_id"] for t in artifact["suites"][0]["task_results"]] == [
        "t-2",
        "t-1",
    ]
    assert artifact["suites"][0]["pass_at_1"] == 0.123456789
    # And the snapshot matches the pre-call state:
    assert artifact["suites"][0]["suite"] == snapshot["suites"][0]["suite"]


# ---------------------------------------------------------------------------
# top_level_sha256() — strips hash_chain
# ---------------------------------------------------------------------------


def test_top_level_sha256_strips_hash_chain() -> None:
    artifact_a = {
        "suites": [],
        "totals": {"pass_at_1": 0.5},
        "hash_chain": {
            "top_level_sha256": "0" * 64,
            "task_ids_sorted_sha256": "0" * 64,
        },
    }
    artifact_b = dict(artifact_a)
    artifact_b.pop("hash_chain")
    artifact_b.pop("totals")  # ensure strips only affect hash_chain
    # Same body minus hash_chain + totals mismatch — not what we want. Build two
    # copies that differ ONLY in hash_chain value:
    a1 = {
        "suites": [],
        "totals": {"pass_at_1": 0.5},
        "hash_chain": {"top_level_sha256": "a" * 64},
    }
    a2 = {
        "suites": [],
        "totals": {"pass_at_1": 0.5},
        "hash_chain": {"top_level_sha256": "b" * 64},
    }
    assert top_level_sha256(a1) == top_level_sha256(a2)


def test_top_level_sha256_changes_when_totals_change() -> None:
    a = {"suites": [], "totals": {"pass_at_1": 0.5}, "hash_chain": {}}
    b = {"suites": [], "totals": {"pass_at_1": 0.9}, "hash_chain": {}}
    assert top_level_sha256(a) != top_level_sha256(b)


# ---------------------------------------------------------------------------
# task_ids_sorted_sha256() — order-independent
# ---------------------------------------------------------------------------


def test_task_ids_sorted_sha256_is_order_independent() -> None:
    a = {"suites": [_suite("ifeval", ["t1", "t2", "t3"])]}
    b = {"suites": [_suite("ifeval", ["t3", "t1", "t2"])]}
    c = {"suites": [_suite("ifeval", ["t2", "t3", "t1"])]}
    assert (
        task_ids_sorted_sha256(a)
        == task_ids_sorted_sha256(b)
        == task_ids_sorted_sha256(c)
    )


def test_task_ids_sorted_sha256_is_suite_order_independent() -> None:
    a = {"suites": [_suite("ifeval", ["t1"]), _suite("arc", ["x1"])]}
    b = {"suites": [_suite("arc", ["x1"]), _suite("ifeval", ["t1"])]}
    assert task_ids_sorted_sha256(a) == task_ids_sorted_sha256(b)
