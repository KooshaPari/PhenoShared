"""Public entrypoint for the MLX stub model used in tests and smoke runs.

The runner keeps the concrete implementation at
``bench.runner.model_adapter_mock.MLXStubAdapter``; this module exposes a
stable, top-level import path so test code doesn't need to know about the
runner internals::

    from bench.runner.mlx_stub import MLXStubAdapter, StubModel, stub_verify_task

What lives here:

* ``MLXStubAdapter`` — re-exported from the runner.
* ``StubModel`` — a :class:`typing.Protocol` that ``MLXStubAdapter``
  satisfies structurally. Tests can type-hint against ``StubModel`` without
  importing the concrete adapter class.
* ``stub_verify_task`` — a ``RunConfig.verify_task`` callback that returns
  ``True`` for any non-empty, non-error completion. Use this in synthetic
  / stub suites whose individual tasks don't carry a known ``expected``
  value (see ``bench.runner.executor_verify.verify_task`` for the default
  strict behaviour).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol

from bench.runner.model_adapter_mock import MLXStubAdapter

if TYPE_CHECKING:
    from bench.runner.executor import TaskDescriptor

__all__ = ["MLXStubAdapter", "StubModel", "stub_verify_task"]


class StubModel(Protocol):
    """Typing protocol for the MLX stub model contract.

    :class:`MLXStubAdapter` satisfies this protocol structurally; tests that
    only care about the stub contract can type-hint against ``StubModel``
    rather than the concrete adapter class.
    """

    name: str

    def complete(
        self,
        prompt: str,
        *,
        temperature: float = ...,
        max_tokens: int = ...,
        system: str | None = ...,
        timeout_s: float = ...,
        extra: Mapping[str, object] | None = ...,
    ) -> object: ...


def stub_verify_task(
    td: TaskDescriptor,
    completion: str,
    adapter: object,
) -> bool:
    """Verify callback for stub / synthetic suites.

    Returns ``True`` for any non-empty completion that is not an error
    sentinel. Use as ``RunConfig(verify_task=stub_verify_task)`` when
    running synthetic suites whose individual tasks don't carry a known
    ``expected`` value.

    The default ``bench.runner.executor_verify.verify_task`` is
    intentionally strict (no ``expected`` => FAIL, per its docstring) so
    that synthetic / stub tasks cannot inflate pass rates. Tests that
    want the lenient stub semantics should opt in explicitly with this
    callback.
    """
    return bool(completion) and not completion.startswith("[error]")
