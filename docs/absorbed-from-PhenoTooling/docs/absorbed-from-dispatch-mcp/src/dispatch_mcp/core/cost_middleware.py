"""Cost-aware router middleware for dispatch_mcp.

This module composes a base :class:`OmniHttpAdapter` with the
cost calculator, budget enforcer, quota tracker, and audit
log. The middleware is the single integration point that the
MCP server composition layer (see :mod:`dispatch_mcp.server`)
wires up; it is intentionally the only place that knows the
exact wire shape of all four subsystems.

The middleware preserves the public surface the existing
server expects — :meth:`dispatch`, :meth:`health`,
:meth:`worker`, :meth:`cancel`, :meth:`close` — so the tool
handlers do not need to change. ``dispatch`` and ``health``
are coroutine methods (matching the ``await`` pattern in
:meth:`dispatch_mcp.server.dispatch_custom`); the inner
adapter remains synchronous and the middleware bridges the
two with non-blocking direct calls. Cost tracking is opt-in
via construction: an instance with the default subsystems
records every dispatch and refuses dispatches that would
exceed policy. A ``CostAwareRouter`` constructed with
``enabled=False`` is a thin pass-through.
"""

from __future__ import annotations

import inspect
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable

from dispatch_mcp.core.audit import AuditLog
from dispatch_mcp.core.budget import BudgetExceeded, BudgetTracker
from dispatch_mcp.core.cost import CostCalculator, CostEstimate
from dispatch_mcp.core.protocol import ProtocolInfo
from dispatch_mcp.core.quota import QuotaExceeded, QuotaTracker
from dispatch_mcp.core.tiers import DEFAULT_REGISTRY, TierRegistry
from dispatch_mcp.core.types import JobResult


@runtime_checkable
class _InnerRouter(Protocol):
    """Structural interface the middleware requires of the wrapped adapter.

    Matches the methods :class:`OmniHttpAdapter` exposes that
    the middleware delegates to. Defined as a Protocol so the
    middleware can be tested against a fake without coupling
    to a concrete adapter class.
    """

    def dispatch(
        self,
        message: str,
        tier: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...

    def health(self) -> dict[str, Any]:
        ...

    def cancel(self, request_id: str) -> bool:
        ...

    def close(self) -> None:
        ...

    def dispatch_message(
        self,
        *,
        tier: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> "Any":
        ...

    def ping(self) -> JobResult:
        ...

    def protocol_info(self) -> ProtocolInfo:
        ...


@dataclass(slots=True, frozen=True)
class CostMiddlewareConfig:
    """Configuration bundle for :class:`CostAwareRouter`.

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


class CostAwareRouter:
    """Wraps a base router with cost tracking, budgeting, and quota gates.

    On every :meth:`dispatch` call the middleware:

    1. Validates the tier against the cost registry.
    2. Estimates input tokens from the message text.
    3. Checks the quota gate (raises :class:`QuotaExceeded` if full).
    4. Estimates pre-dispatch cost and checks the budget gate.
    5. Calls the inner adapter (sync) and translates the response.
    6. Computes actual cost from the response usage block.
    7. Records quota usage, budget spend, and an audit entry.
    8. Returns a :class:`JobResult` enriched with cost metadata.

    Failed dispatches (upstream HTTP errors, timeouts) are
    propagated as exceptions; the middleware does not record
    spend for dispatches that did not happen, so a transient
    upstream failure does not consume the budget.
    """

    __slots__ = ("_inner", "_config", "_calculator", "_logger", "_id_factory")

    def __init__(
        self,
        inner: _InnerRouter,
        config: CostMiddlewareConfig | None = None,
        *,
        logger: logging.Logger | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._inner = inner
        self._config = config or CostMiddlewareConfig()
        self._calculator = CostCalculator(registry=self._config.registry)
        self._logger = logger or logging.getLogger("dispatch_mcp.cost")
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
    def inner(self) -> _InnerRouter:
        """Return the wrapped inner router."""
        return self._inner

    @property
    def client(self) -> Any:
        """Proxy to the inner adapter's ``client`` attribute.

        The :class:`dispatch_mcp.core.port.Router` protocol
        advertises a ``client`` attribute so that health checks
        and the cost middleware can share a transport handle.
        The middleware itself is transport-agnostic and merely
        forwards the lookup.
        """
        return getattr(self._inner, "client", None)

    # ---------------------------------------------------------------- port methods

    async def health(self) -> JobResult:
        """Delegate to the inner adapter and translate the response.

        The inner adapter returns a raw dict; this method
        coerces the dict into a :class:`JobResult` so the
        caller can rely on the unified response shape.
        """
        raw = self._inner.health()
        return self._dict_to_job_result(raw, tier="*")

    def cancel(self, request_id: str) -> bool:
        """Delegate to the inner adapter."""
        return self._inner.cancel(request_id)

    def close(self) -> None:
        """Release the inner adapter's resources and flush the audit log.

        Synchronous so the SIGTERM/SIGINT handler in
        :mod:`dispatch_mcp.server` can invoke it directly
        without spinning up an event loop.
        """
        try:
            self._inner.close()
        finally:
            self._config.audit.close()

    async def aclose(self) -> None:
        """Async counterpart to :meth:`close`.

        The :class:`dispatch_mcp.core.port.Router` protocol
        declares ``close`` as a coroutine; the middleware's
        synchronous ``close`` is preserved for backward
        compatibility with the existing test suite. New code
        (and the ``main()`` signal handler in ``server.py``)
        should prefer the async coroutine.
        """
        self.close()

    async def ping(self) -> JobResult:
        """Forward the liveness probe to the inner adapter.

        The middleware never raises; if the inner adapter has
        no ``ping`` method we synthesize an ``alive`` result
        so the MCP ``ping`` tool always returns a uniform
        shape. If the inner adapter exposes an async ``ping``
        coroutine, we await it; sync returns are forwarded as-is.
        """
        inner_ping = getattr(self._inner, "ping", None)
        if inner_ping is None:
            return JobResult(status="alive", message="dispatch-mcp")
        result = inner_ping()
        if inspect.isawaitable(result):
            return await result  # type: ignore[no-any-return]
        return result  # type: ignore[no-any-return]

    def protocol_info(self) -> ProtocolInfo:
        """Forward the protocol discovery payload to the inner adapter.

        If the inner adapter is missing the protocol endpoint
        (e.g. a legacy fake in a unit test), we return a
        minimal :class:`ProtocolInfo` with default capabilities
        so the discovery tool never crashes.
        """
        info = getattr(self._inner, "protocol_info", None)
        if info is None:
            from dispatch_mcp.core.protocol import (
                DEFAULT_NEGOTIATED_VERSION,
                ServerCapabilities,
                ServerInfo,
            )

            return ProtocolInfo(
                serverVersion="0.0.0+unknown",
                supportedVersions=[DEFAULT_NEGOTIATED_VERSION],
                defaultVersion=DEFAULT_NEGOTIATED_VERSION,
                negotiatedVersion=DEFAULT_NEGOTIATED_VERSION,
                capabilities=ServerCapabilities(),
                serverInfo=ServerInfo(name="dispatch-mcp", version="0.0.0+unknown"),
            )
        return info()

    async def dispatch_message(
        self,
        *,
        tier: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> JobResult:
        """Dispatch ``message`` to ``tier`` with full cost-tracking gates.

        This is the :class:`dispatch_mcp.core.port.Router` protocol's
        primary entrypoint. Returns a :class:`JobResult`. Raises
        :class:`QuotaExceeded` or :class:`BudgetExceeded` when policy
        refuses the dispatch; both inherit from :class:`RuntimeError`
        and carry a structured ``detail`` payload for error reporting.
        """
        if not self._config.enabled:
            return self._dispatch_passthrough(tier=tier, message=message, payload=payload)

        request_id = str(self._id_factory())
        # Pre-dispatch token estimate for the quota gate. The
        # output token count defaults to the calculator's
        # conservative fallback; the post-dispatch accounting
        # refines it with the actual usage block.
        pre_estimate = self._calculator.estimate_from_message(tier, message)
        self._check_quota(tier=tier, request_id=request_id, pre=pre_estimate)
        self._check_budget(tier=tier, request_id=request_id, pre=pre_estimate)

        try:
            raw_response = self._inner.dispatch(message, tier, payload)
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

        # Post-dispatch accounting. Prefer the actual usage
        # block from the upstream response; fall back to the
        # pre-dispatch estimate when the response did not
        # report usage.
        post = self._calculator.estimate_from_response(tier, message, raw_response)
        if post.cost_usd <= 0 and not pre_estimate.is_priced:
            # Preserve the priced/known-model signal from the
            # pre-estimate when the post estimate lost it.
            post = pre_estimate
        self._record_success(
            tier=tier,
            request_id=request_id,
            estimate=post,
            response=raw_response,
        )
        return self._to_job_result(
            tier=tier,
            estimate=post,
            response=raw_response,
            request_id=request_id,
        )

    async def dispatch(
        self,
        *,
        tier: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> JobResult:
        """Alias for :meth:`dispatch_message` kept for callers that
        pre-date the protocol rename.

        Identical behavior; the canonical name is ``dispatch_message``
        to match the :class:`Router` protocol.
        """
        return await self.dispatch_message(
            tier=tier, message=message, payload=payload
        )

    def worker(self, tier: str) -> "TierWorker":
        """Return a per-tier callable bound to ``tier``."""
        return TierWorker(self, tier)

    # ------------------------------------------------------------------ internals

    def _dispatch_passthrough(
        self,
        *,
        tier: str,
        message: str,
        payload: dict[str, Any] | None,
    ) -> JobResult:
        """Call the inner adapter and translate the response without policy."""
        raw = self._inner.dispatch(message, tier, payload)
        return self._dict_to_job_result(raw, tier=tier)

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
        response: dict[str, Any],
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

    def _to_job_result(
        self,
        *,
        tier: str,
        estimate: CostEstimate,
        response: dict[str, Any],
        request_id: str,
    ) -> JobResult:
        """Build a :class:`JobResult` from the upstream response + cost data.

        Upstream response fields take precedence for the
        legacy ``ok``/``message``/``status``/``error`` fields;
        cost-tracking fields are layered on top. ``ok`` is
        coerced to a boolean — ``None`` upstream values become
        ``True`` (default success) so legacy clients continue
        to see a truthy value.
        """
        return self._dict_to_job_result(
            response,
            tier=tier,
            cost_usd=estimate.cost_usd,
            input_tokens=estimate.input_tokens,
            output_tokens=estimate.output_tokens,
            model=estimate.model,
            request_id=request_id,
        )

    def _dict_to_job_result(
        self,
        raw: Any,
        *,
        tier: str,
        cost_usd: float | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        model: str | None = None,
        request_id: str | None = None,
    ) -> JobResult:
        """Translate a raw upstream dict into a :class:`JobResult`."""
        if not isinstance(raw, dict):
            return JobResult(
                ok=False,
                tier=tier,
                error="invalid dispatch response",
                cost_usd=cost_usd,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=model,
                request_id=request_id,
            )
        ok_value = raw.get("ok")
        if isinstance(ok_value, bool):
            ok: bool | None = ok_value
        elif "ok" in raw:
            ok = None
        else:
            ok = True
        return JobResult(
            ok=ok,
            tier=str(raw.get("tier") or tier),
            message=str(raw["message"]) if isinstance(raw.get("message"), str) else None,
            status=str(raw["status"]) if isinstance(raw.get("status"), str) else None,
            error=str(raw["error"]) if isinstance(raw.get("error"), str) else None,
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            request_id=request_id,
        )


class TierWorker:
    """Async callable bound to a single tier; created by :meth:`CostAwareRouter.worker`.

    The :meth:`__call__` coroutine is what the per-tier MCP
    tools ``await`` in :mod:`dispatch_mcp.server`. Returning
    a :class:`TierWorker` (rather than a closure) keeps the
    tier name in the repr for debuggability and tests.
    """

    __slots__ = ("_router", "_tier")

    def __init__(self, router: CostAwareRouter, tier: str) -> None:
        self._router = router
        self._tier = tier

    async def __call__(self, message: str) -> JobResult:
        """Dispatch ``message`` to the bound tier."""
        return await self._router.dispatch(tier=self._tier, message=message)

    def __repr__(self) -> str:
        return f"TierWorker(tier={self._tier!r})"


__all__ = ["CostAwareRouter", "CostMiddlewareConfig"]
