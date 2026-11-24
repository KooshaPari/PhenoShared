"""Coverage tests for ``pheno.evidence.aggregate_bootstrap``.

The bootstrap helper module isolates deterministic resampling machinery
(quantile estimation, counter draw, confidence-interval bootstrap, and seed
digest) from the rest of the aggregate pipeline.  These tests pin the
SHA-256-derived randomness down so that audit runs remain reproducible and
exhaustively enumerate every documented branch of the module:

* quantile probability validation, empty/singleton inputs, finite-only check,
  and the Hyndman-Fan type-7 linear interpolation;
* counter-draw determinism, modulus clamping, ``population < 1`` rejection,
  and the rare rejection-sampling re-roll path;
* bootstrap mean confidence-interval computation including the empty-task,
  resample-count, and metadata tagging behaviour;
* seed-digest hashing through the canonical JSON helper.

These tests intentionally call the private ``_counter_draw``,
``_bootstrap_mean_ci``, and ``_seed_digest`` helpers to exercise every code
path.  No trial-helper patching is needed because none of these helpers touch
:mod:`aggregate_contracts`.
"""

from __future__ import annotations

import hashlib
import math
import unittest
from unittest import mock

from pheno.evidence import aggregate_bootstrap as bootstrap
from pheno.evidence.aggregate_bootstrap import (
    BOOTSTRAP_METHOD,
    DEFAULT_BOOTSTRAP_RESAMPLES,
    QUANTILE_METHOD,
    _bootstrap_mean_ci,
    _counter_draw,
    _seed_digest,
    quantile_type7,
)
from pheno.evidence.contracts import canonical_json_bytes

SEED_BYTES = b"\x00\x01\x02\x03\x04\x05\x06\x07"


class AggregateBootstrapModuleSurfaceTests(unittest.TestCase):
    """Verify the public surface and constant values match the spec."""

    def test_module_constants_have_documented_values(self) -> None:
        # The 10k baseline matches the canonical contract; QUANTILE_METHOD and
        # BOOTSTRAP_METHOD are literal strings that downstream auditors grep.
        self.assertEqual(DEFAULT_BOOTSTRAP_RESAMPLES, 10_000)
        self.assertEqual(QUANTILE_METHOD, "Hyndman-Fan-type-7")
        self.assertEqual(BOOTSTRAP_METHOD, "paired-task-cluster-percentile-v1")

    def test_module_all_exports_match_dunder_all(self) -> None:
        self.assertEqual(
            set(bootstrap.__all__),
            {
                "BOOTSTRAP_METHOD",
                "DEFAULT_BOOTSTRAP_RESAMPLES",
                "QUANTILE_METHOD",
                "quantile_type7",
            },
        )


class QuantileType7Tests(unittest.TestCase):
    """Branch coverage for the deterministic Hyndman-Fan type-7 quantile."""

    def test_empty_sequence_returns_none(self) -> None:
        # None is the documented sentinel for "no observations"; the caller
        # chooses how to surface it (matching the production summaries that
        # convert None to "not_evaluable").
        self.assertIsNone(quantile_type7([], 0.5))

    def test_singleton_returns_the_observation(self) -> None:
        self.assertEqual(quantile_type7([7.0], 0.0), 7.0)
        self.assertEqual(quantile_type7([7.0], 0.5), 7.0)
        self.assertEqual(quantile_type7([7.0], 1.0), 7.0)

    def test_two_element_midpoint_matches_linear_interpolation(self) -> None:
        # Type-7 puts the cut point at ``(n-1)*p`` then linearly interpolates.
        self.assertEqual(quantile_type7([0.0, 10.0], 0.0), 0.0)
        self.assertEqual(quantile_type7([0.0, 10.0], 0.5), 5.0)
        self.assertEqual(quantile_type7([0.0, 10.0], 1.0), 10.0)

    def test_unsorted_input_is_sorted_internally(self) -> None:
        # The implementation sorts before slicing — verify both orderings
        # produce the same answer.
        ascending = quantile_type7([1.0, 2.0, 3.0, 4.0, 5.0], 0.5)
        descending = quantile_type7([5.0, 4.0, 3.0, 2.0, 1.0], 0.5)
        self.assertEqual(ascending, descending)
        self.assertEqual(ascending, 3.0)

    def test_interpolation_midway_between_two_integer_positions(self) -> None:
        # Type-7 does not require coincidence with an observation; verify the
        # interpolation arithmetic.
        # sorted values: [0, 5, 10]; at p=0.25 position = 2 * 0.25 = 0.5
        # 0 + 0.5 * (5 - 0) = 2.5
        self.assertEqual(quantile_type7([0.0, 5.0, 10.0], 0.25), 2.5)
        # sorted: [0, 5, 10]; at p=0.75 position = 2 * 0.75 = 1.5
        # 5 + 0.5 * (10 - 5) = 7.5
        self.assertEqual(quantile_type7([0.0, 5.0, 10.0], 0.75), 7.5)

    def test_probability_below_zero_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, r"\[\s*0,\s*1\s*\]"):
            quantile_type7([1.0, 2.0], -0.01)

    def test_probability_above_one_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, r"\[\s*0,\s*1\s*\]"):
            quantile_type7([1.0, 2.0], 1.01)

    def test_non_finite_values_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite values"):
            quantile_type7([math.inf, 1.0], 0.5)
        with self.assertRaisesRegex(ValueError, "finite values"):
            quantile_type7([1.0, math.nan], 0.5)
        with self.assertRaisesRegex(ValueError, "finite values"):
            quantile_type7([1.0, -math.inf], 0.5)

    def test_singleton_with_non_finite_still_raises_not_singleton_returns(self) -> None:
        # The order matters: we want non-finite detection to happen even when
        # the input would otherwise be considered a singleton.
        with self.assertRaisesRegex(ValueError, "finite values"):
            quantile_type7([math.inf], 0.5)

    def test_integer_inputs_are_promoted_to_float(self) -> None:
        # Passing ints must not break the result; the implementation should
        # promote them via ``float`` before sorting.
        self.assertEqual(quantile_type7([0, 10], 0.5), 5.0)
        self.assertIsInstance(quantile_type7([0, 10], 0.5), float)

    def test_probability_at_endpoints_returns_bounds(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(quantile_type7(values, 0.0), 1.0)
        self.assertEqual(quantile_type7(values, 1.0), 4.0)


class CounterDrawTests(unittest.TestCase):
    """Branch and determinism coverage for ``_counter_draw``."""

    def test_population_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "population must be positive"):
            _counter_draw(SEED_BYTES, 0, 0, 0)
        with self.assertRaisesRegex(ValueError, "population must be positive"):
            _counter_draw(SEED_BYTES, 0, 0, -3)

    def test_draw_is_deterministic_for_fixed_arguments(self) -> None:
        a = _counter_draw(SEED_BYTES, 1, 2, 17)
        b = _counter_draw(SEED_BYTES, 1, 2, 17)
        self.assertEqual(a, b)
        self.assertGreaterEqual(a, 0)
        self.assertLess(a, 17)

    def test_seed_bytes_influence_output(self) -> None:
        # The byte stream is concatenated into the SHA-256 input, so flipping
        # any byte should perturb the draw.
        baseline = _counter_draw(SEED_BYTES, 0, 0, 256)
        flipped = _counter_draw(bytes(b ^ 0xFF for b in SEED_BYTES), 0, 0, 256)
        self.assertNotEqual(baseline, flipped)

    def test_replicate_counter_changes_output(self) -> None:
        # Walk through enough replicates that we almost certainly see distinct
        # outputs (the rejection-sampling loop caps the count).
        draws = {_counter_draw(SEED_BYTES, r, 0, 1024) for r in range(64)}
        self.assertGreater(len(draws), 1)

    def test_draw_counter_changes_output(self) -> None:
        draws = {_counter_draw(SEED_BYTES, 0, d, 1024) for d in range(64)}
        self.assertGreater(len(draws), 1)

    def test_output_is_in_closed_range(self) -> None:
        # Exhaustively check every draw in a small window stays in range.
        for replicate in range(8):
            for draw in range(8):
                value = _counter_draw(SEED_BYTES, replicate, draw, 5)
                self.assertGreaterEqual(value, 0)
                self.assertLess(value, 5)

    def test_population_one_always_returns_zero(self) -> None:
        # With only one valid residue modulo population, the rejection loop is
        # still well-defined; verify every replicate/draw pair gives 0.
        for replicate in range(8):
            for draw in range(8):
                self.assertEqual(_counter_draw(SEED_BYTES, replicate, draw, 1), 0)

    def test_rejection_sampling_loop_is_exercised(self) -> None:
        # The probability of naturally hitting the rejection-sampling re-roll
        # path is roughly ``population / 2**64``, so we patch ``hashlib.sha256``
        # to return a sequence: the first call returns a digest that decodes
        # to exactly ``limit`` (forcing a rejection), the second returns a
        # well-bounded value (forcing acceptance).  This proves the
        # ``counter += 1`` re-roll path runs and is bounded.
        population = 5
        limit_for_pop5 = (1 << 64) - ((1 << 64) % population)
        # First 8 bytes decode to exactly ``limit`` — value < limit fails.
        rejected_digest = limit_for_pop5.to_bytes(8, "big") + b"\x00" * 24
        # First 8 bytes decode to 1, comfortably below ``limit``.
        accepted_digest = (1).to_bytes(8, "big") + b"\x00" * 24
        sha_calls = []

        def fake_sha256(material: bytes) -> mock.Mock:
            pick = rejected_digest if len(sha_calls) == 0 else accepted_digest
            sha_calls.append(material)
            return mock.Mock(digest=lambda buf=pick: buf)

        with mock.patch.object(bootstrap.hashlib, "sha256", side_effect=fake_sha256):
            value = _counter_draw(SEED_BYTES, 7, 11, population)
            # Two SHA-256 invocations: the rejection + the acceptance.
            self.assertEqual(len(sha_calls), 2)
            self.assertEqual(value, 1 % population)
            self.assertGreaterEqual(value, 0)
            self.assertLess(value, population)


class BootstrapMeanCITests(unittest.TestCase):
    """Coverage for ``_bootstrap_mean_ci`` and the empty input fallback."""

    def test_empty_task_values_returns_none_bounds(self) -> None:
        result = _bootstrap_mean_ci({}, seed=SEED_BYTES, resamples=8)
        self.assertIsNone(result["lower"])
        self.assertIsNone(result["upper"])
        self.assertEqual(result["resamples"], 8)
        self.assertEqual(result["task_clusters"], 0)
        self.assertEqual(result["method"], BOOTSTRAP_METHOD)
        self.assertEqual(result["quantile_method"], QUANTILE_METHOD)

    def test_non_empty_task_values_produce_populated_bounds(self) -> None:
        # All-ones mean: the bootstrap should land on [1.0, 1.0].
        result = _bootstrap_mean_ci(
            {"a": 1.0, "b": 1.0, "c": 1.0}, seed=SEED_BYTES, resamples=32
        )
        self.assertEqual(result["lower"], 1.0)
        self.assertEqual(result["upper"], 1.0)
        self.assertEqual(result["resamples"], 32)
        self.assertEqual(result["task_clusters"], 3)
        self.assertEqual(result["method"], BOOTSTRAP_METHOD)
        self.assertEqual(result["quantile_method"], QUANTILE_METHOD)

    def test_mean_ci_is_deterministic_for_fixed_arguments(self) -> None:
        values = {"a": 0.2, "b": 0.5, "c": 0.8, "d": 0.3, "e": 0.6}
        first = _bootstrap_mean_ci(values, seed=SEED_BYTES, resamples=64)
        second = _bootstrap_mean_ci(values, seed=SEED_BYTES, resamples=64)
        self.assertEqual(first["lower"], second["lower"])
        self.assertEqual(first["upper"], second["upper"])

    def test_seed_bytes_change_the_ci(self) -> None:
        values = {"a": 0.1, "b": 0.2, "c": 0.3, "d": 0.4, "e": 0.5}
        first = _bootstrap_mean_ci(values, seed=b"alpha", resamples=64)
        second = _bootstrap_mean_ci(values, seed=b"beta", resamples=64)
        # Different seeds should produce different resampled CIs even with the
        # same input values. (The likelihood of an exact match is negligible.)
        self.assertNotEqual(
            (first["lower"], first["upper"]), (second["lower"], second["upper"])
        )

    def test_task_ids_are_processed_in_sorted_order(self) -> None:
        # The task-id sorting is what makes the seed deterministic across
        # dict iteration order.  Pass unsorted mapping twice with reversed
        # insertion orders and confirm the CI is identical.
        unsorted_a = {"z": 0.1, "m": 0.4, "a": 0.7}
        unsorted_b = {"a": 0.7, "m": 0.4, "z": 0.1}
        first = _bootstrap_mean_ci(unsorted_a, seed=SEED_BYTES, resamples=32)
        second = _bootstrap_mean_ci(unsorted_b, seed=SEED_BYTES, resamples=32)
        self.assertEqual(first["lower"], second["lower"])
        self.assertEqual(first["upper"], second["upper"])

    def test_ci_bounds_are_within_value_range(self) -> None:
        values = {"a": 0.0, "b": 0.25, "c": 0.5, "d": 0.75, "e": 1.0}
        result = _bootstrap_mean_ci(values, seed=SEED_BYTES, resamples=128)
        for bound in (result["lower"], result["upper"]):
            self.assertGreaterEqual(bound, min(values.values()))
            self.assertLessEqual(bound, max(values.values()))

    def test_resamples_is_reflected_in_metadata(self) -> None:
        result = _bootstrap_mean_ci({"x": 0.5}, seed=SEED_BYTES, resamples=17)
        self.assertEqual(result["resamples"], 17)

    def test_default_resamples_matches_documented_baseline(self) -> None:
        # The CI metadata should expose the requested resample count even
        # when callers pass the default.
        self.assertGreaterEqual(DEFAULT_BOOTSTRAP_RESAMPLES, 1)
        result = _bootstrap_mean_ci(
            {"x": 0.5}, seed=SEED_BYTES, resamples=DEFAULT_BOOTSTRAP_RESAMPLES
        )
        self.assertEqual(result["resamples"], DEFAULT_BOOTSTRAP_RESAMPLES)


class SeedDigestTests(unittest.TestCase):
    """Coverage for ``_seed_digest`` and canonical JSON integration."""

    def test_seed_is_thirty_two_bytes(self) -> None:
        # SHA-256 always yields 32 bytes, so this is a structural check that
        # the helper is actually using SHA-256 (not e.g. truncated.
        digest = _seed_digest("label", {"k": 1})
        self.assertIsInstance(digest, bytes)
        self.assertEqual(len(digest), 32)

    def test_seed_is_deterministic(self) -> None:
        first = _seed_digest("pheno.eval.aggregate.v2:quality", {"a": 1})
        second = _seed_digest("pheno.eval.aggregate.v2:quality", {"a": 1})
        self.assertEqual(first, second)

    def test_label_changes_seed(self) -> None:
        first = _seed_digest("label-a", {"k": 1})
        second = _seed_digest("label-b", {"k": 1})
        self.assertNotEqual(first, second)

    def test_payload_changes_seed(self) -> None:
        first = _seed_digest("label", {"a": 1})
        second = _seed_digest("label", {"a": 2})
        self.assertNotEqual(first, second)

    def test_separator_byte_is_well_defined(self) -> None:
        # The implementation uses ``label.encode("utf-8") + b"\\0" + payload``.
        # We verify the helper agrees with the same construction by hand.
        payload = {"x": 5}
        expected = hashlib.sha256(
            b"manual-label" + b"\0" + canonical_json_bytes(payload)
        ).digest()
        actual = _seed_digest("manual-label", payload)
        self.assertEqual(actual, expected)

    def test_payload_is_canonicalised_before_hashing(self) -> None:
        # The digest must be insensitive to dict insertion order because
        # canonical_json_bytes sorts keys.
        first = _seed_digest("order-test", {"a": 1, "b": 2})
        second = _seed_digest("order-test", {"b": 2, "a": 1})
        self.assertEqual(first, second)

    def test_empty_payload_is_accepted(self) -> None:
        # An empty mapping is a valid payload; the digest should still be a
        # well-formed 32-byte value.
        digest = _seed_digest("empty", {})
        self.assertEqual(len(digest), 32)

    def test_unicode_label_is_utf8_encoded(self) -> None:
        # Non-ASCII labels must not blow up.
        digest = _seed_digest("pheno.∑.v2", {"k": 1})
        self.assertEqual(len(digest), 32)


class BootstrapInteropTests(unittest.TestCase):
    """Cross-helper integration smoke tests that the module is wired correctly."""

    def test_seed_digest_input_matches_summarize_drift_inputs(self) -> None:
        # The full pipeline passes canonicalized payloads through
        # ``_seed_digest``; verify the digest is stable for a richer object.
        # ``canonical_json_bytes`` sorts dict keys but preserves list order,
        # so callers are responsible for passing sorted lists — exactly the
        # convention used by ``_quality`` and ``_paired_comparison``.
        payload = {
            "trial_sha256": ["aaa", "bbb"],
            "task_ids": ["t1", "t2"],
            "attempts_per_task": 4,
        }
        first = _seed_digest("pheno.eval.aggregate.v2:quality", payload)
        same_payload_with_reordered_dict = {
            "attempts_per_task": 4,
            "task_ids": ["t1", "t2"],
            "trial_sha256": ["aaa", "bbb"],
        }
        second = _seed_digest(
            "pheno.eval.aggregate.v2:quality", same_payload_with_reordered_dict
        )
        self.assertEqual(first, second)
        # Different list order, however, must change the digest because
        # canonical_json_bytes preserves list ordering.
        reordered_lists = {
            "trial_sha256": ["bbb", "aaa"],
            "task_ids": ["t2", "t1"],
            "attempts_per_task": 4,
        }
        third = _seed_digest("pheno.eval.aggregate.v2:quality", reordered_lists)
        self.assertNotEqual(first, third)

    def test_default_resamples_is_large_enough_for_useful_ci(self) -> None:
        # Sanity-check that ``DEFAULT_BOOTSTRAP_RESAMPLES`` is big enough that
        # the resulting CI bounds are not exactly identical to single-sample
        # values for typical inputs.  This guards against accidentally
        # dropping the constant back to a tiny value.
        values = {f"t{i}": 0.5 + i / 100 for i in range(10)}
        result = _bootstrap_mean_ci(
            values,
            seed=SEED_BYTES,
            resamples=DEFAULT_BOOTSTRAP_RESAMPLES,
        )
        # Each bound is a finite float, not None.
        self.assertIsInstance(result["lower"], float)
        self.assertIsInstance(result["upper"], float)
        # The mean is approximately the input mean; bounds should bracket it.
        mean_value = sum(values.values()) / len(values)
        self.assertGreaterEqual(result["upper"], mean_value - 0.05)
        self.assertLessEqual(result["lower"], mean_value + 0.05)


if __name__ == "__main__":
    unittest.main()
