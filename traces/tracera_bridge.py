"""tracera_bridge — dual-write bridge for trace events.

The pheno `traces/` pipeline emits events in two layers today:

1. A `TraceCollector` (see `traces/ingest.py`) that aggregates events
   from multiple harness log sources and writes them to a JSONL sink
   via `collect_all()`.
2. A `TraceraAdapter` (see `pheno/trace_store/tracera.py`) that mirrors
   events to the Grapheon/Tracera persistent trace repository over
   HTTP.

This module provides a `TraceraBridge` that sits between the two and
dual-writes events to both backends. Configuration is driven by
`config/pheno_runtime.yaml` (`trace_bridges.dual_write` + `include_kinds`)
via `pheno.runtime_config.load_config()`.

Design notes:

- Fail-soft: if the Tracera backend is unreachable, the event is still
  written to the JSONL sink and an error is logged. The bridge never
  raises to the caller.
- Hermetic-test friendly: callers may inject a `TraceStoreAdapter`
  (real or mock) and a JSONL path explicitly. The default constructor
  reads runtime config; tests can bypass the config layer.
- `include_kinds` filter: when the list is non-empty, only events
  whose `kind` is in the list are mirrored to Tracera. JSONL always
  receives every event (it's the on-disk source of truth).
- `install_bridge(trace_collector)` wires the bridge into an existing
  `TraceCollector` by attaching `collector.bridge` (and stashing the
  bridge on the collector's instance for later access). It does NOT
  monkey-patch `collect_all()` — downstream callers can opt-in to
  routing events through the bridge (e.g.
  `for ev in collector.all_sources(): bridge.emit(ev)`).

Refs:
- v0.12 WBS-PERT-100 task 16 (TraceStoreAdapter → Tracera dual-write).
- `pheno/trace_store/protocols.py` (TraceEvent schema).
- `pheno/trace_store/tracera.py` (TraceraAdapter).
- `pheno/runtime_config.py` (trace_bridges config).
"""

from __future__ import annotations

import json
import logging
import os
import random
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pheno.runtime_config import (
    RuntimeConfig,
    TraceBridgesConfig,
    active_environment,
    load_config,
)
from pheno.trace_store import TraceEvent
from pheno.trace_store.protocols import TraceStoreAdapter

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


# A hook that callers can wire in to inspect every emitted event
# (e.g. for tests asserting that both backends received the event).
EmitHook = Any  # Callable[[TraceEvent, str], None]; kept loose so
# tests can stash inspectable state without a strict signature.
SINK_JSONL = "jsonl"
SINK_TRACERA = "tracera"


@runtime_checkable
class _Bridgeable(Protocol):
    """Structural protocol for the collector instance we attach to.

    The bridge only needs to read/write attributes on the collector;
    declaring a Protocol keeps the import-site lax without forcing
    `from traces.ingest import TraceCollector` at module import time.
    """

    bridge: TraceraBridge | None


class TraceraBridge:
    """Dual-write bridge: JSONL sink + optional TraceraAdapter mirror.

    Args:
        adapter: optional TraceStoreAdapter (real TraceraAdapter or
            mock). When None and `dual_write=True`, the bridge
            constructs a fresh `TraceraAdapter` from runtime config.
        jsonl_path: path to the JSONL sink. Defaults to a sibling of
            the trace_store config (see `_default_jsonl_path`).
        dual_write: when True, mirror every event to the Tracera
            adapter (subject to `include_kinds`). When False, the
            adapter is ignored and only JSONL receives events.
        include_kinds: optional list of event kinds to mirror
            (e.g. `["wandb_step", "eval_cell"]`). Empty list = all
            kinds. JSONL always receives every event regardless.
        append: if True, append to the JSONL file; if False, truncate
            on open. Default True (matches the existing TraceCollector
            semantics).
        config: optional explicit RuntimeConfig. When None, the
            constructor reads `pheno.runtime_config.load_config()`.
        flush_on_emit: when True, call `adapter.flush()` after each
            `append_event`. Default False — the existing TraceraAdapter
            writes synchronously, so per-event flush is harmless but
            doing it explicitly is useful for buffered/async adapters
            in tests that record flush calls.

    The bridge is intentionally lightweight: it does not buffer
    events between calls. When `flush_on_emit` is enabled, callers
    can rely on synchronous Tracera persistence after each `emit()`.
    """

    def __init__(
        self,
        *,
        adapter: TraceStoreAdapter | None = None,
        jsonl_path: Path | str | None = None,
        dual_write: bool = True,
        include_kinds: list[str] | None = None,
        append: bool = True,
        config: RuntimeConfig | None = None,
        flush_on_emit: bool = False,
        sample_rate: float | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._config = config
        self._explicit_dual_write = dual_write
        self._explicit_include_kinds = include_kinds
        self._flush_on_emit = flush_on_emit
        self._explicit_sample_rate = sample_rate
        self._rng = rng if rng is not None else random.Random()
        self._jsonl_path = Path(jsonl_path) if jsonl_path is not None else None
        self._append = append
        self._adapter = adapter
        # Bookkeeping for tests / introspection.
        self.emitted_total: int = 0
        self.emitted_jsonl: int = 0
        self.emitted_tracera: int = 0
        self.skipped_kind: int = 0
        self.skipped_sample: int = 0
        self.tracera_errors: int = 0
        self._hooks: list[Any] = []

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def _resolve_jsonl_path(self) -> Path:
        """Resolve the JSONL sink path against the runtime config (if any)."""
        if self._jsonl_path is not None:
            return self._jsonl_path
        # Lazy import to avoid pulling `pheno.paths` at module import.
        from pheno.paths import TRACES_DIR

        return TRACES_DIR / "tracera_bridge.jsonl"

    def _resolve_bridge_config(self) -> TraceBridgesConfig:
        """Read the `trace_bridges` block from the runtime config."""
        if self._config is None:
            self._config = load_config()
        return self._config.trace_bridges

    def _dual_write(self) -> bool:
        """Effective dual_write flag (config wins if constructor wasn't explicit)."""
        if self._explicit_dual_write is not None:
            return self._explicit_dual_write
        return self._resolve_bridge_config().dual_write

    def _include_kinds(self) -> list[str]:
        """Effective include_kinds list."""
        if self._explicit_include_kinds is not None:
            return self._explicit_include_kinds
        return self._resolve_bridge_config().include_kinds

    def _sample_rate(self) -> float:
        """Effective sample rate (clamped to [0.0, 1.0]).

        Resolution order:
        1. Explicit ``sample_rate=`` constructor arg (when not None).
        2. ``TRACERA_DUAL_WRITE_SAMPLE_RATE`` env var.
        3. ``trace_bridges.dual_write_sample_rate`` from runtime config.

        The result is clamped to ``[0.0, 1.0]``; ``1.0`` disables sampling
        and mirrors every event; ``0.0`` mirrors nothing (events still
        land in the JSONL sink).
        """
        if self._explicit_sample_rate is not None:
            return max(0.0, min(1.0, float(self._explicit_sample_rate)))
        env_val = os.environ.get("TRACERA_DUAL_WRITE_SAMPLE_RATE")
        if env_val is not None:
            try:
                return max(0.0, min(1.0, float(env_val)))
            except ValueError:
                pass
        cfg = self._resolve_bridge_config()
        return max(0.0, min(1.0, float(cfg.dual_write_sample_rate)))

    def active_cohort(self) -> str:
        """Return the cohort policy for the active environment.

        Possible values: "on", "off", or any string the operator has
        stored in ``trace_bridges.cohort_policies[<env>]``. Default is
        "off" when the env is unknown.
        """
        cfg = self._resolve_bridge_config()
        return cfg.cohort_policies.get(cfg.active_environment, "off")

    def _resolve_adapter(self) -> TraceStoreAdapter | None:
        """Return the TraceraAdapter, constructing one from config if needed."""
        if self._adapter is not None:
            return self._adapter
        if not self._dual_write():
            return None
        # Lazy import so tests can inject mocks without the network
        # adapter ever being constructed.
        from pheno.trace_store import TraceraAdapter

        cfg = self._config or load_config()
        return TraceraAdapter(
            host=cfg.tracera.host,
            port=cfg.tracera.port,
            base_url=cfg.tracera.base_url,
            token=cfg.tracera.api_token,
            timeout=float(cfg.tracera.timeout_s),
            batch_size=cfg.tracera.batch_size,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def emit(self, event: TraceEvent) -> None:
        """Emit an event to the JSONL sink and (optionally) Tracera.

        Behavior:
        - Always writes the serialized event to the JSONL sink.
        - When `dual_write=True` and the adapter is reachable, mirrors
          the event to Tracera via `append_event`.
        - When `include_kinds` is non-empty and the event's kind is not
          in the list, the Tracera side is skipped (JSONL still gets it).
        - Tracera errors are logged + counted; they never propagate to
          the caller (fail-soft).
        - Registered hooks are invoked AFTER each backend write so
          tests can assert "did the JSONL side see it?" / "did the
          Tracera side see it?" separately.
        """
        self.emitted_total += 1
        # --- JSONL sink (always) ---
        path = self._resolve_jsonl_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event.to_dict(), ensure_ascii=False)
        with path.open("a" if self._append else "w", encoding="utf-8") as fp:
            fp.write(line + "\n")
        self.emitted_jsonl += 1
        for hook in self._hooks:
            try:
                hook(event, SINK_JSONL)
            except Exception:  # pragma: no cover - hook should not crash
                logger.exception("tracera_bridge hook failed on JSONL emit")

        # --- Tracera mirror (optional) ---
        if not self._dual_write():
            return
        kinds = self._include_kinds()
        if kinds and event.kind not in kinds:
            self.skipped_kind += 1
            for hook in self._hooks:
                try:
                    hook(event, SINK_TRACERA + ":skipped")
                except Exception:  # pragma: no cover
                    logger.exception("tracera_bridge hook failed on skip")
            return

        # --- Sample-rate gate (cohort rollout) ---
        rate = self._sample_rate()
        if rate < 1.0 and self._rng.random() > rate:
            self.skipped_sample += 1
            for hook in self._hooks:
                try:
                    hook(event, SINK_TRACERA + ":sampled_out")
                except Exception:  # pragma: no cover
                    logger.exception("tracera_bridge hook failed on sample skip")
            return

        adapter = self._resolve_adapter()
        if adapter is None:
            return

        try:
            adapter.append_event(event)
            self.emitted_tracera += 1
            if self._flush_on_emit:
                adapter.flush()
            for hook in self._hooks:
                try:
                    hook(event, SINK_TRACERA)
                except Exception:  # pragma: no cover
                    logger.exception("tracera_bridge hook failed on Tracera emit")
        except Exception as exc:  # noqa: BLE001 - fail-soft
            self.tracera_errors += 1
            logger.error(
                "tracera_bridge: Tracera append_event failed for kind=%s id=%s: %s",
                event.kind,
                event.id,
                exc,
            )
            for hook in self._hooks:
                try:
                    hook(event, SINK_TRACERA + ":error")
                except Exception:  # pragma: no cover
                    logger.exception("tracera_bridge hook failed on error")

    def flush(self) -> None:
        """Force any buffered Tracera writes to be persisted.

        Best-effort: errors are logged and swallowed. No-op for
        adapters that don't buffer (the default TraceraAdapter writes
        synchronously; this hook is a safety net for buffered/async
        adapters wired in by callers).
        """
        adapter = self._resolve_adapter()
        if adapter is None:
            return
        try:
            adapter.flush()
        except Exception as exc:  # noqa: BLE001
            logger.error("tracera_bridge: Tracera flush failed: %s", exc)

    def add_hook(self, hook: Any) -> None:
        """Register a hook invoked after each backend write.

        Hook signature: ``hook(event: TraceEvent, sink: str) -> None``
        where ``sink`` is one of ``"jsonl"``, ``"tracera"``,
        ``"tracera:skipped"``, ``"tracera:error"``. Used by tests to
        inspect which backend received each event.
        """
        self._hooks.append(hook)

    # ------------------------------------------------------------------
    # Introspection (for tests + diagnostics)
    # ------------------------------------------------------------------

    @property
    def adapter(self) -> TraceStoreAdapter | None:
        """Return the active Tracera adapter (or None if not yet resolved)."""
        return self._adapter

    @property
    def jsonl_path(self) -> Path | None:
        """Return the configured JSONL sink path (or None if not yet resolved)."""
        return self._jsonl_path


def install_bridge(
    trace_collector: Any,
    *,
    bridge: TraceraBridge | None = None,
    jsonl_path: Path | str | None = None,
    config: RuntimeConfig | None = None,
) -> TraceraBridge:
    """Wire a TraceraBridge into an existing TraceCollector.

    The bridge is attached as ``collector.bridge`` so downstream
    callers can route events through it:

    .. code-block:: python

        install_bridge(collector)
        for ev in collector.all_sources():
            collector.bridge.emit(  # type: ignore[union-attr]
                TraceEvent.from_dict(ev.to_dict())
            )

    This function does NOT modify the collector's `collect_all()`
    method. It only adds a `bridge` attribute. The intent is to be
    non-invasive: existing callers of `collect_all()` continue to
    work unchanged.

    Args:
        trace_collector: any object that supports attribute
            assignment (the existing `TraceCollector` works).
        bridge: explicit bridge to attach. When None, a fresh
            bridge is constructed from the runtime config.
        jsonl_path: optional override for the JSONL sink path.
        config: optional explicit RuntimeConfig; bypasses
            `load_config()` for hermetic tests.

    Returns:
        The attached TraceraBridge instance.
    """
    if bridge is None:
        bridge = TraceraBridge(
            jsonl_path=jsonl_path,
            config=config,
        )
    elif jsonl_path is not None:
        # If callers pre-build a bridge AND pass a JSONL path, honor
        # the path (prefer explicit args over the bridge's own).
        bridge._jsonl_path = Path(jsonl_path)
    trace_collector.bridge = bridge
    return bridge


__all__ = [
    "SINK_JSONL",
    "SINK_TRACERA",
    "TraceraBridge",
    "install_bridge",
    "active_environment",
]
