"""Low-overhead recorder for an IntentGraph."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .dag import GraphEdge, GraphNode, IntentGraph


class IntentGraphRecorder:
    def __init__(
        self, run_id: str, suite: str, *, metadata: dict[str, Any] | None = None
    ):
        self.graph = IntentGraph(run_id=run_id, suite=suite, metadata=metadata or {})
        self._started_ns: dict[str, int] = {}

    def start_node(
        self,
        kind: str,
        name: str,
        *,
        parent: str | None = None,
        attributes: dict[str, Any] | None = None,
        node_id: str | None = None,
    ) -> str:
        node_id = node_id or f"{kind}_{uuid.uuid4().hex[:12]}"
        self.graph.nodes.append(
            GraphNode(
                id=node_id,
                kind=kind,
                name=name,
                status="running",
                started_at=datetime.now(UTC).isoformat(),
                attributes=attributes or {},
            )
        )
        self._started_ns[node_id] = time.perf_counter_ns()
        if parent:
            self.graph.edges.append(
                GraphEdge(source=parent, target=node_id, kind="contains")
            )
        return node_id

    def finish_node(
        self, node_id: str, *, status: str, attributes: dict[str, Any] | None = None
    ) -> None:
        index = next(
            (i for i, node in enumerate(self.graph.nodes) if node.id == node_id), None
        )
        if index is None:
            raise KeyError(f"unknown graph node: {node_id}")
        original = self.graph.nodes[index]
        started_ns = self._started_ns.pop(node_id, None)
        duration_ms = (
            (time.perf_counter_ns() - started_ns) / 1_000_000
            if started_ns is not None
            else None
        )
        merged = dict(original.attributes)
        merged.update(attributes or {})
        self.graph.nodes[index] = GraphNode(
            id=original.id,
            kind=original.kind,
            name=original.name,
            status=status,
            started_at=original.started_at,
            finished_at=datetime.now(UTC).isoformat(),
            duration_ms=round(duration_ms, 3) if duration_ms is not None else None,
            attributes=merged,
        )

    def add_edge(self, source: str, target: str, kind: str) -> None:
        self.graph.edges.append(GraphEdge(source=source, target=target, kind=kind))

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.graph.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        return path
