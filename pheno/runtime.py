"""pheno.runtime — orchestrator for the Tracera dual-write integration.

This module ties together the three runtime pieces:

  1. `pheno.runtime_config.load_config()` — typed runtime config view
     (reads `config/pheno_runtime.yaml` with env var overrides).
  2. `pheno.trace_store.tracera.TraceraAdapter` — the HTTP client for
     the Grapheon/Tracera persistent trace repository.
  3. `traces.tracera_bridge.TraceraBridge` + `install_bridge()` — the
     dual-write bridge that mirrors TraceEvent emissions to both the
     JSONL sink (always) and the Tracera adapter (when enabled).

The orchestrator's job is to wire these together behind a single
`start()` entry point so callers don't have to import + instantiate
three layers in the right order. It is **feature-flagged** —
nothing happens unless `runtime_config.trace_bridges.dual_write` is
True AND `runtime_config.tracera.enabled` is True.

Typical usage:

    from pheno.runtime import start, stop
    state = start()                       # idempotent; no-op when disabled
    try:
        ... do work, emit traces ...
    finally:
        stop(state)

When `dual_write` is disabled (the default), `start()` returns a
disabled-state sentinel and `stop()` is a no-op — zero overhead for
callers that don't opt in.

v0.12 WBS-PERT-100 task 17 (Phase 1 — Tracera dual-write integration).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pheno.runtime_config import RuntimeConfig, load_config
from pheno.trace_store import TraceraAdapter
from pheno.trace_store.protocols import TraceStoreAdapter, TraceStoreError

if TYPE_CHECKING:
    from traces.ingest import TraceCollector
    from traces.tracera_bridge import TraceraBridge


logger = logging.getLogger(__name__)


# Module-level state for the most recent start() call. Lets stop()
# tear it down without callers needing to thread the state object
# through their code. Tests should prefer the explicit state-arg form.
_LAST_STATE: RuntimeState | None = None


@dataclass
class RuntimeState:
    """Snapshot of the orchestrator's runtime wiring.

    Returned by `start()` so callers can pass it to `stop()` later.
    `disabled=True` means the orchestrator is a no-op (the feature
    flag was off); no resources need teardown.
    """

    config: RuntimeConfig
    adapter: TraceStoreAdapter | None
    bridge: TraceraBridge | None
    collector: TraceCollector | None
    disabled: bool
    health_ok: bool
    error: str | None = field(default=None)

    @property
    def is_dual_writing(self) -> bool:
        """True iff the bridge is actively mirroring to Tracera."""
        return (
            not self.disabled and self.bridge is not None and self.adapter is not None
        )

    def summary(self) -> dict[str, Any]:
        """Return a dict suitable for logging or cockpit dashboards."""
        return {
            "disabled": self.disabled,
            "dual_write": self.config.trace_bridges.dual_write,
            "tracera_enabled": self.config.tracera.enabled,
            "adapter_present": self.adapter is not None,
            "bridge_present": self.bridge is not None,
            "collector_present": self.collector is not None,
            "health_ok": self.health_ok,
            "error": self.error,
            "tracera_endpoint": (
                self.config.tracera.base_url
                or f"http://{self.config.tracera.host}:{self.config.tracera.port}"
            ),
        }


def start(
    config: RuntimeConfig | None = None,
    *,
    collector: TraceCollector | None = None,
    override_dual_write: bool | None = None,
) -> RuntimeState:
    """Wire the dual-write bridge end-to-end.

    Args:
        config: optional explicit `RuntimeConfig`; defaults to
            `load_config()` (which reads `config/pheno_runtime.yaml`).
        collector: optional existing `TraceCollector` to attach the
            bridge to. When None, the orchestrator does not create a
            collector (callers can do that themselves and call
            `install_bridge(collector)` later).
        override_dual_write: optional override for the runtime
            `trace_bridges.dual_write` flag. Useful for tests / CLI
            `--dual-write` flags.

    Returns:
        A `RuntimeState` describing what was wired (or why nothing
        was wired — see `state.disabled`).

    The function is idempotent: repeated calls return equivalent
    states but do NOT recreate adapters. To force re-creation, call
    `stop(state)` first or pass a fresh `config`.
    """
    global _LAST_STATE
    cfg = config or load_config()
    dual_write = (
        override_dual_write
        if override_dual_write is not None
        else cfg.trace_bridges.dual_write
    )

    # Feature-flagged: when dual_write is off, return a disabled state.
    if not dual_write or not cfg.tracera.enabled:
        state = RuntimeState(
            config=cfg,
            adapter=None,
            bridge=None,
            collector=collector,
            disabled=True,
            health_ok=True,
        )
        _LAST_STATE = state
        logger.info(
            "pheno.runtime.start: dual_write disabled "
            "(dual_write=%s, tracera.enabled=%s); no bridge wired",
            dual_write,
            cfg.tracera.enabled,
        )
        return state

    # Build adapter.
    adapter = _build_adapter(cfg)
    health_ok = True
    error: str | None = None
    if cfg.tracera.health_check_on_init:
        try:
            health = adapter.health()
            health_ok = health.get("status") == "ok"
            if not health_ok:
                error = "tracera /healthz returned " + str(health.get("status"))
        except TraceStoreError as exc:
            health_ok = False
            error = str(exc)
            logger.warning(
                "pheno.runtime.start: tracera health check failed (%s); "
                "bridge will be wired but flush() errors will be logged.",
                exc,
            )

    # Build bridge. TraceraBridge reads timeout/batch_size from the
    # TraceraAdapter (passed in) and the runtime config's tracera block
    # for flush intervals. Pass the adapter through explicitly so the
    # bridge doesn't need to re-construct it.
    from traces.tracera_bridge import TraceraBridge, install_bridge

    bridge = TraceraBridge(
        adapter=adapter,
        dual_write=True,
        include_kinds=list(cfg.trace_bridges.include_kinds),
        config=cfg,
    )

    # Attach bridge to collector if provided.
    if collector is not None:
        install_bridge(collector, bridge)  # type: ignore[misc]

    state = RuntimeState(
        config=cfg,
        adapter=adapter,
        bridge=bridge,
        collector=collector,
        disabled=False,
        health_ok=health_ok,
        error=error,
    )
    _LAST_STATE = state
    logger.info(
        "pheno.runtime.start: bridge wired (dual_write=%s, health_ok=%s, "
        "endpoint=%s, include_kinds=%s)",
        dual_write,
        health_ok,
        state.summary().get("tracera_endpoint"),
        cfg.trace_bridges.include_kinds,
    )
    return state


def stop(state: RuntimeState | None = None) -> None:
    """Tear down the bridge (drain buffer + flush).

    No-op when `state.disabled` is True. When the bridge has buffered
    events, attempts a final flush; errors are logged but not raised.
    """
    global _LAST_STATE
    target = state or _LAST_STATE
    if target is None or target.disabled:
        return
    if target.bridge is not None:
        try:
            target.bridge.flush()
            logger.info("pheno.runtime.stop: bridge flushed + detached")
        except TraceStoreError as exc:
            logger.warning(
                "pheno.runtime.stop: bridge flush failed (%s); "
                "%d events remain in buffer",
                exc,
                getattr(target.bridge, "buffer_size", lambda: -1)(),
            )
    # Detach bridge from collector if we attached one.
    if target.collector is not None:
        target.collector.bridge = None
    _LAST_STATE = None


def current_state() -> RuntimeState | None:
    """Return the most recent state without tearing it down.

    Useful for tests / health checks that need to introspect the
    orchestrator without stopping it.
    """
    return _LAST_STATE


def _build_adapter(cfg: RuntimeConfig) -> TraceraAdapter:
    """Construct a TraceraAdapter from the typed runtime config."""
    return TraceraAdapter(
        base_url=cfg.tracera.base_url,
        host=cfg.tracera.host,
        port=cfg.tracera.port,
        token=cfg.tracera.api_token,
        timeout=float(cfg.tracera.timeout_s),
        batch_size=int(cfg.tracera.batch_size),
    )


@contextmanager  # type: ignore[misc, unused-ignore]
def dual_write(
    config: RuntimeConfig | None = None,
    *,
    collector: TraceCollector | None = None,
    override_dual_write: bool | None = None,
) -> Iterator[RuntimeState]:
    """Context manager that wraps start()/stop() with guaranteed cleanup.

    Typical usage in fixture scripts:

        from pheno.runtime import dual_write

        with dual_write(collector=collector) as state:
            ... emit trace events ...
        # bridge flushed + detached on exit, even on exception

    The context manager exits cleanly on exceptions: stop() runs in a
    finally block so a partial dual-write never leaves events buffered.
    `stop()` itself is fail-soft (logs but does not raise), so the
    exception (if any) from the `with` block propagates unchanged.
    """
    state = start(
        config=config,
        collector=collector,
        override_dual_write=override_dual_write,
    )
    try:
        yield state
    finally:
        stop(state)
