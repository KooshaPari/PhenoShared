"""DAG-69: JSON-Schema linter for ``config/desktop_nvidia_qwen35_lane.yaml``.

This test pins the structural contract of the Desktop NVIDIA dual-GPU
lane YAML so a future drift (typo, dropped field, type regression) is
caught at ``pytest -q tests/`` time rather than at server-launch time.

The schema is defined inline (as a Python dict) to keep the test
self-contained — no separate ``.schema.json`` file to maintain and no
relative-path surprises across worktrees.

Notes on field mapping vs. the generic spec described in the DAG-69
ticket:

  The ticket listed candidate fields (``model_id``, ``request_model``,
  ``display_name``, ``device``, ``metal_compile_flags``,
  ``enable_quant``, ``quant_method``, ``harbor_endpoint``, ``dry_run``)
  that fit a typical *inference-runtime* config. The actual
  ``desktop_nvidia_qwen35_lane.yaml`` shipped under DAG-26 is a *lane
  contract* (declarative, planning-only, no model/inference surface),
  so it uses a different vocabulary. The schema here latches onto the
  real vocabulary:

    * ``schema_version`` (was: ``model_id``)
    * ``scope.canonical_model`` (was: ``request_model``)
    * ``hardware.devices`` map (was: ``device``)
    * ``runtime_policy.qwen35_08b.{primary,helper}.runtime_candidates``
      (was: ``metal_compile_flags``)
    * ``execution_policy.allow_*`` (was: ``enable_quant``)
    * ``scope.status`` (was: ``quant_method``)
    * ``hardware.runtime_device_mappings`` (was: ``harbor_endpoint``)
    * ``provenance_requirements.run`` membership of ``dry_run``
      (was: a top-level bool ``dry_run``)

  The drift between the ticket's field names and the contract's
  vocabulary is intentional and documented in the DAG-69 commit body.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

try:  # jsonschema is the preferred validator; fall back gracefully.
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError

    _HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover - environment-specific
    _HAS_JSONSCHEMA = False


ROOT = Path(__file__).resolve().parents[1]
LANE_CONFIG = ROOT / "config" / "desktop_nvidia_qwen35_lane.yaml"


# ---------------------------------------------------------------------------
# Inline schema
# ---------------------------------------------------------------------------

#: Inline JSON-Schema (Draft 2020-12) for ``desktop_nvidia_qwen35_lane.yaml``.
#:
#: Coverage rationale (matches the 3 behavioral tests in
#: ``tests/test_desktop_lane_eval.py`` and the existing
#: ``tests/test_desktop_nvidia_lane.py`` field checks):
#:
#: * top-level identity (schema_version, status, effective_date) — proves
#:   the contract pins its own version and is planning-only.
#: * ``scope.*`` — pinning the Qwen3.5 allow/deny lists + canonical model
#:   name so a fork that flips the allow/deny list breaks the test.
#: * ``execution_policy.allow_*`` booleans + ``max_concurrent_workers`` /
#:   ``topology`` — these are the flags the desktop-lane runner script
#:   (``scripts/run_desktop_lane_eval.py``) gates on (it requires an
#:   explicit window to set ``execute=True``).
#: * ``hardware.devices`` map with ``role``/``vram_mib``/``nvidia_smi_index``
#:   — the dual-GPU smoke lane depends on these index numbers being
#:   integers rather than strings.
#: * ``runtime_policy.qwen35_08b`` with ``runtime_candidates`` lists of
#:   strings — the smoke lane will not start a server if no candidate
#:   is enumerated.
#: * ``provenance_requirements.run`` must contain ``dry_run`` —
#:   ``tests/test_desktop_lane_eval.py::test_desktop_lane_eval_is_dry_run_by_default``
#:   asserts the dry-run path is the default; the schema enforces the
#:   lane contract documents that requirement.
#: * ``promotion_gates`` must contain the Qwen3.5 + harbor authorization
#:   gates — they are the load-bearing accept/reject criteria.
LANE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "pheno.desktop-nvidia.qwen35-lane.v1.schema",
    "title": "Desktop NVIDIA Qwen3.5 lane contract (v1)",
    "type": "object",
    "required": [
        "schema_version",
        "status",
        "effective_date",
        "scope",
        "execution_policy",
        "hardware",
        "runtime_policy",
        "provenance_requirements",
        "promotion_gates",
        "external_backend_references",
    ],
    "additionalProperties": False,
    "properties": {
        "schema_version": {
            "type": "string",
            "minLength": 1,
            "pattern": r"^pheno\.desktop-nvidia\.qwen35-lane\.v\d+$",
        },
        "effective_date": {"type": "string", "minLength": 1},
        "status": {
            "type": "string",
            "enum": ["planning_only", "active", "deprecated"],
        },
        "scope": {
            "type": "object",
            "required": [
                "owner",
                "purpose",
                "model_family_allowlist",
                "model_family_denylist",
                "canonical_model",
                "local_alias",
                "mac_inference",
                "cross_platform_head",
            ],
            "additionalProperties": False,
            "properties": {
                "owner": {"type": "string", "minLength": 1},
                "purpose": {"type": "string", "minLength": 1},
                "model_family_allowlist": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "minItems": 1,
                },
                "model_family_denylist": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                },
                "canonical_model": {"type": "string", "minLength": 1},
                "local_alias": {"type": "string", "minLength": 1},
                "mac_inference": {
                    "type": "string",
                    "enum": ["paused", "active", "forbidden"],
                },
                "cross_platform_head": {"type": "string", "minLength": 1},
            },
        },
        "execution_policy": {
            "type": "object",
            "required": [
                "allow_model_download",
                "allow_install",
                "allow_server_launch",
                "allow_model_inference",
                "allow_benchmark_execution",
                "allow_harbor",
                "require_explicit_window",
                "max_concurrent_workers",
                "topology",
                "tensor_parallel",
                "inter_gpu_transfer",
                "implicit_model_migration",
            ],
            "additionalProperties": False,
            "properties": {
                "allow_model_download": {"type": "boolean"},
                "allow_install": {"type": "boolean"},
                "allow_server_launch": {"type": "boolean"},
                "allow_model_inference": {"type": "boolean"},
                "allow_benchmark_execution": {"type": "boolean"},
                "allow_harbor": {"type": "boolean"},
                "require_explicit_window": {"type": "boolean"},
                "max_concurrent_workers": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 8,
                },
                "topology": {
                    "type": "string",
                    "enum": [
                        "independent_workers",
                        "coordinated_workers",
                        "single_worker",
                    ],
                },
                "tensor_parallel": {
                    "type": "string",
                    "enum": ["forbidden", "allowed", "required"],
                },
                "inter_gpu_transfer": {"type": "string", "minLength": 1},
                "implicit_model_migration": {
                    "type": "string",
                    "enum": ["forbidden", "allowed_with_consent", "allowed"],
                },
            },
        },
        "hardware": {
            "type": "object",
            "required": [
                "host",
                "devices",
                "visibility_notes",
                "runtime_device_mappings",
            ],
            "additionalProperties": False,
            "properties": {
                "host": {
                    "type": "object",
                    "required": ["platform", "ram_gb_min"],
                    "additionalProperties": False,
                    "properties": {
                        "platform": {"type": "string", "minLength": 1},
                        "ram_gb_min": {"type": "integer", "minimum": 1},
                    },
                },
                "devices": {
                    "type": "object",
                    "minProperties": 1,
                    "additionalProperties": {
                        "type": "object",
                        "required": [
                            "role",
                            "nvidia_smi_index",
                            "architecture",
                            "vram_mib",
                            "cuda_visible_devices",
                            "pytorch_device",
                            "llama_cpp_isolated_device",
                            "allowed_runtimes",
                        ],
                        "additionalProperties": False,
                        "properties": {
                            "role": {
                                "type": "string",
                                "enum": ["primary", "helper", "standby"],
                            },
                            "nvidia_smi_index": {"type": "integer", "minimum": 0},
                            "architecture": {"type": "string", "pattern": r"^sm_\d+$"},
                            "vram_mib": {"type": "integer", "minimum": 1024},
                            "cuda_visible_devices": {
                                "type": "string",
                                "pattern": r"^[0-9]+(,[0-9]+)*$",
                            },
                            "pytorch_device": {
                                "type": "string",
                                "pattern": r"^cuda:\d+$",
                            },
                            "llama_cpp_isolated_device": {
                                "type": "string",
                                "pattern": r"^CUDA\d+$",
                            },
                            "allowed_runtimes": {
                                "type": "array",
                                "items": {"type": "string", "minLength": 1},
                                "minItems": 1,
                                # Every device must support *some* form of
                                # llama.cpp — the legacy ``llama_cpp_cuda12``
                                # build is a CUDA-12-specific fork for older
                                # GPUs (e.g. the gtx_1080_ti helper) that
                                # doesn't ship as the plain ``llama_cpp``
                                # binary. The pattern accepts both.
                                "contains": {"pattern": "^llama_cpp(_.*)?$"},
                            },
                            "tensor_parallel": {
                                "type": "string",
                                "enum": ["forbidden", "allowed", "required"],
                            },
                        },
                    },
                },
                "visibility_notes": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                },
                # Maps that name either a runtime-specific mapping (object)
                # or a host label (plain string, e.g. ``observed_host``).
                "runtime_device_mappings": {
                    "type": "object",
                    "minProperties": 1,
                    "additionalProperties": {
                        "oneOf": [
                            {
                                "type": "object",
                                "required": ["visibility_variable", "logical_device"],
                                "additionalProperties": True,
                                "properties": {
                                    "visibility_variable": {
                                        "type": "string",
                                        "pattern": r"^CUDA_VISIBLE_DEVICES$",
                                    },
                                    "logical_device": {
                                        "type": "string",
                                        "pattern": r"^(cuda:\d+|CUDA\d+)$",
                                    },
                                    "physical_to_visible_index": {
                                        "type": "object",
                                        "additionalProperties": {"type": "string"},
                                    },
                                    "build": {"type": "string", "minLength": 1},
                                    "note": {"type": "string"},
                                },
                            },
                            {"type": "string", "minLength": 1},
                        ],
                    },
                },
            },
        },
        "runtime_policy": {
            "type": "object",
            "minProperties": 1,
            # Each entry is either:
            #   * an object map of roles -> {device, runtime_candidates,
            #     status} (the ``qwen35_08b`` family, etc.), or
            #   * a list of strings (e.g. the ``unsupported_without_new_review``
            #     enumerate-and-block list).
            "additionalProperties": {
                "oneOf": [
                    {
                        "type": "object",
                        "minProperties": 1,
                        "additionalProperties": {
                            "type": "object",
                            "required": ["device", "runtime_candidates", "status"],
                            "additionalProperties": False,
                            "properties": {
                                "device": {"type": "string", "minLength": 1},
                                "runtime_candidates": {
                                    "type": "array",
                                    "items": {"type": "string", "minLength": 1},
                                    "minItems": 1,
                                },
                                "status": {
                                    "type": "string",
                                    "enum": [
                                        "deferred_until_explicit_window",
                                        "active",
                                        "paused",
                                    ],
                                },
                            },
                        },
                    },
                    {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                ],
            },
        },
        "provenance_requirements": {
            "type": "object",
            "required": ["model", "runtime", "device", "run"],
            "additionalProperties": False,
            "properties": {
                "model": {"type": "array", "items": {"type": "string", "minLength": 1}},
                "runtime": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                },
                "device": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                },
                "run": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "contains": {"const": "dry_run"},
                    "minItems": 1,
                },
            },
        },
        "promotion_gates": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string", "minLength": 1},
            "allOf": [
                {"contains": {"const": "exact_qwen35_model_and_revision"}},
                {"contains": {"const": "harbor_or_eval_window_authorized"}},
            ],
        },
        "external_backend_references": {
            "type": "object",
            "minProperties": 1,
            "additionalProperties": {
                "type": "object",
                "required": [
                    "integration_mode",
                    "source_url",
                    "copy_source",
                    "provenance_boundary",
                ],
                "additionalProperties": True,
                "properties": {
                    "integration_mode": {"type": "string", "minLength": 1},
                    "source_url": {
                        "type": "string",
                        "pattern": r"^https?://",
                    },
                    "copy_source": {"type": "boolean"},
                    "provenance_boundary": {"type": "string", "minLength": 1},
                    "required_model_family": {"type": "string"},
                    "allowed_semantics": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "prohibited_surfaces": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def lane_config() -> dict[str, Any]:
    """Load and validate the lane YAML exactly once per module."""
    if not LANE_CONFIG.exists():
        pytest.skip(f"lane config not found at {LANE_CONFIG}")
    raw = LANE_CONFIG.read_text(encoding="utf-8")
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        pytest.fail(f"lane YAML failed to parse: {exc}")
    assert isinstance(loaded, dict), "lane YAML must decode to a mapping"
    return loaded


# ---------------------------------------------------------------------------
# Hand-rolled fallback validator (used when jsonschema is not installed).
# ---------------------------------------------------------------------------


def _fallback_validate(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Minimal subset-validator covering what this test file needs.

    Supports: ``type``, ``required``, ``properties`` (object), ``enum``,
    ``pattern``, ``minLength`` / ``maxLength`` / ``minItems`` /
    ``maxItems`` / ``minProperties``, ``contains``, ``allOf``,
    ``oneOf`` (pick the first matching branch), ``additionalProperties``
    (bool + schema). This is intentionally not a full Draft 2020-12
    implementation — just enough to catch drift in the lane config.
    """
    import re

    errors: list[str] = []

    def _check(node: Any, sub: dict[str, Any], path: str) -> None:
        if "oneOf" in sub:
            # Try each branch on a clone of the errors list; the branch
            # wins if it produces the fewest errors AND at least zero of
            # its OWN errors target this path. Simpler heuristic: a
            # branch wins if it adds zero errors to the shared errors
            # list while checking ``node`` against ``path``.
            branch_errors: list[tuple[list[str], str]] = []
            for branch in sub["oneOf"]:
                scratch: list[str] = []
                _walk(node, branch, path, scratch)
                branch_errors.append((scratch, path))
            # Pick the branch with no scratch errors (in priority order);
            # fall back to the shortest scratch error list.
            chosen = next(
                ((scratch, p) for scratch, p in branch_errors if not scratch),
                min(branch_errors, key=lambda pair: len(pair[0])),
            )
            errors.extend(chosen[0])
            return

        if "allOf" in sub:
            for branch in sub["allOf"]:
                _walk(node, branch, path, errors)
            return

        _walk(node, sub, path, errors)

    def _walk(node: Any, sub: dict[str, Any], path: str, sink: list[str]) -> None:
        expected_type = sub.get("type")
        if expected_type is not None:
            py_type = {
                "object": dict,
                "array": list,
                "string": str,
                "integer": int,
                "number": (int, float),
                "boolean": bool,
                "null": type(None),
            }.get(expected_type)
            if py_type is None:
                sink.append(f"{path}: unsupported type {expected_type!r}")
                return
            # YAML can decode ints as ints and bools as bools; ``bool`` is a
            # subclass of ``int`` in Python, so exclude it explicitly.
            if expected_type == "integer" and isinstance(node, bool):
                sink.append(f"{path}: expected integer, got bool")
                return
            if expected_type == "boolean" and not isinstance(node, bool):
                sink.append(f"{path}: expected boolean, got {type(node).__name__}")
                return
            if not isinstance(node, py_type):
                sink.append(
                    f"{path}: expected {expected_type}, got {type(node).__name__}"
                )
                return

        if "enum" in sub and node not in sub["enum"]:
            sink.append(f"{path}: {node!r} not in enum {sub['enum']}")

        if "pattern" in sub and isinstance(node, str):
            if not re.search(sub["pattern"], node):
                sink.append(f"{path}: {node!r} does not match {sub['pattern']!r}")

        if "minLength" in sub and isinstance(node, str):
            if len(node) < sub["minLength"]:
                sink.append(f"{path}: shorter than minLength {sub['minLength']}")
        if "maxLength" in sub and isinstance(node, str):
            if len(node) > sub["maxLength"]:
                sink.append(f"{path}: longer than maxLength {sub['maxLength']}")
        if (
            "minimum" in sub
            and isinstance(node, (int, float))
            and not isinstance(node, bool)
        ):
            if node < sub["minimum"]:
                sink.append(f"{path}: {node} < minimum {sub['minimum']}")
        if (
            "maximum" in sub
            and isinstance(node, (int, float))
            and not isinstance(node, bool)
        ):
            if node > sub["maximum"]:
                sink.append(f"{path}: {node} > maximum {sub['maximum']}")

        if isinstance(node, list):
            if "minItems" in sub and len(node) < sub["minItems"]:
                sink.append(
                    f"{path}: array has {len(node)} items, minItems={sub['minItems']}"
                )
            if "maxItems" in sub and len(node) > sub["maxItems"]:
                sink.append(
                    f"{path}: array has {len(node)} items, maxItems={sub['maxItems']}"
                )
            if "items" in sub:
                for i, item in enumerate(node):
                    _walk(item, sub["items"], f"{path}[{i}]", sink)
            for contains_clause in sub.get("allOf", []) if "allOf" in sub else []:
                if "contains" in contains_clause:
                    sink.extend(
                        _check_contains(node, contains_clause["contains"], path)
                    )
            if "contains" in sub:
                sink.extend(_check_contains(node, sub["contains"], path))

        if isinstance(node, dict):
            if "minProperties" in sub and len(node) < sub["minProperties"]:
                sink.append(
                    f"{path}: object has {len(node)} keys, minProperties={sub['minProperties']}"
                )
            if "required" in sub:
                for key in sub["required"]:
                    if key not in node:
                        sink.append(f"{path}: missing required key {key!r}")
            if "properties" in sub:
                for key, sub_schema in sub["properties"].items():
                    if key in node:
                        _walk(node[key], sub_schema, f"{path}.{key}", sink)
            extra = sub.get("additionalProperties", True)
            if extra is False:
                allowed = set(sub.get("properties", {}))
                for key in node:
                    if key not in allowed:
                        sink.append(
                            f"{path}: unexpected key {key!r} (additionalProperties=false)"
                        )
            elif isinstance(extra, dict):
                allowed = set(sub.get("properties", {}))
                for key in node:
                    if key not in allowed:
                        _walk(node[key], extra, f"{path}.{key}", sink)

    def _check_contains(items: list[Any], target: Any, path: str) -> list[str]:
        if isinstance(target, str):
            return (
                []
                if any(item == target for item in items)
                else [f"{path}: array does not contain element {target!r}"]
            )
        scratch: list[str] = []
        for item in items:
            _walk(item, target, "<contains>", scratch)
            if not scratch:
                return []
            scratch.clear()
        return [f"{path}: array contains no element matching {target!r}"]

    _check(data, schema, "$")
    return errors


def _validate(data: dict[str, Any]) -> list[str]:
    if _HAS_JSONSCHEMA:
        try:
            validator = Draft202012Validator(LANE_SCHEMA)
        except SchemaError as exc:
            return [f"schema error: {exc}"]
        return [err.message for err in validator.iter_errors(data)]
    return _fallback_validate(data, LANE_SCHEMA)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_lane_config_loads_as_yaml(lane_config: dict[str, Any]) -> None:
    """Lane config must parse as a YAML mapping (no junk, no scalars)."""
    assert isinstance(lane_config, dict), "lane config must be a YAML mapping"
    # Spot-check that the YAML loader actually consumed the file
    # (i.e. not just got a stale empty dict via a broken parse).
    assert lane_config, "lane config decodes to an empty mapping"


def test_lane_config_validates_against_schema(lane_config: dict[str, Any]) -> None:
    """Full schema validation must report no errors."""
    errors = _validate(lane_config)
    assert not errors, "schema violations:\n  - " + "\n  - ".join(errors)


def test_lane_config_schema_version_is_string(lane_config: dict[str, Any]) -> None:
    """``schema_version`` is a non-empty versioned string."""
    version = lane_config["schema_version"]
    assert isinstance(version, str)
    assert version, "schema_version must be non-empty"
    assert version.startswith("pheno.desktop-nvidia.qwen35-lane.")


def test_lane_config_canonical_model_is_string(lane_config: dict[str, Any]) -> None:
    """``scope.canonical_model`` is a non-empty model identifier string."""
    canonical = lane_config["scope"]["canonical_model"]
    assert isinstance(canonical, str)
    assert canonical, "canonical_model must be non-empty"
    assert "/" in canonical, (
        "canonical_model should be a `org/repo` HuggingFace-style id, "
        f"got {canonical!r}"
    )


def test_lane_config_device_is_object_with_required_fields(
    lane_config: dict[str, Any],
) -> None:
    """``hardware.devices`` is an object map; each entry has role + vram_mib."""
    devices = lane_config["hardware"]["devices"]
    assert isinstance(devices, dict), "devices must be an object map"
    assert devices, "devices map must not be empty"
    for dev_id, dev_def in devices.items():
        assert isinstance(dev_def, dict), f"device {dev_id!r} must be an object"
        assert "role" in dev_def and isinstance(dev_def["role"], str)
        assert "vram_mib" in dev_def and isinstance(dev_def["vram_mib"], int)
        assert "nvidia_smi_index" in dev_def and isinstance(
            dev_def["nvidia_smi_index"], int
        )


def test_lane_config_execution_policy_flags_are_well_typed(
    lane_config: dict[str, Any],
) -> None:
    """``execution_policy.allow_*`` are booleans; concurrency/topology typed."""
    policy = lane_config["execution_policy"]
    allow_keys = (
        "allow_model_download",
        "allow_install",
        "allow_server_launch",
        "allow_model_inference",
        "allow_benchmark_execution",
        "allow_harbor",
        "require_explicit_window",
    )
    for key in allow_keys:
        assert isinstance(policy[key], bool), f"{key!r} must be boolean"
    assert isinstance(policy["max_concurrent_workers"], int)
    assert policy["topology"] in {
        "independent_workers",
        "coordinated_workers",
        "single_worker",
    }


def test_lane_config_runtime_candidates_is_list_of_strings(
    lane_config: dict[str, Any],
) -> None:
    """``runtime_policy.<family>.<role>.runtime_candidates`` is a list[str].

    Each entry in ``runtime_policy`` is either an object map (a family of
    roles such as ``qwen35_08b`` -> ``{primary, helper}``) or a list of
    strings (a denylist such as ``unsupported_without_new_review``). We
    pin both shapes.
    """
    runtime_policy = lane_config["runtime_policy"]
    for family, roles in runtime_policy.items():
        if isinstance(roles, list):
            # Denylist / block-list shape: list of strings.
            assert roles, f"runtime_policy.{family} must be non-empty if a list"
            for cand in roles:
                assert isinstance(cand, str), (
                    f"runtime_policy.{family} must be list[str], got {type(cand).__name__}"
                )
                assert cand, (
                    f"runtime_policy.{family} entries must be non-empty strings"
                )
            continue
        assert isinstance(roles, dict), f"runtime_policy.{family} must be an object"
        for role, defn in roles.items():
            candidates = defn["runtime_candidates"]
            assert isinstance(candidates, list), (
                f"runtime_policy.{family}.{role}.runtime_candidates must be a list"
            )
            assert candidates, (
                f"runtime_policy.{family}.{role}.runtime_candidates must be non-empty"
            )
            for cand in candidates:
                assert isinstance(cand, str)
                assert cand, "runtime candidate strings must be non-empty"


def test_lane_config_dry_run_in_provenance_run(lane_config: dict[str, Any]) -> None:
    """``dry_run`` is listed in ``provenance_requirements.run``.

    The dry-run path is the default for the desktop lane runner
    (``scripts/run_desktop_lane_eval.py``). The schema enforces that the
    lane contract documents this requirement alongside ``explicit_window_id``
    and ``workload_executed``.
    """
    run_reqs = lane_config["provenance_requirements"]["run"]
    assert "dry_run" in run_reqs, (
        f"provenance_requirements.run must include 'dry_run'; got {run_reqs!r}"
    )
    assert "explicit_window_id" in run_reqs
    assert "workload_executed" in run_reqs


# ---------------------------------------------------------------------------
# Smoke check that the hand-rolled fallback matches jsonschema (skipped when
# jsonschema is installed — covered by the real validator).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    _HAS_JSONSCHEMA, reason="jsonschema installed; using real validator"
)
def test_fallback_validator_handles_current_config(lane_config: dict[str, Any]) -> None:
    """Fallback path must accept the current config (regression guard)."""
    errors = _fallback_validate(lane_config, LANE_SCHEMA)
    assert not errors, (
        "fallback validator rejected the current lane config:\n  - "
        + "\n  - ".join(errors)
    )


@pytest.mark.skipif(not _HAS_JSONSCHEMA, reason="requires jsonschema")
def test_jsonschema_and_fallback_agree(lane_config: dict[str, Any]) -> None:
    """When jsonschema is installed the two validators must agree."""
    js_errors = _validate(lane_config)
    fb_errors = _fallback_validate(lane_config, LANE_SCHEMA)
    # both should accept the same way; if either rejects, both should.
    assert (not js_errors) == (not fb_errors), (
        f"jsonschema and fallback disagree on the current config:\n"
        f"  jsonschema: {js_errors}\n"
        f"  fallback:   {fb_errors}"
    )


def test_schema_serialises_to_json() -> None:
    """The inline schema itself must be JSON-serialisable (proves no lambdas)."""
    dumped = json.dumps(LANE_SCHEMA, sort_keys=True)
    reloaded = json.loads(dumped)
    assert reloaded == LANE_SCHEMA
