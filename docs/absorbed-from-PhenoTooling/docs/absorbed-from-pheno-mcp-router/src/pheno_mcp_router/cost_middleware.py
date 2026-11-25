"""Cost-aware LLM middleware for pheno-mcp-router.

This module composes a substrate :class:`~pheno_mcp_router.ports.LlmPort`
with the cost calculator, budget enforcer, quota tracker, and
audit log. The middleware is the single integration point that
a ``pheno-mcp-*`` server wires up; it is intentionally the only
place that knows the exact wire shape of all four subsystems.

The middleware preserves the public surface the substrate
expects — :meth:`LlmPort.chat` returns just the assistant text
(LlmPort contract) — while adding a tier-aware :meth:`dispatch`
method that layers cost metadata on top. ``LlmPort.chat`` is
the substrate-level entrypoint; ``dispatch(tier=...)`` is the
cost-tracking entrypoint. A ``CostAwareLlmAdapter`` constructed
with ``enabled=False`` is a thin pass-through.

Substrate-level port hooks
--------------------------
The middleware implements :class:`~pheno_mcp_router.ports.LlmAdapter`
so it can be used anywhere an :class:`~pheno_mcp_router.ports.LlmPort`
is expected (e.g., as the chat backend of an ``McpRouter``). The
cost/budget/quota subsystems are substrate-internal; the
middleware composes them on top of any inner ``LlmPort`` the
caller provides.

Ported from dispatch-mcp W2-1 (commit ``6aad7fa``) per L5-104.1.
The original wired around a dispatch-mcp-internal ``Router``
protocol that called ``inner.dispatch(message, tier, payload) ->
dict`` and returned a ``JobResult``. The substrate does not
have these types — the LlmPort contract is the strict
``async chat(messages, model) -> str`` surface. The cost
middleware was rewritten to thread tier through a new
``dispatch()`` entrypoint while keeping ``chat()`` as a
substrate-compliant pass-through.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from pheno_mcp_router.audit import AuditLog
from pheno_mcp_router.budget import BudgetExceeded, BudgetTracker
from pheno_mcp_router.cost import CostCalculator, CostEstimate, TokenEstimator
from pheno_mcp_router.ports import LlmAdapter, LlmPort
from pheno_mcp_router.quota import QuotaExceeded, QuotaTracker
from pheno_mcp_router.tiers import DEFAULT_REGISTRY, TierRegistry


@dataclass(slots=True, frozen=True)
class CostMiddlewareConfig:
    """Configuration bundle for :class:`CostAwareLlmAdapter`.

    ``enabled`` is the master switch. When ``False`` the
    middleware is a pure pass-through — useful for unit tests
    that want to exercise the legacy code path and for
    emergency kill switches in production.
    """

    enabled: bool = True
    registry: TierRegistry = field(default_factory=lambda: DEFAULT_REGISTRY)
    budget: BudgetTracker = field(default_factory=BudgetTracker)
    quota: QuotaTracker = field(default_factory=QuotaTracker)
    audit: AuditLog = field(default_factory=AuditLog)


@dataclass(slots=True, frozen=True)
class CostAwareDispatchResult:
    """Result of a tier-aware :meth:`CostAwareLlmAdapter.dispatch` call.

    Mirrors the dispatch-mcp ``JobResult`` shape (cost metadata
    + decision/reason) without inheriting dispatch-mcp types.
    ``text`` is the assistant response; ``cost_usd`` is the
    actual cost charged; ``request_id`` is a per-call UUID for
    audit correlation; ``decision`` is ``"allowed"`` /
    ``"blocked"`` and ``reason`` is a machine-readable tag.
    """

    text: str
    tier: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    is_priced: bool
    request_id: str
    decision: str
    reason: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for inclusion in tool responses and audit summaries."""
        return {
            "text": self.text,
            "tier": self.tier,
            "model": self.model,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 8),
            "is_priced": self.is_priced,
            "request_id": self.request_id,
            "decision": self.decision,
            "reason": self.reason,
            "detail": dict(self.detail),
        }


def _serialize_messages(messages: list[Mapping[str, Any]]) -> str:
    """Serialize chat messages to a single text blob for token estimation.

    Joins all message content (system + user + assistant) into
    one UTF-8 string. Used for pre-dispatch input-token
    estimation; the actual LLM call still receives the structured
    messages list.
    """
    parts: list[str] = []
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, Mapping):
                    text = block.get("text")
                    if isinstance(text, str):
                        parts.append(text)
    return "\n".join(parts)


class CostAwareLlmAdapter(LlmAdapter):
    """Wraps an inner :class:`LlmPort` with cost / budget / quota / audit tracking.

    On every :meth:`dispatch` call the middleware:

    1. Validates the tier against the cost registry.
    2. Estimates input tokens from the serialized messages.
    3. Checks the quota gate (raises :class:`QuotaExceeded` if full).
    4. Estimates pre-dispatch cost and checks the budget gate.
    5. Calls the inner adapter (LlmPort.chat).
    6. Estimates output tokens from the response text.
    7. Records quota usage, budget spend, and an audit entry.
    8. Returns a :class:`CostAwareDispatchResult` with the text
       and full cost metadata.

    Failed dispatches (upstream errors) are recorded as
    ``decision="blocked", reason="upstream_error"`` audit entries
    and re-raised; they do not consume budget.
    """

    __slots__ = ("_inner", "_config", "_calculator", "_logger", "_id_factory")

    def __init__(
        self,
        inner: LlmPort,
        config: CostMiddlewareConfig | None = None,
        *,
        logger: logging.Logger | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not isinstance(inner, LlmPort):
            # LlmPort is a runtime_checkable Protocol; structural check.
            raise TypeError(
                f"inner must satisfy LlmPort protocol (async chat(messages, model) -> str); "
                f"got {type(inner).__name__}"
            )
        self._inner = inner
        self._config = config or CostMiddlewareConfig()
        self._calculator = CostCalculator(registry=self._config.registry)
        self._logger = logger or logging.getLogger("pheno_mcp_router.cost_middleware")
        self._id_factory = id_factory or uuid.uuid4

    # ---------------------------------------------------------------- properties

    @property
    def config(self) -> CostMiddlewareConfig:
        """Return the active middleware configuration."""
        return self._config

    @property
    def calculator(self) -> CostCalculator:
        """Return the cost calculator (for inspection and tests)."""
        return self._calculator

    @property
    def inner(self) -> LlmPort:
        """Return the wrapped inner LlmPort."""
        return self._inner

    # ---------------------------------------------------------- LlmPort surface

    async def chat(self, messages: list[Mapping[str, Any]], model: str) -> str:
        """LlmPort.chat surface — passthrough with tier="unknown" tracking.

        Substrate callers that use the cost-aware middleware as an
        ``LlmPort`` get plain text passthrough; the cost / quota /
        audit subsystems still record the dispatch under the
        ``unknown`` tier. For tier-aware cost tracking, callers
        should use :meth:`dispatch` instead.
        """
        if not self._config.enabled:
            return await self._inner.chat(messages, model)
        return await self.dispatch(messages, model, tier="unknown")

    # ----------------------------------------------------------- tier-aware API

    async def dispatch(
        self,
        messages: list[Mapping[str, Any]],
        model: str,
        *,
        tier: str,
    ) -> str:
        """Tier-aware dispatch that returns the assistant text only.

        Equivalent to :meth:`chat` semantically — returns the
        LLM's reply text — but threads the tier through the cost
        / quota / budget / audit subsystems. Use this method
        when the caller knows which upstream tier the dispatch
        targets (the common case for ``pheno-mcp-*`` servers).
        """
        result = await self.dispatch_with_metadata(messages, model, tier=tier)
        return result.text

    async def dispatch_with_metadata(
        self,
        messages: list[Mapping[str, Any]],
        model: str,
        *,
        tier: str,
    ) -> CostAwareDispatchResult:
        """Tier-aware dispatch returning :class:`CostAwareDispatchResult`.

        Full cost / quota / budget / audit accounting with the
        response text and metadata bundled together. Use this
        when the caller needs the cost line item (e.g., to
        return to an MCP tool caller alongside the model output).
        """
        if not self._config.enabled:
            return await self._dispatch_passthrough(messages=messages, model=model, tier=tier)

        request_id = str(self._id_factory())
        message_text = _serialize_messages(messages)
        # Pre-dispatch token estimate for the quota gate. The
        # output token count defaults to the calculator's
        # conservative fallback; the post-dispatch accounting
        # refines it from the actual response text.
        pre_estimate = self._calculator.estimate_from_message(tier, message_text)
        self._check_quota(tier=tier, request_id=request_id, pre=pre_estimate)
        self._check_budget(tier=tier, request_id=request_id, pre=pre_estimate)

        try:
            text = await self._inner.chat(messages, model)
        except Exception as exc:
            # Upstream failure — do not charge the budget. We
            # still record an audit entry with decision=blocked
            # so operators see the failure in the trail.
            self._config.audit.record(
                tier=tier,
                model=pre_estimate.model,
                provider=pre_estimate.provider,
                input_tokens=pre_estimate.input_tokens,
                output_tokens=0,
                cost_usd=0.0,
                decision="blocked",
                reason="upstream_error",
                request_id=request_id,
                is_priced=pre_estimate.is_priced,
                detail={"error": type(exc).__name__, "message": str(exc)},
            )
            raise

        # Post-dispatch accounting. Estimate output tokens from
        # the response text since LlmPort.chat returns only the
        # text (no usage block). The estimate is conservative —
        # any real usage block should override via a future
        # richer-port extension. The canonical cost computation
        # goes via the calculator using the pre+post token counts.
        output_tokens = TokenEstimator.from_message(text)
        post = self._calculator.estimate_from_response(
            tier=tier,
            message=message_text,
            response={"usage": {"input_tokens": pre_estimate.input_tokens, "output_tokens": output_tokens}},
        )
        self._record_success(
            tier=tier,
            request_id=request_id,
            estimate=post,
        )
        return CostAwareDispatchResult(
            text=text,
            tier=tier,
            model=post.model,
            provider=post.provider,
            input_tokens=post.input_tokens,
            output_tokens=post.output_tokens,
            cost_usd=post.cost_usd,
            is_priced=post.is_priced,
            request_id=request_id,
            decision="allowed",
            reason="ok",
        )

    def worker(self, tier: str) -> "TierWorker":
        """Return a per-tier callable bound to ``tier``."""
        return TierWorker(self, tier)

    # ------------------------------------------------------------------ internals

    async def _dispatch_passthrough(
        self,
        *,
        messages: list[Mapping[str, Any]],
        model: str,
        tier: str,
    ) -> CostAwareDispatchResult:
        """Call the inner adapter and translate the response without policy.

        Used when ``enabled=False`` to keep the audit entry but
        skip quota/budget gates. The cost is still computed
        (and recorded as ``decision="allowed"``) so a disabled
        middleware does not silently drop audit data.
        """
        request_id = str(self._id_factory())
        message_text = _serialize_messages(messages)
        text = await self._inner.chat(messages, model)
        output_tokens = TokenEstimator.from_message(text)
        pre = self._calculator.estimate_from_message(tier, message_text)
        post = self._calculator.estimate_from_response(
            tier=tier,
            message=message_text,
            response={"usage": {"input_tokens": pre.input_tokens, "output_tokens": output_tokens}},
        )
        self._record_success(tier=tier, request_id=request_id, estimate=post)
        return CostAwareDispatchResult(
            text=text,
            tier=tier,
            model=post.model,
            provider=post.provider,
            input_tokens=post.input_tokens,
            output_tokens=post.output_tokens,
            cost_usd=post.cost_usd,
            is_priced=post.is_priced,
            request_id=request_id,
            decision="allowed",
            reason="ok",
        )

    def _check_quota(
        self,
        *,
        tier: str,
        request_id: str,
        pre: CostEstimate,
    ) -> None:
        """Raise :class:`QuotaExceeded` if the dispatch would breach quota.

        Records a blocked audit entry on failure so the
        refusal is visible in the trail.
        """
        try:
            self._config.quota.check(tier, tokens=pre.input_tokens)
        except QuotaExceeded as exc:
            self._config.audit.record(
                tier=tier,
                model=pre.model,
                provider=pre.provider,
                input_tokens=pre.input_tokens,
                output_tokens=0,
                cost_usd=0.0,
                decision="blocked",
                reason="quota",
                request_id=request_id,
                is_priced=pre.is_priced,
                detail=exc.detail,
            )
            raise

    def _check_budget(
        self,
        *,
        tier: str,
        request_id: str,
        pre: CostEstimate,
    ) -> None:
        """Raise :class:`BudgetExceeded` if the dispatch would breach budget."""
        try:
            self._config.budget.check(tier, pre.cost_usd)
        except BudgetExceeded as exc:
            self._config.audit.record(
                tier=tier,
                model=pre.model,
                provider=pre.provider,
                input_tokens=pre.input_tokens,
                output_tokens=0,
                cost_usd=0.0,
                decision="blocked",
                reason="budget",
                request_id=request_id,
                is_priced=pre.is_priced,
                detail=exc.detail,
            )
            raise

    def _record_success(
        self,
        *,
        tier: str,
        request_id: str,
        estimate: CostEstimate,
    ) -> None:
        """Apply post-dispatch accounting: budget spend, quota usage, audit."""
        self._config.budget.record(tier, estimate.cost_usd)
        self._config.quota.record(tier, estimate.tokens)
        self._config.audit.record(
            tier=tier,
            model=estimate.model,
            provider=estimate.provider,
            input_tokens=estimate.input_tokens,
            output_tokens=estimate.output_tokens,
            cost_usd=estimate.cost_usd,
            decision="allowed",
            reason="ok",
            request_id=request_id,
            is_priced=estimate.is_priced,
        )


class TierWorker:
    """Async callable bound to a single tier; created by :meth:`CostAwareLlmAdapter.worker`.

    The :meth:`__call__` coroutine is what per-tier MCP tools
    ``await`` when the substrate is wired into an MCP server.
    Returning a :class:`TierWorker` (rather than a closure) keeps
    the tier name in the repr for debuggability and tests.
    """

    __slots__ = ("_router", "_tier")

    def __init__(self, router: CostAwareLlmAdapter, tier: str) -> None:
        self._router = router
        self._tier = tier

    async def __call__(self, messages: list[Mapping[str, Any]], model: str) -> str:
        """Dispatch ``messages`` to the bound tier and return the assistant text."""
        return await self._router.dispatch(messages, model, tier=self._tier)

    def __repr__(self) -> str:
        return f"TierWorker(tier={self._tier!r})"


__all__ = [
    "CostAwareDispatchResult",
    "CostAwareLlmAdapter",
    "CostMiddlewareConfig",
    "TierWorker",
]
