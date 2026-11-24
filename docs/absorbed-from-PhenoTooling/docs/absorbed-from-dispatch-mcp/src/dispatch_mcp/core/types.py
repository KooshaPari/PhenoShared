from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class JobResult:
    """Serialized result returned by dispatch-mcp tools.

    The original ``ok``/``tier``/``message``/``status``/``error``
    fields are preserved for backward compatibility with
    existing MCP clients. The cost-tracking fields
    (``cost_usd``, ``input_tokens``, ``output_tokens``,
    ``model``, ``request_id``) are populated by the
    cost-aware middleware when cost tracking is enabled; they
    are ``None`` (and therefore omitted from
    :meth:`to_dict`) when the dispatch predates the cost
    middleware or the tracking subsystem is disabled.
    """

    ok: bool | None = None
    tier: str | None = None
    message: str | None = None
    status: str | None = None
    error: str | None = None
    # Cost-tracking fields populated by core.cost_middleware.
    cost_usd: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str | None = None
    request_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the public MCP tool response shape.

        ``None``-valued fields are omitted so the response
        shape stays minimal for the legacy code path. Numeric
        fields are rounded to a fixed precision to keep tool
        outputs stable for log diffing and snapshot tests.
        """
        result: dict[str, Any] = {}
        for key, value in (
            ("ok", self.ok),
            ("tier", self.tier),
            ("message", self.message),
            ("status", self.status),
            ("error", self.error),
            ("cost_usd", round(self.cost_usd, 8) if self.cost_usd is not None else None),
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
            ("model", self.model),
            ("request_id", self.request_id),
        ):
            if value is not None:
                result[key] = value
        return result
