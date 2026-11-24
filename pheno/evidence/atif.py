"""Evidence-grade integrity checks layered on canonical Harbor ATIF validation.

Harbor's ``Trajectory`` Pydantic model and ``TrajectoryValidator`` remain the
schema authority for ATIF.  This module intentionally does *not* duplicate
Harbor's field typing, timestamp, multimodal-content, or source-specific
validation.  It adds the closed-world invariants Pheno needs before a
trajectory can support scoreable evidence:

* every trajectory document has a stable, file-wide-unique ``trajectory_id``;
* embedded subagent references resolve to exactly one direct child and every
  embedded child is referenced exactly once; and
* tool calls and observation results form a step-local bijection.

Call Harbor validation first, then this overlay.  ``session_id`` is deliberately
never used as a resolution key: ATIF-v1.7 defines it as run-scoped, so parents,
siblings, and continuation documents may share it.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .contracts import ContractError

ATIF_SCHEMA_VERSION = "ATIF-v1.7"
MAX_EMBEDDED_DEPTH = 64


@dataclass(frozen=True)
class AtifIntegritySummary:
    """Counts proven by :func:`validate_atif_integrity`."""

    root_trajectory_id: str
    trajectory_count: int
    step_count: int
    tool_call_count: int
    correlated_tool_call_count: int
    embedded_subagent_count: int
    embedded_subagent_reference_count: int
    external_trajectory_reference_count: int

    @property
    def tool_observation_correlation(self) -> float:
        """Return one only after the validator has proved a full bijection."""

        return 1.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the ATIF integrity summary to a JSON-friendly dict."""
        return {
            "schema_version": ATIF_SCHEMA_VERSION,
            "root_trajectory_id": self.root_trajectory_id,
            "trajectory_count": self.trajectory_count,
            "step_count": self.step_count,
            "tool_call_count": self.tool_call_count,
            "correlated_tool_call_count": self.correlated_tool_call_count,
            "tool_observation_correlation": self.tool_observation_correlation,
            "embedded_subagent_count": self.embedded_subagent_count,
            "embedded_subagent_reference_count": (
                self.embedded_subagent_reference_count
            ),
            "external_trajectory_reference_count": (
                self.external_trajectory_reference_count
            ),
        }


@dataclass
class _Counts:
    trajectory_count: int = 0
    step_count: int = 0
    tool_call_count: int = 0
    correlated_tool_call_count: int = 0
    embedded_subagent_count: int = 0
    embedded_subagent_reference_count: int = 0
    external_trajectory_reference_count: int = 0


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{path} must be an object")
    return value


def _array(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{path} must be an array")
    return value


def _optional_array(root: Mapping[str, Any], field: str, path: str) -> list[Any]:
    value = root.get(field)
    if value is None:
        return []
    return _array(value, f"{path}.{field}")


def _nonempty_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{path} must be a non-empty string")
    return value


def _optional_nonempty_text(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _nonempty_text(value, path)


def _validate_step_correlation(
    step: Mapping[str, Any],
    *,
    path: str,
    trajectory_call_ids: set[str],
    embedded_reference_paths: dict[str, str],
    allow_external_references: bool,
    counts: _Counts,
) -> None:
    tool_calls = _optional_array(step, "tool_calls", path)
    call_paths: dict[str, str] = {}
    for index, raw_call in enumerate(tool_calls):
        call_path = f"{path}.tool_calls[{index}]"
        call = _object(raw_call, call_path)
        call_id = _nonempty_text(call.get("tool_call_id"), f"{call_path}.tool_call_id")
        if call_id in call_paths:
            raise ContractError(
                f"{call_path}.tool_call_id duplicates {call_paths[call_id]}: {call_id!r}"
            )
        if call_id in trajectory_call_ids:
            raise ContractError(
                f"{call_path}.tool_call_id is not unique within the trajectory: "
                f"{call_id!r}"
            )
        call_paths[call_id] = f"{call_path}.tool_call_id"
        trajectory_call_ids.add(call_id)

    observation_value = step.get("observation")
    if observation_value is None:
        results: list[Any] = []
    else:
        observation = _object(observation_value, f"{path}.observation")
        results = _array(observation.get("results"), f"{path}.observation.results")

    result_call_ids: list[str] = []
    for index, raw_result in enumerate(results):
        result_path = f"{path}.observation.results[{index}]"
        result = _object(raw_result, result_path)
        source_call_id = _optional_nonempty_text(
            result.get("source_call_id"), f"{result_path}.source_call_id"
        )
        if source_call_id is not None:
            if source_call_id not in call_paths:
                raise ContractError(
                    f"{result_path}.source_call_id {source_call_id!r} does not "
                    "reference a tool call in the same step"
                )
            result_call_ids.append(source_call_id)

        refs = _optional_array(result, "subagent_trajectory_ref", result_path)
        for ref_index, raw_ref in enumerate(refs):
            ref_path = f"{result_path}.subagent_trajectory_ref[{ref_index}]"
            ref = _object(raw_ref, ref_path)
            trajectory_id = _optional_nonempty_text(
                ref.get("trajectory_id"), f"{ref_path}.trajectory_id"
            )
            trajectory_path = _optional_nonempty_text(
                ref.get("trajectory_path"), f"{ref_path}.trajectory_path"
            )
            if trajectory_id is None and trajectory_path is None:
                raise ContractError(
                    f"{ref_path} must set trajectory_id or trajectory_path; "
                    "session_id is informational only"
                )
            if trajectory_id is not None:
                if trajectory_id in embedded_reference_paths:
                    raise ContractError(
                        f"{ref_path}.trajectory_id duplicates reference at "
                        f"{embedded_reference_paths[trajectory_id]}: "
                        f"{trajectory_id!r}"
                    )
                embedded_reference_paths[trajectory_id] = f"{ref_path}.trajectory_id"
                counts.embedded_subagent_reference_count += 1
            else:
                counts.external_trajectory_reference_count += 1
                if not allow_external_references:
                    raise ContractError(
                        f"{ref_path}.trajectory_path is external and cannot be "
                        "validated as a closed offline artifact"
                    )

    result_counts = Counter(result_call_ids)
    duplicated_results = sorted(
        call_id for call_id, count in result_counts.items() if count != 1
    )
    if duplicated_results:
        raise ContractError(
            f"{path}.observation has multiple results for tool calls: "
            f"{duplicated_results}"
        )
    missing_results = sorted(set(call_paths) - set(result_counts))
    if missing_results:
        raise ContractError(
            f"{path}.tool_calls have no correlated observation result: "
            f"{missing_results}"
        )

    counts.tool_call_count += len(call_paths)
    counts.correlated_tool_call_count += len(result_counts)


def _validate_trajectory(
    raw_trajectory: Any,
    *,
    path: str,
    depth: int,
    all_trajectory_ids: dict[str, str],
    allow_external_references: bool,
    counts: _Counts,
) -> None:
    if depth > MAX_EMBEDDED_DEPTH:
        raise ContractError(
            f"{path} exceeds maximum embedded trajectory depth {MAX_EMBEDDED_DEPTH}"
        )
    trajectory = _object(raw_trajectory, path)
    if trajectory.get("schema_version") != ATIF_SCHEMA_VERSION:
        raise ContractError(
            f"{path}.schema_version must be exactly {ATIF_SCHEMA_VERSION}"
        )
    trajectory_id = _nonempty_text(
        trajectory.get("trajectory_id"), f"{path}.trajectory_id"
    )
    if trajectory_id in all_trajectory_ids:
        raise ContractError(
            f"{path}.trajectory_id duplicates {all_trajectory_ids[trajectory_id]}: "
            f"{trajectory_id!r}"
        )
    all_trajectory_ids[trajectory_id] = f"{path}.trajectory_id"
    counts.trajectory_count += 1

    steps = _array(trajectory.get("steps"), f"{path}.steps")
    counts.step_count += len(steps)
    trajectory_call_ids: set[str] = set()
    embedded_reference_paths: dict[str, str] = {}
    for index, raw_step in enumerate(steps):
        step_path = f"{path}.steps[{index}]"
        step = _object(raw_step, step_path)
        _validate_step_correlation(
            step,
            path=step_path,
            trajectory_call_ids=trajectory_call_ids,
            embedded_reference_paths=embedded_reference_paths,
            allow_external_references=allow_external_references,
            counts=counts,
        )

    children = _optional_array(trajectory, "subagent_trajectories", path)
    child_ids: dict[str, str] = {}
    for index, raw_child in enumerate(children):
        child_path = f"{path}.subagent_trajectories[{index}]"
        child = _object(raw_child, child_path)
        child_id = _nonempty_text(
            child.get("trajectory_id"), f"{child_path}.trajectory_id"
        )
        if child_id in child_ids:
            raise ContractError(
                f"{child_path}.trajectory_id duplicates {child_ids[child_id]}: "
                f"{child_id!r}"
            )
        child_ids[child_id] = f"{child_path}.trajectory_id"

    dangling_refs = sorted(set(embedded_reference_paths) - set(child_ids))
    if dangling_refs:
        raise ContractError(
            f"{path} has embedded subagent references with no direct child: "
            f"{dangling_refs}"
        )
    orphan_children = sorted(set(child_ids) - set(embedded_reference_paths))
    if orphan_children:
        raise ContractError(
            f"{path}.subagent_trajectories contains unreferenced children: "
            f"{orphan_children}"
        )

    counts.embedded_subagent_count += len(children)
    for index, child in enumerate(children):
        _validate_trajectory(
            child,
            path=f"{path}.subagent_trajectories[{index}]",
            depth=depth + 1,
            all_trajectory_ids=all_trajectory_ids,
            allow_external_references=allow_external_references,
            counts=counts,
        )

    continuation = _optional_nonempty_text(
        trajectory.get("continued_trajectory_ref"),
        f"{path}.continued_trajectory_ref",
    )
    if continuation is not None:
        counts.external_trajectory_reference_count += 1
        if not allow_external_references:
            raise ContractError(
                f"{path}.continued_trajectory_ref is external and cannot be "
                "validated as a closed offline artifact"
            )


def validate_atif_integrity(
    trajectory: Mapping[str, Any],
    *,
    allow_external_references: bool = False,
) -> AtifIntegritySummary:
    """Validate Pheno's ATIF-v1.7 evidence invariants.

    Harbor validation MUST run before this function.  By default all delegated
    and continuation trajectories must be embedded in the supplied JSON so the
    artifact is closed and can be hashed as one unit.  Setting
    ``allow_external_references`` accepts file/URL references but only counts
    them; callers must separately resolve, validate, and hash those targets
    before treating the result as scoreable.
    """

    root = _object(trajectory, "trajectory")
    counts = _Counts()
    _validate_trajectory(
        root,
        path="trajectory",
        depth=0,
        all_trajectory_ids={},
        allow_external_references=allow_external_references,
        counts=counts,
    )
    return AtifIntegritySummary(
        root_trajectory_id=_nonempty_text(
            root.get("trajectory_id"), "trajectory.trajectory_id"
        ),
        trajectory_count=counts.trajectory_count,
        step_count=counts.step_count,
        tool_call_count=counts.tool_call_count,
        correlated_tool_call_count=counts.correlated_tool_call_count,
        embedded_subagent_count=counts.embedded_subagent_count,
        embedded_subagent_reference_count=(counts.embedded_subagent_reference_count),
        external_trajectory_reference_count=(
            counts.external_trajectory_reference_count
        ),
    )


__all__ = [
    "ATIF_SCHEMA_VERSION",
    "AtifIntegritySummary",
    "MAX_EMBEDDED_DEPTH",
    "validate_atif_integrity",
]
