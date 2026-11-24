"""EvaluationReport canonicalization (v0.5).

Production implementation of the algorithm specified in
``EVAL_RESULT_CANONICALIZATION.md``.  Producer and consumer MUST agree on
this byte-for-byte so ``schema_hash`` and ``top_level_sha256`` match.

Three public surfaces:

* :func:`canonicalize`  — dict/list/scalar -> canonical UTF-8 bytes
* :func:`sha256_hex`     — convenience: sha256 over canonical bytes
* :func:`prepare_artifact` — apply the producer-side acceptance cases
  P5 (sort task_results by task_id) and P7 (round pass_at_1 to 4 dp)
  before canonicalizing.

Acceptance rules (per EVAL_RESULT_CANONICALIZATION.md):
  * dict keys are sorted lex (UTF-8 codepoint order); lists preserve order
  * ``task_results`` MUST be sorted by ``task_id`` lex (P5) — this module
    sorts in :func:`prepare_artifact`.
  * ``pass_at_1`` and other floats MUST already be rounded to 4 dp (P7).
    :func:`prepare_artifact` rounds known float fields defensively.
  * separators=(",", ":"); ensure_ascii=False; no BOM.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

# Top-level fields whose direct numeric values must be rounded to 4 dp
# (acceptance case P7).  Per-suite ``pass_at_1`` and per-task
# ``raw_score`` are handled separately because they live inside the
# ``suites`` list.
_FLOAT_4DP_TOP_LEVEL = (("totals", "pass_at_1"),)

# Canonical evidence_label enum (mirrors bench/contracts/EVAL_RESULT_CONTRACT.md
# and tests/test_evidence_label.py:CANONICAL_LABELS). Producer-side labels
# are kept distinct from consumer-side ones so the hash_chain can prove
# which side created the artifact.
CANONICAL_EVIDENCE_LABELS: frozenset[str] = frozenset(
    {
        "live verified",  # consumer-side promotion gate
        "historical",     # consumer-side promotion gate
        "reported",       # consumer-side promotion gate
        "inferred",       # producer-side only, never advanced
        "unknown",        # placeholder; explicit non-claim
        "backfilled",     # producer-side only (snapshot_sota.py --date path)
    }
)


def _sort(obj: Any) -> Any:
    """Recursively sort dict keys lex; lists preserve order."""
    if isinstance(obj, dict):
        return {k: _sort(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_sort(x) for x in obj]
    return obj


def canonicalize(obj: Any) -> bytes:
    """Return canonical UTF-8 bytes for ``obj``.

    The bytes are deterministic for equal-shape inputs across producers
    and consumers (Python dict ordering, JSON whitespace, etc. all
    normalized).
    """
    return json.dumps(
        _sort(obj),
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_hex(obj: Any) -> str:
    """Lowercase hex SHA-256 over :func:`canonicalize`."""
    return hashlib.sha256(canonicalize(obj)).hexdigest()


def validate_evidence_label(label: str) -> None:
    """Reject ``label`` if it is not in :data:`CANONICAL_EVIDENCE_LABELS`.

    This is the consumer-side gate called by every downstream reader of an
    EvaluationReport envelope. It enforces DAG-24 / contract rule C6:

    * unknown / undeclared labels are rejected with ``ValueError`` so the
      promotion-gate code path fails loud (rather than silently treating
      an "anything goes" string as a valid evidence tier).
    * the canonical labels are case-sensitive and whitespace-sensitive
      (the contract spells them out exactly).
    * the empty string is rejected (use ``"unknown"`` to signal
      intentional non-claim).

    >>> validate_evidence_label("live verified")  # no-op
    >>> validate_evidence_label("not-a-real-label")
    Traceback (most recent call last):
        ...
    ValueError: unknown evidence_label: 'not-a-real-label'; ...
    """
    if not isinstance(label, str):
        raise ValueError(
            f"evidence_label must be str, got {type(label).__name__}"
        )
    if label not in CANONICAL_EVIDENCE_LABELS:
        raise ValueError(
            f"unknown evidence_label: {label!r}; "
            f"must be one of {sorted(CANONICAL_EVIDENCE_LABELS)}"
        )


def _round4(value: Any) -> Any:
    """Round a scalar to 4 decimal places; pass through non-numerics."""
    if isinstance(value, bool):
        # bool is a subclass of int; don't treat it as a float.
        return value
    if isinstance(value, float):
        return round(float(value), 4)
    return value


def prepare_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    """Apply producer-side acceptance cases P5 + P7 to a v0.5 envelope.

    P5: sort ``task_results`` by ``task_id`` (lexicographic) inside every
        suite, and sort ``suites`` by ``suite`` at the top level if it
        exists as a list.
    P7: round known float fields to 4 decimal places (totals.pass_at_1,
        each suite's pass_at_1, and each task_results[*].raw_score).

    The input dict is not mutated; a deep-enough copy is returned so
    callers can safely use it without leaking sort/round side effects
    back to the producer.
    """
    artifact = copy.deepcopy(artifact)

    # P5: suites list (top-level) sorted by .suite
    if "suites" in artifact and isinstance(artifact["suites"], list):
        artifact["suites"] = sorted(
            artifact["suites"], key=lambda s: s.get("suite", "")
        )
        # P5: each suite's task_results sorted by task_id
        for suite in artifact["suites"]:
            tr = suite.get("task_results")
            if isinstance(tr, list):
                suite["task_results"] = sorted(tr, key=lambda t: t.get("task_id", ""))
                # P7: round per-cell raw_score
                for t in suite["task_results"]:
                    if "raw_score" in t:
                        t["raw_score"] = _round4(t["raw_score"])
            # P7: round suite.pass_at_1 (lives inside the suites list,
            # not at the top level).
            if "pass_at_1" in suite:
                suite["pass_at_1"] = _round4(suite["pass_at_1"])

    # P7: top-level float fields
    for top, sub in _FLOAT_4DP_TOP_LEVEL:
        if top in artifact and isinstance(artifact[top], dict) and sub in artifact[top]:
            artifact[top][sub] = _round4(artifact[top][sub])

    return artifact


def top_level_sha256(artifact: dict[str, Any]) -> str:
    """SHA-256 of canonical bytes of ``artifact`` with hash_chain stripped.

    Per the contract, ``top_level_sha256`` is computed over the artifact
    body minus the ``hash_chain`` field.  :func:`prepare_artifact` is
    applied first so the producer-side acceptance rules hold.
    """
    prepared = prepare_artifact(artifact)
    if "hash_chain" in prepared:
        prepared = {k: v for k, v in prepared.items() if k != "hash_chain"}
    return sha256_hex(prepared)


def task_ids_sorted_sha256(artifact: dict[str, Any]) -> str:
    """SHA-256 of '\\n'.join(sorted(task_ids)) across all suites."""
    ids: list[str] = []
    suites = artifact.get("suites", [])
    if isinstance(suites, list):
        for suite in suites:
            tr = suite.get("task_results", []) if isinstance(suite, dict) else []
            if isinstance(tr, list):
                for t in tr:
                    if isinstance(t, dict) and "task_id" in t:
                        ids.append(t["task_id"])
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()
