"""Typed, serializable DAG schema for passive run recording."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

NODE_KINDS = {
    "run",
    "model_call",
    "tool_call",
    "verifier",
    "artifact",
    "decision",
    "subagent",
}
EDGE_KINDS = {"contains", "depends_on", "produces", "verifies", "follows", "delegates"}


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: str
    name: str
    status: str = "pending"
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in NODE_KINDS:
            raise ValueError(f"unsupported node kind: {self.kind}")
        if not self.id or not self.name:
            raise ValueError("graph nodes require non-empty id and name")


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    kind: str

    def __post_init__(self) -> None:
        if self.kind not in EDGE_KINDS:
            raise ValueError(f"unsupported edge kind: {self.kind}")
        if self.source == self.target:
            raise ValueError("self edges are not allowed")


@dataclass
class IntentGraph:
    run_id: str
    suite: str
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    schema_version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("graph node ids must be unique")
        known = set(ids)
        adjacency: dict[str, list[str]] = {node_id: [] for node_id in known}
        for edge in self.edges:
            if edge.source not in known or edge.target not in known:
                raise ValueError(
                    f"edge references unknown node: {edge.source} -> {edge.target}"
                )
            adjacency[edge.source].append(edge.target)

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("intent graph contains a cycle")
            if node_id in visited:
                return
            visiting.add(node_id)
            for target in adjacency[node_id]:
                visit(target)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in known:
            visit(node_id)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "suite": self.suite,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [asdict(edge) for edge in self.edges],
        }
