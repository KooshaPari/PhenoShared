"""Tests for the :mod:`pheno_mcp_router.cost` cost calculator.

The cost calculator is pure (no I/O, no shared state) so the test
suite exercises every arithmetic path, both the explicit
``TokenUsage`` input and the message-based / response-based
convenience wrappers, and the unknown-tier fallback behaviour that
the rest of the cost subsystem relies on.

Ported from dispatch-mcp W2-1 (test_core_cost.py @ 6aad7fa) per
L5-104.1 with import rewrite.
"""

from __future__ import annotations

import pytest

from pheno_mcp_router.cost import (
    CostCalculator,
    CostEstimate,
    TokenEstimator,
    TokenUsage,
)
from pheno_mcp_router.tiers import DEFAULT_REGISTRY, UNKNOWN_PRICING


# ---------------------------------------------------------------------------
# TokenUsage
# ---------------------------------------------------------------------------


def test_token_usage_total_sums_components() -> None:
    """``total`` is the simple sum of input + output tokens."""
    usage = TokenUsage(input_tokens=100, output_tokens=50)
    assert usage.total == 150


def test_token_usage_zero_total_is_valid() -> None:
    """A zero-cost probe dispatch is not an error."""
    usage = TokenUsage(input_tokens=0, output_tokens=0)
    assert usage.total == 0


def test_token_usage_rejects_negative_input() -> None:
    """Negative input tokens raise ``ValueError`` at construction."""
    with pytest.raises(ValueError, match="input_tokens must be >= 0"):
        TokenUsage(input_tokens=-1, output_tokens=0)


def test_token_usage_rejects_negative_output() -> None:
    """Negative output tokens raise ``ValueError`` at construction."""
    with pytest.raises(ValueError, match="output_tokens must be >= 0"):
        TokenUsage(input_tokens=0, output_tokens=-1)


# ---------------------------------------------------------------------------
# TokenEstimator.from_message
# ---------------------------------------------------------------------------


def test_estimator_from_empty_message_returns_one_token() -> None:
    """An empty message maps to one token so quota gates can never be bypassed."""
    assert TokenEstimator.from_message("") == 1


def test_estimator_from_short_message_rounds_up() -> None:
    """The estimator rounds up so partial tokens still count."""
    # 4-byte ASCII string → 1 token; 5-byte → 2 tokens.
    assert TokenEstimator.from_message("a") == 1
    assert TokenEstimator.from_message("abcd") == 1
    assert TokenEstimator.from_message("abcde") == 2


def test_estimator_from_multibyte_counts_bytes() -> None:
    """Multi-byte characters inflate the estimate (BPE typically 1 token each)."""
    # 1 emoji is 4 bytes UTF-8 → 1 token.
    assert TokenEstimator.from_message("\u2728") == 1
    # 3 emoji is 12 bytes → 3 tokens.
    assert TokenEstimator.from_message("\u2728\u2728\u2728") == 3


def test_estimator_from_long_message_uses_chars_per_4() -> None:
    """The estimator is a chars/4 heuristic (with a minimum of 1)."""
    # 400 ASCII chars → 100 tokens.
    assert TokenEstimator.from_message("x" * 400) == 100


# ---------------------------------------------------------------------------
# TokenEstimator.from_response
# ---------------------------------------------------------------------------


def test_estimator_from_response_uses_usage_block() -> None:
    """A well-formed ``usage`` block is used verbatim."""
    response = {"usage": {"input_tokens": 123, "output_tokens": 456}}
    usage = TokenEstimator.from_response(response, "ignored")
    assert usage.input_tokens == 123
    assert usage.output_tokens == 456


def test_estimator_from_response_falls_back_when_usage_missing() -> None:
    """No ``usage`` block → message-based estimate + default output."""
    response = {"ok": True, "message": "hi"}
    usage = TokenEstimator.from_response(response, "hello world")
    # 11 ASCII bytes / 4 = 2.75 → 3 input tokens.
    assert usage.input_tokens == 3
    # Default output fallback (256) keeps the quota gate conservative.
    assert usage.output_tokens == 256


def test_estimator_from_response_handles_malformed_usage() -> None:
    """A malformed usage block is treated as missing."""
    # Wrong types for the inner fields.
    response = {"usage": {"input_tokens": "nope", "output_tokens": None}}
    usage = TokenEstimator.from_response(response, "hello")
    assert usage.input_tokens >= 1
    assert usage.output_tokens == 256


def test_estimator_from_response_handles_negative_usage() -> None:
    """Negative token counts in the usage block are treated as missing."""
    response = {"usage": {"input_tokens": -1, "output_tokens": -5}}
    usage = TokenEstimator.from_response(response, "hi")
    assert usage.input_tokens >= 1
    assert usage.output_tokens == 256


def test_estimator_from_response_handles_non_dict_response() -> None:
    """A non-dict response (None, list, string) does not crash."""
    for raw in (None, [], "oops", 42):
        usage = TokenEstimator.from_response(raw, "x")  # type: ignore[arg-type]
        assert usage.input_tokens >= 1
        assert usage.output_tokens == 256


# ---------------------------------------------------------------------------
# CostCalculator.estimate
# ---------------------------------------------------------------------------


def test_calculator_uses_tier_pricing() -> None:
    """Estimate produces input + output cost from the registered tier."""
    calc = CostCalculator()
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
    estimate = calc.estimate("haiku", usage)
    # haiku is $0.80/M input + $4.00/M output = $4.80/M tokens total.
    assert estimate.input_cost == pytest.approx(0.80)
    assert estimate.output_cost == pytest.approx(4.00)
    assert estimate.cost_usd == pytest.approx(4.80)
    assert estimate.is_priced is True
    assert estimate.model == "claude-3-5-haiku-20241022"
    assert estimate.provider == "anthropic"


def test_calculator_unknown_tier_marks_unpriced() -> None:
    """An unregistered tier returns zero cost and ``is_priced=False``."""
    calc = CostCalculator()
    estimate = calc.estimate("not-a-real-tier", TokenUsage(100, 100))
    assert estimate.cost_usd == 0.0
    assert estimate.is_priced is False
    # Even unpriced, the audit trail still gets a model name (the
    # sentinel "unknown" so the row is not orphaned).
    assert estimate.model == UNKNOWN_PRICING.model
    assert estimate.provider == UNKNOWN_PRICING.provider


def test_calculator_uses_custom_registry() -> None:
    """An injected registry is consulted instead of the default."""
    from pheno_mcp_router.tiers import TierPricing, TierRegistry

    custom = TierRegistry(
        tiers={
            "custom": TierPricing(
                name="custom",
                provider="acme",
                model="acme-1",
                input_per_1m=10.0,
                output_per_1m=20.0,
            )
        }
    )
    calc = CostCalculator(registry=custom)
    estimate = calc.estimate("custom", TokenUsage(1_000_000, 1_000_000))
    assert estimate.cost_usd == pytest.approx(30.0)
    assert estimate.is_priced is True


def test_calculator_default_registry_property() -> None:
    """The ``registry`` property is exposed for inspection."""
    calc = CostCalculator()
    assert calc.registry is DEFAULT_REGISTRY


# ---------------------------------------------------------------------------
# estimate_from_message
# ---------------------------------------------------------------------------


def test_estimate_from_message_uses_estimator() -> None:
    """Pre-dispatch estimation combines the message heuristic with pricing."""
    calc = CostCalculator()
    estimate = calc.estimate_from_message("haiku", "hello world")
    # 11 bytes / 4 = 3 input tokens; default 256 output tokens.
    assert estimate.input_tokens == 3
    assert estimate.output_tokens == 256
    # haiku rates: 3 * 0.80/M + 256 * 4.00/M ≈ 0.0000024 + 0.001024 = 0.0010264
    assert estimate.cost_usd == pytest.approx(0.0010264, abs=1e-9)


def test_estimate_from_message_honors_explicit_output_tokens() -> None:
    """The caller can override the default output-token estimate."""
    calc = CostCalculator()
    estimate = calc.estimate_from_message("haiku", "x", output_tokens=1000)
    assert estimate.output_tokens == 1000


def test_estimate_from_message_unknown_tier() -> None:
    """An unknown tier still gets a TokenUsage-shaped estimate (zero cost)."""
    calc = CostCalculator()
    estimate = calc.estimate_from_message("mystery", "hello")
    assert estimate.is_priced is False
    assert estimate.cost_usd == 0.0
    assert estimate.input_tokens >= 1


# ---------------------------------------------------------------------------
# estimate_from_response
# ---------------------------------------------------------------------------


def test_estimate_from_response_prefers_actual_usage() -> None:
    """Post-dispatch estimation uses real usage over the message heuristic."""
    calc = CostCalculator()
    response = {"usage": {"input_tokens": 5000, "output_tokens": 1000}}
    estimate = calc.estimate_from_response("haiku", "ignored", response)
    # haiku: 5000 * 0.80/M + 1000 * 4.00/M = 0.004 + 0.004 = 0.008
    assert estimate.input_tokens == 5000
    assert estimate.output_tokens == 1000
    assert estimate.cost_usd == pytest.approx(0.008)


def test_estimate_from_response_falls_back_when_no_usage() -> None:
    """No usage block → fall back to message + default output estimate."""
    calc = CostCalculator()
    estimate = calc.estimate_from_response("haiku", "hello", {"ok": True})
    assert estimate.input_tokens >= 1
    assert estimate.output_tokens == 256


# ---------------------------------------------------------------------------
# CostEstimate.to_dict
# ---------------------------------------------------------------------------


def test_cost_estimate_to_dict_shape() -> None:
    """The serialized shape is stable (used by audit entries and tool outputs)."""
    estimate = CostEstimate(
        tier="haiku",
        model="claude-3-5-haiku-20241022",
        provider="anthropic",
        input_tokens=1000,
        output_tokens=500,
        input_cost=0.0008,
        output_cost=0.002,
        cost_usd=0.0028,
        is_priced=True,
    )
    payload = estimate.to_dict()
    assert payload["tier"] == "haiku"
    assert payload["model"] == "claude-3-5-haiku-20241022"
    assert payload["provider"] == "anthropic"
    assert payload["input_tokens"] == 1000
    assert payload["output_tokens"] == 500
    assert payload["input_cost_usd"] == pytest.approx(0.0008)
    assert payload["output_cost_usd"] == pytest.approx(0.002)
    assert payload["cost_usd"] == pytest.approx(0.0028)
    assert payload["is_priced"] is True


def test_cost_estimate_to_dict_rounds_to_8dp() -> None:
    """Currency fields are rounded so log diffs and snapshots stay stable."""
    estimate = CostEstimate(
        tier="haiku",
        model="m",
        provider="p",
        input_tokens=1,
        output_tokens=1,
        input_cost=0.000000123456789,
        output_cost=0.000000987654321,
        cost_usd=0.000001111110110,
        is_priced=True,
    )
    payload = estimate.to_dict()
    # 8 decimal places: 0.00000012 / 0.00000099 / 0.00000111
    assert payload["input_cost_usd"] == pytest.approx(0.00000012, abs=1e-9)
    assert payload["output_cost_usd"] == pytest.approx(0.00000099, abs=1e-9)
    assert payload["cost_usd"] == pytest.approx(0.00000111, abs=1e-9)
