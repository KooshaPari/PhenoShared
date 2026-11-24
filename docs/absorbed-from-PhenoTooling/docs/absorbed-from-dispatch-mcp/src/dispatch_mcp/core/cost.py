"""Cost calculator middleware for dispatch_mcp.

Given a tier and a token-usage record, the calculator returns a
:class:`CostEstimate` containing the USD cost, the canonical
upstream model, and the per-component breakdown. The calculator
is pure (no I/O, no shared state) and safe to invoke from any
thread or async context.

The companion :class:`TokenEstimator` provides a best-effort
token count for input messages when the upstream response does
not include a usage block. Estimation is deliberately simple
(chars/4) — it is only used for pre-dispatch budget/quota
checks. Post-dispatch accounting should use the actual usage
returned by OmniRoute whenever possible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from dispatch_mcp.core.tiers import DEFAULT_REGISTRY, UNKNOWN_PRICING, TierPricing, TierRegistry

# Approximate characters-per-token for English text. Published
# tokenizer statistics for BPE tokenizers (cl100k_base, o200k_base,
# Claude, Kimi) cluster between 3.5 and 4.5 chars/token for natural
# language; we use 4 as a conservative over-estimate. The over-
# estimate biases pre-dispatch budget enforcement toward rejecting
# requests that *might* exceed budget, which is the safer default.
_CHARS_PER_TOKEN: Final[int] = 4

# Fallback output-token count used when the response does not report
# usage and we have no other signal. The number is intentionally
# conservative so unmeasured dispatches do not silently slip under
# the budget radar.
_DEFAULT_OUTPUT_TOKEN_ESTIMATE: Final[int] = 256


@dataclass(slots=True, frozen=True)
class TokenUsage:
    """Input and output token counts for a single dispatch.

    ``input_tokens`` measures the prompt that was sent to the model.
    ``output_tokens`` measures the model's response. Both are
    non-negative integers; a zero value is a valid degenerate case
    (e.g. a probe dispatch).
    """

    input_tokens: int
    output_tokens: int

    @property
    def total(self) -> int:
        """Return the sum of input and output tokens."""
        return self.input_tokens + self.output_tokens

    def __post_init__(self) -> None:
        if self.input_tokens < 0:
            raise ValueError("input_tokens must be >= 0")
        if self.output_tokens < 0:
            raise ValueError("output_tokens must be >= 0")


@dataclass(slots=True, frozen=True)
class CostEstimate:
    """Computed cost for a single dispatch.

    ``model`` is the canonical upstream model identifier (e.g.
    ``"claude-opus-4"``). ``is_priced`` is ``False`` when the tier
    was not in the registry; in that case ``cost_usd`` is the
    conservative default rate used for budget enforcement.
    ``input_cost`` and ``output_cost`` are the component
    breakdown; their sum equals ``cost_usd`` up to float
    arithmetic.
    """

    tier: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    cost_usd: float
    is_priced: bool

    @property
    def tokens(self) -> int:
        """Return the sum of input and output tokens.

        Used by the quota tracker so the caller does not have to
        re-sum the components when recording windowed usage.
        """
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict[str, str | int | float | bool]:
        """Serialize for inclusion in tool responses and audit entries."""
        return {
            "tier": self.tier,
            "model": self.model,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "input_cost_usd": round(self.input_cost, 8),
            "output_cost_usd": round(self.output_cost, 8),
            "cost_usd": round(self.cost_usd, 8),
            "is_priced": self.is_priced,
        }


class TokenEstimator:
    """Best-effort token counting when upstream usage is unavailable.

    The estimator is stateless. The :meth:`from_message` method
    accepts the raw text of the prompt; :meth:`from_response_usage`
    extracts counts from a dict shaped like OmniRoute's response
    payload (``{"usage": {"input_tokens": N, "output_tokens": M}}``)
    and falls back to the input message plus a conservative
    default output estimate when the usage block is absent.
    """

    __slots__ = ()

    @staticmethod
    def from_message(message: str) -> int:
        """Estimate input tokens for ``message`` using a chars/4 heuristic.

        Bytes are used (not characters) so multi-byte scripts are
        not under-counted. The result is rounded up so that an
        empty message still maps to a positive number of tokens —
        this prevents zero-token dispatches from bypassing
        pre-dispatch quota checks.
        """
        if not message:
            return 1
        # BPE tokenizers typically encode multi-byte characters in
        # one token, so byte length is a closer lower bound than
        # character length for non-ASCII content.
        byte_len = len(message.encode("utf-8"))
        return max(1, (byte_len + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN)

    @staticmethod
    def from_response(response: dict[str, Any], message: str) -> TokenUsage:
        """Extract :class:`TokenUsage` from an OmniRoute response.

        If the response contains a ``usage`` block with
        ``input_tokens`` and ``output_tokens`` keys, those values
        are used. Otherwise the input is estimated from the
        message text and the output falls back to
        :data:`_DEFAULT_OUTPUT_TOKEN_ESTIMATE`. Malformed usage
        blocks (missing keys, wrong types) are treated as absent
        so a single bad response cannot crash the cost pipeline.
        """
        usage: Any = response.get("usage") if isinstance(response, dict) else None
        if isinstance(usage, dict):
            in_raw = usage.get("input_tokens")
            out_raw = usage.get("output_tokens")
            in_tok = int(in_raw) if isinstance(in_raw, int | float) and in_raw >= 0 else None
            out_tok = int(out_raw) if isinstance(out_raw, int | float) and out_raw >= 0 else None
            if in_tok is not None and out_tok is not None:
                return TokenUsage(input_tokens=in_tok, output_tokens=out_tok)
        return TokenUsage(
            input_tokens=TokenEstimator.from_message(message),
            output_tokens=_DEFAULT_OUTPUT_TOKEN_ESTIMATE,
        )


class CostCalculator:
    """Compute cost for a dispatch given its tier and token usage.

    The calculator is constructed with a :class:`TierRegistry` and
    is otherwise stateless. Compute cost is O(1); the calculator
    is safe to call from the request hot path.
    """

    __slots__ = ("_registry",)

    def __init__(self, registry: TierRegistry | None = None) -> None:
        self._registry: TierRegistry = registry or DEFAULT_REGISTRY

    @property
    def registry(self) -> TierRegistry:
        """Return the tier registry (read-only access)."""
        return self._registry

    def estimate(self, tier: str, usage: TokenUsage) -> CostEstimate:
        """Return a :class:`CostEstimate` for ``tier`` and ``usage``.

        Unknown tiers yield an :data:`UNKNOWN_PRICING`-based
        estimate with ``is_priced=False``. This is deliberate: a
        dispatch to an unpriced tier still gets a cost line item
        in the audit trail so operators can spot drift, even
        though the cost is zero.
        """
        pricing: TierPricing = self._registry.get(tier)
        is_priced = pricing is not UNKNOWN_PRICING
        input_cost = pricing.input_per_1m * usage.input_tokens / 1_000_000
        output_cost = pricing.output_per_1m * usage.output_tokens / 1_000_000
        return CostEstimate(
            tier=tier,
            model=pricing.model,
            provider=pricing.provider,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            cost_usd=input_cost + output_cost,
            is_priced=is_priced,
        )

    def estimate_from_message(
        self,
        tier: str,
        message: str,
        output_tokens: int | None = None,
    ) -> CostEstimate:
        """Estimate cost for ``tier`` from a raw message string.

        This is a convenience wrapper that combines
        :meth:`TokenEstimator.from_message` and :meth:`estimate`.
        Use it for pre-dispatch budgeting when actual usage is
        not yet available. ``output_tokens`` defaults to
        :data:`_DEFAULT_OUTPUT_TOKEN_ESTIMATE`.
        """
        usage = TokenUsage(
            input_tokens=TokenEstimator.from_message(message),
            output_tokens=(
                output_tokens
                if output_tokens is not None
                else _DEFAULT_OUTPUT_TOKEN_ESTIMATE
            ),
        )
        return self.estimate(tier, usage)

    def estimate_from_response(
        self,
        tier: str,
        message: str,
        response: dict[str, Any],
    ) -> CostEstimate:
        """Estimate cost from a real OmniRoute response.

        Prefers actual usage from the response payload, falling
        back to character-based estimation when usage is absent
        or malformed. This is the function the cost-tracking
        middleware calls after a dispatch completes.
        """
        usage = TokenEstimator.from_response(response, message)
        return self.estimate(tier, usage)
