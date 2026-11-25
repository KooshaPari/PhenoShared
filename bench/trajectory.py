"""Trajectory readers for ATIF v1.7 + CTRF JSONL producing a unified RunRecord."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class RecordFormat(StrEnum):
    """Source on-disk format."""

    ATIF = "atif"
    CTRF = "ctrf"
    UNIFIED = "unified"


class StepRole(StrEnum):
    """Role of a trajectory step (user, assistant, tool, system, observation)."""

    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"
    OBSERVATION = "observation"


@dataclass
class ToolCall:
    """One tool/function invocation inside a step."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        return asdict(self)


@dataclass
class Step:
    """One ordered event in a model trajectory."""

    step_id: int
    role: StepRole
    content: str
    timestamp: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    observation: str = ""
    latency_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        return {
            "step_id": self.step_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "tool_calls": [c.to_dict() for c in self.tool_calls],
            "observation": self.observation,
            "latency_ms": self.latency_ms,
        }


@dataclass
class RunRecord:
    """Trajectory record unified across ATIF and CTRF inputs."""

    record_id: str
    source_format: RecordFormat
    suite: str
    task_id: str
    agent: str
    model: str
    started_at: str
    stopped_at: str
    steps: list[Step] = field(default_factory=list)
    status: str = "unknown"
    reward: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        return {
            "record_id": self.record_id,
            "source_format": self.source_format.value,
            "suite": self.suite,
            "task_id": self.task_id,
            "agent": self.agent,
            "model": self.model,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status,
            "reward": self.reward,
            "extra": dict(self.extra),
        }

    def to_json(self) -> str:
        """Serialize to a single-line JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunRecord:
        """Inverse of `to_dict`."""
        steps_raw = data.get("steps", [])
        steps = [
            Step(
                step_id=int(s.get("step_id", i)),
                role=StepRole(s.get("role", "user"))
                if not isinstance(s.get("role"), StepRole)
                else s["role"],
                content=str(s.get("content", "")),
                timestamp=str(s.get("timestamp", "")),
                tool_calls=[
                    ToolCall(
                        name=c.get("name", ""),
                        arguments=dict(c.get("arguments", {})),
                        call_id=c.get("call_id", ""),
                    )
                    for c in s.get("tool_calls", [])
                ],
                observation=str(s.get("observation", "")),
                latency_ms=s.get("latency_ms"),
            )
            for i, s in enumerate(steps_raw)
        ]
        return cls(
            record_id=data.get("record_id", str(uuid.uuid4())),
            source_format=RecordFormat(data.get("source_format", "unified")),
            suite=str(data.get("suite", "")),
            task_id=str(data.get("task_id", "")),
            agent=str(data.get("agent", "")),
            model=str(data.get("model", "")),
            started_at=str(data.get("started_at", "")),
            stopped_at=str(data.get("stopped_at", "")),
            steps=steps,
            status=str(data.get("status", "unknown")),
            reward=data.get("reward"),
            extra=dict(data.get("extra", {})),
        )


# ---------------------------------------------------------------------------
# ATIF v1.7 reader (https://github.com/IBM/ATIF — Agent Trajectory Interchange Format)
# ---------------------------------------------------------------------------


def parse_atif(payload: dict[str, Any]) -> list[RunRecord]:
    """Parse an ATIF v1.7 document into a list of `RunRecord`s."""
    records: list[RunRecord] = []
    if "trajectories" not in payload:
        return records
    schema_version = str(payload.get("schema", "ATIF/1.7"))
    for idx, traj in enumerate(payload["trajectories"]):
        steps_in = traj.get("steps", [])
        steps: list[Step] = []
        for i, s in enumerate(steps_in):
            tool_calls_in = s.get("tool_calls") or s.get("toolCalls") or []
            tc = [
                ToolCall(
                    name=str(t.get("name", "")),
                    arguments=dict(t.get("arguments", t.get("args", {}))),
                    call_id=str(t.get("call_id", t.get("id", ""))),
                )
                for t in tool_calls_in
            ]
            steps.append(
                Step(
                    step_id=int(s.get("step_id", s.get("id", i))),
                    role=StepRole(s.get("role", "assistant")),
                    content=str(s.get("content", s.get("text", ""))),
                    timestamp=str(s.get("timestamp", "")),
                    tool_calls=tc,
                    observation=str(s.get("observation", "")),
                    latency_ms=s.get("latency_ms"),
                )
            )
        record_id = str(traj.get("session_id", traj.get("trajectory_id", uuid.uuid4())))
        records.append(
            RunRecord(
                record_id=record_id,
                source_format=RecordFormat.ATIF,
                suite=str(traj.get("suite", traj.get("benchmark", ""))),
                task_id=str(traj.get("task_id", "")),
                agent=str(traj.get("agent_name", traj.get("agent", ""))),
                model=str(traj.get("model", "")),
                started_at=str(traj.get("started_at", "")),
                stopped_at=str(traj.get("stopped_at", "")),
                steps=steps,
                status=str(traj.get("status", "unknown")),
                reward=traj.get("reward"),
                extra={"schema": schema_version, "index": idx},
            )
        )
    return records


def parse_ctrf(payload: dict[str, Any]) -> list[RunRecord]:
    """Parse a CTRF document into one RunRecord per `results` entry."""
    results_in = payload.get("results", [])
    suite_name = ""
    if results_in and isinstance(results_in[0], dict):
        suite_name = str(results_in[0].get("suite", ""))
    records: list[RunRecord] = []
    for idx, r in enumerate(results_in):
        steps_in = r.get("steps", []) or []
        steps: list[Step] = []
        for i, s in enumerate(steps_in):
            steps.append(
                Step(
                    step_id=int(s.get("step_id", i)),
                    role=StepRole(
                        s.get("role", "system")
                        if s.get("role") in StepRole.__members__
                        else "system"
                    ),
                    content=str(s.get("message", s.get("name", ""))),
                    timestamp=str(s.get("started", "")),
                    tool_calls=[],
                    observation=str(s.get("trace", "")),
                    latency_ms=(
                        float(s.get("duration", 0))
                        if s.get("duration") is not None
                        else None
                    ),
                )
            )
        record_id = str(r.get("name", uuid.uuid4()))
        records.append(
            RunRecord(
                record_id=record_id,
                source_format=RecordFormat.CTRF,
                suite=suite_name,
                task_id=str(r.get("name", "")),
                agent=str(payload.get("report", {}).get("testFramework", "")),
                model="",
                started_at=str(r.get("started", "")),
                stopped_at=str(r.get("stopped", "")),
                steps=steps,
                status=str(r.get("status", "unknown")),
                reward=None,
                extra={
                    "duration": r.get("duration"),
                    "message": r.get("message", ""),
                    "trace": r.get("trace", ""),
                    "index": idx,
                },
            )
        )
    return records


def detect_and_parse(payload: dict[str, Any]) -> list[RunRecord]:
    """Auto-detect format from a parsed JSON object and parse into RunRecord list."""
    if "results" in payload and isinstance(payload["results"], list):
        return parse_ctrf(payload)
    if "trajectories" in payload and isinstance(payload["trajectories"], list):
        return parse_atif(payload)
    return []


# ---------------------------------------------------------------------------
# JSONL readers / writers
# ---------------------------------------------------------------------------


def read_jsonl(path: str | Path) -> Iterator[RunRecord]:
    """Stream RunRecords from a JSONL file, each line is one record."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    with p.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            fmt = obj.get("source_format", "unified")
            if fmt == "atif":
                yield from parse_atif(obj)
            elif fmt == "ctrf":
                yield from parse_ctrf(obj)
            else:
                yield RunRecord.from_dict(obj)


def write_jsonl(records: Iterable[RunRecord], path: str | Path) -> int:
    """Write RunRecords as one JSON object per line; returns count written."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with p.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(rec.to_json() + "\n")
            count += 1
    return count


def read_atif_document(path: str | Path) -> list[RunRecord]:
    """Read one ATIF v1.7 JSON document and parse all trajectories."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    with p.open("r", encoding="utf-8") as fh:
        obj = json.load(fh)
    return parse_atif(obj)


def read_ctrf_document(path: str | Path) -> list[RunRecord]:
    """Read one CTRF JSON document and parse all results."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    with p.open("r", encoding="utf-8") as fh:
        obj = json.load(fh)
    return parse_ctrf(obj)
